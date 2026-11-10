"""CS-006: is an email address worth sending to? Free checks, no outside service.

1. Is it written like an email address (one @, a real-looking domain, no spaces)?
2. Can its domain receive email? We ask the internet's address book (DNS) for the domain's mail servers, the same
   question an email server asks before sending. A domain that doesn't exist, or has no mail servers and no
   website address to fall back on, can't receive anything.

What this can't tell: whether one person's mailbox still exists at a working domain (jane@bigcompany.com after Jane
left). Only sending does that - a bounce is caught by the bounce scan (CS-001). If a lookup can't be answered
(the network is slow, or the domain's own DNS servers don't answer - often a passing fault), the address is given the
benefit of the doubt. Only "this domain doesn't exist" (a definite answer from the domain registry) or "no mail
servers and no address at all" counts as can't-receive.

Flagged addresses are left out by default, but a person can still choose to send to them (mail merge "Send anyway").
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from email_validator import EmailNotValidError, validate_email

NOT_WRITTEN_RIGHT = "address isn't written correctly"
NO_MAIL = "domain can't receive email"

# Common slips, so the reason can say what was probably meant.
TYPOS = {"gmial.com": "gmail.com", "gamil.com": "gmail.com", "gmai.com": "gmail.com", "gmail.co": "gmail.com",
         "gmail.co.uk": "gmail.com", "hotmial.com": "hotmail.com", "hotmail.co": "hotmail.co.uk", "hotmal.com": "hotmail.com",
         "outlok.com": "outlook.com", "yahooo.com": "yahoo.com", "yaho.com": "yahoo.com", "btinternet.co": "btinternet.com",
         "btinternet.co.uk": "btinternet.com", "icloud.co": "icloud.com"}

_TTL = 24 * 3600
_cache: dict[str, tuple[float, bool | None]] = {}   # domain -> (checked at, can receive mail; None = couldn't tell)


def written_problem(address: str | None) -> str | None:
    """Why the address can't be right as written, or None."""
    a = (address or "").strip()
    if not a:
        return None
    try:
        validate_email(a, check_deliverability=False)
    except EmailNotValidError:
        return NOT_WRITTEN_RIGHT
    dom = a.rsplit("@", 1)[1].lower()
    if dom in TYPOS:
        return f"{NOT_WRITTEN_RIGHT} (did they mean {TYPOS[dom]}?)"
    return None


def suggested_fix(address: str | None) -> str | None:
    """The address with a common domain slip corrected (jane@gmial.com -> jane@gmail.com), or None."""
    a = (address or "").strip()
    if "@" not in a:
        return None
    local, dom = a.rsplit("@", 1)
    fixed = TYPOS.get(dom.lower())
    return f"{local}@{fixed}" if fixed and local else None


def _lookup(domain: str) -> bool | None:
    import dns.exception
    import dns.resolver

    r = dns.resolver.Resolver()
    r.lifetime = 3
    try:
        r.resolve(domain, "MX")
        return True
    except dns.resolver.NXDOMAIN:
        return False   # the registry says the domain doesn't exist - a definite answer
    except dns.resolver.NoAnswer:
        pass   # no mail servers listed: mail falls back to the domain's own address
    except (dns.exception.Timeout, dns.exception.DNSException, OSError):
        return None
    try:
        r.resolve(domain, "A")
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    except (dns.exception.Timeout, dns.exception.DNSException, OSError):
        return None


def domains_without_mail(domains: set[str]) -> set[str]:
    """Which of these domains certainly can't receive email. Looked up together, remembered for a day."""
    now = time.monotonic()
    todo = [d for d in domains if d not in _cache or now - _cache[d][0] > _TTL]
    if todo:
        with ThreadPoolExecutor(max_workers=16) as pool:
            for d, ok in zip(todo, pool.map(_lookup, todo)):
                _cache[d] = (now, ok)
    return {d for d in domains if _cache.get(d, (0, None))[1] is False}


def problems(db, addresses: list[str | None]) -> dict[str, str]:
    """{address (lower case): why it's left out} for the addresses that can't work."""
    from app.automations import runtime_settings

    out: dict[str, str] = {}
    domains: dict[str, set[str]] = {}
    for a in addresses:
        a = (a or "").strip()
        if not a or a.lower() in out:
            continue
        if why := written_problem(a):
            out[a.lower()] = why
        else:
            domains.setdefault(a.rsplit("@", 1)[1].lower(), set()).add(a.lower())
    if domains and runtime_settings.get_bool(db, "email_domain_check_enabled"):
        for d in domains_without_mail(set(domains)):
            for a in domains[d]:
                out[a] = NO_MAIL
    return out
