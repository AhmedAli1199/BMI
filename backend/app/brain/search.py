"""The assistant's search over what people have written about clients: notes, history, activities, call notes
and opportunities (docs/ai-hub-plan.md, phase 2).

Indexing (index_pending, run by the brain_index job every 15 minutes):
- One row per piece of text in brain_chunks, with a short header that says what it is - "Note · Caribbean
  Journal · Sarah Jones · 12 Mar 2024" - so a snippet makes sense on its own (contextual retrieval).
- Only new or changed records are picked up: the database compares a fingerprint (md5) of each record's text
  with the one stored, so a run over 100,000 notes is one quick query, not 100,000 reads.
- Long texts (call transcripts, long notes) are split into overlapping parts.
- If pgvector is there and Gemini is set up, each chunk also gets an embedding (meaning search).

Searching (search):
- Access first: only chunks about contacts/companies this person may see, and private ones only for whoever
  wrote them. Then optional narrowing to one company/contact, kinds and dates.
- Keyword ranking (Postgres full text, good for exact rates, dates and names) and meaning ranking (embeddings)
  are merged with reciprocal rank fusion. Without embeddings it's keyword only.
"""
from __future__ import annotations

import logging
import math
import re
import uuid
from datetime import datetime

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import Identity

log = logging.getLogger("app.brain.search")

DIMS = 768
CHUNK_CHARS = 1800
OVERLAP = 200
RRF_K = 60

KIND_LABEL = {"note": "Note", "history": "History", "activity": "Activity", "call": "Call notes", "opportunity": "Opportunity"}

# Each source: one SELECT giving id, contact_id, company_id, source_db, private_to, occurred_at, label, body, plus
# the text expression that's fingerprinted. Notes and history can hang off a contact, a company or an opportunity.
_ENTITY = """
  CASE WHEN {t}.entity_type = 'contact' THEN {t}.entity_id
       WHEN {t}.entity_type = 'opportunity' THEN (SELECT o.contact_id FROM opportunities o WHERE o.id = {t}.entity_id) END AS contact_id,
  CASE WHEN {t}.entity_type = 'company' THEN {t}.entity_id
       WHEN {t}.entity_type = 'contact' THEN (SELECT c.company_id FROM contacts c WHERE c.id = {t}.entity_id)
       WHEN {t}.entity_type = 'opportunity' THEN (SELECT o.company_id FROM opportunities o WHERE o.id = {t}.entity_id) END AS company_id
"""
SOURCES: dict[str, tuple[str, str]] = {
    "note": (
        "coalesce(n.note_type, '') || '|' || coalesce(n.body, '')",
        f"""SELECT n.id, {_ENTITY.format(t='n')}, n.source_db,
                   CASE WHEN n.is_private THEN n.created_by_user_id END AS private_to,
                   n.act_created_at AS occurred_at, coalesce(n.note_type, 'Note') AS label, coalesce(n.body, '') AS body
            FROM notes n WHERE n.entity_type IN ('contact', 'company', 'opportunity') AND coalesce(n.body, '') <> ''""",
    ),
    "history": (
        "h.history_type || '|' || coalesce(h.subject, '') || '|' || coalesce(h.details, '')",
        f"""SELECT h.id, {_ENTITY.format(t='h')}, h.source_db,
                   CASE WHEN h.is_private THEN h.created_by_user_id END AS private_to,
                   h.occurred_at, h.history_type AS label,
                   trim(coalesce(h.subject, '') || E'\\n' || coalesce(h.details, '')) AS body
            FROM history_entries h WHERE h.entity_type IN ('contact', 'company', 'opportunity')
              AND (coalesce(h.subject, '') <> '' OR coalesce(h.details, '') <> '')""",
    ),
    "activity": (
        "coalesce(a.activity_type, '') || '|' || coalesce(a.subject, '') || '|' || coalesce(a.details, '') || '|' || a.start_at::text",
        """SELECT a.id, a.contact_id, coalesce(a.company_id, (SELECT c.company_id FROM contacts c WHERE c.id = a.contact_id)) AS company_id,
                  a.source_db, CASE WHEN a.is_private THEN a.created_by_user_id END AS private_to, a.start_at AS occurred_at,
                  coalesce(a.activity_type, 'Activity') AS label,
                  trim(coalesce(a.subject, '') || E'\\n' || coalesce(a.details, '')) AS body
           FROM activities a WHERE coalesce(a.subject, '') <> '' OR coalesce(a.details, '') <> ''""",
    ),
    "call": (
        "coalesce(r.title, '') || '|' || coalesce(r.notes::text, '')",
        """SELECT r.id, r.contact_id, coalesce(r.company_id, (SELECT c.company_id FROM contacts c WHERE c.id = r.contact_id)) AS company_id,
                  NULL::varchar AS source_db, NULL::uuid AS private_to, coalesce(r.started_at, r.created_at) AS occurred_at,
                  coalesce(r.title, 'Call') AS label, r.notes::text AS body
           FROM call_recordings r WHERE r.status = 'completed' AND r.notes IS NOT NULL""",
    ),
    "opportunity": (
        "coalesce(o.name, '') || '|' || coalesce(o.status, '') || '|' || coalesce(o.stage_name, '') || '|' || coalesce(o.total_amount::text, '') || '|' || coalesce(o.close_reason, '')",
        """SELECT o.id, o.contact_id, coalesce(o.company_id, (SELECT c.company_id FROM contacts c WHERE c.id = o.contact_id)) AS company_id,
                  o.source_db, NULL::uuid AS private_to, coalesce(o.actual_close_at, o.estimated_close_at, o.open_at) AS occurred_at,
                  'Opportunity' AS label,
                  trim(coalesce(o.name, '') || E'\\nStatus: ' || coalesce(o.status, '') || coalesce(' · stage ' || o.stage_name, '')
                       || coalesce(E'\\nValue: £' || o.total_amount::text, '') || coalesce(E'\\nClosed because: ' || o.close_reason, '')) AS body
           FROM opportunities o WHERE coalesce(o.name, '') <> ''""",
    ),
}


def _md5_sql(kind: str) -> str:
    return f"md5({SOURCES[kind][0]})"


def _alias(kind: str) -> str:
    return {"note": "n", "history": "h", "activity": "a", "call": "r", "opportunity": "o"}[kind]


def vector_ready(db: Session) -> bool:
    return bool(db.execute(text(
        "SELECT 1 FROM information_schema.columns WHERE table_name = 'brain_chunks' AND column_name = 'embedding'")).first())


def ensure_vector(db: Session) -> bool:
    """Adds the embedding column the first time pgvector turns up (installed after the migration ran)."""
    if vector_ready(db):
        return True
    if not db.execute(text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).first():
        return False
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.execute(text(f"ALTER TABLE brain_chunks ADD COLUMN IF NOT EXISTS embedding vector({DIMS})"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_brain_chunks_embedding ON brain_chunks USING hnsw (embedding vector_cosine_ops)"))
        db.commit()
        return True
    except Exception:
        db.rollback()
        log.warning("pgvector is available but couldn't be enabled - searching by keyword only")
        return False


# ---- turning text into pieces ------------------------------------------------------------------

_TAGS = re.compile(r"<[^>]+>")


def clean(body: str) -> str:
    """Notes copied from Outlook can be HTML or RTF; keep the words."""
    s = body or ""
    if s.lstrip().startswith("{\\rtf"):
        s = re.sub(r"\\[a-z]+-?\d* ?|[{}]", " ", s)
    s = _TAGS.sub(" ", s).replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", s)).strip()


def call_text(raw: str) -> str:
    """Call notes are stored as JSON (summary, decisions, actions...); flatten them to readable lines."""
    import json
    try:
        d = json.loads(raw)
    except (TypeError, ValueError):
        return raw or ""
    out = []
    for k, v in (d.items() if isinstance(d, dict) else []):
        if isinstance(v, list):
            items = [x if isinstance(x, str) else " - ".join(str(y) for y in x.values() if y) if isinstance(x, dict) else str(x) for x in v]
            if items:
                out.append(f"{k.replace('_', ' ').capitalize()}: " + "; ".join(items))
        elif v:
            out.append(f"{k.replace('_', ' ').capitalize()}: {v}")
    return "\n".join(out)


def pieces(body: str) -> list[str]:
    body = body.strip()
    if len(body) <= CHUNK_CHARS:
        return [body] if body else []
    out, start = [], 0
    while start < len(body):
        end = min(len(body), start + CHUNK_CHARS)
        if end < len(body):   # end on a sentence or line where possible
            cut = max(body.rfind("\n", start + CHUNK_CHARS // 2, end), body.rfind(". ", start + CHUNK_CHARS // 2, end))
            end = cut + 1 if cut > 0 else end
        out.append(body[start:end].strip())
        if end >= len(body):
            break
        start = max(end - OVERLAP, start + 1)
    return [p for p in out if p]


# ---- embeddings ----------------------------------------------------------------------------------

_embedder = None   # tests put a function here: list[str], task -> list[list[float]]


def set_embedder(fn) -> None:
    global _embedder
    _embedder = fn


def _gemini_embed(texts: list[str], task: str) -> list[list[float]] | None:
    if not settings.gemini_api_key:
        return None
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.gemini_api_key)
    res = client.models.embed_content(model=settings.brain_embedding_model, contents=texts,
                                      config=types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS))
    return [list(e.values) for e in res.embeddings]


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]] | None:
    """Unit-length vectors (only full-size Gemini embeddings come normalised), or None when not available."""
    if not texts:
        return []
    try:
        vecs = (_embedder or _gemini_embed)(texts, task)
    except Exception:
        log.exception("embedding failed")
        return None
    if not vecs:
        return None
    out = []
    for v in vecs:
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


# ---- indexing ----------------------------------------------------------------------------------

def _names(db: Session, contact_ids: set, company_ids: set) -> tuple[dict, dict]:
    people = dict(db.execute(text("SELECT id, coalesce(full_name, trim(coalesce(first_name,'') || ' ' || coalesce(last_name,''))) FROM contacts WHERE id = ANY(:ids)"),
                             {"ids": list(contact_ids)}).all()) if contact_ids else {}
    firms = dict(db.execute(text("SELECT id, name FROM companies WHERE id = ANY(:ids)"), {"ids": list(company_ids)}).all()) if company_ids else {}
    return people, firms


def header(kind: str, label: str, firm: str | None, person: str | None, when: datetime | None) -> str:
    bits = [KIND_LABEL.get(kind, kind) if label in (None, "", KIND_LABEL.get(kind)) else f"{KIND_LABEL.get(kind, kind)} ({label})"]
    bits += [b for b in (firm, person) if b]
    if when:
        bits.append(f"{when:%-d %b %Y}")
    return " · ".join(bits)


def index_pending(db: Session, limit: int = 400, *, remove_gone: bool = True) -> dict:
    """Adds or refreshes chunks for records that are new or changed since they were indexed, removes chunks
    whose record has gone (unless remove_gone is off), and embeds anything not yet embedded. Safe to run as often as
    you like. "more" says a list hit the limit, so another batch has work to do.

    A record with no words left once cleaned (a note that's only formatting) still gets an empty part-0 chunk, so it
    counts as done: without it, every run picked it up again. Searches skip empty chunks."""
    out = {"indexed": 0, "removed": 0, "embedded": 0, "more": False}
    for kind, (fingerprint, sql) in SOURCES.items():
        a = _alias(kind)
        rows = db.execute(text(f"""
            WITH src AS ({sql.replace(f"SELECT {a}.id,", f"SELECT {a}.id, md5({fingerprint}) AS fp,", 1)})
            SELECT src.* FROM src
            LEFT JOIN brain_chunks c ON c.source_type = :kind AND c.source_id = src.id AND c.part = 0
            WHERE c.id IS NULL OR c.hash <> src.fp
            LIMIT :lim"""), {"kind": kind, "lim": limit}).mappings().all()
        out["more"] = out["more"] or len(rows) >= limit
        if rows:
            people, firms = _names(db, {r["contact_id"] for r in rows if r["contact_id"]}, {r["company_id"] for r in rows if r["company_id"]})
            ids = [r["id"] for r in rows]
            db.execute(text("DELETE FROM brain_chunks WHERE source_type = :kind AND source_id = ANY(:ids)"), {"kind": kind, "ids": ids})
            for r in rows:
                body = call_text(r["body"]) if kind == "call" else clean(r["body"])
                head = header(kind, r["label"], firms.get(r["company_id"]), people.get(r["contact_id"]), r["occurred_at"])
                for i, part in enumerate(pieces(body) or [""]):
                    db.execute(text("""INSERT INTO brain_chunks (id, source_type, source_id, part, contact_id, company_id, source_db,
                                       private_to, occurred_at, header, body, hash, embedded, indexed_at)
                                       VALUES (:id, :kind, :sid, :part, :contact, :company, :db, :priv, :at, :head, :body, :hash, false, now())"""),
                               {"id": uuid.uuid4(), "kind": kind, "sid": r["id"], "part": i, "contact": r["contact_id"], "company": r["company_id"],
                                "db": r["source_db"], "priv": r["private_to"], "at": r["occurred_at"], "head": head, "body": part, "hash": r["fp"]})
                out["indexed"] += 1
        if remove_gone:   # records that no longer exist (or no longer have text)
            gone = db.execute(text(f"""DELETE FROM brain_chunks c WHERE c.source_type = :kind
                                       AND NOT EXISTS (SELECT 1 FROM ({sql}) src WHERE src.id = c.source_id)"""), {"kind": kind})
            out["removed"] += gone.rowcount or 0
        db.commit()
    if ensure_vector(db):
        todo = db.execute(text("SELECT id, header, body FROM brain_chunks WHERE NOT embedded AND body <> '' ORDER BY indexed_at LIMIT :lim"),
                          {"lim": limit}).all()
        for i in range(0, len(todo), 50):
            batch = todo[i:i + 50]
            vecs = embed([f"{h}\n{b}" for _, h, b in batch])
            if vecs is None:
                break
            for (cid, _, _), v in zip(batch, vecs):
                db.execute(text("UPDATE brain_chunks SET embedding = CAST(:v AS vector), embedded = true WHERE id = :id"), {"v": _vec(v), "id": cid})
                out["embedded"] += 1
            db.commit()
        out["more"] = out["more"] or (len(todo) >= limit and out["embedded"] == len(todo))   # not when embedding failed
    return out


# ---- searching ---------------------------------------------------------------------------------

def _access(db: Session, identity: Identity) -> tuple[str, dict]:
    """SQL condition on brain_chunks c for what this person may see (same rules as the contact and company pages)."""
    from app.core import visibility as vis
    g = vis.grants(db, identity)
    params: dict = {"me": identity.user_uuid}
    priv = "(c.private_to IS NULL OR c.private_to = :me)"
    if g.unrestricted:
        return priv, params
    params.update(dbs=list(g.full_dbs), groups=list(g.groups))
    seen_contact = ("c.contact_id IN (SELECT id FROM contacts WHERE source_db = ANY(:dbs) "
                    "OR id IN (SELECT contact_id FROM group_memberships WHERE group_id = ANY(:groups)))")
    seen_company = ("c.company_id IN (SELECT id FROM companies WHERE source_db = ANY(:dbs) OR id IN (SELECT company_id FROM contacts "
                    "WHERE company_id IS NOT NULL AND id IN (SELECT contact_id FROM group_memberships WHERE group_id = ANY(:groups))))")
    return (f"{priv} AND ((c.contact_id IS NOT NULL AND {seen_contact}) OR (c.contact_id IS NULL AND c.company_id IS NOT NULL AND {seen_company}))",
            params)


def search(db: Session, identity: Identity, query: str, *, company_id: uuid.UUID | None = None, contact_id: uuid.UUID | None = None,
           kinds: list[str] | None = None, since: datetime | None = None, until: datetime | None = None, limit: int = 8) -> list[dict]:
    where, params = _access(db, identity)
    conds = [where, "c.body <> ''"]
    if company_id:
        conds.append("c.company_id = :company")
        params["company"] = company_id
    if contact_id:
        conds.append("c.contact_id = :contact")
        params["contact"] = contact_id
    if kinds:
        conds.append("c.source_type = ANY(:kinds)")
        params["kinds"] = [k for k in kinds if k in SOURCES]
    if since:
        conds.append("c.occurred_at >= :since")
        params["since"] = since
    if until:
        conds.append("c.occurred_at <= :until")
        params["until"] = until
    flt = " AND ".join(conds)
    ranked: dict[uuid.UUID, float] = {}
    q = (query or "").strip()
    if q:
        params["q"] = q
        kw = db.execute(text(f"""SELECT c.id FROM brain_chunks c WHERE {flt} AND c.tsv @@ websearch_to_tsquery('english', :q)
                                 ORDER BY ts_rank_cd(c.tsv, websearch_to_tsquery('english', :q)) DESC, c.occurred_at DESC NULLS LAST LIMIT 30"""), params).scalars().all()
        if not kw:   # every word didn't match: any of them will do
            params["qor"] = " OR ".join(w for w in re.findall(r"\w{3,}", q))
            if params["qor"]:
                kw = db.execute(text(f"""SELECT c.id FROM brain_chunks c WHERE {flt} AND c.tsv @@ websearch_to_tsquery('english', :qor)
                                         ORDER BY ts_rank_cd(c.tsv, websearch_to_tsquery('english', :qor)) DESC LIMIT 30"""), params).scalars().all()
        for i, cid in enumerate(kw):
            ranked[cid] = ranked.get(cid, 0) + 1 / (RRF_K + i + 1)
        if vector_ready(db):
            qv = embed([q], "RETRIEVAL_QUERY")
            if qv:
                params["qv"] = _vec(qv[0])
                sem = db.execute(text(f"""SELECT c.id FROM brain_chunks c WHERE {flt} AND c.embedding IS NOT NULL
                                          ORDER BY c.embedding <=> CAST(:qv AS vector) LIMIT 30"""), params).scalars().all()
                for i, cid in enumerate(sem):
                    ranked[cid] = ranked.get(cid, 0) + 1 / (RRF_K + i + 1)
    else:   # nothing to look for: the latest about that client
        latest = db.execute(text(f"SELECT c.id FROM brain_chunks c WHERE {flt} ORDER BY c.occurred_at DESC NULLS LAST LIMIT :n"),
                            {**params, "n": limit}).scalars().all()
        ranked = {cid: 1.0 / (i + 1) for i, cid in enumerate(latest)}
    top = sorted(ranked, key=lambda k: -ranked[k])[:limit]
    if not top:
        return []
    rows = {r["id"]: r for r in db.execute(text("""SELECT id, source_type, source_id, contact_id, company_id, occurred_at, header, body
                                                   FROM brain_chunks WHERE id = ANY(:ids)""").bindparams(bindparam("ids")), {"ids": top}).mappings()}
    out = []
    for cid in top:
        r = rows[cid]
        link = (f"/calls/{r['source_id']}" if r["source_type"] == "call" else f"/contacts/{r['contact_id']}" if r["contact_id"]
                else f"/companies/{r['company_id']}" if r["company_id"] else None)
        out.append({"what": r["header"], "kind": r["source_type"], "date": r["occurred_at"].strftime("%-d %b %Y") if r["occurred_at"] else None,
                    "text": r["body"][:900], "link": link})
    return out


def stats(db: Session) -> dict:
    row = db.execute(text("SELECT count(*) FILTER (WHERE body <> ''), count(*) FILTER (WHERE embedded), max(indexed_at) FROM brain_chunks")).one()
    return {"chunks": row[0], "embedded": row[1], "last_indexed": row[2], "meaning_search": vector_ready(db)}

