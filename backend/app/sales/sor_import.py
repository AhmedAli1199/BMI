"""One-time import of BMI's SOR workbooks (2023-2026) into the Sales
Order Register tables. Run via scripts/import_sor.py.

The workbooks share one core layout - a summary block at the top
(MONTH, Exchange rate, Cumulative value...), then a two-row header
(Date | Client | Size | Series | Position | Salesper. | Rate US$ | £ |
Invoice number | Invoice value | Page number | Invoice difference |
Reason for difference | one commission column per rep) - with a few
per-title variations (events have tables/seats, awards have entries,
TBTM adds a Total column, Visit USA adds Planner/Online columns). So
columns are found by their *labels*, never their position.

What the importer deliberately does NOT do is guess: a date it can't
read, a value typed as "40, 0000", a salesperson code it doesn't know -
each is imported as-is with an `import_warning` the UI surfaces, so a
person fixes it once instead of the importer silently getting it wrong.

Duplicate files:
- "-Copy(1)" files (every 2023 workbook has one) are skipped.
- Visit USA Travel Planner ships as a pair each year: a working copy
  ("...2026.xls", with the rep's notes: "need po", "agency comm") and a
  reconciled "...edition.xls" (notes removed, every difference zeroed).
  Same bookings. The edition file is imported; the working copy's notes
  and pre-reconciliation invoice values are merged onto the matching
  rows so nothing is lost.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import SalesEdition, SalesOrder, SalesOrderCredit, SalesRep, SalesTitle
from app.sales.reference import ensure_reference_data, rep_code_for, title_for_file

logger = logging.getLogger("app.sales.sor_import")

Cell = str | float | datetime | None

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


# ---- Reading --------------------------------------------------------------

def read_workbook(path: Path) -> dict[str, list[list[Cell]]]:
    """Sheet name -> rows of plain Python values (str / float / datetime /
    None), for both legacy .xls (xlrd) and .xlsx (openpyxl)."""
    if path.suffix.lower() == ".xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        out = {}
        for ws in wb.worksheets:
            out[ws.title] = [[_clean(v) for v in row] for row in ws.iter_rows(values_only=True)]
        return out

    import xlrd

    book = xlrd.open_workbook(str(path))
    out = {}
    for sh in book.sheets():
        rows = []
        for r in range(sh.nrows):
            row = []
            for c in range(sh.ncols):
                cell = sh.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    try:
                        row.append(xlrd.xldate.xldate_as_datetime(cell.value, book.datemode))
                    except Exception:  # noqa: BLE001 - corrupt date cell, keep raw
                        row.append(cell.value)
                elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR):
                    row.append(None)
                else:
                    row.append(_clean(cell.value))
            rows.append(row)
        out[sh.name] = rows
    return out


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return float(v)
    return v


# ---- Value parsing --------------------------------------------------------

def parse_money(v: Cell) -> tuple[float | None, str | None]:
    """(value, warning). Numbers pass through; text like "£1,250" parses;
    anything ambiguous ("40, 0000") returns (None, warning)."""
    if v is None:
        return None, None
    if isinstance(v, float):
        return round(v, 2), None
    if isinstance(v, datetime):
        return None, f"expected an amount, found a date ({v:%d/%m/%Y})"
    s = str(v).replace("£", "").replace("$", "").strip()
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?|-?\d+(\.\d+)?", s):
        return round(float(s.replace(",", "")), 2), None
    if not re.search(r"\d", s):
        return None, None  # a word ("tbc", "FOC") - not a value, not worth a warning
    return None, f"couldn't read amount {s!r}"


def parse_date(v: Cell) -> tuple[date | None, str | None]:
    if v is None:
        return None, None
    if isinstance(v, datetime):
        return v.date(), None
    if isinstance(v, float):
        return None, None
    s = str(v).strip()
    m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{2}|\d{4})", s)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        y = y + 2000 if y < 100 else y
        try:
            return date(y, mo, d), None
        except ValueError:
            pass
    return None, f"couldn't read date {s!r}"


def parse_pages(size: str | None, product_line: str) -> float | None:
    """Page-equivalents for print sizes - what the sheet header's "Number
    pages booked" adds up. None for anything that isn't a page (banners,
    listings, event tickets)."""
    if not size or product_line not in ("print",):
        return None
    s = size.lower().replace("½", "1/2").strip()
    m = re.fullmatch(r"(\d+)\s*x\s*(\d+)/(\d+)(\s*page)?", s)
    if m:
        return int(m[1]) * int(m[2]) / int(m[3])
    m = re.fullmatch(r"(\d+(?:\.\d+)?)?\s*(fp|full page|page|dps)\b.*", s)
    if m:
        n = float(m[1]) if m[1] else 1.0
        return n * (2 if m[2] == "dps" else 1)
    m = re.fullmatch(r"(\d+)/(\d+)(\s*page)?", s)
    if m:
        return int(m[1]) / int(m[2])
    m = re.fullmatch(r"(\d+(?:\.\d+)?)", s)
    if m and float(m[1]) <= 10:
        return float(m[1])
    return None


def edition_date_for(year: int, sheet: str, period: Cell) -> date | None:
    if isinstance(period, datetime):
        return period.date()
    for text in (str(period or ""), sheet):
        m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", text.lower())
        if m:
            day = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)\b", text.lower())
            try:
                return date(year, MONTHS[m[1]], int(day[1]) if day else 1)
            except ValueError:
                return date(year, MONTHS[m[1]], 1)
    return None


def edition_kind(product_line: str, sheet: str, period: Cell) -> str:
    if product_line == "events":
        return "event"
    if product_line == "awards":
        return "awards"
    if product_line == "digital" or re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", sheet.lower()):
        return "month" if product_line == "digital" else "issue"
    return "issue"


# ---- Sheet parsing --------------------------------------------------------

def _norm(v: Cell) -> str:
    return re.sub(r"\s+", " ", str(v)).strip().lower() if v is not None else ""


@dataclass
class ParsedRow:
    row_index: int
    client: str
    cells: dict[str, Cell]
    rep_credits: dict[str, float]
    text: str
    continuation: bool = False
    raw: list = field(default_factory=list)
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedSheet:
    name: str
    period: Cell = None
    exchange_rate: float | None = None
    sheet_total: float | None = None
    rows: list[ParsedRow] = field(default_factory=list)


_COLS = {
    "date": ("date",),
    "size": ("size", "sponsor"),
    "series": ("series",),
    "position": ("position",),
    "rep": ("salesper.", "sales"),
    "usd": ("rate us$", "us$", "rate $", "rate"),
    "gbp": ("£",),
    "invoice_number": ("invoice number",),
    "invoice_value": ("invoice value",),
    "reason": ("reason for difference",),
}


def parse_sheet(name: str, rows: list[list[Cell]]) -> ParsedSheet | None:
    if re.search(r"template|do ?n.?t copy|^(blank|sheet)\s*\d*\b", name.strip(), re.IGNORECASE):
        return None  # the copy-from template and unused placeholder sheets
    hdr = next((i for i, r in enumerate(rows[:15]) if any(_norm(v).endswith("client") for v in r)), None)
    if hdr is None or hdr == 0:
        return None

    width = max(len(r) for r in rows[hdr - 1: hdr + 1])
    top = rows[hdr - 1] + [None] * width
    labels = [_norm(f"{top[i] or ''} {rows[hdr][i] if i < len(rows[hdr]) else ''}") for i in range(width)]
    col: dict[str, int] = {}
    client_col = next(i for i, lab in enumerate(labels) if lab.endswith("client"))
    for key, names in _COLS.items():
        for n in names:
            idx = next((i for i, lab in enumerate(labels) if lab == n and i not in col.values()), None)
            if idx is not None:
                col[key] = idx
                break
    if "gbp" not in col:
        return None  # an entries/attendee list (e.g. "IND Entries ALPHA"), not bookings

    # Commission columns: everything right of the reason/difference column
    # whose header is a known rep.
    start = max(col.get("reason", 0), col.get("invoice_value", 0)) + 1
    rep_cols = {i: rep_code_for(rows[hdr][i]) for i in range(start, len(rows[hdr]))
                if rows[hdr][i] is not None and rep_code_for(rows[hdr][i])}

    # Any other labelled column left of the commission block (Seats, Table
    # no., Paid?, Travel Planner / Online, Page number...) is kept as-is.
    # Running totals and the computed difference column are not data.
    def _pretty(i: int) -> str | None:
        # Headers span two rows ("Page" over "number", "Travel" over
        # "Planner"); join them, dropping a leading "Rate"/"Invoice" that
        # belongs to the neighbouring mapped column.
        parts = [v for v in (top[i], rows[hdr][i] if i < len(rows[hdr]) else None)
                 if isinstance(v, str) and v.strip() and not re.fullmatch(r"[\d.,\s]+", v)]
        label = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if len(parts) == 2:
            label = re.sub(r"^(rate|invoice)\s+", "", label, flags=re.IGNORECASE)
        return label or None
    used = set(col.values()) | {client_col}
    extra_cols = {}
    for i in range(start):
        label = _pretty(i) if i not in used else None
        if label and _norm(label) not in ("invoice difference", "difference", "total", "invoice", "rate", "number", "value"):
            extra_cols[i] = label

    parsed = ParsedSheet(name=name.strip())
    for r in rows[:hdr]:
        for i, v in enumerate(r):
            lab = _norm(v)
            nxt = next((x for x in r[i + 1:] if x is not None), None)
            if lab in ("month", "date") and parsed.period is None:
                # An empty MONTH cell must not pick up the next label along.
                if not (isinstance(nxt, str) and _norm(nxt) in ("exchange rate", "pages sold")) and not isinstance(nxt, float):
                    parsed.period = nxt
            elif lab == "exchange rate" and isinstance(nxt, float):
                parsed.exchange_rate = nxt
            elif lab.startswith("cumulative value") and parsed.sheet_total is None:
                parsed.sheet_total, _ = parse_money(nxt)

    last_client: str | None = None
    last_row = -10
    for ri in range(hdr + 1, len(rows)):
        r = rows[ri] + [None] * width
        client = r[client_col]
        client = None if client is None or isinstance(client, float) else str(client).strip() or None
        value, _ = parse_money(r[col["gbp"]])
        inv = r[col["invoice_number"]] if "invoice_number" in col else None
        has_invoice = inv is not None and not isinstance(inv, float) and bool(re.search(r"\d", str(inv)))
        continuation = False
        if client is None:
            # A second instalment / extra invoice on the row under a
            # booking, with the client cell left blank.
            # Only in the block of lines directly under a booking (no blank
            # line between) - a £ figure further down is a cost/P&L block
            # (events sheets), not another instalment.
            empty = all(v is None or v == 0 for v in r)
            if empty:
                last_row = -10  # a blank line ends the booking above
                continue
            if last_client and last_row >= 0 and ((value or 0) > 0 or has_invoice):
                client, continuation = last_client, True
            else:
                continue  # a package line ("Enews") under a booking - part of it, no value of its own
        if client.lower().startswith(("total", "totals")):
            continue
        text = " ".join(str(v) for v in r if v is not None)
        looks_like_booking = (
            (value or 0) != 0 or has_invoice
            or ("rep" in col and r[col["rep"]] is not None)
            or ("date" in col and r[col["date"]] is not None)
            or re.search(r"\bCANX\b|CANCEL|CONTRA|MOVED TO", text.upper())
        )
        if not looks_like_booking:
            continue  # cost breakdowns, section labels ("Direct Costs", "Room Hire") typed into the client column
        last_client = client
        last_row = ri
        credits = {}
        for i, code in rep_cols.items():
            amount, _ = parse_money(r[i])
            if amount:
                credits[code] = credits.get(code, 0) + amount
        parsed.rows.append(ParsedRow(
            row_index=ri + 1,
            client=client,
            cells={k: r[i] for k, i in col.items()},
            rep_credits=credits,
            text=text,
            continuation=continuation,
            raw=r,
            extra={lab: (f"{r[i]:g}" if isinstance(r[i], float) else r[i].strftime("%d/%m/%Y") if isinstance(r[i], datetime) else str(r[i]).strip())
                   for i, lab in extra_cols.items() if r[i] is not None and r[i] != 0 and str(r[i]).strip()},
        ))
    return parsed


# ---- Import ---------------------------------------------------------------

@dataclass
class ImportReport:
    files: int = 0
    skipped_files: list[str] = field(default_factory=list)
    editions: int = 0
    orders: int = 0
    warnings: int = 0
    # (title, year, edition, imported_total, sheet_total)
    checks: list[tuple[str, int, str, float, float | None]] = field(default_factory=list)


def _cell_with(row: ParsedRow, pattern: str) -> str | None:
    return next((str(v).strip() for v in row.raw if isinstance(v, str) and re.search(pattern, v, re.IGNORECASE)), None)


def _status_for(row: ParsedRow) -> tuple[str, str | None, str | None]:
    """(status, moved-to note, the sheet text that decided it). The text is
    kept so the app can show *why* - e.g. a "Size" cell reading "Judge
    ticket cancelled 4/9" that Excel clips to "Judge ticket" on screen."""
    moved_cell = _cell_with(row, r"moved to")
    if moved_cell:
        return "moved", moved_cell[:200], moved_cell
    cancel_cell = _cell_with(row, r"\bCANX\b|CANCELL?ED\b")
    if cancel_cell and not re.search(r"CANCELLED AGAINST", cancel_cell, re.IGNORECASE):
        return "cancelled", None, cancel_cell
    contra_cell = _cell_with(row, r"\bCONTRA\b")
    if contra_cell:
        return "contra", None, contra_cell
    return "booked", None, None


def _group_files(root: Path) -> list[tuple[int, Path, Path | None]]:
    """(year, file, working_copy_or_None) for every workbook worth importing."""
    out = []
    for year_dir in sorted(p for p in root.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}", p.name)):
        files = sorted(p for p in year_dir.iterdir()
                       if p.suffix.lower() in (".xls", ".xlsx") and not p.name.startswith("."))
        files = [p for p in files if "copy(" not in p.name.lower()]
        planners = [p for p in files if title_for_file(p.name) and title_for_file(p.name).slug == "visit-usa-planner"]
        edition = next((p for p in planners if "edition" in p.name.lower()), None)
        working = next((p for p in planners if p is not edition), None) if edition else None
        for p in files:
            if p is working:
                continue
            out.append((int(year_dir.name), p, working if p is edition else None))
    return out


def import_sor(db: Session, root: Path, *, replace: bool = False) -> ImportReport:
    ensure_reference_data(db)
    if replace:
        imported = db.query(SalesEdition.id).filter(SalesEdition.source_file.isnot(None))
        db.query(SalesOrder).filter(SalesOrder.edition_id.in_(imported.scalar_subquery())).delete(synchronize_session=False)  # credits cascade
        db.query(SalesEdition).filter(SalesEdition.source_file.isnot(None)).delete(synchronize_session=False)
        db.flush()
    elif db.query(SalesEdition).filter(SalesEdition.source_file.isnot(None)).first():
        raise RuntimeError("SOR workbooks were already imported - rerun with replace=True to reimport.")

    titles = {t.slug: t for t in db.query(SalesTitle).all()}
    reps = {r.code: r for r in db.query(SalesRep).all()}
    report = ImportReport()

    for year, path, working_copy in _group_files(root):
        tdef = title_for_file(path.name)
        if not tdef:
            report.skipped_files.append(f"{year}/{path.name} (no matching title)")
            continue
        title = titles[tdef.slug]
        try:
            book = read_workbook(path)
        except Exception as exc:  # noqa: BLE001 - one unreadable file shouldn't stop the rest
            report.skipped_files.append(f"{year}/{path.name} ({exc})")
            continue
        report.files += 1
        working = read_workbook(working_copy) if working_copy else {}

        for sheet_name, rows in book.items():
            sheet = parse_sheet(sheet_name, rows)
            if not sheet:
                continue
            wsheet = parse_sheet(sheet_name, working.get(sheet_name, [])) if sheet_name in working else None
            wrows = {(r.row_index, r.client): r for r in (wsheet.rows if wsheet else [])}

            name = sheet.name
            existing = db.query(SalesEdition).filter_by(title_id=title.id, year=year, name=name).one_or_none()
            if existing:  # two workbooks for one title+year with the same sheet name
                name = f"{name} ({path.stem})"[:120]
            ed = SalesEdition(
                id=uuid.uuid4(), title_id=title.id, year=year, name=name,
                period_label=(sheet.period.strftime("%B %Y") if isinstance(sheet.period, datetime) else
                              (str(sheet.period)[:200] if sheet.period is not None else None)),
                edition_date=edition_date_for(year, sheet.name, sheet.period),
                kind=edition_kind(tdef.product_line, sheet.name, sheet.period),
                status="closed" if year < date.today().year else "open",
                exchange_rate=sheet.exchange_rate,
                source_file=f"{year}/{path.name}", source_sheet=sheet_name,
                sheet_total_gbp=sheet.sheet_total,
            )
            db.add(ed)
            db.flush()
            report.editions += 1
            total = 0.0

            for row in sheet.rows:
                warnings = []
                if row.continuation:
                    warnings.append("client cell was blank on the sheet - assumed to be the same client as the row above")
                c = row.cells
                value, w = parse_money(c.get("gbp")); warnings += [w] if w else []
                usd, _ = parse_money(c.get("usd"))
                inv_value, _ = parse_money(c.get("invoice_value"))
                raw_inv_value = c.get("invoice_value")
                # Text typed into the invoice-value cell ("part of overpaid
                # credit of 4K rest on People Awards") is an explanation, not
                # an amount - kept as the reason, amount left unknown.
                inv_value_text = raw_inv_value.strip() if isinstance(raw_inv_value, str) and inv_value is None and raw_inv_value.strip() else None
                booked_on, w = parse_date(c.get("date")); warnings += [w] if w else []
                status, moved_note, status_reason = _status_for(row)

                raw_rep = c.get("rep")
                raw_rep = None if raw_rep is None or isinstance(raw_rep, float) else str(raw_rep).strip()
                parts = [p for p in re.split(r"[/&,+]", raw_rep or "") if p.strip()]
                codes = [rep_code_for(p) for p in parts]
                if raw_rep and (not codes or None in codes) and raw_rep.upper() not in ("TBC", "CONTRA"):
                    warnings.append(f"unknown salesperson {raw_rep!r}")
                codes = [x for x in codes if x]
                # Credits: the sheet's own commission columns when it filled
                # them in (that's how a shared "SP/ST" booking gets split),
                # else the full value to the salesperson(s) named.
                credits = dict(row.rep_credits)
                if not codes and credits:
                    codes = list(credits)
                if not credits and codes and value:
                    credits = {k: round(value / len(codes), 2) for k in codes}
                credited = sum(credits.values())
                if (value and credits and status == "booked" and abs(credited - value) > 1
                        and not (inv_value is not None and abs(credited - inv_value) <= 1)):
                    # Crediting the invoiced amount (e.g. part-invoiced, rest
                    # "next quarter") is a normal sheet pattern - only a
                    # figure matching neither is worth a look.
                    warnings.append(f"sheet credits reps with £{credited:,.2f} in total - neither the booking value (£{value:,.2f}) nor the amount invoiced")
                code = codes[0] if codes else None

                inv_no = c.get("invoice_number")
                if isinstance(inv_no, float):
                    inv_no = None if inv_no == 0 else f"{inv_no:.0f}"
                else:
                    inv_no = None if inv_no is None else str(inv_no).strip()
                order_ref = None
                if inv_no and re.fullmatch(r"\d{7,}", inv_no) and not value:
                    # An online ticket/order number on a £0 seat - not a BMI invoice.
                    order_ref, inv_no = inv_no, None
                if inv_no and not re.search(r"\d", inv_no):  # "Moved to OBH 107", "tbc" - a note, not an invoice
                    moved_note = moved_note or inv_no
                    inv_no = None
                reason = c.get("reason")
                reason = None if reason is None or isinstance(reason, float) else str(reason)
                if inv_value_text and inv_value_text.lower() not in ("value", "invoice value"):
                    reason = "; ".join(filter(None, [reason, inv_value_text]))
                notes = moved_note

                wrow = wrows.get((row.row_index, row.client))
                if wrow:
                    wreason = wrow.cells.get("reason")
                    if wreason is not None and not isinstance(wreason, float) and not reason:
                        reason = str(wreason)
                    winv, _ = parse_money(wrow.cells.get("invoice_value"))
                    if winv is not None and inv_value is not None and abs(winv - inv_value) > 0.5:
                        notes = "; ".join(filter(None, [notes, f"Working copy showed an invoice of £{winv:,.2f}"]))

                agency = None
                if reason and "agency" in reason.lower() and value and inv_value is not None and inv_value < value:
                    agency = round(value - inv_value, 2)

                size = c.get("size")
                size = None if size is None else (f"{size:g}" if isinstance(size, float) else str(size))[:120]
                num = lambda v: None if v is None else (f"{v:g}" if isinstance(v, float) else str(v))[:60]  # noqa: E731
                order_id = uuid.uuid4()
                db.add(SalesOrder(
                    id=order_id, edition_id=ed.id, client_name=row.client[:256],
                    rep_id=reps[code].id if code in reps else None,
                    booked_on=booked_on, size=size, pages=parse_pages(size, tdef.product_line),
                    series=num(c.get("series")), position=num(c.get("position")),
                    rate_usd=usd, value_gbp=value or 0, agency_commission_gbp=agency,
                    invoice_number=inv_no[:60] if inv_no else None, invoice_value_gbp=inv_value if inv_no else None,
                    invoice_note=reason, status=status, notes=notes,
                    source_file=f"{year}/{path.name}", source_sheet=sheet_name, source_row=row.row_index,
                    import_warning="; ".join(warnings) or None,
                    order_ref=order_ref, status_reason=status_reason, extra=row.extra,
                ))
                for rc, amount in credits.items():
                    if rc in reps and amount:
                        db.add(SalesOrderCredit(id=uuid.uuid4(), order_id=order_id, rep_id=reps[rc].id, amount_gbp=amount))
                report.orders += 1
                report.warnings += bool(warnings)
                total += value or 0
            report.checks.append((title.name, year, name, round(total, 2), sheet.sheet_total))
        db.flush()

    _link_moves(db)
    return report


def _link_moves(db: Session) -> None:
    """Best effort: "Moved to OBH 107" -> link to that edition when the
    number/name is unambiguous within the same title and year."""
    moved = db.query(SalesOrder, SalesEdition).join(SalesEdition, SalesOrder.edition_id == SalesEdition.id).filter(
        SalesOrder.status == "moved", SalesOrder.moved_to_edition_id.is_(None)).all()
    for order, ed in moved:
        m = re.search(r"moved to\s+(.+)", (order.notes or "").lower())
        if not m:
            continue
        target = re.sub(r"^(obh|tbtm|connect)\s+", "", m[1].strip())
        candidates = db.query(SalesEdition).filter(
            SalesEdition.title_id == ed.title_id, SalesEdition.year.in_([ed.year, ed.year + 1]),
            SalesEdition.id != ed.id).all()
        hits = [c for c in candidates if c.name.lower().strip() == target or c.name.lower().endswith(target)]
        if len(hits) == 1:
            order.moved_to_edition_id = hits[0].id


def edition_window(ed: SalesEdition) -> tuple[date, date]:
    """(start, end) a reasonable 'this edition is live' window - used by
    invoice chasing to decide when an uninvoiced booking is overdue."""
    start = ed.edition_date or date(ed.year, 1, 1)
    return start, start + timedelta(days=45)
