"""Writes a proposal into one of BMI's three Word templates.

The templates are Matt's: A4 pages with the title's artwork, a header line
reading "Campaign/Advertiser name 2026/27", a footer (website, publisher
address, other BMI products) and four named styles. We keep every bit of
that exactly as designed - the builder only (1) swaps the campaign name in
the header (and footer, if it appears there) and (2) fills the empty body
with paragraphs in the template's own styles.

Body text is plain: blank lines separate paragraphs, **double asterisks**
make words bold, and a line starting "- " becomes a bullet.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import docx
from docx.document import Document as DocumentType
from docx.text.paragraph import Paragraph

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_FILES = {"obh": "obh.docx", "stm": "stm.docx", "tbtm": "tbtm.docx"}
TEMPLATE_LABELS = {"obh": "Onboard Hospitality", "stm": "Selling Travel", "tbtm": "The Business Travel Magazine"}

STYLE_HEADING = "STM Sub heading"
STYLE_BODY = "STM body copy"
STYLE_BOLD = "STM body BOLD"
PLACEHOLDER = "Campaign/Advertiser name"

_BOLD = re.compile(r"\*\*(.+?)\*\*")


def template_for_slug(slug: str | None) -> str:
    """Which template a title uses: OBH titles -> obh, TBTM -> tbtm, everything else (Selling Travel and its sister products) -> stm."""
    s = (slug or "").lower()
    return "obh" if s.startswith("obh") else "tbtm" if s.startswith("tbtm") else "stm"


def _replace_in_paragraph(p: Paragraph, campaign: str) -> bool:
    """Swaps the placeholder line for the campaign name, keeping the first run's formatting."""
    if PLACEHOLDER not in p.text:
        return False
    runs = p.runs
    if not runs:
        return False
    runs[0].text = campaign
    for r in runs[1:]:
        r.text = ""
    return True


def _header_footers(document: DocumentType):
    for section in document.sections:
        for part in (section.header, section.first_page_header, section.even_page_header,
                     section.footer, section.first_page_footer, section.even_page_footer):
            yield part


def _add_runs(p: Paragraph, text: str, bold: bool = False) -> None:
    pos = 0
    for m in _BOLD.finditer(text):
        if m.start() > pos:
            r = p.add_run(text[pos:m.start()])
            r.bold = True if bold else None
        p.add_run(m.group(1)).bold = True
        pos = m.end()
    if pos < len(text):
        r = p.add_run(text[pos:])
        r.bold = True if bold else None


def _paragraphs(body: str) -> list[str]:
    return [" ".join(chunk.split()) if not chunk.lstrip().startswith("- ") else chunk.strip()
            for chunk in re.split(r"\n\s*\n", (body or "").strip()) if chunk.strip()]


def _money(v: float) -> str:
    """"£1,200.00", and "-£120.00" for an offer taken off."""
    return f"-£{-v:,.2f}" if v < 0 else f"£{v:,.2f}"


def investment_paragraphs(lines: list[dict], discount_pct: float = 0.0) -> list[tuple[str, str]]:
    """The price table as (text, "body"|"bold") paragraphs: each option with its lines, the issues they run in,
    any % off, offers, the % off the whole proposal and the total. Shared by the Word file and the screen preview."""
    from app.proposals.pricing import line_total, totals

    out: list[tuple[str, str]] = []
    tots = totals(lines, discount_pct)
    many = len(tots) > 1
    for t in tots:
        if many:
            out.append((t["option"], "bold"))
        for ln in [x for x in lines if x.get("option") in (t["option"], None)]:
            qty, price = float(ln.get("qty") or 1), float(ln.get("unit_price") or 0)
            disc = float(ln.get("discount_pct") or 0)
            gross, net = qty * price, line_total(ln)
            head = f"{ln['product']}: " + (f"{qty:g} x {_money(price)} = {_money(gross)}" if qty != 1 else _money(price))
            if disc:
                head += f", less {disc * 100:g}% = {_money(net)}"
            out.append((head, "body"))
            if ln.get("issue_labels"):
                out.append(("Runs in " + ", ".join(ln["issue_labels"]), "body"))
        if t["discount_gbp"]:
            out.append((f"Less {discount_pct * 100:g}% discount: {_money(-t['discount_gbp'])}", "body"))
        out.append((f"{t['option'] + ' total' if many else 'Total'}: {_money(t['total_gbp'])}", "bold"))
    return out


def build_docx(*, template: str, campaign_name: str, sections: list[dict], lines: list[dict], total: float, discount_pct: float = 0.0) -> bytes:
    document = docx.Document(TEMPLATE_DIR / TEMPLATE_FILES[template])

    for part in _header_footers(document):
        for p in part.paragraphs:
            _replace_in_paragraph(p, campaign_name)

    # Clear the sample paragraphs (one per style), keeping the page setup that lives in sectPr.
    body = document.element.body
    for p in list(document.paragraphs):
        body.remove(p._element)

    def add(text: str, style: str, bold: bool = False) -> Paragraph:
        p = document.add_paragraph(style=style)
        _add_runs(p, text, bold)
        return p

    for section in sections:
        heading = (section.get("heading") or "").strip()
        if heading:
            add(heading, STYLE_HEADING)
        if section.get("kind") == "investment" and lines:
            for text, style in investment_paragraphs(lines, discount_pct):
                add(text, STYLE_BOLD if style == "bold" else STYLE_BODY)
        for chunk in _paragraphs(section.get("body", "")):
            if chunk.startswith("- "):
                for item in (x.strip() for x in chunk.split("\n") if x.strip()):
                    add("•  " + item[2:].strip() if item.startswith("- ") else item, STYLE_BODY)
            else:
                add(chunk, STYLE_BODY)

    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()
