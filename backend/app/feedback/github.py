"""Each piece of feedback as a GitHub issue (optional: GITHUB_FEEDBACK_REPO + GITHUB_FEEDBACK_TOKEN).
Screenshots are saved on their own branch (GITHUB_FEEDBACK_BRANCH) so they show inside the issue, even in a
private repository. Status changes and comments in the app are passed on; fixed / won't do closes the issue."""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.feedback import text
from app.models import Feedback, FeedbackImage

logger = logging.getLogger("app.feedback.github")
API = "https://api.github.com"


def enabled() -> bool:
    return bool(settings.github_feedback_repo.strip() and settings.github_feedback_token.strip())


class GitHubError(Exception):
    pass


def _client() -> httpx.Client:
    return httpx.Client(base_url=API, timeout=30, headers={
        "Authorization": f"Bearer {settings.github_feedback_token.strip()}",
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "bmi-brain-feedback"})


def _check(r: httpx.Response, what: str) -> dict:
    if r.status_code >= 300:
        raise GitHubError(f"{what}: GitHub said {r.status_code} {r.text[:300]}")
    return r.json() if r.content else {}


def _repo() -> str:
    return settings.github_feedback_repo.strip().strip("/")


def _ensure_branch(c: httpx.Client) -> str:
    repo, branch = _repo(), settings.github_feedback_branch.strip() or "feedback-screenshots"
    if c.get(f"/repos/{repo}/branches/{branch}").status_code == 200:
        return branch
    info = _check(c.get(f"/repos/{repo}"), "Reading the repository")
    ref = _check(c.get(f"/repos/{repo}/git/ref/heads/{info['default_branch']}"), "Reading the main branch")
    r = c.post(f"/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": ref["object"]["sha"]})
    if r.status_code not in (201, 422):   # 422: someone else just made it
        _check(r, "Making the screenshots branch")
    return branch


def _upload_images(c: httpx.Client, f: Feedback, images: list[FeedbackImage]) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    if not images:
        return links
    repo = _repo()
    branch = _ensure_branch(c)
    for i, img in enumerate(images, 1):
        if not img.github_url:
            ext = "jpg" if "jpeg" in img.content_type else "png"
            path = f"feedback/{f.number:04d}/{i}.{ext}"
            r = c.put(f"/repos/{repo}/contents/{path}", json={
                "message": f"Feedback #{f.number}: screenshot {i}", "branch": branch,
                "content": base64.b64encode(img.data).decode()})
            if r.status_code == 422:   # already there (a retry)
                pass
            else:
                _check(r, "Saving a screenshot")
            img.github_url = f"https://github.com/{repo}/blob/{branch}/{path}?raw=true"
        links.append((img.label or f"Screenshot {i}", img.github_url))
    return links


def _labels(f: Feedback) -> list[str]:
    return ["feedback", {"broken": "bug", "confusing": "confusing", "idea": "idea", "looks_wrong": "looks wrong"}.get(f.kind, f.kind)]


def sync(db: Session, f: Feedback) -> None:
    """Create the issue, or bring its text, state and labels up to date. Errors are kept on the feedback
    (shown to admins with a Try again button), never raised to the person who sent it."""
    if not enabled():
        return
    images = list(db.query(FeedbackImage).filter(FeedbackImage.feedback_id == f.id).order_by(FeedbackImage.position))
    try:
        with _client() as c:
            links = _upload_images(c, f, images)
            body = text.markdown(f, links)[:60000]
            repo = _repo()
            if f.github_number is None:
                r = c.post(f"/repos/{repo}/issues", json={"title": text.title(f)[:250], "body": body, "labels": _labels(f)})
                if r.status_code == 422:   # labels not allowed for this token
                    r = c.post(f"/repos/{repo}/issues", json={"title": text.title(f)[:250], "body": body})
                issue = _check(r, "Making the issue")
                f.github_number, f.github_url = issue["number"], issue["html_url"]
            else:
                closed = f.status in ("fixed", "wont_do")
                patch = {"title": text.title(f)[:250], "body": body, "state": "closed" if closed else "open"}
                if closed:
                    patch["state_reason"] = "completed" if f.status == "fixed" else "not_planned"
                _check(c.patch(f"/repos/{repo}/issues/{f.github_number}", json=patch), "Updating the issue")
        f.github_error = None
        f.github_synced_at = datetime.now(timezone.utc)
    except (GitHubError, httpx.HTTPError) as e:
        logger.warning("feedback %s: GitHub sync failed: %s", f.number, e)
        f.github_error = str(e)[:1000]


def comment(f: Feedback, who: str, body: str) -> None:
    """Pass a comment or status note on to the issue (best effort)."""
    if not enabled() or not f.github_number:
        return
    try:
        with _client() as c:
            _check(c.post(f"/repos/{_repo()}/issues/{f.github_number}/comments", json={"body": f"**{who}** (in BMI Brain): {body}"}),
                   "Adding a comment")
    except (GitHubError, httpx.HTTPError) as e:
        logger.warning("feedback %s: GitHub comment failed: %s", f.number, e)
