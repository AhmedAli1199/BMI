"""Feedback from testers (app/models/feedback.py): send it from any page, see everyone's on one board,
"me too", comments, status, the download, and (optionally) a GitHub issue for each."""
from __future__ import annotations

import base64
import io
import json
import re
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.routes.messaging import current_user
from app.db.session import SessionLocal, get_db
from app.feedback import github, text
from app.models import Feedback, FeedbackImage, User
from app.models.feedback import FEEDBACK_KINDS, FEEDBACK_STATUSES
from app.services.notify import create_notification

router = APIRouter(prefix="/feedback", tags=["feedback"])

MAX_IMAGES = 6
MAX_IMAGE_BYTES = 4 * 1024 * 1024
DATA_URL = re.compile(r"^data:(image/(?:png|jpeg));base64,(.+)$", re.S)
WORD = re.compile(r"[a-z0-9]{4,}")


def _is_manager(u: User) -> bool:
    return u.role in ("admin", "data_manager")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _out(f: Feedback, me: User, images: list[FeedbackImage] | None = None, full: bool = False) -> dict:
    mine = str(f.user_id) == str(me.id) if f.user_id else False
    d = {
        "id": str(f.id), "number": f.number, "kind": f.kind, "kind_label": text.KIND_LABEL.get(f.kind, f.kind),
        "message": f.message, "page_path": f.page_path, "page_title": f.page_title,
        "user_name": f.user_name, "user_role": f.user_role, "mine": mine,
        "elements": f.elements or [], "status": f.status, "status_label": text.STATUS_LABEL.get(f.status, f.status),
        "status_note": f.status_note, "status_by": f.status_by, "status_at": f.status_at.isoformat() if f.status_at else None,
        "me_too": [m.get("name") for m in f.me_too or []], "me_too_mine": any(m.get("user_id") == str(me.id) for m in f.me_too or []),
        "comment_count": len(f.comments or []),
        "created_at": f.created_at.isoformat() if f.created_at else None, "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        "github_url": f.github_url,
        "images": [{"id": str(i.id), "label": i.label, "width": i.width, "height": i.height} for i in images or []],
        "can_edit": mine or _is_manager(me), "can_set_status": _is_manager(me),
        "can_delete": _is_manager(me) or (mine and f.status == "new"),
    }
    if full:
        d["comments"] = f.comments or []
        # What the browser saw is for the people fixing things, not everyone.
        d["context"] = (f.context or {}) if _is_manager(me) or mine else {}
        d["github_error"] = "GitHub didn't take this one." if f.github_error and _is_manager(me) else None
    return d


def _images_for(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[FeedbackImage]]:
    out: dict[uuid.UUID, list[FeedbackImage]] = {i: [] for i in ids}
    if not ids:
        return out
    # Only the small details, not the pictures themselves.
    rows = db.query(FeedbackImage.id, FeedbackImage.feedback_id, FeedbackImage.label, FeedbackImage.width, FeedbackImage.height,
                    FeedbackImage.position).filter(FeedbackImage.feedback_id.in_(ids)).order_by(FeedbackImage.position)
    for r in rows:
        out[r.feedback_id].append(r)  # type: ignore[arg-type]
    return out


def _sync_later(feedback_id: uuid.UUID, comment: tuple[str, str] | None = None) -> None:
    if not github.enabled():
        return
    db = SessionLocal()
    try:
        f = db.get(Feedback, feedback_id)
        if not f:
            return
        github.sync(db, f)
        if comment:
            github.comment(f, *comment)
        db.commit()
    finally:
        db.close()


def _notify(db: Session, f: Feedback, title: str, body: str | None, skip: uuid.UUID | None) -> None:
    people = {str(f.user_id)} if f.user_id else set()
    people |= {m.get("user_id") for m in f.me_too or [] if m.get("user_id")}
    for uid in people - {str(skip) if skip else ""}:
        try:
            create_notification(db, uuid.UUID(uid), "feedback", title, body, link=f"/feedback?open={f.id}", email=False)
        except ValueError:
            continue


# ---- Sending ------------------------------------------------------------------

class ImageIn(BaseModel):
    data: str = Field(max_length=7_000_000)
    label: str | None = Field(default=None, max_length=300)
    width: int | None = None
    height: int | None = None


class FeedbackIn(BaseModel):
    kind: str = "broken"
    message: str = Field(default="", max_length=8000)
    page_path: str = Field(default="/", max_length=500)
    page_title: str | None = Field(default=None, max_length=300)
    page_url: str | None = Field(default=None, max_length=1000)
    elements: list[dict] = Field(default_factory=list, max_length=10)
    context: dict = Field(default_factory=dict)
    images: list[ImageIn] = Field(default_factory=list)


def _clean_elements(items: list[dict]) -> list[dict]:
    keep = ("label", "role", "text", "selector", "path", "heading", "source", "rect", "viewport")
    out = []
    for e in items[:10]:
        d = {k: e.get(k) for k in keep if e.get(k) not in (None, "", [])}
        for k in ("label", "role", "heading", "path"):
            if isinstance(d.get(k), str):
                d[k] = d[k][:300]
        if isinstance(d.get("text"), str):
            d["text"] = d["text"][:500]
        if isinstance(d.get("selector"), str):
            d["selector"] = d["selector"][:1000]
        if isinstance(d.get("source"), list):
            d["source"] = [str(s)[:200] for s in d["source"][:6]]
        out.append(d)
    return out


def _clean_context(ctx: dict) -> dict:
    out = {k: str(ctx[k])[:300] for k in ("browser", "viewport", "screen", "zoom", "theme", "time_zone", "app_version", "language") if ctx.get(k)}
    errs = ctx.get("errors") if isinstance(ctx.get("errors"), list) else []
    out["errors"] = [{"at": str(e.get("at", ""))[:40], "kind": str(e.get("kind", ""))[:40], "message": str(e.get("message", ""))[:1000]}
                     for e in errs[-20:] if isinstance(e, dict)]
    return out


@router.post("")
def send(p: FeedbackIn, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if p.kind not in FEEDBACK_KINDS:
        raise HTTPException(422, "Choose what kind of feedback this is.")
    if not p.message.strip() and not p.elements and not p.images:
        raise HTTPException(422, "Say what's wrong, point at something, or add a screenshot first.")
    if len(p.images) > MAX_IMAGES:
        raise HTTPException(422, f"Add up to {MAX_IMAGES} screenshots.")
    pics = []
    for img in p.images:
        m = DATA_URL.match(img.data.strip())
        if not m:
            raise HTTPException(422, "One of the screenshots couldn't be read. Try taking it again.")
        raw = base64.b64decode(m.group(2), validate=False)
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(422, "One of the screenshots is too big. Try a smaller area.")
        pics.append((m.group(1), raw, img))
    path = (p.page_path or "/").split("#")[0][:500] or "/"
    f = Feedback(id=uuid.uuid4(), user_id=user.id, user_name=user.name, user_role=user.role, kind=p.kind, message=p.message.strip(),
                 page_path=path, page_title=(p.page_title or "")[:300] or None, page_url=p.page_url, elements=_clean_elements(p.elements),
                 context=_clean_context(p.context), status="new", me_too=[], comments=[])
    db.add(f)
    db.flush()
    for i, (ctype, raw, img) in enumerate(pics):
        db.add(FeedbackImage(id=uuid.uuid4(), feedback_id=f.id, position=i, label=(img.label or f"Screenshot {i + 1}")[:300],
                             content_type=ctype, data=raw, width=img.width, height=img.height))
    # Let the people who look after the app know (in the app, no email).
    for uid in db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True), User.id != user.id)):
        create_notification(db, uid, "feedback", f"New feedback #{f.number} from {user.name}", (f.message or "")[:200] or None,
                            link=f"/feedback?open={f.id}", email=False)
    db.commit()
    db.refresh(f)
    background.add_task(_sync_later, f.id)
    return _out(f, user, list(db.query(FeedbackImage).filter_by(feedback_id=f.id).order_by(FeedbackImage.position)), full=True)


# ---- The board ----------------------------------------------------------------

def _filtered(db: Session, status: str | None, kind: str | None, path: str | None, mine: bool, q: str | None, user: User,
              since: datetime | None = None):
    stmt = select(Feedback)
    if status == "open":
        stmt = stmt.where(Feedback.status.in_(("new", "looking")))
    elif status == "closed":
        stmt = stmt.where(Feedback.status.in_(("fixed", "wont_do")))
    elif status in FEEDBACK_STATUSES:
        stmt = stmt.where(Feedback.status == status)
    if kind in FEEDBACK_KINDS:
        stmt = stmt.where(Feedback.kind == kind)
    if path:
        stmt = stmt.where(Feedback.page_path == path)
    if mine:
        stmt = stmt.where(Feedback.user_id == user.id)
    if since:
        stmt = stmt.where(Feedback.created_at >= since)
    if q and q.strip():
        like = f"%{q.strip()}%"
        num = q.strip().lstrip("#")
        conds = [Feedback.message.ilike(like), Feedback.page_path.ilike(like), Feedback.page_title.ilike(like), Feedback.user_name.ilike(like)]
        if num.isdigit():
            conds.append(Feedback.number == int(num))
        stmt = stmt.where(or_(*conds))
    return stmt


@router.get("")
def board(status: str | None = None, kind: str | None = None, path: str | None = None, mine: bool = False, q: str | None = None,
          sort: str = "new", limit: int = Query(default=60, le=200), offset: int = 0,
          db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    stmt = _filtered(db, status, kind, path, mine, q, user)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if sort == "votes":
        stmt = stmt.order_by(func.jsonb_array_length(Feedback.me_too).desc(), Feedback.created_at.desc())
    elif sort == "updated":
        stmt = stmt.order_by(Feedback.updated_at.desc())
    elif sort == "old":
        stmt = stmt.order_by(Feedback.created_at)
    else:
        stmt = stmt.order_by(Feedback.created_at.desc())
    rows = list(db.scalars(stmt.offset(offset).limit(limit)))
    imgs = _images_for(db, [r.id for r in rows])
    counts = dict(db.execute(select(Feedback.status, func.count()).group_by(Feedback.status)).all())
    pages = [{"path": p, "title": t, "count": n} for p, t, n in db.execute(
        select(Feedback.page_path, func.max(Feedback.page_title), func.count()).where(Feedback.status.in_(("new", "looking")))
        .group_by(Feedback.page_path).order_by(func.count().desc()).limit(30)).all()]
    return {"items": [_out(r, user, imgs.get(r.id)) for r in rows], "total": total,
            "counts": {s: counts.get(s, 0) for s in FEEDBACK_STATUSES}, "pages": pages,
            "github": github.enabled(), "can_manage": _is_manager(user)}


@router.get("/similar")
def similar(path: str = "/", q: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    """Open feedback that might be the same thing: this page first, then anything with the same words."""
    words = set(WORD.findall(q.lower()))
    rows = list(db.scalars(select(Feedback).where(Feedback.status.in_(("new", "looking"))).order_by(Feedback.created_at.desc()).limit(300)))

    def score(f: Feedback) -> float:
        theirs = set(WORD.findall((f.message or "").lower() + " " + " ".join(str(e.get("label", "")) for e in f.elements or []).lower()))
        overlap = len(words & theirs) / max(1, len(words | theirs)) if words else 0
        return (1.0 if f.page_path == path else 0) + 2 * overlap

    ranked = sorted((r for r in rows if score(r) > (0.15 if words else 0.5)), key=score, reverse=True)[:5]
    imgs = _images_for(db, [r.id for r in ranked])
    return [_out(r, user, imgs.get(r.id)) for r in ranked]


@router.get("/pins")
def pins(path: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    """Open feedback about this page, with what was pointed at - shown as numbered dots on the page."""
    rows = list(db.scalars(select(Feedback).where(Feedback.page_path == path, Feedback.status.in_(("new", "looking")))
                           .order_by(Feedback.created_at.desc()).limit(50)))
    return [{"id": str(f.id), "number": f.number, "kind": f.kind, "kind_label": text.KIND_LABEL.get(f.kind, f.kind),
             "message": (f.message or "")[:200], "user_name": f.user_name, "status": f.status, "me_too": len(f.me_too or []),
             "elements": [{"label": e.get("label"), "selector": e.get("selector"), "rect": e.get("rect"), "viewport": e.get("viewport")}
                          for e in f.elements or []]} for f in rows]


@router.get("/export")
def export(status: str | None = None, kind: str | None = None, path: str | None = None, mine: bool = False, q: str | None = None,
           since: datetime | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Download feedback: a zip with feedback.md (to read), feedback.json (everything) and the screenshots.
    Built a piece at a time, so a very long list doesn't run out of memory."""
    ids = list(db.scalars(_filtered(db, status, kind, path, mine, q, user, since).with_only_columns(Feedback.id).order_by(Feedback.number)))
    spool = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    count = 0
    with zipfile.ZipFile(spool, "w", zipfile.ZIP_DEFLATED) as z:
        md = io.StringIO()
        md.write(f"# BMI Brain feedback\n\nDownloaded {_now():%d %b %Y %H:%M} UTC by {user.name}.\n\n")
        items = []
        for start in range(0, len(ids), 50):
            for f in db.scalars(select(Feedback).where(Feedback.id.in_(ids[start:start + 50])).order_by(Feedback.number)):
                count += 1
                links = []
                imgs = list(db.query(FeedbackImage).filter_by(feedback_id=f.id).order_by(FeedbackImage.position))
                for i, img in enumerate(imgs, 1):
                    name = f"images/{f.number:04d}-{i}.{'jpg' if 'jpeg' in img.content_type else 'png'}"
                    z.writestr(name, img.data)
                    links.append((img.label or f"Screenshot {i}", name))
                md.write(f"\n---\n\n## #{f.number} {text.title(f).split(': ', 1)[-1]}\n\n{text.markdown(f, links)}\n")
                items.append({**_out(f, user, full=True), "context": f.context or {}, "page_url": f.page_url,
                              "screenshots": [n for _, n in links]})
                for x in (*imgs, f):   # let go of the pictures as we go
                    db.expunge(x)
        if not count:
            md.write("\nNothing matched.\n")
        z.writestr("feedback.md", md.getvalue())
        z.writestr("feedback.json", json.dumps(items, indent=2, default=str))
    spool.seek(0)

    def chunks():
        try:
            while block := spool.read(1024 * 1024):
                yield block
        finally:
            spool.close()

    return StreamingResponse(chunks(), media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="feedback-{_now():%Y-%m-%d}.zip"'})


@router.get("/images/{image_id}")
def image(image_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    img = db.get(FeedbackImage, image_id)
    if not img:
        raise HTTPException(404, "That screenshot isn't there any more.")
    return Response(img.data, media_type=img.content_type, headers={"Cache-Control": "private, max-age=86400"})


def _get(db: Session, fid: uuid.UUID) -> Feedback:
    f = db.get(Feedback, fid)
    if not f:
        raise HTTPException(404, "That feedback isn't there any more.")
    return f


def _full(db: Session, f: Feedback, user: User) -> dict:
    return _out(f, user, list(_images_for(db, [f.id])[f.id]), full=True)


@router.get("/{fid}")
def one(fid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return _full(db, _get(db, fid), user)


@router.post("/{fid}/me-too")
def me_too(fid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    f = _get(db, fid)
    if f.user_id == user.id:
        raise HTTPException(422, "This is your own feedback.")
    have = [m for m in f.me_too or [] if m.get("user_id") != str(user.id)]
    if len(have) == len(f.me_too or []):
        have.append({"user_id": str(user.id), "name": user.name, "at": _now().isoformat()})
    f.me_too = have
    db.commit()
    return _full(db, f, user)


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@router.post("/{fid}/comments")
def add_comment(fid: uuid.UUID, p: CommentIn, background: BackgroundTasks, db: Session = Depends(get_db),
                user: User = Depends(current_user)) -> dict:
    f = _get(db, fid)
    f.comments = [*(f.comments or []), {"id": uuid.uuid4().hex[:12], "user_id": str(user.id), "name": user.name,
                                        "text": p.text.strip(), "at": _now().isoformat()}]
    f.updated_at = _now()
    _notify(db, f, f"{user.name} commented on feedback #{f.number}", p.text.strip()[:200], skip=user.id)
    db.commit()
    background.add_task(_sync_later, f.id, (user.name, p.text.strip()))
    return _full(db, f, user)


class StatusIn(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=4000)


@router.put("/{fid}/status")
def set_status(fid: uuid.UUID, p: StatusIn, background: BackgroundTasks, db: Session = Depends(get_db),
               user: User = Depends(current_user)) -> dict:
    if not _is_manager(user):
        raise HTTPException(403, "Only administrators and data managers can change where feedback is up to.")
    if p.status not in FEEDBACK_STATUSES:
        raise HTTPException(422, "Choose a status.")
    f = _get(db, fid)
    changed = f.status != p.status
    f.status, f.status_note, f.status_by, f.status_at = p.status, (p.note or "").strip() or None, user.name, _now()
    if changed:
        label = text.STATUS_LABEL[p.status]
        _notify(db, f, f"Your feedback #{f.number}: {label}", f.status_note, skip=user.id)
    db.commit()
    note = f"Status: {text.STATUS_LABEL[p.status]}" + (f" - {f.status_note}" if f.status_note else "")
    background.add_task(_sync_later, f.id, (user.name, note) if changed else None)
    return _full(db, f, user)


class EditIn(BaseModel):
    kind: str | None = None
    message: str | None = Field(default=None, max_length=8000)


@router.put("/{fid}")
def edit(fid: uuid.UUID, p: EditIn, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    f = _get(db, fid)
    if f.user_id != user.id and not _is_manager(user):
        raise HTTPException(403, "Only the person who sent it can change it.")
    if p.kind is not None:
        if p.kind not in FEEDBACK_KINDS:
            raise HTTPException(422, "Choose what kind of feedback this is.")
        f.kind = p.kind
    if p.message is not None:
        f.message = p.message.strip()
    db.commit()
    background.add_task(_sync_later, f.id)
    return _full(db, f, user)


@router.delete("/{fid}")
def delete(fid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    f = _get(db, fid)
    if not (_is_manager(user) or (f.user_id == user.id and f.status == "new")):
        raise HTTPException(403, "Only administrators can delete feedback once someone is looking at it.")
    db.delete(f)
    db.commit()
    return {"ok": True}


@router.post("/{fid}/github")
def retry_github(fid: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not _is_manager(user):
        raise HTTPException(403, "Only administrators can do this.")
    if not github.enabled():
        raise HTTPException(422, "GitHub isn't connected yet.")
    f = _get(db, fid)
    github.sync(db, f)
    db.commit()
    if f.github_error:
        raise HTTPException(502, "GitHub didn't take it. Check the token and the repository name, then try again.")
    return _full(db, f, user)
