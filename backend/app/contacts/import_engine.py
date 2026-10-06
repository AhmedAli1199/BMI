"""Turns mapped spreadsheet rows into contacts: tidying, checking, finding
people who are already in the CRM, and saving.

Three steps, all driven by the same row drafts so what the review screen shows
is exactly what gets saved:

  build_drafts()  - clean each row into a draft (names split, emails/phones
                    validated, postcode upper-cased...) and list its problems
  analyse()       - decide for each row: new / update an existing contact /
                    skip (already there, repeated in the file, or unusable)
  commit()        - write it, remembering enough to undo

Nothing here guesses a value that isn't in the file.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.contacts.import_mapper import EMAIL_RE, PREFIXES, UK_POST_RE
from app.models import Company, Contact, ContactImport, Email, Group, GroupMembership, Note
from app.models.contact_channel import Address, Phone

DEFAULT_OPTIONS = {
    "source_db": None,           # which database the contacts go into (required before import)
    "on_duplicate": "fill_blanks",  # skip | fill_blanks | overwrite | create
    "create_companies": True,    # companies that aren't in the CRM yet are created
    "group_id": None,            # add everyone to this existing group...
    "new_group_name": None,      # ...or to a new group with this name
}
ON_DUPLICATE = ("skip", "fill_blanks", "overwrite", "create")

PHONE_TYPES = {"phone": "Business", "mobile": "Mobile", "home_phone": "Home", "fax": "Fax", "other_phone": "Other"}
PARTICLES = {"van", "von", "de", "der", "den", "da", "di", "del", "della", "le", "la", "du", "bin", "ibn", "al", "st", "ten", "ter", "mac"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "mba", "mbe", "obe", "cbe", "frsa", "msc", "bsc", "esq", "md", "cta", "fcca", "acca", "cima"}
EMPTY_WORDS = {"n/a", "na", "none", "null", "nil", "-", "--", "tbc", "unknown", "?", "x"}
TRUE_WORDS = {"yes", "y", "true", "1", "x", "opt out", "opted out", "unsubscribed", "unsubscribe", "do not email", "dnc", "suppressed"}


# ---- cleaning helpers -----------------------------------------------------------------

def tidy_name(v: str | None) -> str | None:
    """"JOHN SMITH" / "john smith" -> "John Smith". Names that already have mixed case are left alone."""
    if not v:
        return None
    v = re.sub(r"\s+", " ", v).strip()
    if v and (v.isupper() or v.islower()):
        v = " ".join(_cap(w) for w in v.split(" "))
    return v or None


def _cap(w: str) -> str:
    out = "-".join(p[:1].upper() + p[1:].lower() for p in w.split("-"))
    out = re.sub(r"^(Mc)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    out = re.sub(r"^(O')([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out if w.lower() not in PARTICLES else w.lower()


def split_name(full: str) -> dict:
    """"Dr Ann Marie van der Berg Jr" -> prefix Dr, first Ann, middle Marie, last van der Berg, suffix Jr.
    "Lee, Ann" -> first Ann, last Lee."""
    s = re.sub(r"\s+", " ", full).strip()
    out: dict = {}
    if s.count(",") == 1:
        a, b = [p.strip() for p in s.split(",")]
        if b and b.lower().strip(".") not in SUFFIXES:
            s = f"{b} {a}"
    tokens = s.replace(",", " ").split()
    if tokens and tokens[0].strip(".").lower() in PREFIXES and len(tokens) > 1:
        out["prefix"] = tokens.pop(0)
    suffixes = []
    while len(tokens) > 1 and tokens[-1].strip(".").lower() in SUFFIXES:
        suffixes.insert(0, tokens.pop())
    if suffixes:
        out["suffix"] = " ".join(suffixes)
    if len(tokens) == 1:
        out["first"] = tokens[0]
        out["one_word"] = True
    elif tokens:
        i = len(tokens) - 1
        while i > 1 and tokens[i - 1].lower() in PARTICLES:
            i -= 1
        out["first"], out["last"] = tokens[0], " ".join(tokens[i:])
        if i > 1:
            out["middle"] = " ".join(tokens[1:i])
    return out


def parse_emails(cell: str) -> tuple[list[str], list[str]]:
    """(valid addresses, things that looked like addresses but aren't)."""
    good, bad = [], []
    # "Ann Lee <ann@x.com>" - keep the address, drop the display name
    angled = re.findall(r"<([^<>\s]+@[^<>\s]+)>", cell)
    rest = re.sub(r"[^;,<>]*<[^<>\s]+@[^<>\s]+>", " ", cell) if angled else cell
    for m in angled + re.split(r"[;,\s]+", rest.strip()):
        m = m.strip("<>()[]\"' ").replace("mailto:", "")
        if not m or m.lower() in EMPTY_WORDS:
            continue
        m = m.lower().rstrip(".")
        (good if EMAIL_RE.match(m) else bad).append(m)
    return list(dict.fromkeys(good)), bad


def parse_phone(cell: str) -> tuple[str | None, str | None]:
    """(number, problem)."""
    v = cell.strip()
    if not v or v.lower() in EMPTY_WORDS:
        return None, None
    if re.fullmatch(r"\d(\.\d+)?[eE]\+?\d+", v):
        return None, f"“{v}” was turned into a scientific number by Excel - format the column as text and re-upload"
    digits = re.sub(r"\D", "", v)
    if len(digits) < 6:
        return None, f"“{v}” is too short to be a phone number"
    return v, None


def parse_date(v: str) -> date | None:
    v = v.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def norm_company(n: str | None) -> str:
    n = (n or "").lower()
    n = re.sub(r"[^a-z0-9 ]+", " ", n.replace("&", " and "))
    n = re.sub(r"\b(ltd|limited|plc|llc|inc|incorporated|llp|co|company|corp|corporation|the|gmbh|sa|sl|ag|bv)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60] or "field"


# ---- drafts ------------------------------------------------------------------------------

@dataclass
class Draft:
    n: int                         # data row number, 1-based
    first: str | None = None
    middle: str | None = None
    last: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    salutation: str | None = None
    job_title: str | None = None
    department: str | None = None
    category: str | None = None
    referred_by: str | None = None
    birthdate: date | None = None
    company: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[tuple[str, str]] = field(default_factory=list)   # (type, number)
    address: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    custom: dict = field(default_factory=dict)
    unsubscribed: bool = False
    issues: list[dict] = field(default_factory=list)  # {"level": "error"|"warning", "text"}

    @property
    def full_name(self) -> str | None:
        return " ".join(x for x in (self.first, self.last) if x) or None

    def warn(self, text: str):
        self.issues.append({"level": "warning", "text": text})

    @property
    def fatal(self) -> bool:
        return any(i["level"] == "error" for i in self.issues)


TEXT_FIELDS = {"first_name": "first", "middle_name": "middle", "last_name": "last", "name_prefix": "prefix", "name_suffix": "suffix",
               "salutation": "salutation", "job_title": "job_title", "department": "department", "category": "category",
               "referred_by": "referred_by", "company": "company"}
ADDRESS_FIELDS = {"address_line1": "line1", "address_line2": "line2", "address_line3": "line3", "city": "city", "state": "state",
                  "postcode": "postal_code", "country": "country"}
EMAIL_FIELDS = ("email", "email_2", "email_3")
LIMITS = {"first": 128, "middle": 128, "last": 256, "prefix": 64, "suffix": 64, "salutation": 64, "job_title": 256, "department": 256,
          "category": 512, "referred_by": 128, "company": 256}


def custom_key_for(spec: dict) -> str | None:
    f = spec.get("field", "")
    if f.startswith("custom:"):
        return f[7:]
    if f == "new_custom":
        return slug(spec.get("name") or "") if spec.get("name") else None
    return None


def build_drafts(headers: list[str], rows: list[list[str]], mapping: dict, excluded: set[int] | None = None) -> list[Draft]:
    specs = {int(i): m for i, m in mapping.items() if m.get("field") not in (None, "", "skip")}
    drafts = []
    for n, row in enumerate(rows, start=1):
        d = Draft(n)
        full = None
        email_cells: dict[str, str] = {}
        notes: list[tuple[str, str]] = []
        for i, spec in specs.items():
            v = (row[i] if i < len(row) else "").strip()
            if not v:
                continue
            f = spec["field"]
            if f in TEXT_FIELDS:
                setattr(d, TEXT_FIELDS[f], v)
            elif f == "full_name":
                full = v
            elif f in EMAIL_FIELDS:
                email_cells[f] = v
            elif f in PHONE_TYPES:
                for part in v.split(";"):
                    num, problem = parse_phone(part)
                    if problem:
                        d.warn(problem)
                    elif num:
                        d.phones.append((spec.get("type") or PHONE_TYPES[f], num))
            elif f in ADDRESS_FIELDS:
                d.address[ADDRESS_FIELDS[f]] = v
            elif f == "birthdate":
                d.birthdate = parse_date(v)
                if d.birthdate is None:
                    d.warn(f"“{v}” isn't a date the importer understands - birthday left out")
            elif f == "notes":
                notes.append((headers[i], v))
            elif f == "group":
                d.groups += [g.strip() for g in re.split(r"[;|,]", v) if g.strip()]
            elif f == "unsubscribed":
                d.unsubscribed = v.strip().lower() in TRUE_WORDS
            else:
                key = custom_key_for(spec)
                if key:
                    d.custom[key] = v
        # names
        if full and not (d.first or d.last):
            parts = split_name(full)
            d.first, d.middle, d.last = parts.get("first"), d.middle or parts.get("middle"), parts.get("last")
            d.prefix = d.prefix or parts.get("prefix")
            d.suffix = d.suffix or parts.get("suffix")
            if parts.get("one_word"):
                d.warn(f"Only one name given (“{full}”) - saved as a first name")
        for attr in ("first", "middle", "last"):
            setattr(d, attr, tidy_name(getattr(d, attr)))
        post = d.address.get("postal_code")
        if post and UK_POST_RE.match(post.strip()):
            d.address["postal_code"] = re.sub(r"^(.*?)\s*(\d[A-Za-z]{2})$", r"\1 \2", post.strip().upper())
        # emails: primary first
        for f in EMAIL_FIELDS:
            if f in email_cells:
                good, bad = parse_emails(email_cells[f])
                d.emails += [e for e in good if e not in d.emails]
                for b in bad:
                    d.warn(f"“{b}” isn't a valid email address - left out")
        # notes: one column = the text itself; several = labelled by column
        if len(notes) == 1:
            d.notes = [notes[0][1]]
        else:
            d.notes = [f"{h}: {v}" for h, v in notes]
        for k, limit in LIMITS.items():
            v = getattr(d, k)
            if v and len(v) > limit:
                setattr(d, k, v[:limit])
                d.warn(f"“{v[:30]}…” was cut to {limit} characters")
        if not (d.first or d.last or d.emails):
            d.issues.append({"level": "error", "text": "No name or email on this row - skipped"})
        elif not (d.first or d.last):
            d.warn("No name - will be saved with just the email address")
        drafts.append(d)
    return drafts


# ---- finding people already in the CRM -----------------------------------------------------

@dataclass
class Match:
    contact_id: uuid.UUID
    name: str | None
    kind: str  # email | name_company | possible


def find_existing(db: Session, source_db: str, drafts: list[Draft]) -> dict[int, Match]:
    found: dict[int, Match] = {}
    by_email: dict[str, list[int]] = {}
    for d in drafts:
        for e in d.emails:
            by_email.setdefault(e, []).append(d.n)
    keys = list(by_email)
    for i in range(0, len(keys), 1000):
        chunk = keys[i:i + 1000]
        for addr, cid, name in db.execute(
            select(func.lower(Email.address), Contact.id, Contact.full_name).join(Contact, Contact.id == Email.contact_id)
            .where(Contact.source_db == source_db, func.lower(Email.address).in_(chunk))
        ):
            for n in by_email[addr]:
                found.setdefault(n, Match(cid, name, "email"))
    rest = [d for d in drafts if d.n not in found and d.last]
    lasts = list({d.last.lower() for d in rest})
    people: dict[str, list] = {}
    for i in range(0, len(lasts), 1000):
        for cid, first, last, full, comp, free in db.execute(
            select(Contact.id, Contact.first_name, Contact.last_name, Contact.full_name, Company.name, Contact.company_name_freetext)
            .outerjoin(Company, Company.id == Contact.company_id)
            .where(Contact.source_db == source_db, func.lower(Contact.last_name).in_(lasts[i:i + 1000]))
        ):
            people.setdefault((last or "").lower(), []).append((cid, first, full, comp or free))
    for d in rest:
        for cid, first, full, comp in people.get(d.last.lower(), []):
            if not first or not d.first or not _same_first(d.first, first):
                continue
            mine, theirs = norm_company(d.company), norm_company(comp)
            if mine and theirs:
                if fuzz.token_set_ratio(mine, theirs) >= 88:
                    found[d.n] = Match(cid, full, "name_company")
                    break
            else:
                found.setdefault(d.n, Match(cid, full, "possible"))  # same name, company unknown on one side
    return found


def _same_first(a: str, b: str) -> bool:
    a, b = a.lower().strip("."), b.lower().strip(".")
    return a == b or (len(a) == 1 and b.startswith(a)) or (len(b) == 1 and a.startswith(b))


# ---- analysis ------------------------------------------------------------------------------

def analyse(db: Session, imp: ContactImport) -> dict:
    """The review screen's data: a status for every row plus the totals. Saved on the import so the
    screen can page through it without recomputing."""
    opts = {**DEFAULT_OPTIONS, **(imp.options or {})}
    drafts = build_drafts(imp.headers, imp.rows, imp.mapping)
    excluded = set(imp.excluded or [])
    matches = find_existing(db, opts["source_db"], drafts) if opts.get("source_db") else {}
    seen_emails: dict[str, int] = {}
    seen_people: dict[tuple, int] = {}
    out = []
    totals = {"new": 0, "update": 0, "skip_existing": 0, "skip_repeat": 0, "error": 0, "excluded": 0, "warnings": 0, "possible": 0}
    for d in drafts:
        row = {"n": d.n, "name": d.full_name, "email": d.emails[0] if d.emails else None, "company": d.company,
               "phone": d.phones[0][1] if d.phones else None, "issues": d.issues, "match": None, "status": "new"}
        m = matches.get(d.n)
        key = (d.first or "").lower(), (d.last or "").lower(), norm_company(d.company)
        repeat_of = next((seen_emails[e] for e in d.emails if e in seen_emails), None) or (seen_people.get(key) if key[1] else None)
        if d.n in excluded:
            row["status"] = "excluded"
        elif d.fatal:
            row["status"] = "error"
        elif repeat_of:
            row["status"] = "skip_repeat"
            d.warn(f"Same person as row {repeat_of} of this file")
            row["issues"] = d.issues
        elif m and m.kind != "possible":
            row["match"] = {"id": str(m.contact_id), "name": m.name, "kind": m.kind}
            row["status"] = "skip_existing" if opts["on_duplicate"] == "skip" else ("new" if opts["on_duplicate"] == "create" else "update")
        elif m:
            row["match"] = {"id": str(m.contact_id), "name": m.name, "kind": "possible"}
        if row["status"] in ("new", "update", "skip_existing"):
            for e in d.emails:
                seen_emails.setdefault(e, d.n)
            if key[1]:
                seen_people.setdefault(key, d.n)
        totals[row["status"]] = totals.get(row["status"], 0) + 1
        if row["match"] and row["match"]["kind"] == "possible" and row["status"] == "new":
            totals["possible"] += 1
        if any(i["level"] == "warning" for i in row["issues"]):
            totals["warnings"] += 1
        out.append(row)
    return {"totals": totals, "rows": out, "at": datetime.now(timezone.utc).isoformat()}


# ---- saving --------------------------------------------------------------------------------

def _find_company(db: Session, source_db: str, name: str, cache: dict, imp_id: str, created: list, allow_create: bool) -> Company | None:
    key = norm_company(name)
    if not key:
        return None
    if key in cache:
        return cache[key]
    cands = db.scalars(select(Company).where(Company.source_db == source_db, func.lower(Company.name).like(f"%{key.split()[0]}%"))).all() if key.split() else []
    best = next((c for c in cands if norm_company(c.name) == key), None) or next(
        (c for c in cands if fuzz.ratio(norm_company(c.name), key) >= 95), None)
    if best is None and allow_create:
        best = Company(id=uuid.uuid4(), source_db=source_db, source_act_id=f"import:{imp_id}:c{len(created) + 1}", name=name[:256], custom_fields={})
        db.add(best)
        db.flush()
        created.append(str(best.id))
    cache[key] = best
    return best


def commit(db: Session, imp: ContactImport, user_id: uuid.UUID | None) -> dict:
    opts = {**DEFAULT_OPTIONS, **(imp.options or {})}
    source_db = opts["source_db"]
    analysis = analyse(db, imp)
    status = {r["n"]: r for r in analysis["rows"]}
    drafts = {d.n: d for d in build_drafts(imp.headers, imp.rows, imp.mapping)}
    tag = imp.id.hex[:8]
    now = datetime.now(timezone.utc)

    group_ids: list[uuid.UUID] = []
    created_groups: list[str] = []
    if opts.get("group_id"):
        group_ids.append(uuid.UUID(str(opts["group_id"])))
    elif (opts.get("new_group_name") or "").strip():
        g = Group(id=uuid.uuid4(), source_db=source_db, source_act_id=f"import:{tag}:g0", name=opts["new_group_name"].strip()[:256], custom_fields={})
        db.add(g)
        db.flush()
        group_ids.append(g.id)
        created_groups.append(str(g.id))
    group_cache: dict[str, uuid.UUID] = {}
    cc: dict = {}
    created_companies: list[str] = []
    created_ids: list[str] = []
    updated_before: dict[str, dict] = {}
    counts = {"created": 0, "updated": 0, "skipped": 0, "unchanged": 0}
    new_custom: dict[str, str] = {}
    for i, spec in imp.mapping.items():
        if spec.get("field") == "new_custom" and spec.get("name"):
            new_custom[slug(spec["name"])] = spec["name"].strip()

    def child_id(kind: str, n: int, k: int) -> str:
        return f"import:{tag}:{n}:{kind}{k}"

    def groups_for(d: Draft) -> list[uuid.UUID]:
        ids = list(group_ids)
        for name in d.groups:
            gid = group_cache.get(name.lower())
            if gid is None:
                g = db.scalars(select(Group).where(Group.source_db == source_db, func.lower(Group.name) == name.lower())).first()
                if g is None:
                    g = Group(id=uuid.uuid4(), source_db=source_db, source_act_id=f"import:{tag}:g{len(created_groups) + 1}", name=name[:256], custom_fields={})
                    db.add(g)
                    db.flush()
                    created_groups.append(str(g.id))
                gid = group_cache[name.lower()] = g.id
            ids.append(gid)
        return list(dict.fromkeys(ids))

    for n, row in status.items():
        d = drafts[n]
        st = row["status"]
        if st in ("excluded", "error", "skip_repeat", "skip_existing"):
            counts["skipped"] += 1
            continue
        company = _find_company(db, source_db, d.company, cc, tag, created_companies, opts["create_companies"]) if d.company else None
        if st == "new":
            c = Contact(
                id=uuid.uuid4(), source_db=source_db, source_act_id=f"import:{tag}:{n}", company_id=company.id if company else None,
                owner_user_id=user_id, first_name=d.first, middle_name=d.middle, last_name=d.last, full_name=d.full_name,
                name_prefix=d.prefix, name_suffix=d.suffix, salutation=d.salutation, job_title=d.job_title, department=d.department,
                category=d.category, referred_by=d.referred_by, birthdate=d.birthdate, company_name_freetext=d.company,
                is_unsubscribed=d.unsubscribed, is_email_opted_out=d.unsubscribed,
                custom_fields={**d.custom, "_import": {"id": str(imp.id), "file": imp.filename, "row": n}},
            )
            db.add(c)
            db.flush()
            for k, e in enumerate(d.emails):
                db.add(Email(id=uuid.uuid4(), source_db=source_db, source_act_id=child_id("e", n, k), contact_id=c.id, address=e, is_primary=k == 0, type_label="Business"))
            for k, (t, num) in enumerate(d.phones):
                db.add(Phone(id=uuid.uuid4(), source_db=source_db, source_act_id=child_id("p", n, k), contact_id=c.id, number=num, type_label=t, is_primary=k == 0))
            if d.address:
                db.add(Address(id=uuid.uuid4(), source_db=source_db, source_act_id=child_id("a", n, 0), contact_id=c.id, type_label="Business", is_primary=True, **d.address))
            for k, text in enumerate(d.notes):
                db.add(Note(id=uuid.uuid4(), source_db=source_db, source_act_id=child_id("n", n, k), entity_type="contact", entity_id=c.id,
                            note_type="Note", body=text, act_created_at=now, created_by_user_id=user_id))
            for gid in groups_for(d):
                db.add(GroupMembership(id=uuid.uuid4(), group_id=gid, contact_id=c.id))
            created_ids.append(str(c.id))
            counts["created"] += 1
        else:  # update
            c = db.get(Contact, uuid.UUID(row["match"]["id"]))
            undo = _update_existing(db, c, d, company, opts["on_duplicate"] == "overwrite", n, tag, source_db, now, user_id, groups_for(d))
            if undo:
                updated_before[str(c.id)] = undo
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1
    if new_custom:
        from app.contacts.fields import get_custom_labels, set_custom_labels, forget_custom_keys
        labels = get_custom_labels(db)
        set_custom_labels(db, {**labels, **{k: v for k, v in new_custom.items() if k not in labels}})
        forget_custom_keys()
    imp.status, imp.imported_at = "imported", now
    imp.created_contact_ids = created_ids
    imp.updated_before = updated_before
    imp.result = {**counts, "created_companies": created_companies, "created_groups": created_groups, "totals": analysis["totals"],
                  "rows": analysis["rows"]}
    db.commit()
    return imp.result


def _update_existing(db, c: Contact, d: Draft, company, overwrite: bool, n: int, tag: str, source_db: str, now, user_id, group_ids) -> dict | None:
    """Adds what the file has to an existing contact. Returns what Undo needs, or None if nothing changed."""
    undo: dict = {"fields": {}, "emails": [], "phones": [], "addresses": [], "notes": [], "groups": [], "custom": {}}
    simple = {"first_name": d.first, "middle_name": d.middle, "last_name": d.last, "name_prefix": d.prefix, "name_suffix": d.suffix,
              "salutation": d.salutation, "job_title": d.job_title, "department": d.department, "category": d.category,
              "referred_by": d.referred_by, "birthdate": d.birthdate}
    for col, new in simple.items():
        old = getattr(c, col)
        if new and (old in (None, "") or (overwrite and old != new)):
            undo["fields"][col] = old.isoformat() if isinstance(old, date) else old
            setattr(c, col, new)
    if d.first or d.last:
        full = " ".join(x for x in (c.first_name, c.last_name) if x) or None
        if full != c.full_name:
            undo["fields"].setdefault("full_name", c.full_name)
            c.full_name = full
    if company and (c.company_id is None or (overwrite and c.company_id != company.id)):
        undo["fields"]["company_id"] = str(c.company_id) if c.company_id else None
        c.company_id = company.id
        if d.company:
            undo["fields"]["company_name_freetext"] = c.company_name_freetext
            c.company_name_freetext = d.company
    if d.unsubscribed and not c.is_unsubscribed:
        undo["fields"]["is_unsubscribed"] = c.is_unsubscribed
        undo["fields"]["is_email_opted_out"] = c.is_email_opted_out
        c.is_unsubscribed = c.is_email_opted_out = True
    for key, v in d.custom.items():
        old = (c.custom_fields or {}).get(key)
        if old in (None, "") or (overwrite and old != v):
            undo["custom"][key] = old
            c.custom_fields = {**(c.custom_fields or {}), key: v}
    have = {e.lower() for e in db.scalars(select(Email.address).where(Email.contact_id == c.id)) if e}
    has_primary = bool(db.scalar(select(Email.id).where(Email.contact_id == c.id, Email.is_primary.is_(True)).limit(1)))
    for k, e in enumerate(d.emails):
        if e not in have:
            eid = uuid.uuid4()
            db.add(Email(id=eid, source_db=source_db, source_act_id=child_id_(tag, "e", n, k), contact_id=c.id, address=e, is_primary=not has_primary and k == 0, type_label="Business"))
            undo["emails"].append(str(eid))
    have_nums = {re.sub(r"\D", "", p) for p in db.scalars(select(Phone.number).where(Phone.contact_id == c.id)) if p}
    for k, (t, num) in enumerate(d.phones):
        if re.sub(r"\D", "", num) not in have_nums:
            pid = uuid.uuid4()
            db.add(Phone(id=pid, source_db=source_db, source_act_id=child_id_(tag, "p", n, k), contact_id=c.id, number=num, type_label=t, is_primary=False))
            undo["phones"].append(str(pid))
    if d.address and not db.scalar(select(Address.id).where(Address.contact_id == c.id).limit(1)):
        aid = uuid.uuid4()
        db.add(Address(id=aid, source_db=source_db, source_act_id=child_id_(tag, "a", n, 0), contact_id=c.id, type_label="Business", is_primary=True, **d.address))
        undo["addresses"].append(str(aid))
    for k, text in enumerate(d.notes):
        nid = uuid.uuid4()
        db.add(Note(id=nid, source_db=source_db, source_act_id=child_id_(tag, "n", n, k), entity_type="contact", entity_id=c.id, note_type="Note",
                    body=text, act_created_at=now, created_by_user_id=user_id))
        undo["notes"].append(str(nid))
    for gid in group_ids:
        if not db.scalar(select(GroupMembership.id).where(GroupMembership.contact_id == c.id, GroupMembership.group_id == gid)):
            mid = uuid.uuid4()
            db.add(GroupMembership(id=mid, group_id=gid, contact_id=c.id))
            undo["groups"].append(str(mid))
    changed = any(undo[k] for k in undo)
    if changed:
        db.flush()
    return undo if changed else None


def child_id_(tag: str, kind: str, n: int, k: int) -> str:
    return f"import:{tag}:{n}:{kind}{k}"


def undo_import(db: Session, imp: ContactImport) -> dict:
    """Removes what the import added, but keeps any contact someone has worked on since."""
    from app.models import Activity, FieldChange, HistoryEntry
    kept = deleted = reverted = 0
    for cid in imp.created_contact_ids:
        cu = uuid.UUID(cid)
        c = db.get(Contact, cu)
        if not c:
            continue
        touched = (
            db.scalar(select(func.count()).select_from(FieldChange).where(FieldChange.entity_type == "contact", FieldChange.entity_id == cu))
            or db.scalar(select(func.count()).select_from(HistoryEntry).where(HistoryEntry.entity_type == "contact", HistoryEntry.entity_id == cu))
            or db.scalar(select(func.count()).select_from(Activity).where(Activity.contact_id == cu))
            or db.scalar(select(func.count()).select_from(Note).where(Note.entity_type == "contact", Note.entity_id == cu, ~Note.source_act_id.like("import:%")))
        )
        if touched:
            kept += 1
            continue
        for model, col in ((GroupMembership, GroupMembership.contact_id), (Address, Address.contact_id), (Phone, Phone.contact_id), (Email, Email.contact_id)):
            db.execute(model.__table__.delete().where(col == cu))
        db.execute(Note.__table__.delete().where(Note.entity_type == "contact", Note.entity_id == cu))
        db.delete(c)
        deleted += 1
    for cid, u in imp.updated_before.items():
        c = db.get(Contact, uuid.UUID(cid))
        if not c:
            continue
        for col, old in u["fields"].items():
            if col == "birthdate" and isinstance(old, str):
                old = date.fromisoformat(old)
            if col == "company_id" and old:
                old = uuid.UUID(old)
            setattr(c, col, old)
        cf = dict(c.custom_fields or {})
        for key, old in u["custom"].items():
            if old is None:
                cf.pop(key, None)
            else:
                cf[key] = old
        c.custom_fields = cf
        for model, ids in ((Email, u["emails"]), (Phone, u["phones"]), (Address, u["addresses"]), (Note, u["notes"]), (GroupMembership, u["groups"])):
            if ids:
                db.execute(model.__table__.delete().where(model.id.in_([uuid.UUID(i) for i in ids])))
        reverted += 1
    db.flush()
    for gid in imp.result.get("created_groups", []):
        if not db.scalar(select(func.count()).select_from(GroupMembership).where(GroupMembership.group_id == uuid.UUID(gid))):
            db.execute(Group.__table__.delete().where(Group.id == uuid.UUID(gid)))
    for cid in imp.result.get("created_companies", []):
        cu = uuid.UUID(cid)
        if not db.scalar(select(func.count()).select_from(Contact).where(Contact.company_id == cu)):
            db.execute(Company.__table__.delete().where(Company.id == cu))
    imp.status, imp.undone_at = "undone", datetime.now(timezone.utc)
    db.commit()
    return {"deleted": deleted, "kept": kept, "reverted": reverted}
