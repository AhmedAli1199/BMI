"""Reads an uploaded spreadsheet (xlsx / xls / csv) or PDF into plain rows of text.

Everything is turned into text on the way in - the mapper and the importer
decide what a cell means. Nothing here knows about contact fields.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time

MAX_BYTES = 15 * 1024 * 1024
MAX_ROWS = 20000


class ImportFileError(ValueError):
    """Message is shown to the person uploading."""


@dataclass
class Parsed:
    rows: list[list[str]]            # every row of the chosen sheet, including any header/title rows
    sheets: list[dict]               # [{"name", "rows"}] - several for a workbook
    sheet_name: str | None = None
    notes: list[str] = field(default_factory=list)
    ai_read: bool = False            # the rows were read from a PDF's text by the AI - extra checking advised


def file_kind(filename: str, data: bytes) -> str:
    name = filename.lower()
    if data[:4] == b"%PDF" or name.endswith(".pdf"):
        return "pdf"
    if data[:2] == b"PK" or name.endswith((".xlsx", ".xlsm")):
        return "xlsx"
    if data[:4] == b"\xd0\xcf\x11\xe0" or name.endswith(".xls"):
        return "xls"
    if name.endswith((".csv", ".txt", ".tsv")):
        return "csv"
    raise ImportFileError("Upload an Excel file (.xlsx or .xls), a CSV, or a PDF.")


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, datetime):
        return v.date().isoformat() if v.time() == time(0, 0) else v.isoformat(sep=" ", timespec="minutes")
    if isinstance(v, date):
        return v.isoformat()
    return re.sub(r"\s+", " ", str(v).replace("\xa0", " ")).strip()


def _trim(rows: list[list[str]]) -> list[list[str]]:
    """Drops fully blank rows and trailing blank columns."""
    rows = [r for r in rows if any(c for c in r)]
    width = max((max((i for i, c in enumerate(r) if c), default=-1) + 1 for r in rows), default=0)
    return [r[:width] + [""] * (width - len(r)) for r in rows]


def parse(filename: str, data: bytes, sheet: str | None = None) -> tuple[str, Parsed]:
    if not data:
        raise ImportFileError("That file is empty.")
    if len(data) > MAX_BYTES:
        raise ImportFileError("That file is over 15 MB - split it into smaller files.")
    kind = file_kind(filename, data)
    fn = {"xlsx": _xlsx, "xls": _xls, "csv": _csv, "pdf": _pdf}[kind]
    parsed = fn(data, sheet)
    parsed.rows = _trim(parsed.rows)
    if not parsed.rows:
        raise ImportFileError("There's nothing readable in that file.")
    if len(parsed.rows) > MAX_ROWS + 1:
        raise ImportFileError(f"That file has more than {MAX_ROWS:,} rows - split it and import in parts.")
    return kind, parsed


def _pick_sheet(names_rows: dict[str, list[list[str]]], want: str | None) -> tuple[str, list[dict]]:
    sheets = [{"name": n, "rows": len([r for r in rows if any(r)])} for n, rows in names_rows.items()]
    if want and want in names_rows:
        return want, sheets
    best = max(sheets, key=lambda s: s["rows"])  # the busiest sheet is nearly always the contact list
    return best["name"], sheets


def _xlsx(data: bytes, sheet: str | None) -> Parsed:
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise ImportFileError("That Excel file couldn't be opened - is it password protected or damaged?")
    allrows = {ws.title: [[_cell(c) for c in row] for row in ws.iter_rows(values_only=True)] for ws in wb.worksheets if ws.sheet_state == "visible"}
    if not allrows:
        raise ImportFileError("That workbook has no visible sheets.")
    name, sheets = _pick_sheet(allrows, sheet)
    notes = [f"This workbook has {len(sheets)} sheets - reading “{name}”. Switch sheet below if that's not the right one."] if len(sheets) > 1 and not sheet else []
    return Parsed(allrows[name], sheets, name, notes)


def _xls(data: bytes, sheet: str | None) -> Parsed:
    import xlrd
    try:
        wb = xlrd.open_workbook(file_contents=data)
    except Exception:
        raise ImportFileError("That Excel file couldn't be opened - is it damaged?")
    allrows = {}
    for ws in wb.sheets():
        rows = []
        for r in range(ws.nrows):
            row = []
            for c in range(ws.ncols):
                cell = ws.cell(r, c)
                v = cell.value
                if cell.ctype == xlrd.XL_CELL_DATE:
                    v = xlrd.xldate_as_datetime(v, wb.datemode)
                row.append(_cell(v))
            rows.append(row)
        allrows[ws.name] = rows
    name, sheets = _pick_sheet(allrows, sheet)
    notes = [f"This workbook has {len(sheets)} sheets - reading “{name}”. Switch sheet below if that's not the right one."] if len(sheets) > 1 and not sheet else []
    return Parsed(allrows[name], sheets, name, notes)


def _csv(data: bytes, sheet: str | None) -> Parsed:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:20000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [[_cell(c) for c in row] for row in csv.reader(io.StringIO(text), dialect)]
    return Parsed(rows, [{"name": "CSV", "rows": len(rows)}], "CSV")


def _pdf(data: bytes, sheet: str | None) -> Parsed:
    """Tables first (a contact list exported to PDF nearly always is one). If a page has no table,
    the text is read by the AI, which is slower and must be checked by eye."""
    import pdfplumber
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception:
        raise ImportFileError("That PDF couldn't be opened - is it password protected or damaged?")
    rows: list[list[str]] = []
    text_pages: list[str] = []
    with pdf:
        pages = pdf.pages[:60]
        for page in pages:
            tables = [t for t in page.extract_tables() if t and max(len(r) for r in t) >= 2]
            if tables:
                for t in tables:
                    rows.extend([[_cell(c) for c in r] for r in t])
            else:
                text_pages.append(page.extract_text() or "")
    notes = ["Read from a PDF - check the column matching and the review step carefully."]
    if rows:
        # A table that runs over several pages repeats its header row - keep the first only.
        head = rows[0]
        rows = [rows[0]] + [r for r in rows[1:] if r != head]
        return Parsed(rows, [{"name": "PDF", "rows": len(rows)}], "PDF", notes)
    text = "\n".join(text_pages).strip()
    if len(text) < 20:
        raise ImportFileError("That PDF has no readable text - it looks like a scan. Export the list to Excel or CSV, or retype it into a spreadsheet.")
    ai_rows = _ai_rows(text)
    if not ai_rows:
        raise ImportFileError("We couldn't find a table or a list of contacts in that PDF. Try exporting the list to Excel or CSV instead.")
    notes.append("There was no table in this PDF, so the contact details were picked out of its text by the AI. Check every row in the review step.")
    return Parsed(ai_rows, [{"name": "PDF", "rows": len(ai_rows)}], "PDF", notes, ai_read=True)


AI_COLUMNS = ["First name", "Last name", "Job title", "Company", "Email", "Phone", "Mobile", "Address", "City", "Postcode", "Country"]


def _ai_rows(text: str) -> list[list[str]]:
    from app.automations import llm
    if not llm.is_configured():
        return []
    out: list[list[str]] = []
    # The model reads about 6,000 characters at a time; contacts split across a chunk edge are rare and just show up in the review.
    for i in range(0, min(len(text), 60000), 6000):
        res = llm.extract_json(
            "You extract contact details from text taken from a PDF. Return JSON {\"contacts\": [..]} where each contact has only these string keys: "
            + ", ".join(AI_COLUMNS) + ". Copy values exactly as written; never invent or complete anything; omit keys you can't see. "
            "Skip page headers, footers and anything that isn't a person or organisation's contact details.",
            text[i:i + 6000], max_tokens=3000, purpose="contact_import_pdf")
        for c in (res or {}).get("contacts") or []:
            if isinstance(c, dict):
                out.append([_cell(c.get(col)) for col in AI_COLUMNS])
    if not out:
        return []
    return [AI_COLUMNS] + out


def _looks_like_data(cell: str) -> bool:
    return bool(re.search(r"@|\d{5,}|^\d+$", cell))


def detect_header(rows: list[list[str]]) -> tuple[int, bool]:
    """(index of the header row, whether there is one). Skips title rows above the table; says
    "no header" when the first real row is itself a contact (emails / phone numbers)."""
    for i, row in enumerate(rows[:12]):
        filled = [c for c in row if c]
        if len(filled) < 2:
            continue  # a title or blank-ish line above the table
        if sum(_looks_like_data(c) for c in filled) >= max(1, len(filled) // 3):
            return i, False
        return i, True
    return 0, True


def split_rows(rows: list[list[str]], header_row: int, has_header: bool) -> tuple[list[str], list[list[str]]]:
    """(headers, data rows). Without a header, columns are named A, B, C…"""
    width = max(len(r) for r in rows)
    if has_header and header_row < len(rows):
        headers = rows[header_row] + [""] * (width - len(rows[header_row]))
        body = rows[header_row + 1:]
    else:
        headers = [_col_letter(i) for i in range(width)]
        body = rows[header_row:]
    headers = [h if h else f"Column {_col_letter(i)}" for i, h in enumerate(headers)]
    return headers, [r + [""] * (width - len(r)) for r in body]


def _col_letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s
