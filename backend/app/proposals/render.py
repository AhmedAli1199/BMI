"""A proposal's sections as they go out: blocks filled in from the Brain's data, rich text cleaned, the same
content for the email and for the Word document.

A section is {"id", "kind", "heading", "body", "html"?, "block"?: {"kind", "config"}}:
  - "block" set: a ready-made block (app/proposals/blocks.py), filled in when shown or sent;
  - "html" set: rich text from the editor;
  - neither: older plain-text wording ("**bold**", "- " bullets), still supported.
"""
from __future__ import annotations

import html as html_lib
import re

from sqlalchemy.orm import Session

from app.models import Proposal
from app.proposals import blocks

_ALLOWED = {"p", "div", "br", "b", "strong", "i", "em", "u", "a", "ul", "ol", "li", "h2", "h3", "h4", "span", "table", "thead",
            "tbody", "tfoot", "tr", "td", "th", "img", "mark", "font", "blockquote", "hr"}
_ATTRS = {"href", "src", "alt", "width", "height", "style", "colspan", "rowspan"}


def clean_html(raw: str) -> str:
    """Keeps formatting, drops anything that could run code or load something unexpected."""
    from html.parser import HTMLParser

    out: list[str] = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs, end=False):
            if tag not in _ALLOWED:
                return
            kept = []
            for k, v in attrs:
                if k not in _ATTRS or v is None:
                    continue
                if k in ("href", "src"):
                    low = v.strip().lower()
                    if not (low.startswith(("http://", "https://", "mailto:")) or (k == "src" and low.startswith("data:image/"))):
                        continue
                if k == "style" and re.search(r"expression|url\(|javascript", v, re.I):
                    continue
                kept.append(f' {k}="{html_lib.escape(v, quote=True)}"')
            out.append(f"<{tag}{''.join(kept)}{' /' if end else ''}>")

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs, end=True)

        def handle_endtag(self, tag):
            if tag in _ALLOWED and tag not in ("br", "img", "hr"):
                out.append(f"</{tag}>")

        def handle_data(self, data):
            out.append(html_lib.escape(data, quote=False))

    p = P(convert_charrefs=True)
    p.feed(raw or "")
    p.close()
    return "".join(out)


def text_to_html(body: str) -> str:
    """Older plain-text wording ("**bold**", "- " bullets, blank lines between paragraphs) as HTML."""
    out = []
    for chunk in re.split(r"\n\s*\n", (body or "").strip()):
        if not chunk.strip():
            continue
        lines = [ln for ln in chunk.split("\n") if ln.strip()]
        inline = lambda s: re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_lib.escape(s.strip()))  # noqa: E731
        if all(ln.lstrip().startswith("- ") for ln in lines):
            out.append("<ul>" + "".join(f"<li>{inline(ln.lstrip()[2:])}</li>" for ln in lines) + "</ul>")
        else:
            out.append("<p>" + "<br>".join(inline(ln) for ln in lines) + "</p>")
    return "".join(out)


def section_html(db: Session, p: Proposal, s: dict) -> str:
    if s.get("block"):
        b = s["block"]
        return blocks.render(db, b.get("kind"), b.get("config"), title_id=p.title_id, lines=p.lines or [],
                             discount_pct=float(p.discount_pct or 0))
    content = clean_html(s["html"]) if s.get("html") else text_to_html(s.get("body") or "")
    if s.get("kind") == "investment" and p.lines:   # the Investment section always opens with the package and prices
        content = blocks.package_html(p.lines, float(p.discount_pct or 0)) + content
    return content


def output_sections(db: Session, p: Proposal) -> list[dict]:
    """The sections ready for the Word builder: blocks and rich text get "out_html"; older plain-text sections are
    left as they are, so the Word file lays them out exactly as before (Investment as priced paragraphs)."""
    return [{**s, "out_html": section_html(db, p, s)} if (s.get("block") or s.get("html")) else s for s in p.sections or []]


def email_html(db: Session, p: Proposal, intro: str | None = None) -> str:
    """The whole proposal as the body of an email."""
    parts = [f"<div style=\"font-family:Calibri,Arial,sans-serif;font-size:11pt;color:#111827;line-height:1.45\">"]
    if intro and intro.strip():
        parts.append(clean_html(intro) if "<" in intro else text_to_html(intro))
    for s in p.sections or []:
        if (s.get("heading") or "").strip():
            parts.append(f"<h3 style=\"font-size:13pt;margin:18px 0 6px\">{html_lib.escape(s['heading'].strip())}</h3>")
        parts.append(section_html(db, p, s))
    parts.append("</div>")
    return "".join(parts)


def email_warnings(body_html: str) -> list[str]:
    """Things that may not show well in Outlook - suggested, never blocking."""
    out = []
    images = re.findall(r"<img[^>]+src=\"data:image/[^\"]+\"", body_html)
    size = len(body_html.encode())
    if len(images) > 4:
        out.append(f"There are {len(images)} pictures. Emails with lots of pictures can land in junk folders - think about sending a Word document instead.")
    if size > 2_500_000:
        out.append("This is a big email because of the pictures. Make them smaller, or send it as a Word document.")
    for t in re.findall(r"<tr>(.*?)</tr>", body_html, re.S):
        if len(re.findall(r"<t[dh]\b", t)) > 5:
            out.append("A table has more than 5 columns, which is hard to read on a phone. Fewer columns, or a Word document, works better.")
            break
    return out


def inline_images(body_html: str) -> tuple[str, list[tuple[str, str, bytes, str]]]:
    """Moves data: pictures into inline attachments (cid:), which Outlook shows reliably. Returns the new HTML and
    the attachments as (file name, content type, bytes, content id)."""
    import base64
    import uuid

    files: list[tuple[str, str, bytes, str]] = []

    def swap(m):
        ext, data = m.group(1), m.group(2)
        cid = f"img{len(files) + 1}-{uuid.uuid4().hex[:8]}"
        try:
            ct = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
            files.append((f"{cid}.{'jpg' if ext in ('jpg', 'jpeg') else ext}", ct, base64.b64decode(data), cid))
        except Exception:
            return m.group(0)
        return f'src="cid:{cid}"'

    body = re.sub(r'src="data:image/(png|jpeg|jpg|gif);base64,([^"]+)"', swap, body_html)
    return body, files
