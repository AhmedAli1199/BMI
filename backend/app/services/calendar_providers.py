"""Reading people's Google and Outlook calendars (read-only), each turned into the same plain shape.

Both sign-ins are delegated OAuth: the person approves once, we keep an encrypted refresh token and
read their own calendar. Nothing is ever written to anyone's calendar.

Outlook uses the same Microsoft app registration as "Connect Outlook" (mail), but as its OWN grant with
its own scopes - adding a calendar scope to the mail sign-in would break every existing mail token on
its next refresh until each person reconnected.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.calendar import CalendarConnection
from app.services import outlook

MS_SCOPES = "offline_access User.Read Calendars.Read"
GOOGLE_SCOPES = "openid email https://www.googleapis.com/auth/calendar.readonly"


class CalendarAuthError(Exception):
    """The grant stopped working - the person has to reconnect."""


class CalendarNotConfigured(Exception):
    pass


@dataclass
class CalEvent:
    id: str
    ical_uid: str | None
    title: str | None
    start: datetime
    end: datetime
    all_day: bool
    join_url: str | None
    organizer_email: str | None
    organizer_name: str | None
    attendees: list[dict] = field(default_factory=list)   # [{email, name, response}]
    my_response: str = "none"     # organizer | accepted | tentative | declined | none
    is_private: bool = False
    cancelled: bool = False


# ---- Meeting links -----------------------------------------------------------------------------

_LINKS = [
    ("google_meet", re.compile(r"https?://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}", re.I)),
    ("teams", re.compile(r"https?://teams\.microsoft\.com/l/meetup-join/[^\s\"'<>)]+", re.I)),
    ("teams", re.compile(r"https?://teams\.live\.com/meet/[^\s\"'<>)]+", re.I)),
    ("teams", re.compile(r"https?://teams\.microsoft\.com/meet/[^\s\"'<>)]+", re.I)),
    ("zoom", re.compile(r"https?://(?:[\w-]+\.)?zoom\.us/(?:j|my|w)/[^\s\"'<>)]+", re.I)),
]


def find_link(*texts: str | None) -> tuple[str | None, str | None]:
    """The first Meet / Teams / Zoom link in any of the texts, and its platform."""
    for text in texts:
        if not text:
            continue
        for platform, rx in _LINKS:
            m = rx.search(text)
            if m:
                return m.group(0).rstrip(".,;>"), platform
    return None, None


def link_identity(url: str | None, platform: str | None) -> str | None:
    """A stable id for the meeting room, the same however each calendar wrote the link."""
    if not url:
        return None
    u = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(u.path)
    if platform == "google_meet":
        return "meet:" + path.strip("/").lower()
    if platform == "teams":
        m = re.search(r"(19:meeting_[^/@]+@thread\.v2)", path, re.I)
        return "teams:" + (m.group(1).lower() if m else path.strip("/").lower())
    if platform == "zoom":
        m = re.search(r"/j/(\d+)", path)
        return "zoom:" + (m.group(1) if m else path.strip("/").lower())
    return url.lower()


# ---- Shared token handling ---------------------------------------------------------------------

def _store(conn: CalendarConnection, body: dict) -> None:
    conn.access_token_enc = outlook.encrypt(body["access_token"])
    conn.access_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(body.get("expires_in", 3600)) - 120)
    if body.get("refresh_token"):
        conn.refresh_token_enc = outlook.encrypt(body["refresh_token"])
    conn.status, conn.last_error = "connected", None


def access_token(db: Session, conn: CalendarConnection) -> str:
    if conn.access_token_enc and conn.access_expires_at and conn.access_expires_at > datetime.now(timezone.utc):
        return outlook.decrypt(conn.access_token_enc)
    refresh = outlook.decrypt(conn.refresh_token_enc)
    try:
        body = (_ms_token if conn.provider == "microsoft" else _google_token)({"grant_type": "refresh_token", "refresh_token": refresh})
    except CalendarAuthError as e:
        conn.status, conn.last_error = "error", str(e)
        raise
    _store(conn, body)
    return body["access_token"]


# ---- Microsoft ---------------------------------------------------------------------------------

def ms_authorize_url(user_id, return_to: str) -> str:
    cid, _, tenant = outlook._client()
    params = {"client_id": cid, "response_type": "code", "redirect_uri": outlook.redirect_uri(), "response_mode": "query",
              "scope": MS_SCOPES, "state": outlook.make_state(user_id, return_to, purpose="calendar"), "prompt": "select_account"}
    return str(httpx.URL(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize", params=params))


def _ms_token(data: dict) -> dict:
    cid, secret, tenant = outlook._client()
    r = httpx.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                   data={"client_id": cid, "client_secret": secret, "scope": MS_SCOPES, **data}, timeout=20)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code >= 300:
        if "AADSTS65001" in (body.get("error_description") or "") or body.get("error") == "consent_required":
            raise CalendarAuthError("Your organisation needs to approve calendar access for this app first.")
        raise CalendarAuthError("Microsoft didn't accept the sign-in. Please connect your calendar again.")
    return body


def ms_complete(code: str) -> tuple[dict, str]:
    body = _ms_token({"grant_type": "authorization_code", "code": code, "redirect_uri": outlook.redirect_uri()})
    me = httpx.get(f"{outlook.GRAPH_BASE}/me", headers={"Authorization": f"Bearer {body['access_token']}"},
                   params={"$select": "mail,userPrincipalName"}, timeout=15).json()
    return body, me.get("mail") or me.get("userPrincipalName") or ""


_MS_RESPONSE = {"organizer": "organizer", "accepted": "accepted", "tentativelyAccepted": "tentative", "declined": "declined"}


def _ms_dt(v: dict | None) -> datetime:
    s = (v or {}).get("dateTime", "")[:26]
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def ms_events(db: Session, conn: CalendarConnection, start: datetime, end: datetime) -> list[CalEvent]:
    token = access_token(db, conn)
    headers = {"Authorization": f"Bearer {token}", "Prefer": 'outlook.timezone="UTC", outlook.body-content-type="text"'}
    url = f"{outlook.GRAPH_BASE}/me/calendarView"
    params = {"startDateTime": start.isoformat(), "endDateTime": end.isoformat(), "$top": "100",
              "$select": "id,iCalUId,subject,start,end,isAllDay,isCancelled,onlineMeeting,onlineMeetingUrl,location,body,"
                         "organizer,attendees,responseStatus,sensitivity"}
    out: list[CalEvent] = []
    while url:
        r = httpx.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 401:
            conn.access_token_enc = None
            raise CalendarAuthError("Microsoft stopped accepting the calendar sign-in. Please connect it again.")
        if r.status_code == 403:
            raise CalendarAuthError("Your organisation hasn't allowed calendar access for this app yet.")
        r.raise_for_status()
        data = r.json()
        for e in data.get("value", []):
            link, _ = find_link((e.get("onlineMeeting") or {}).get("joinUrl"), e.get("onlineMeetingUrl"),
                                (e.get("location") or {}).get("displayName"), (e.get("body") or {}).get("content"))
            org = (e.get("organizer") or {}).get("emailAddress") or {}
            people = [{"email": (a.get("emailAddress") or {}).get("address", "").lower(), "name": (a.get("emailAddress") or {}).get("name"),
                       "response": _MS_RESPONSE.get((a.get("status") or {}).get("response"), "none")}
                      for a in e.get("attendees") or [] if (a.get("emailAddress") or {}).get("address")]
            out.append(CalEvent(
                id=e["id"], ical_uid=e.get("iCalUId"), title=e.get("subject"), start=_ms_dt(e.get("start")), end=_ms_dt(e.get("end")),
                all_day=bool(e.get("isAllDay")), join_url=link, organizer_email=(org.get("address") or "").lower() or None,
                organizer_name=org.get("name"), attendees=people,
                my_response=_MS_RESPONSE.get((e.get("responseStatus") or {}).get("response"), "none"),
                is_private=e.get("sensitivity") in ("private", "confidential"), cancelled=bool(e.get("isCancelled")),
            ))
        url, params = data.get("@odata.nextLink"), None
    return out


# ---- Google ------------------------------------------------------------------------------------

def google_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def google_redirect_uri() -> str:
    return f"{settings.app_base_url.rstrip('/')}/api/google/callback"


def google_authorize_url(user_id, return_to: str) -> str:
    if not google_configured():
        raise CalendarNotConfigured("Google Calendar isn't set up yet.")
    params = {"client_id": settings.google_client_id, "redirect_uri": google_redirect_uri(), "response_type": "code",
              "scope": GOOGLE_SCOPES, "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true",
              "state": outlook.make_state(user_id, return_to, purpose="google_calendar")}
    return str(httpx.URL("https://accounts.google.com/o/oauth2/v2/auth", params=params))


def _google_token(data: dict) -> dict:
    r = httpx.post("https://oauth2.googleapis.com/token", data={"client_id": settings.google_client_id,
                   "client_secret": settings.google_client_secret, **data}, timeout=20)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code >= 300:
        raise CalendarAuthError("Google didn't accept the sign-in. Please connect your calendar again.")
    return body


def google_complete(code: str) -> tuple[dict, str]:
    body = _google_token({"grant_type": "authorization_code", "code": code, "redirect_uri": google_redirect_uri()})
    if "calendar.readonly" not in (body.get("scope") or ""):
        raise CalendarAuthError("Please tick the box that lets BMI Brain see your calendar, then try again.")
    cal = httpx.get("https://www.googleapis.com/calendar/v3/calendars/primary",
                    headers={"Authorization": f"Bearer {body['access_token']}"}, timeout=15).json()
    return body, (cal.get("id") or "").lower()


_G_RESPONSE = {"accepted": "accepted", "tentative": "tentative", "declined": "declined", "needsAction": "none"}


def _g_dt(v: dict) -> tuple[datetime, bool]:
    if v.get("dateTime"):
        return datetime.fromisoformat(v["dateTime"].replace("Z", "+00:00")).astimezone(timezone.utc), False
    return datetime.combine(date.fromisoformat(v["date"]), time(0), tzinfo=timezone.utc), True


def google_events(db: Session, conn: CalendarConnection, start: datetime, end: datetime) -> list[CalEvent]:
    token = access_token(db, conn)
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    params = {"timeMin": start.isoformat(), "timeMax": end.isoformat(), "singleEvents": "true", "maxResults": "250",
              "orderBy": "startTime"}
    out: list[CalEvent] = []
    while True:
        r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        if r.status_code in (401, 403):
            conn.access_token_enc = None
            raise CalendarAuthError("Google stopped accepting the calendar sign-in. Please connect it again.")
        r.raise_for_status()
        data = r.json()
        for e in data.get("items", []):
            if "start" not in e:
                continue
            s, all_day = _g_dt(e["start"])
            en, _ = _g_dt(e.get("end") or e["start"])
            video = next((p.get("uri") for p in (e.get("conferenceData") or {}).get("entryPoints", []) if p.get("entryPointType") == "video"), None)
            link, _ = find_link(e.get("hangoutLink"), video, e.get("location"), e.get("description"))
            org = e.get("organizer") or {}
            people = [{"email": a["email"].lower(), "name": a.get("displayName"), "response": _G_RESPONSE.get(a.get("responseStatus"), "none")}
                      for a in e.get("attendees") or [] if a.get("email") and not a.get("resource")]
            me = next((a for a in e.get("attendees") or [] if a.get("self")), None)
            mine = "organizer" if org.get("self") or not e.get("attendees") else _G_RESPONSE.get((me or {}).get("responseStatus"), "none")
            out.append(CalEvent(
                id=e["id"], ical_uid=e.get("iCalUID"), title=e.get("summary"), start=s, end=en, all_day=all_day, join_url=link,
                organizer_email=(org.get("email") or "").lower() or None, organizer_name=org.get("displayName"), attendees=people,
                my_response=mine, is_private=e.get("visibility") in ("private", "confidential"), cancelled=e.get("status") == "cancelled",
            ))
        if not data.get("nextPageToken"):
            break
        params = {**params, "pageToken": data["nextPageToken"]}
    return out


def fetch_events(db: Session, conn: CalendarConnection, start: datetime, end: datetime) -> list[CalEvent]:
    return (ms_events if conn.provider == "microsoft" else google_events)(db, conn, start, end)
