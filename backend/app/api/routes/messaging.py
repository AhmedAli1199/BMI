"""Reminders, notifications (the bell), Outlook connection, mail-merge
templates and mail merges. Everything here is per signed-in user."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import Identity, get_identity
from app.db.session import get_db
from app.models import Company, Contact, Group, User
from app.models.messaging import (
    MailAccount, MailAttachment, MailMerge, MailMergeRecipient, MailTemplate, Notification, Reminder,
)
from app.services import mail_merge as mm
from app.services import outlook
from app.services.contact_lookup import LookupFilters, lookup_ids
from app.services.notify import automation_mailbox, automation_mailbox_ready
from app.services.reminders import reminder_subject

router = APIRouter(tags=["messaging"])

MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024  # Graph's inline-attachment limit per sendMail call is ~3-4MB
MAX_ATTACHMENTS_TOTAL = 3 * 1024 * 1024


def current_user(db: Session = Depends(get_db), identity: Identity = Depends(get_identity)) -> User:
    uid = identity.user_uuid
    user = db.get(User, uid) if uid else None
    if not user and identity.user_id == "local-dev" and settings.environment != "production":
        # The frontend's local-dev bypass has no user row - act as the first admin.
        user = db.scalar(select(User).where(User.is_active.is_(True)).order_by((User.role == "admin").desc(), User.created_at))
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to use this feature.")
    return user


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---- Reminders --------------------------------------------------------------

class ReminderIn(BaseModel):
    due_at: datetime
    note: str | None = Field(default=None, max_length=4000)
    contact_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    email_me: bool = True


class ReminderPatch(BaseModel):
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=4000)
    email_me: bool | None = None
    status: str | None = Field(default=None, pattern="^(open|done|cancelled)$")


class ReminderOut(BaseModel):
    id: uuid.UUID
    due_at: datetime
    note: str | None
    contact_id: uuid.UUID | None
    company_id: uuid.UUID | None
    about: str
    link: str | None
    email_me: bool
    status: str
    notified_at: datetime | None
    created_at: datetime | None


def _reminder_out(db: Session, r: Reminder) -> ReminderOut:
    about, link = reminder_subject(db, r)
    return ReminderOut(id=r.id, due_at=r.due_at, note=r.note, contact_id=r.contact_id, company_id=r.company_id,
                       about=about, link=link, email_me=r.email_me, status=r.status, notified_at=r.notified_at,
                       created_at=r.created_at)


@router.get("/reminders", response_model=list[ReminderOut])
def list_reminders(status: str = Query("open", pattern="^(open|done|cancelled|all)$"),
                   contact_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None,
                   db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Reminder).where(Reminder.user_id == user.id)
    if status != "all":
        stmt = stmt.where(Reminder.status == status)
    if contact_id:
        stmt = stmt.where(Reminder.contact_id == contact_id)
    if company_id:
        stmt = stmt.where(Reminder.company_id == company_id)
    stmt = stmt.order_by(Reminder.due_at.desc() if status in ("done", "cancelled") else Reminder.due_at).limit(500)
    return [_reminder_out(db, r) for r in db.scalars(stmt)]


@router.post("/reminders", response_model=ReminderOut, status_code=201)
def create_reminder(payload: ReminderIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if payload.contact_id and not db.get(Contact, payload.contact_id):
        raise HTTPException(404, "Contact not found")
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(404, "Company not found")
    r = Reminder(id=uuid.uuid4(), user_id=user.id, contact_id=payload.contact_id, company_id=payload.company_id,
                 due_at=_aware(payload.due_at), note=(payload.note or "").strip() or None, email_me=payload.email_me,
                 status="open")
    db.add(r)
    db.commit()
    return _reminder_out(db, r)


def _own_reminder(db: Session, rid: uuid.UUID, user: User) -> Reminder:
    r = db.get(Reminder, rid)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "Reminder not found")
    return r


@router.patch("/reminders/{reminder_id}", response_model=ReminderOut)
def update_reminder(reminder_id: uuid.UUID, payload: ReminderPatch, db: Session = Depends(get_db),
                    user: User = Depends(current_user)):
    r = _own_reminder(db, reminder_id, user)
    data = payload.model_dump(exclude_unset=True)
    if "due_at" in data and data["due_at"]:
        r.due_at, r.notified_at = _aware(data["due_at"]), None  # snooze / reschedule re-arms it
        r.status = "open"
    if "note" in data:
        r.note = (data["note"] or "").strip() or None
    if data.get("email_me") is not None:
        r.email_me = data["email_me"]
    if data.get("status"):
        r.status = data["status"]
        r.completed_at = datetime.now(timezone.utc) if r.status == "done" else None
    db.commit()
    return _reminder_out(db, r)


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.delete(_own_reminder(db, reminder_id, user))
    db.commit()


# ---- Notifications ----------------------------------------------------------

class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str | None
    link: str | None
    created_at: datetime | None
    read_at: datetime | None
    email_status: str | None


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread: int


def _unread(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None))) or 0


@router.get("/notifications", response_model=NotificationList)
def list_notifications(limit: int = Query(30, ge=1, le=200), unread_only: bool = False,
                       db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = db.scalars(stmt.order_by(Notification.created_at.desc()).limit(limit)).all()
    return NotificationList(items=[NotificationOut.model_validate(n, from_attributes=True) for n in rows],
                            unread=_unread(db, user))


@router.get("/notifications/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return {"unread": _unread(db, user)}


@router.post("/notifications/{notification_id}/read", status_code=204)
def mark_read(notification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.read_at = n.read_at or datetime.now(timezone.utc)
    db.commit()


@router.post("/notifications/read-all", status_code=204)
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
               .values(read_at=datetime.now(timezone.utc)))
    db.commit()


# ---- Outlook ----------------------------------------------------------------

class MailStatus(BaseModel):
    configured: bool
    connected: bool
    email: str | None = None
    display_name: str | None = None
    connected_at: datetime | None = None
    needs_reconnect: bool = False
    last_error: str | None = None
    automation_mailbox: str | None = None
    automation_mailbox_ready: bool = False
    per_minute: int = 25


@router.get("/mail/status", response_model=MailStatus)
def mail_status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    from app.automations.runtime_settings import get_int

    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    return MailStatus(
        configured=outlook.is_configured(), connected=bool(acct), email=acct.email if acct else None,
        display_name=acct.display_name if acct else None, connected_at=acct.connected_at if acct else None,
        needs_reconnect=bool(acct and acct.last_error), last_error=acct.last_error if acct else None,
        automation_mailbox=automation_mailbox(db) or None, automation_mailbox_ready=automation_mailbox_ready(db),
        per_minute=get_int(db, "mail_merge_per_minute"),
    )


@router.get("/mail/outlook/start")
def outlook_start(return_to: str = "/settings", user: User = Depends(current_user)) -> dict:
    try:
        return {"url": outlook.authorize_url(user.id, login_hint=user.email, return_to=return_to)}
    except outlook.OutlookNotConfigured as exc:
        raise HTTPException(400, str(exc))


class CallbackIn(BaseModel):
    code: str
    state: str


@router.post("/mail/outlook/callback")
def outlook_callback(payload: CallbackIn, db: Session = Depends(get_db)) -> dict:
    # No current_user here: the signed state carries who started the sign-in.
    try:
        acct, return_to = outlook.complete_sign_in(db, payload.code, payload.state)
    except (outlook.OutlookAuthError, outlook.OutlookNotConfigured) as exc:
        raise HTTPException(400, str(exc))
    return {"email": acct.email, "return_to": return_to}


@router.delete("/mail/outlook", status_code=204)
def outlook_disconnect(db: Session = Depends(get_db), user: User = Depends(current_user)):
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    if acct:
        db.delete(acct)
        db.commit()


# ---- Templates --------------------------------------------------------------

class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    subject: str | None = Field(default=None, max_length=500)
    body: str = ""
    shared: bool = True


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    subject: str | None
    body: str
    shared: bool
    mine: bool
    owner_name: str | None
    updated_at: datetime | None


def _template_out(db: Session, t: MailTemplate, user: User) -> TemplateOut:
    owner = db.get(User, t.owner_user_id) if t.owner_user_id else None
    return TemplateOut(id=t.id, name=t.name, subject=t.subject, body=t.body, shared=t.shared,
                       mine=t.owner_user_id == user.id, owner_name=owner.name if owner else None, updated_at=t.updated_at)


@router.get("/mail/fields")
def merge_fields() -> list[dict]:
    return [{"key": k, "label": label, "example": ex} for k, (label, ex) in mm.FIELDS.items()]


@router.get("/mail/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(MailTemplate).where(or_(MailTemplate.shared.is_(True), MailTemplate.owner_user_id == user.id))
                      .order_by(func.lower(MailTemplate.name))).all()
    return [_template_out(db, t, user) for t in rows]


@router.post("/mail/templates", response_model=TemplateOut, status_code=201)
def create_template(payload: TemplateIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = MailTemplate(id=uuid.uuid4(), owner_user_id=user.id, **payload.model_dump())
    db.add(t)
    db.commit()
    return _template_out(db, t, user)


def _editable_template(db: Session, tid: uuid.UUID, user: User) -> MailTemplate:
    t = db.get(MailTemplate, tid)
    if not t or not (t.shared or t.owner_user_id == user.id):
        raise HTTPException(404, "Template not found")
    if t.owner_user_id not in (None, user.id) and user.role != "admin":
        raise HTTPException(403, "Only the template's owner (or an admin) can change it - save a copy instead.")
    return t


@router.put("/mail/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: uuid.UUID, payload: TemplateIn, db: Session = Depends(get_db),
                    user: User = Depends(current_user)):
    t = _editable_template(db, template_id, user)
    for k, v in payload.model_dump().items():
        setattr(t, k, v)
    db.commit()
    return _template_out(db, t, user)


@router.delete("/mail/templates/{template_id}", status_code=204)
def delete_template(template_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.delete(_editable_template(db, template_id, user))
    db.commit()


# ---- Recipients -------------------------------------------------------------

class RecipientSource(BaseModel):
    """Act!'s "Select contacts": the current lookup, a group, a company,
    or hand-picked contacts."""
    kind: str = Field(pattern="^(lookup|group|company|contacts)$")
    group_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    contact_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50000)
    q: str | None = None
    source_db: str | None = None
    company: str | None = None
    city: str | None = None
    country: str | None = None
    title: str | None = None
    sort: str = "name"
    desc: bool = False
    conds: str | None = None  # advanced search (JSON), same as the contacts list
    match: str = "all"


class RecipientOut(BaseModel):
    contact_id: uuid.UUID
    name: str
    company: str | None
    email: str | None
    city: str | None
    country: str | None
    has_address: bool
    unsubscribed: bool
    bounced: bool


class RecipientsOut(BaseModel):
    label: str
    total: int
    truncated: bool
    items: list[RecipientOut]


def _resolve(db: Session, src: RecipientSource) -> tuple[list[uuid.UUID], str, bool]:
    limit = settings.mail_merge_max_recipients
    if src.kind == "group":
        g = db.get(Group, src.group_id) if src.group_id else None
        if not g:
            raise HTTPException(404, "Group not found")
        f, label = LookupFilters(group_id=g.id), f"Group: {g.name}"
    elif src.kind == "company":
        c = db.get(Company, src.company_id) if src.company_id else None
        if not c:
            raise HTTPException(404, "Company not found")
        f, label = LookupFilters(company_id=c.id), f"Company: {c.name}"
    elif src.kind == "contacts":
        if not src.contact_ids:
            raise HTTPException(400, "Pick at least one contact.")
        f = LookupFilters(contact_ids=src.contact_ids)
        label = "1 contact" if len(src.contact_ids) == 1 else f"{len(src.contact_ids)} selected contacts"
    else:
        from app.contacts.conditions import BadCondition, parse_conditions
        try:
            conditions = parse_conditions(src.conds)
        except BadCondition as exc:
            raise HTTPException(422, str(exc))
        f = LookupFilters(q=src.q, source_db=src.source_db, company=src.company, city=src.city,
                          country=src.country, title=src.title, sort=src.sort, desc=src.desc,
                          conditions=conditions, match_any=src.match == "any")
        bits = [v for v in (src.q, src.company, src.city, src.country, src.title) if v] + (["advanced search"] if conditions else [])
        label = "Current lookup" + (f": {', '.join(bits)}" if bits else " (all contacts)")
    if src.kind != "lookup":
        f.sort, f.desc = src.sort, src.desc
    ids = lookup_ids(db, f, limit=limit + 1)
    return ids[:limit], label, len(ids) > limit


@router.post("/mail-merge/recipients", response_model=RecipientsOut)
def preview_recipients(src: RecipientSource, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ids, label, truncated = _resolve(db, src)
    items = []
    for cid, c in mm.contexts(db, ids, user):
        items.append(RecipientOut(contact_id=cid, name=c["full_name"] or "(no name)", company=c["company"] or None,
                                  email=c["email"] or None, city=c["city"] or None, country=c["country"] or None,
                                  has_address=bool(c["address_block"]), unsubscribed=c["_unsubscribed"], bounced=c["_bounced"]))
    return RecipientsOut(label=label, total=len(items), truncated=truncated, items=items)


class PreviewIn(BaseModel):
    contact_id: uuid.UUID | None = None
    subject: str | None = None
    body: str = ""


@router.post("/mail-merge/preview")
def preview_render(payload: PreviewIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if payload.contact_id:
        found = mm.contexts(db, [payload.contact_id], user)
        if not found:
            raise HTTPException(404, "Contact not found")
        ctx = found[0][1]
    else:
        ctx = {k: ex for k, (_, ex) in mm.FIELDS.items()} | {"my_name": user.name, "my_email": user.email}
    body = mm.render(payload.body, ctx)
    return {"subject": mm.render(payload.subject or "", ctx), "body": body, "html": mm.to_html(body),
            "unknown_fields": mm.unknown_fields(payload.subject, payload.body)}


# ---- Attachments ------------------------------------------------------------

class AttachmentOut(BaseModel):
    id: uuid.UUID
    filename: str
    size: int
    content_type: str


@router.post("/mail-merge/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(413, "Attachments can be up to 3 MB each - share bigger files as a link instead.")
    a = MailAttachment(id=uuid.uuid4(), uploaded_by_user_id=user.id, filename=(file.filename or "attachment")[:255],
                       content_type=file.content_type or "application/octet-stream", size=len(data), data=data)
    db.add(a)
    db.commit()
    return AttachmentOut(id=a.id, filename=a.filename, size=a.size, content_type=a.content_type)


@router.delete("/mail-merge/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = db.get(MailAttachment, attachment_id)
    if a and a.uploaded_by_user_id == user.id and a.merge_id is None:
        db.delete(a)
        db.commit()


# ---- Run a merge ------------------------------------------------------------

class MergeIn(BaseModel):
    output: str = Field(pattern="^(email|word|labels|data)$")
    source_label: str | None = Field(default=None, max_length=300)
    contact_ids: list[uuid.UUID] = Field(min_length=1, max_length=50000)
    subject: str | None = Field(default=None, max_length=500)
    body: str = ""
    cc: str | None = Field(default=None, max_length=500)
    bcc: str | None = Field(default=None, max_length=500)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    record_history: str = Field(default="email_full", pattern="^(email_full|subject_only|none)$")
    history_regarding: str | None = Field(default=None, max_length=300)
    # Act!'s "If contacts have no e-mail address": skip them, or also make
    # letters for them (the response then tells the UI to download those).
    no_email: str = Field(default="skip", pattern="^(skip|letters)$")
    include_unsubscribed: bool = False
    data_format: str = Field(default="xlsx", pattern="^(xlsx|csv)$")
    test_only: bool = False  # email: send one rendered copy to myself only


class MergeOut(BaseModel):
    id: uuid.UUID
    output: str
    source_label: str | None
    subject: str | None
    status: str
    total: int
    sent: int
    failed: int
    skipped: int
    error: str | None
    from_email: str | None
    created_at: datetime | None
    finished_at: datetime | None
    created_by: str | None = None
    letters_for_no_email: int = 0


def _merge_out(db: Session, m: MailMerge, **extra) -> MergeOut:
    u = db.get(User, m.created_by_user_id) if m.created_by_user_id else None
    return MergeOut(id=m.id, output=m.output, source_label=m.source_label, subject=m.subject, status=m.status,
                    total=m.total, sent=m.sent, failed=m.failed, skipped=m.skipped, error=m.error,
                    from_email=m.from_email, created_at=m.created_at, finished_at=m.finished_at,
                    created_by=u.name if u else None, **extra)


def _eligible(ctx: dict, include_unsub: bool) -> str | None:
    """Reason a contact is skipped for email, or None."""
    if not ctx["email"]:
        return "no email address"
    if ctx["_unsubscribed"] and not include_unsub:
        return "unsubscribed"
    if ctx["_bounced"] and not include_unsub:
        return "email bounced"
    return None


def _docs(db: Session, payload: MergeIn, ctxs: list[tuple[uuid.UUID, dict]], user: User, output: str):
    if output == "labels":
        blocks = [("\n".join(x for x in (c["full_name"], c["company"]) if x) + "\n" + c["address_block"]).strip()
                  for _, c in ctxs if c["address_block"]]
        return mm.labels_docx(blocks), "labels.docx", \
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if output == "data":
        buf = mm.data_file([c for _, c in ctxs], payload.data_format)
        if payload.data_format == "csv":
            return buf, "merge-data.csv", "text/csv"
        return buf, "merge-data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    letters = [mm.to_text(mm.render(payload.body, c)) for _, c in ctxs]
    return mm.letters_docx(letters), "letters.docx", \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/mail-merge")
def run_merge(payload: MergeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """email -> queues the merge and returns it (JSON); word/labels/data ->
    the file itself."""
    if len(payload.contact_ids) > settings.mail_merge_max_recipients:
        raise HTTPException(400, f"A mail merge can go to at most {settings.mail_merge_max_recipients:,} contacts - "
                                 "for bigger mailings export the merge data to Mailchimp.")
    unknown = mm.unknown_fields(payload.subject, payload.body)
    if unknown:
        raise HTTPException(400, f"Unknown merge field(s): {', '.join('{{' + u + '}}' for u in unknown)}")
    ctxs = mm.contexts(db, payload.contact_ids, user)
    if not ctxs:
        raise HTTPException(400, "None of those contacts exist any more.")

    if payload.output != "email":
        buf, filename, ctype = _docs(db, payload, ctxs, user, payload.output)
        if payload.output == "word" and payload.record_history != "none":
            regarding = payload.history_regarding or payload.subject or "Letter"
            for cid, _ in ctxs:
                mm.record_history(db, cid, "Letter Sent", regarding, None, user.id)
            db.add(MailMerge(id=uuid.uuid4(), created_by_user_id=user.id, output="word", source_label=payload.source_label,
                             subject=regarding, body=payload.body, record_history=payload.record_history,
                             history_regarding=regarding, status="done", total=len(ctxs), sent=len(ctxs),
                             finished_at=datetime.now(timezone.utc)))
            db.commit()
        return StreamingResponse(buf, media_type=ctype, headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    # ---- email
    if not (payload.subject or "").strip():
        raise HTTPException(400, "An email needs a subject.")
    acct = db.scalar(select(MailAccount).where(MailAccount.user_id == user.id))
    if not acct:
        raise HTTPException(409, "Connect your Outlook mailbox first (Settings > Email) - mail merge sends from your own account.")
    atts = db.scalars(select(MailAttachment).where(MailAttachment.id.in_(payload.attachment_ids))).all() if payload.attachment_ids else []
    if any(a.uploaded_by_user_id != user.id for a in atts):
        raise HTTPException(403, "Attachment not found")
    if sum(a.size for a in atts) > MAX_ATTACHMENTS_TOTAL:
        raise HTTPException(413, "Attachments add up to more than 3 MB - Outlook can't send that per message.")

    if payload.test_only:
        cid, ctx = ctxs[0]
        try:
            outlook.send_mail(db, acct, to=[acct.email], subject="[TEST] " + mm.render(payload.subject or "", ctx),
                              html_body=mm.to_html(mm.render(payload.body, ctx)),
                              attachments=[(a.filename, a.content_type, a.data) for a in atts])
        except outlook.OutlookAuthError as exc:
            raise HTTPException(409, f"{exc}")
        except Exception as exc:
            raise HTTPException(502, f"Outlook didn't accept the test: {exc}")
        return {"test_sent_to": acct.email, "rendered_for": ctx["full_name"]}

    m = MailMerge(id=uuid.uuid4(), created_by_user_id=user.id, output="email", source_label=payload.source_label,
                  subject=payload.subject, body=payload.body, from_email=acct.email, cc=payload.cc, bcc=payload.bcc,
                  record_history=payload.record_history, history_regarding=payload.history_regarding,
                  status="queued", total=len(ctxs))
    db.add(m)
    db.flush()
    no_email_ids = []
    for cid, ctx in ctxs:
        reason = _eligible(ctx, payload.include_unsubscribed)
        rec = MailMergeRecipient(id=uuid.uuid4(), merge_id=m.id, contact_id=cid, email=ctx["email"] or None,
                                 status="skipped" if reason else "queued", error=reason)
        db.add(rec)
        if reason:
            m.skipped += 1
            if reason == "no email address":
                no_email_ids.append(cid)
    for a in atts:
        a.merge_id = m.id
    if m.skipped == m.total:
        m.status, m.finished_at = "done", datetime.now(timezone.utc)
    db.commit()
    return _merge_out(db, m, letters_for_no_email=len(no_email_ids) if payload.no_email == "letters" else 0)


@router.get("/mail-merge", response_model=list[MergeOut])
def list_merges(mine: bool = True, db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(MailMerge)
    if mine or user.role != "admin":
        stmt = stmt.where(MailMerge.created_by_user_id == user.id)
    return [_merge_out(db, m) for m in db.scalars(stmt.order_by(MailMerge.created_at.desc()).limit(100))]


def _own_merge(db: Session, mid: uuid.UUID, user: User) -> MailMerge:
    m = db.get(MailMerge, mid)
    if not m or (m.created_by_user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Mail merge not found")
    return m


class MergeDetail(MergeOut):
    body: str
    cc: str | None
    bcc: str | None
    record_history: str
    attachments: list[AttachmentOut]
    recipients: list[dict]


@router.get("/mail-merge/{merge_id}", response_model=MergeDetail)
def get_merge(merge_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = _own_merge(db, merge_id, user)
    rows = db.execute(select(MailMergeRecipient, Contact.full_name).outerjoin(Contact, Contact.id == MailMergeRecipient.contact_id)
                      .where(MailMergeRecipient.merge_id == m.id).order_by(MailMergeRecipient.status, Contact.full_name)).all()
    atts = db.scalars(select(MailAttachment).where(MailAttachment.merge_id == m.id)).all()
    base = _merge_out(db, m).model_dump()
    return MergeDetail(**base, body=m.body, cc=m.cc, bcc=m.bcc, record_history=m.record_history,
                       attachments=[AttachmentOut(id=a.id, filename=a.filename, size=a.size, content_type=a.content_type) for a in atts],
                       recipients=[{"contact_id": r.contact_id, "name": name, "email": r.email, "status": r.status,
                                    "error": r.error, "sent_at": r.sent_at} for r, name in rows])


@router.post("/mail-merge/{merge_id}/cancel", response_model=MergeOut)
def cancel_merge(merge_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = _own_merge(db, merge_id, user)
    if m.status in ("queued", "sending", "failed"):
        mm.cancel(db, m)
        db.commit()
    return _merge_out(db, m)


@router.post("/mail-merge/{merge_id}/resume", response_model=MergeOut)
def resume_merge(merge_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """After reconnecting Outlook (or to retry failed messages)."""
    m = _own_merge(db, merge_id, user)
    if m.output != "email" or m.status == "cancelled":
        raise HTTPException(400, "Only a paused or finished email merge can be resumed.")
    retried = db.execute(update(MailMergeRecipient).where(MailMergeRecipient.merge_id == m.id,
                                                          MailMergeRecipient.status == "failed")
                         .values(status="queued", error=None)).rowcount
    m.failed = max(0, m.failed - retried)
    queued = db.scalar(select(func.count()).select_from(MailMergeRecipient).where(
        MailMergeRecipient.merge_id == m.id, MailMergeRecipient.status == "queued")) or 0
    if queued:
        m.status, m.error, m.finished_at = "queued", None, None
    db.commit()
    return _merge_out(db, m)


@router.post("/mail-merge/{merge_id}/letters")
def letters_for_missing_email(merge_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Act!'s "print letters for contacts with no e-mail" - the same
    message as letters for everyone this email merge skipped for having no
    address."""
    m = _own_merge(db, merge_id, user)
    ids = list(db.scalars(select(MailMergeRecipient.contact_id).where(
        MailMergeRecipient.merge_id == m.id, MailMergeRecipient.error == "no email address")))
    ctxs = mm.contexts(db, [i for i in ids if i], user)
    if not ctxs:
        raise HTTPException(404, "Everyone in this merge had an email address.")
    buf = mm.letters_docx([mm.to_text(mm.render(m.body, c)) for _, c in ctxs])
    if m.record_history != "none":
        for cid, _ in ctxs:
            mm.record_history(db, cid, "Letter Sent", m.history_regarding or m.subject, None, user.id)
        db.commit()
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": 'attachment; filename="letters-no-email.docx"'})
