"""Hand-offs after a sale (15 Oct call): once a booking is confirmed and accounts have checked it, each item is
passed to the team that makes it happen, so nothing gets lost in Teams chats and email.

Who (Matt and Clare): sponsored editorial, sponsored content and social media go to the editor for that magazine
(all the places it appears - print, online, newsletter, social - are editorial's job); everything else (display
ads, banners, HTML emails) goes to production. Exception: sponsored content for Caribbean and Visit USA is built
from fillable forms, so it goes to production. A sponsored package can go to both. The salesperson can change it
on each item ("Hand off to"), and the addresses come from the routing table (Bookings > Hand-offs), blank until
someone fills it in.

When: when accounts pass the booking check (or when the booking is confirmed, if the check is switched off).
Sponsored content whose format the client hasn't decided yet ("to be decided") waits for editorial until the
salesperson fills it in. Each team gets one email per booking from the automation mailbox: the client, the items,
the dates of every activity, the copy contact, and a ready-written email asking the client for their copy or
artwork. Each item is sent once; "Send again" re-sends after a change.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SalesDeal, SalesEdition, SalesRate, SalesRep, SalesTitle, User

logger = logging.getLogger("app.sales.handoffs")

TEAMS = ("editorial", "production")
EDITORIAL_WORDS = re.compile(r"sponsor|advertorial|partner content|feature|spotlight|interview|q\s*&\s*a|profile|guest|social|editorial|"
                             r"article|advertorial|branded content|content|insight|meet the|ask the expert|news story|focus", re.I)
PRODUCTION_ONLY_WORDS = re.compile(r"banner|mpu|skyscraper|leaderboard|html|solus|display|full page|half page|quarter page|page advert|"
                                   r"cover|insert|bellyband|dps|double page(?! focus)", re.I)
FORM_TITLES = re.compile(r"caribbean|visit\s*usa", re.I)   # sponsored content built from fillable forms: production
ACTIVITY_LABEL = {"print": "In print", "online": "Online", "newsletter": "Newsletter", "social": "Social media", "banner": "Banner",
                  "email": "HTML email", "event": "At the event", "other": "Other"}
UNDECIDED = re.compile(r"^\s*(tbc|tbd|to be (decided|confirmed)|not decided( yet)?|\?+)?\s*$", re.I)


def _addresses(text: str | None) -> list[str]:
    return [a.strip() for a in re.split(r"[;,\s]+", text or "") if "@" in a]


def suggest_team(title: SalesTitle | None, line: dict, rate: SalesRate | None = None) -> str:
    """The Brain's suggestion for who works on an item: editorial, production or both."""
    words = " ".join(x for x in (line.get("description"), line.get("detail"), line.get("size"),
                                 rate.product if rate else None, getattr(rate, "section", None) if rate else None) if x)
    sponsored = bool(EDITORIAL_WORDS.search(words))
    if sponsored and title and FORM_TITLES.search(f"{title.name} {title.slug}"):
        return "production"
    if sponsored and PRODUCTION_ONLY_WORDS.search(words) and re.search(r"banner|html|solus|mpu", words, re.I):
        return "both"   # a sponsored package with digital artwork too
    return "editorial" if sponsored else "production"


def routes(db: Session) -> dict:
    from app.sales import deals as dl
    st = dl.settings(db)
    r = st.handoff_routes or {}
    return {"default": r.get("default") or {}, "titles": r.get("titles") or {}}


def route_for(db: Session, title_id: str | None, team: str, table: dict | None = None) -> list[str]:
    """The routing table's addresses for a magazine and team (the magazine's own row, else the default row).
    Production falls back to the "Production - always copied" addresses in Confirmation details."""
    table = table or routes(db)
    own = (table["titles"].get(str(title_id)) or {}).get(team) if title_id else None
    found = _addresses(own) or _addresses(table["default"].get(team))
    if not found and team == "production":
        from app.sales import deals as dl
        found = _addresses(dl.settings(db).production_emails)
    return found


def resolve(db: Session, d: SalesDeal, line: dict, table: dict | None = None) -> dict:
    """Who this line goes to, after the salesperson's choices: {"team", "editorial": [...], "production": [...], "format", "waiting"}."""
    title_id = line.get("title_id")
    title = db.get(SalesTitle, uuid.UUID(str(title_id))) if title_id else None
    rate = db.get(SalesRate, uuid.UUID(str(line["rate_id"]))) if line.get("rate_id") else None
    h = line.get("handoff") or {}
    team = h.get("team") or "auto"
    suggested = suggest_team(title, line, rate)
    if team == "auto":
        team = suggested
    out = {"team": team, "suggested": suggested, "format": (h.get("format") or "").strip() or None,
           "editorial": [], "production": [], "waiting": None}
    for t in TEAMS:
        if team in (t, "both"):
            typed = _addresses(h.get(f"{t}_to"))
            out[t] = typed or route_for(db, title_id, t, table)
    if team in ("editorial", "both") and (out["format"] is None or UNDECIDED.match(out["format"] or "")) and EDITORIAL_WORDS.search(
            " ".join(x for x in (line.get("description"), line.get("detail")) if x) or ""):
        out["waiting"] = "Waiting for the format (the client hasn't decided yet)" if out["format"] else "Waiting for the format"
    return out


def ready(db: Session, d: SalesDeal) -> bool:
    from app.automations import order_checks as oc
    return d.status == "confirmed" and (bool(d.checked_at) or not oc.enabled(db))


def _line_sig(line: dict, team: str, to: list[str]) -> str:
    keep = {k: line.get(k) for k in ("description", "detail", "title_id", "activities")}
    keep["placements"] = [(p.get("edition_id"), p.get("item_date"), p.get("copy_due")) for p in line.get("placements") or []]
    keep["format"] = (line.get("handoff") or {}).get("format")
    return hashlib.sha1(json.dumps([keep, team, sorted(to)], sort_keys=True, default=str).encode()).hexdigest()[:16]


def status(db: Session, d: SalesDeal) -> list[dict]:
    """Per line: who it goes to and where it's up to - for the booking page."""
    table = routes(db)
    log = d.handoff_log or {}
    out = []
    for ln in d.lines or []:
        r = resolve(db, d, ln, table)
        teams = []
        for t in TEAMS:
            if r["team"] not in (t, "both"):
                continue
            sent = (log.get(ln.get("key")) or {}).get(t) or {}
            if sent.get("at") and not sent.get("error"):
                state = "sent"
            elif sent.get("error"):
                state = "failed"
            elif not r[t]:
                state = "no_address"
            elif t == "editorial" and r["waiting"]:
                state = "waiting_format"
            elif not ready(db, d):
                state = "waiting_check"
            else:
                state = "due"
            teams.append({"team": t, "to": r[t], "state": state, "sent_at": sent.get("at"), "error": sent.get("error")})
        out.append({"line": ln.get("key"), "description": ln.get("description") or ln.get("size") or "", "team": r["team"],
                    "suggested": r["suggested"], "format": r["format"], "teams": teams,
                    "activities": ln.get("activities") or []})
    return out


# ---- the email --------------------------------------------------------------------------------------------

def _esc(s) -> str:
    return html.escape(str(s or ""))


def _fmt(d) -> str:
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return d
    return f"{d:%-d %b %Y}"


def _line_facts(db: Session, ln: dict) -> dict:
    from app.api.routes.sales import edition_label
    eds = []
    for p in ln.get("placements") or []:
        ed = db.get(SalesEdition, uuid.UUID(str(p["edition_id"]))) if p.get("edition_id") else None
        if ed:
            t = db.get(SalesTitle, ed.title_id)
            eds.append({"label": edition_label(t, ed), "runs": p.get("item_date") or (ed.edition_date.isoformat() if ed.edition_date else None),
                        "copy_due": p.get("copy_due") or (ed.copy_deadline.isoformat() if ed.copy_deadline else None)})
    return {"issues": eds, "activities": ln.get("activities") or []}


def _client_contact(d: SalesDeal) -> tuple[str, str | None]:
    if d.copy_contact_name or d.copy_contact_email:
        return (d.copy_contact_name or d.copy_contact_email or ""), d.copy_contact_email
    return (d.contact_name or d.client_name), d.contact_email


def chase_email(d: SalesDeal, team: str, items: list[tuple[dict, dict, dict]], sender_hint: str) -> str:
    """The ready-written email to the client asking for their copy (editorial) or artwork (production)."""
    name, _ = _client_contact(d)
    first = (name or "").split()[0] if name and "@" not in name else "there"
    what = []
    dues = []
    for ln, r, f in items:
        where = ", ".join(x["label"] for x in f["issues"]) or "the issue"
        fmt = f" ({r['format']})" if r.get("format") else ""
        what.append(f"- {ln.get('description') or 'your booking'}{fmt} in {where}")
        dues += [x["copy_due"] for x in f["issues"] if x.get("copy_due")]
    due = f" by {_fmt(min(dues))}" if dues else ""
    if team == "editorial":
        ask = (f"To get your sponsored content under way, could you send us{due} your brief, any copy you'd like us to work from, "
               "and your images and logo? We'll shape it for our readers and send it back to you to approve before it runs.")
    else:
        ask = f"Could you send us your artwork{due}? We'll send over the specification if you need it."
    return "\n".join([f"Hi {first},", "", f"Thanks again for booking with us:", *what, "", ask, "",
                      "Thanks,", sender_hint])


def _email_html(db: Session, d: SalesDeal, team: str, items: list[tuple[dict, dict, dict]]) -> tuple[str, str]:
    from app.core.config import settings
    rep = db.get(SalesRep, d.rep_id) if d.rep_id else None
    rep_user = db.get(User, rep.user_id) if rep and rep.user_id else None
    name, email = _client_contact(d)
    link = f"{settings.app_base_url.rstrip('/')}/sales/deals/{d.id}"
    rows = []
    for ln, r, f in items:
        bits = [f"<b>{_esc(ln.get('description') or ln.get('size') or 'Item')}</b>"]
        if r.get("format"):
            bits.append(f"Format: {_esc(r['format'])}")
        if ln.get("detail"):
            bits.append(_esc(ln["detail"]))
        for x in f["issues"]:
            bits.append(f"{_esc(x['label'])}{' - runs ' + _fmt(x['runs']) if x.get('runs') else ''}{' - copy due ' + _fmt(x['copy_due']) if x.get('copy_due') else ''}")
        for a in f["activities"]:
            bits.append(f"{_esc(ACTIVITY_LABEL.get(a.get('kind'), a.get('kind')))}{' - ' + _fmt(a.get('on')) if a.get('on') else ''}{' (' + _esc(a['note']) + ')' if a.get('note') else ''}")
        rows.append("<li>" + "<br>".join(bits) + "</li>")
    draft = chase_email(d, team, items, (rep.name if rep else "The BMI team"))
    team_word = "editorial" if team == "editorial" else "production"
    subject = f"New booking for {team_word}: {d.client_name} (booking {d.number})"
    body = (f"<p>A booking that needs {team_word} has been confirmed and checked by accounts.</p>"
            f"<p><b>Client:</b> {_esc(d.client_name)}<br><b>Their contact for copy and artwork:</b> {_esc(name)}{' &lt;' + _esc(email) + '&gt;' if email else ''}"
            f"<br><b>Salesperson:</b> {_esc(rep.name if rep else 'House account')}{' (' + _esc(rep_user.email) + ')' if rep_user else ''}</p>"
            f"<ul>{''.join(rows)}</ul>"
            + (f"<p><b>Copy and artwork notes:</b> {_esc(d.copy_instructions)}</p>" if d.copy_instructions else "")
            + f"<p><a href=\"{link}\">Open the booking</a></p>"
            f"<hr><p><b>A ready-written email to the client</b> (copy it, change anything, and send it from your own mailbox):</p>"
            f"<pre style=\"white-space:pre-wrap;font-family:inherit\">{_esc(draft)}</pre>")
    return subject, body


def process(db: Session, d: SalesDeal, only_lines: set[str] | None = None, force: bool = False) -> dict:
    """Send what's due: each team once per booking, for lines not sent yet (or `only_lines` with force = Send again).
    Never raises: failures are recorded on the booking and shown with a Send again button."""
    from app.services.notify import automation_mailbox_ready, send_automation_email

    result = {"sent": 0, "failed": 0}
    if not ready(db, d):
        return result
    table = routes(db)
    log = dict(d.handoff_log or {})
    by_team: dict[str, list[tuple[dict, dict, dict]]] = {t: [] for t in TEAMS}
    for ln in d.lines or []:
        key = ln.get("key")
        if only_lines is not None and key not in only_lines:
            continue
        r = resolve(db, d, ln, table)
        for t in TEAMS:
            if r["team"] not in (t, "both") or not r[t] or (t == "editorial" and r["waiting"]):
                continue
            prev = (log.get(key) or {}).get(t) or {}
            if prev.get("at") and not prev.get("error") and not force:
                continue
            by_team[t].append((ln, r, _line_facts(db, ln)))
    if not any(by_team.values()):
        return result
    can_send = automation_mailbox_ready(db)
    now = datetime.now(timezone.utc).isoformat()
    for t, items in by_team.items():
        if not items:
            continue
        to = sorted({a for _, r, _ in items for a in r[t]})
        error = None
        if not can_send:
            error = "The automation mailbox isn't set up yet, so the email couldn't go."
        else:
            try:
                subject, body = _email_html(db, d, t, items)
                send_automation_email(db, to, subject, body)
            except Exception:
                logger.exception("hand-off email for booking %s (%s) failed", d.number, t)
                error = "The email didn't go. Try Send again in a minute."
        for ln, r, _ in items:
            entry = dict(log.get(ln.get("key")) or {})
            entry[t] = {"to": r[t], "at": now if not error else None, "error": error, "sig": _line_sig(ln, t, r[t])}
            log[ln.get("key")] = entry
        result["failed" if error else "sent"] += 1
    d.handoff_log = log
    return result
