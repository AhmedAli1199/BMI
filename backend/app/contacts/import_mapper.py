"""Works out which spreadsheet column is which contact field.

Like the import screens of popular CRMs it proposes a mapping for every
column, and it is deliberately forgiving: "First Name", "firstname",
"FIRST_NAME", "Forename", "Given name", "Frist Name" and "fname" all land on
First name. It reads two kinds of clue and combines them:

* the **header** - cleaned up, then compared with a list of phrases per field
  (exact, "contains all the words", close spelling), including numbered
  variants such as "Email 2" or "Phone 3", and
* the **values** - a column full of email addresses is Email whatever it is
  called, UK postcodes are Postcode, "Mr / Mrs / Dr" is Title, and so on.

When two different fields are almost equally likely, it leaves the column for
a person to decide (and shows the candidates) rather than guessing.

To teach it a new header phrase, add it to the right entry of TARGETS below -
nothing else needs to change. Custom fields already in the CRM are matched by
their names too, so once BMI's Act! custom fields are named ("ABTA number"),
a column called "ABTA No" maps to it by itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

# ---- the fields a column can be imported into ---------------------------------------

@dataclass(frozen=True)
class Target:
    key: str
    label: str
    group: str
    aliases: tuple[str, ...]
    multi: bool = False  # more than one column may feed it (notes, groups)


def _t(key, label, group, aliases, multi=False) -> Target:
    return Target(key, label, group, tuple(a for a in aliases.split("|") if a), multi)


TARGETS: list[Target] = [
    _t("first_name", "First name", "Name",
       "first name|firstname|first|given name|given names|given|forename|fore name|forenames|christian name|fname|f name|first nm|name first|prename|first name of contact|contact first name"),
    _t("middle_name", "Middle name", "Name", "middle name|middlename|middle|middle initial|middle names|mname|m name|second given name"),
    _t("last_name", "Last name", "Name",
       "last name|lastname|last|surname|sur name|family name|family|lname|l name|second name|name last|last nm|contact last name|contact surname"),
    _t("full_name", "Full name", "Name",
       "name|full name|fullname|contact name|contact|person|display name|customer name|client name|contact person|complete name|names|delegate|delegate name|attendee|attendee name|full nm"),
    _t("name_prefix", "Title (Mr, Mrs…)", "Name", "prefix|name prefix|honorific|courtesy title|name title|title prefix|pre title|mr mrs|salutation title"),
    _t("name_suffix", "Name suffix", "Name", "suffix|name suffix|post nominal|post nominals|postnominal|postnominals|generational suffix|qualifications"),
    _t("salutation", "Salutation", "Name", "salutation|greeting|dear|addressed as|preferred name|known as|nickname|informal name|dear name"),
    _t("job_title", "Job title", "Job",
       "job title|jobtitle|position|role|job|job role|job position|designation|occupation|function|job function|work title|position title|profession|job name|title"),
    _t("department", "Department", "Job", "department|dept|division|team|business unit|section|dept name"),
    _t("company", "Company", "Company",
       "company|company name|companyname|organisation|organization|org|organisation name|organization name|employer|business name|account|account name|firm|firm name|institution|agency|agency name|client company|company organisation|trading name|practice|employer name|workplace|co name|company org"),
    _t("email", "Email", "Email",
       "email|e mail|email address|e mail address|emailaddress|mail|email 1|primary email|work email|business email|main email|contact email|email id|e mail 1|email address 1|electronic mail|emailaddr|email addr|e addr|mail address"),
    _t("email_2", "Email 2", "Email",
       "email 2|second email|secondary email|alternative email|alternate email|other email|additional email|email address 2|personal email|home email|email2|e mail 2|alt email"),
    _t("email_3", "Email 3", "Email", "email 3|third email|email address 3|email3|e mail 3"),
    _t("phone", "Phone (work)", "Phone",
       "phone|telephone|tel|phone number|telephone number|tel no|phone no|work phone|business phone|office phone|office|office tel|direct|direct line|direct dial|switchboard|main phone|landline|phone 1|telephone 1|tel 1|contact number|contact phone|contact no|ph|phone work|work tel|company phone|business tel|daytime phone|day phone|work telephone|telephone no|tel number|phone num|telephone work|office telephone|ddi"),
    _t("mobile", "Mobile", "Phone",
       "mobile|mobile phone|mobile number|mobile no|mob|cell|cell phone|cellphone|cell number|gsm|mobile tel|mob no|mobile telephone|portable|cell phone number|mobile 1|mobile num|mob phone|mobile tel no"),
    _t("home_phone", "Home phone", "Phone", "home phone|home tel|home telephone|home number|residential phone|private phone|private tel|evening phone|home tel no"),
    _t("fax", "Fax", "Phone", "fax|fax number|facsimile|fax no|fax tel|fax num"),
    _t("other_phone", "Other phone", "Phone",
       "other phone|phone 2|phone2|telephone 2|tel 2|secondary phone|alternative phone|alternate phone|second phone|additional phone|phone 3|other tel|other number|other telephone|alt phone|tel2"),
    _t("address_line1", "Address line 1", "Address",
       "address|address 1|address line 1|address1|street|street address|street 1|addr 1|addr1|line 1|address line1|street name|mailing address|postal address|business address|work address|address line|address street|street address 1|office address|addr|add 1|add1|address 1 street"),
    _t("address_line2", "Address line 2", "Address", "address 2|address line 2|address2|street 2|addr 2|addr2|line 2|street address 2|address line2|add 2|add2|building|address 2 street"),
    _t("address_line3", "Address line 3", "Address", "address 3|address line 3|address3|street 3|addr 3|addr3|line 3|add 3|add3"),
    _t("city", "City / town", "Address", "city|town|city town|town city|locality|suburb|municipality|post town|posttown|address city|city name|city or town|town or city"),
    _t("state", "County / state", "Address", "county|state|province|region|state province|state county|county state|county region|shire|prefecture|state or province|county or state|state region"),
    _t("postcode", "Postcode", "Address", "postcode|post code|postal code|postalcode|zip|zip code|zipcode|zip postal code|pc|postcode zip|post zip|postal|pcode|post cd|postal zip|zip or postcode"),
    _t("country", "Country", "Address", "country|country name|nation|country region|ctry|country or region|cntry"),
    _t("category", "Category", "Other", "category|categories|segment|contact type|classification|contact category|cat"),
    _t("referred_by", "Referred by", "Other", "referred by|referrer|referral|referral source|source|lead source|how did you hear|heard about us|introduced by|referred"),
    _t("birthdate", "Birthday", "Other", "birthday|birthdate|birth date|date of birth|dob|d o b|born|birth day|bday"),
    _t("notes", "Notes", "Other",
       "notes|note|comments|comment|remarks|remark|description|additional information|additional info|memo|details|info|general notes|bmi notes|observations|other information|other info|notes comments", multi=True),
    _t("group", "Add to group", "Other", "group|groups|list|lists|tags|tag|mailing list|distribution list|group name|segments|group membership", multi=True),
    _t("unsubscribed", "Do not email", "Other",
       "unsubscribed|unsubscribe|opt out|optout|opted out|do not email|do not contact|dnc|no email|email opt out|email opted out|marketing opt out|dont email|do not mail|suppress|suppressed|gdpr opt out|email unsubscribed|no mailings|no marketing"),
]
BY_KEY = {t.key: t for t in TARGETS}
SINGLE = {t.key for t in TARGETS if not t.multi}

# A column named like this is a row number / system ID - nothing to import.
SKIP_PHRASES = {"id", "number", "no.", "numbernumber", "row", "row number", "index", "#", "ref", "reference", "record id", "contact id", "customer id",
                "client id", "uuid", "guid", "s no", "sr no", "serial", "serial no", "sl no", "sno"}
NOISE = {"the", "of", "contact", "contacts", "primary", "main", "your", "their", "required", "optional", "field", "column", "details", "detail", "no", "number", "num"}

# "second family" slots: a second column that looks like email / phone is put in the next slot.
OVERFLOW = {"email": ["email_2", "email_3"], "email_2": ["email_3"], "phone": ["other_phone"], "mobile": ["other_phone"], "home_phone": ["other_phone"]}
NUMBERED = {  # "Email 2" style: base word -> slots by number
    "email": ["email", "email_2", "email_3"], "e mail": ["email", "email_2", "email_3"], "mail": ["email", "email_2", "email_3"],
    "phone": ["phone", "other_phone", "other_phone"], "telephone": ["phone", "other_phone", "other_phone"], "tel": ["phone", "other_phone", "other_phone"],
    "mobile": ["mobile", "other_phone", "other_phone"], "address": ["address_line1", "address_line2", "address_line3"],
    "street": ["address_line1", "address_line2", "address_line3"], "addr": ["address_line1", "address_line2", "address_line3"],
}
WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "first": 1, "second": 2, "third": 3, "1st": 1, "2nd": 2, "3rd": 3, "primary": 1, "secondary": 2, "alternate": 2, "alternative": 2, "other": 2, "additional": 2}

QUALIFIERS = {"mobile", "cell", "gsm", "home", "fax", "work", "business", "office", "direct", "secondary", "alternative", "alternate", "second", "personal", "private", "evening"}
MAP_AT = 0.60        # below this a column stays unmapped
HIGH_AT = 0.85       # at/above: "matched"; between: "check this"
AMBIGUOUS_GAP = 0.06 # two different fields this close = let a person choose


# ---- header cleaning -----------------------------------------------------------------

ABBREVIATIONS = {"num": "number", "nbr": "number", "nr": "number", "no": "number", "tel": "tel", "addr": "addr"}


def norm(header: str) -> str:
    h = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", header or "")  # camelCase -> camel Case
    h = h.lower().replace("&", " and ").replace("/", " ").replace("\\", " ")
    h = re.sub(r"[^a-z0-9#]+", " ", h)
    h = re.sub(r"\b(the|your|their|please|enter|required|optional)\b", " ", h)
    h = " ".join(ABBREVIATIONS.get(w, w) for w in h.split())
    return h


def compact(s: str) -> str:
    return s.replace(" ", "")


# ---- value sniffing --------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")
UK_POST_RE = re.compile(r"^[A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2}$")
UK_MOBILE_RE = re.compile(r"^(\+?44\s?\(?0?\)?\s?7|0\s?7)\d")
URL_RE = re.compile(r"^(https?://|www\.)", re.I)
PREFIXES = {"mr", "mrs", "ms", "miss", "mx", "dr", "prof", "professor", "sir", "dame", "lord", "lady", "rev", "reverend", "capt", "captain",
            "major", "col", "colonel", "master", "mister", "madam", "hon", "cllr", "fr"}
COUNTRIES = {c.lower() for c in (
    "United Kingdom UK U.K. England Scotland Wales Northern Ireland Great Britain GB Ireland Eire France Germany Spain Italy Portugal Netherlands Holland Belgium "
    "Switzerland Austria Sweden Norway Denmark Finland Poland Greece Turkey USA US U.S.A. United States America Canada Mexico Brazil Argentina Australia "
    "New Zealand India China Japan Singapore Hong Kong UAE United Arab Emirates Dubai Qatar Saudi Arabia South Africa Egypt Morocco Kenya Thailand "
    "Malaysia Indonesia Philippines Vietnam South Korea Israel Cyprus Malta Iceland Czech Republic Hungary Romania Croatia Jamaica Barbados Bahamas Chile Peru Colombia"
).replace("U.K.", "UK").split(" ") if False} | {c.lower() for c in (
    "United Kingdom,UK,U.K.,England,Scotland,Wales,Northern Ireland,Great Britain,GB,Ireland,Eire,France,Germany,Spain,Italy,Portugal,Netherlands,Holland,Belgium,"
    "Switzerland,Austria,Sweden,Norway,Denmark,Finland,Poland,Greece,Turkey,USA,US,U.S.A.,United States,America,Canada,Mexico,Brazil,Argentina,Australia,"
    "New Zealand,India,China,Japan,Singapore,Hong Kong,UAE,United Arab Emirates,Dubai,Qatar,Saudi Arabia,South Africa,Egypt,Morocco,Kenya,Thailand,"
    "Malaysia,Indonesia,Philippines,Vietnam,South Korea,Israel,Cyprus,Malta,Iceland,Czech Republic,Hungary,Romania,Croatia,Jamaica,Barbados,Bahamas,Chile,Peru,Colombia"
).split(",")}


def is_phone(v: str) -> bool:
    if "@" in v or re.search(r"[A-Za-z]{3,}", re.sub(r"(ext|x)\.?\s*\d+$", "", v, flags=re.I)):
        return False
    digits = re.sub(r"\D", "", v)
    return 7 <= len(digits) <= 16 and bool(re.fullmatch(r"[+\d\s().\-/xX]+", v.strip()) or re.fullmatch(r"[+\d\s().\-/]+(ext\.?\s*\d+)?", v.strip(), re.I))


def _ratio(values: list[str], test) -> float:
    return sum(1 for v in values if test(v)) / len(values) if values else 0.0


def sniff(values: list[str]) -> dict[str, float]:
    """How much of the column looks like each kind of thing (0-1)."""
    v = [x for x in values if x][:100]
    parts = lambda x: [p for p in re.split(r"[;,\s]+", x) if p]  # noqa: E731
    return {
        "email": _ratio(v, lambda x: bool(parts(x)) and all(EMAIL_RE.match(p) for p in parts(x))),
        "phone": _ratio(v, is_phone),
        "uk_mobile": _ratio(v, lambda x: is_phone(x) and bool(UK_MOBILE_RE.match(x.strip()))),
        "postcode": _ratio(v, lambda x: bool(UK_POST_RE.match(x.strip()))),
        "url": _ratio(v, lambda x: bool(URL_RE.match(x.strip()))),
        "prefix": _ratio(v, lambda x: x.strip(" .").lower() in PREFIXES),
        "country": _ratio(v, lambda x: x.strip(" .").lower() in COUNTRIES),
        "fullname": _ratio(v, lambda x: bool(re.fullmatch(r"[A-Za-zÀ-ÿ'’\-. ]+", x)) and 2 <= len(x.split()) <= 4),
        "oneword": _ratio(v, lambda x: bool(re.fullmatch(r"[A-Za-zÀ-ÿ'’\-.]+", x))),
        "date": _ratio(v, lambda x: bool(re.fullmatch(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", x.strip()))),
        "n": float(len(v)),
    }


# content type -> (target key, score it earns on its own)
def content_scores(s: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    if s["n"] < 1:
        return out
    if s["email"] >= 0.8:
        out["email"] = 0.92
    if s["prefix"] >= 0.8:
        out["name_prefix"] = 0.92
    if s["postcode"] >= 0.8:
        out["postcode"] = 0.88
    if s["country"] >= 0.7:
        out["country"] = 0.82
    if s["phone"] >= 0.8 and s["email"] < 0.3:
        if s["uk_mobile"] >= 0.8:
            out["mobile"] = 0.78
        out["phone"] = 0.72
    return out


# ---- the matcher -----------------------------------------------------------------------

@dataclass
class Candidate:
    target: str
    score: float
    why: str
    tokens: frozenset = frozenset()  # the heading words this match used (a longer match beats the shorter one inside it)


@dataclass
class ColumnResult:
    index: int
    header: str
    samples: list[str]
    field: str | None             # chosen target key, "skip", or None = nobody matched
    level: str                    # high | medium | ambiguous | none | empty | skip
    confidence: float
    reason: str
    candidates: list[dict] = field(default_factory=list)
    warning: str | None = None


def _phrase_index(extra: dict[str, list[str]]) -> list[tuple[str, str, list[str], str]]:
    """(target, phrase, tokens, compact) for every alias, including custom-field names."""
    out = []
    for t in TARGETS:
        for a in t.aliases:
            a = norm(a) or a
            out.append((t.key, a, a.split(), compact(a)))
    for key, phrases in extra.items():
        for a in phrases:
            n = norm(a)
            if n:
                out.append((key, n, n.split(), compact(n)))
    return out


_VOCAB: set[str] | None = None


def _vocab() -> set[str]:
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = {w for t in TARGETS for a in t.aliases for w in norm(a).split() if len(w) >= 4 and not w.isdigit()}
    return _VOCAB


def _spell(h: str) -> str:
    """"frist name" -> "first name": fixes each unknown word to the closest word we know."""
    vocab = _vocab()
    out = []
    for w in h.split():
        if len(w) >= 4 and w not in vocab and not w.isdigit():
            best = max(vocab, key=lambda v: fuzz.ratio(w, v))
            w = best if fuzz.ratio(w, best) >= 80 else w
        out.append(w)
    return " ".join(out)


def header_scores(header: str, index: list[tuple[str, str, list[str], str]]) -> list[Candidate]:
    h = norm(header)
    if not h:
        return []
    best: dict[str, Candidate] = {}

    def offer(c: Candidate):
        if c.target not in best or c.score > best[c.target].score:
            best[c.target] = c

    def run(h: str, penalty: float, note: str):
        ht = h.split()
        hc = compact(h)
        for target, phrase, tokens, comp in index:
            if h == phrase or hc == comp:
                offer(Candidate(target, 1.0 - penalty, f"The heading “{header}” is a standard name for this{note}", frozenset(ht)))
                continue
            # every word of the phrase appears in the heading ("Primary email address" ⊇ "email address")
            if len(tokens) <= len(ht) and set(tokens) <= set(ht):
                extras = [w for w in ht if w not in tokens]
                if len(extras) <= 2:
                    head = 0.08 if ht[-1] == tokens[-1] else 0.0
                    score = 0.80 + 0.12 * (len(tokens) / len(ht)) + head - (0.0 if all(w in NOISE for w in extras) else 0.02)
                    offer(Candidate(target, min(score, 0.97) - penalty, f"The heading “{header}” contains “{phrase}”{note}", frozenset(tokens)))
                    continue
            # close spelling of the whole heading ("firstnaem")
            if len(comp) >= 4 and abs(len(comp) - len(hc)) <= 3:
                r = fuzz.ratio(hc, comp)
                if r >= 85:
                    offer(Candidate(target, 0.6 + 0.25 * (r - 85) / 15 - penalty, f"The heading “{header}” is spelled like “{phrase}”", frozenset(ht)))

    run(h, 0.0, "")
    fixed = _spell(h)
    if fixed != h:
        run(fixed, 0.04, f" (read as “{fixed}”)")
    # "Email 2", "Phone 3", "E-mail 2 Address", "Business Street 2": a number picks the slot
    toks = h.split()
    digits = [t for t in toks if t in ("1", "2", "3", "4", "5")]
    words = [WORD_NUMBERS[t] for t in toks if t in WORD_NUMBERS and t not in ("primary", "other", "alternate", "alternative", "additional", "secondary")]
    if len(digits) + len(words) == 1:
        n = int(digits[0]) if digits else words[0]
        base = [t for t in toks if t not in digits and t not in WORD_NUMBERS or t in ("primary",) and False]
        while base and base[-1] in ("address", "number", "addr", "tel", "id") and len(base) > 1:
            base = base[:-1]
        base_s = " ".join(base)
        for word, slots in NUMBERED.items():
            if base_s == word or base_s.endswith(" " + word):
                offer(Candidate(slots[min(n, 3) - 1], 0.95 if n <= 3 else 0.7, f"“{header}” is the number {n} {word}", frozenset(toks)))
    # a longer match swallows the shorter one inside it: "first name" beats "name" for "contact first name"
    cands = list(best.values())
    cands = [c for c in cands if not any(o.target != c.target and c.tokens < o.tokens and o.score >= c.score - 0.15 for o in cands)]
    # "Mobile phone number": the qualifier (mobile / home / fax / work…) says more than the generic "phone number"
    cands = [c for c in cands if not any(o.target != c.target and (o.tokens & QUALIFIERS) and not (c.tokens & QUALIFIERS) and o.score >= c.score - 0.1 for o in cands)]
    return sorted(cands, key=lambda c: -c.score)


def match_columns(headers: list[str], rows: list[list[str]], custom: dict[str, list[str]] | None = None) -> list[ColumnResult]:
    """Proposes a field (or none) for each column. `custom` = {"custom:user3": ["ABTA number"], ...}."""
    index = _phrase_index(custom or {})
    labels = {t.key: t.label for t in TARGETS}
    for key, phrases in (custom or {}).items():
        labels[key] = phrases[0] if phrases else key
    results: list[ColumnResult] = []
    ranked: dict[int, list[Candidate]] = {}

    for i, header in enumerate(headers):
        values = [r[i] for r in rows if i < len(r) and r[i]]
        samples = list(dict.fromkeys(values))[:5]
        res = ColumnResult(i, header, samples, None, "none", 0.0, "")
        results.append(res)
        if not values:
            res.field, res.level, res.reason = "skip", "empty", "This column is empty"
            continue
        if norm(header) in SKIP_PHRASES:
            res.field, res.level, res.confidence, res.reason = "skip", "skip", 0.9, "Looks like a row number or ID, so it isn't imported"
            continue
        s = sniff(values)
        cs = content_scores(s)
        cands = {c.target: c for c in header_scores(header, index)}
        nh = norm(header)
        # "Title" means Mr/Mrs in one file and Job title in another - the values decide
        if nh == "title":
            cands = {k: v for k, v in cands.items() if k not in ("job_title", "name_prefix")}
            if s["prefix"] >= 0.5:
                cands["name_prefix"] = Candidate("name_prefix", 0.95, "The values are Mr / Mrs / Dr…")
            else:
                cands["job_title"] = Candidate("job_title", 0.9, "“Title” with values that read as job titles")
        # content agreeing with the heading raises it; content alone can still carry the column
        for target, c_score in cs.items():
            c = cands.get(target)
            if c and c.score >= 0.6:
                cands[target] = Candidate(target, min(1.0, max(c.score, c_score) + 0.06), c.why + ("" if "values" in c.why else " and the values fit"))
            elif not c or c.score < c_score:
                cands[target] = Candidate(target, c_score, {"email": "The values are email addresses", "name_prefix": "The values are Mr / Mrs / Dr…",
                                                            "postcode": "The values are UK postcodes", "country": "The values are country names",
                                                            "phone": "The values are phone numbers", "mobile": "The values are UK mobile numbers"}[target])
        # heading says one data type but the values clearly say another: don't trust the heading
        for target, c in list(cands.items()):
            kind = {"email": "email", "email_2": "email", "email_3": "email", "phone": "phone", "mobile": "phone", "home_phone": "phone",
                    "other_phone": "phone", "fax": "phone", "postcode": "postcode"}.get(target)
            if kind and s["n"] >= 3 and s[kind] < 0.3 and c.score < 1.01 and any(s[k] >= 0.8 for k in ("email", "phone", "postcode") if k != kind):
                res.warning = f"“{header}” looks like {target.replace('_', ' ')}, but the values don't"
                cands[target] = Candidate(target, c.score - 0.35, c.why)
        # a bare "Name" with single-word values and no separate surname column is a first name - decided in the second pass
        ranked[i] = sorted(cands.values(), key=lambda c: -c.score)

    # "Name" next to a "Surname" column is the first name
    mapped_last = any(r and r[0].target == "last_name" and r[0].score >= MAP_AT for r in ranked.values()) and not any(
        r and r[0].target == "first_name" and r[0].score >= MAP_AT for r in ranked.values())
    for i, r in ranked.items():
        if r and r[0].target == "full_name" and norm(headers[i]) in ("name", "contact name", "names") and mapped_last and sniff([x[i] for x in rows if i < len(x) and x[i]])["oneword"] >= 0.7:
            ranked[i] = [Candidate("first_name", 0.88, "A “Name” column next to a surname column holds first names")] + r[1:]

    # Assign fields to columns, strongest first; a field can only be used once (second email -> Email 2 …)
    taken: dict[str, int] = {}
    order = sorted((i for i in ranked if ranked[i] and ranked[i][0].score >= MAP_AT), key=lambda i: -ranked[i][0].score)
    for i in order:
        res = results[i]
        cands = ranked[i]
        top = cands[0]
        runner = next((c for c in cands[1:] if c.target != top.target), None)
        if runner and runner.score >= MAP_AT and top.score - runner.score < AMBIGUOUS_GAP and top.score < 1.0:
            res.field, res.level, res.confidence = None, "ambiguous", top.score
            res.reason = f"Could be {labels.get(top.target, top.target)} or {labels.get(runner.target, runner.target)} - choose one"
            res.candidates = _cand_out(cands, labels)
            continue
        target = top.target
        why = top.why
        if target in SINGLE and target in taken:
            slot = next((s for s in OVERFLOW.get(target, []) if s not in taken), None)
            if slot is None:
                res.field, res.level, res.confidence = None, "none", top.score
                res.reason = f"Also looks like {labels.get(target, target)}, which “{headers[taken[target]]}” already feeds"
                res.candidates = _cand_out(cands, labels)
                continue
            target, why = slot, f"A second {labels.get(top.target, top.target).lower()} column goes to {labels.get(slot, slot)}"
        taken[target] = i
        res.field, res.confidence, res.reason = target, top.score, why
        res.level = "high" if top.score >= HIGH_AT else "medium"
        res.candidates = _cand_out([c for c in cands if c.target != top.target], labels)

    for res in results:
        if res.level == "none" and res.field is None and not res.reason:
            maybe = ranked.get(res.index, [])
            if maybe and maybe[0].score >= 0.45:
                res.reason = f"Not sure - maybe {labels.get(maybe[0].target, maybe[0].target)}"
                res.candidates = _cand_out(maybe, labels)
            else:
                res.reason = "No matching field found"
    return results


def _cand_out(cands: list[Candidate], labels: dict[str, str]) -> list[dict]:
    return [{"field": c.target, "label": labels.get(c.target, c.target), "score": c.score} for c in cands if c.score >= 0.45][:3]
