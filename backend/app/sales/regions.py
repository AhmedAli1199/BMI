"""Selling Travel regions and who covers each one (Matt, 20 Oct 2026). A client goes by the destination it promotes,
not where its office is - Visit Malta has a London office but is a Malta client.

`spot(text)` finds the regions a client's name, website and description mention. Longer names are matched first
and taken out, so "New Jersey" never counts as Jersey (Channel Islands) and "Royal Caribbean" is a cruise line,
not the Caribbean. "UK" words are weak: "Tourism Australia UK" is an Australia client, so they only count when
nothing else is mentioned.

Left out on purpose, so the Brain asks instead of guessing: places that could be in two regions (Turkey, Egypt,
Cyprus, Georgia) and words that are usually something else ("American", "Jordan" as a name).

To change who covers a region, change REGION_REP. To add a place, add it to its region in PLACES.
"""
from __future__ import annotations

import re

# Region -> SalesRep code. Steve's "all events (worldwide)" and David's Accessibility Awards are products, not
# regions - see app/sales/ownership.py AREAS.
REGION_REP: dict[str, str] = {
    "North America": "SP", "Caribbean": "SP", "UK": "SP", "Pacific": "SP",
    "Spain": "ST", "Indian Ocean": "ST", "Middle East and Gulf": "ST",
    "Asia": "DW", "Africa": "DW", "Australasia": "DW", "India and sub-continent": "DW", "Western Europe": "DW",
    "Eastern Europe": "DW", "Scandinavia": "DW", "Mexico and Central America": "DW", "South America": "DW",
    "Ocean and river cruise": "DW", "Channel Islands": "DW",
}

PLACES: dict[str, tuple[str, ...]] = {
    "North America": (
        "usa", "united states", "visit usa", "brand usa", "canada", "canadian", "alaska", "hawaii", "florida",
        "california", "new york", "nyc", "las vegas", "orlando", "miami", "texas", "new england", "boston", "chicago",
        "san francisco", "los angeles", "seattle", "washington state", "washington dc", "new orleans", "louisiana",
        "arizona", "colorado", "utah", "nevada", "tennessee", "nashville", "memphis", "kentucky", "virginia",
        "carolina", "new jersey", "pennsylvania", "philadelphia", "maryland", "massachusetts", "maine", "vermont",
        "oregon", "montana", "wyoming", "idaho", "michigan", "illinois", "ohio", "wisconsin", "minnesota", "mississippi",
        "alabama", "missouri", "oklahoma", "new mexico", "south dakota", "north dakota", "ontario", "quebec", "toronto",
        "montreal", "vancouver", "british columbia", "alberta", "nova scotia", "newfoundland", "yukon", "manitoba",
        "saskatchewan", "new brunswick", "prince edward island", "great lakes", "niagara",
    ),
    "Caribbean": (
        "caribbean", "jamaica", "barbados", "bahamas", "antigua", "barbuda", "st lucia", "saint lucia", "grenada",
        "cayman", "turks and caicos", "bermuda", "aruba", "curacao", "bonaire", "dominican republic", "punta cana",
        "cuba", "puerto rico", "trinidad", "tobago", "virgin islands", "bvi", "anguilla", "st kitts", "nevis",
        "dominica", "st vincent", "grenadines", "martinique", "guadeloupe", "st barts", "st barths", "st maarten",
        "st martin", "montserrat", "haiti",
    ),
    "UK": (
        "england", "scotland", "scottish", "wales", "welsh", "northern ireland", "visitbritain", "visit britain",
        "visitengland", "visit england", "visitscotland", "visit scotland", "cornwall", "devon", "yorkshire",
        "lake district", "cotswolds", "isle of man", "isle of wight", "edinburgh", "glasgow", "highlands",
    ),
    "Pacific": (
        "fiji", "tahiti", "french polynesia", "bora bora", "cook islands", "samoa", "tonga", "vanuatu",
        "new caledonia", "papua new guinea", "palau", "south pacific", "solomon islands", "micronesia",
    ),
    "Spain": (
        "spain", "spanish", "canary islands", "canaries", "tenerife", "gran canaria", "lanzarote", "fuerteventura",
        "la palma", "balearic", "mallorca", "majorca", "menorca", "minorca", "ibiza", "formentera", "andalucia",
        "andalusia", "costa del sol", "costa brava", "costa blanca", "barcelona", "madrid", "seville", "malaga",
        "valencia", "benidorm", "catalonia", "galicia", "basque",
    ),
    "Indian Ocean": (
        "indian ocean", "maldives", "mauritius", "seychelles", "reunion", "madagascar", "rodrigues", "zanzibar",
    ),
    "Middle East and Gulf": (
        "middle east", "gulf", "arabian", "uae", "united arab emirates", "dubai", "abu dhabi", "ras al khaimah",
        "sharjah", "ajman", "fujairah", "qatar", "doha", "oman", "muscat", "bahrain", "saudi", "saudi arabia",
        "riyadh", "jeddah", "alula", "red sea", "kuwait", "israel", "tel aviv", "jerusalem", "lebanon", "beirut",
        "jordan tourism", "visit jordan", "petra", "aqaba",
    ),
    "Asia": (
        "asia", "asian", "japan", "japanese", "tokyo", "kyoto", "china", "chinese", "beijing", "shanghai",
        "hong kong", "macau", "macao", "taiwan", "korea", "seoul", "thailand", "thai", "bangkok", "phuket",
        "koh samui", "vietnam", "hanoi", "cambodia", "laos", "malaysia", "malaysian", "kuala lumpur", "borneo",
        "sabah", "sarawak", "langkawi", "penang", "singapore", "indonesia", "bali", "lombok", "philippines",
        "manila", "myanmar", "burma", "mongolia", "uzbekistan", "kazakhstan", "kyrgyzstan", "silk road",
    ),
    "Africa": (
        "africa", "african", "south africa", "cape town", "johannesburg", "kenya", "tanzania", "serengeti",
        "kilimanjaro", "uganda", "rwanda", "botswana", "namibia", "zambia", "zimbabwe", "victoria falls",
        "morocco", "moroccan", "marrakech", "tunisia", "ghana", "nigeria", "ethiopia", "mozambique", "malawi",
        "cape verde", "senegal", "gambia", "sierra leone", "eswatini", "swaziland", "lesotho", "algeria", "safari",
    ),
    "Australasia": (
        "australia", "australian", "new zealand", "aotearoa", "tasmania", "queensland", "new south wales",
        "sydney", "melbourne", "victoria australia", "western australia", "south australia", "adelaide",
        "northern territory", "great barrier reef", "auckland", "christchurch", "queenstown",
    ),
    "India and sub-continent": (
        "india", "indian", "incredible india", "goa", "kerala", "rajasthan", "delhi", "mumbai", "sri lanka",
        "nepal", "bhutan", "bangladesh", "pakistan", "himalaya", "himalayan",
    ),
    "Western Europe": (
        "france", "french", "paris", "provence", "normandy", "brittany", "loire", "bordeaux", "riviera", "corsica",
        "italy", "italian", "rome", "venice", "tuscany", "sicily", "sardinia", "amalfi", "lake garda", "milan",
        "portugal", "portuguese", "lisbon", "algarve", "porto", "madeira", "azores", "germany", "german",
        "bavaria", "berlin", "munich", "austria", "austrian", "vienna", "tyrol", "switzerland", "swiss",
        "netherlands", "holland", "dutch", "amsterdam", "belgium", "belgian", "flanders", "brussels", "luxembourg",
        "ireland", "irish", "dublin", "tourism ireland", "greece", "greek", "athens", "crete", "rhodes", "corfu",
        "santorini", "mykonos", "malta", "maltese", "gozo", "monaco", "andorra", "gibraltar", "liechtenstein",
    ),
    "Eastern Europe": (
        "eastern europe", "poland", "polish", "krakow", "warsaw", "czech", "czechia", "prague", "hungary",
        "hungarian", "budapest", "croatia", "croatian", "dubrovnik", "slovenia", "slovakia", "romania",
        "bulgaria", "serbia", "montenegro", "albania", "bosnia", "macedonia", "estonia", "latvia", "lithuania",
        "baltic", "baltics", "ukraine", "armenia", "azerbaijan", "moldova",
    ),
    "Scandinavia": (
        "scandinavia", "scandinavian", "nordic", "norway", "norwegian", "sweden", "swedish", "denmark", "danish",
        "copenhagen", "finland", "finnish", "lapland", "iceland", "icelandic", "faroe", "greenland", "stockholm",
        "oslo", "helsinki", "fjords",
    ),
    "Mexico and Central America": (
        "mexico", "mexican", "cancun", "riviera maya", "los cabos", "central america", "costa rica", "panama",
        "belize", "guatemala", "honduras", "nicaragua", "el salvador",
    ),
    "South America": (
        "south america", "latin america", "brazil", "brazilian", "rio de janeiro", "argentina", "buenos aires",
        "patagonia", "chile", "peru", "peruvian", "machu picchu", "colombia", "ecuador", "galapagos", "bolivia",
        "uruguay", "paraguay", "venezuela", "guyana", "suriname", "amazon",
    ),
    "Ocean and river cruise": (
        "cruise", "cruises", "cruising", "river cruise", "cruise line", "royal caribbean", "norwegian cruise",
        "p&o cruises", "p o cruises", "cunard", "princess cruises", "celebrity cruises", "msc cruises", "costa cruises",
        "carnival cruise", "viking cruises", "viking river", "ama waterways", "amawaterways", "uniworld", "scenic cruises", "scenic luxury", "avalon waterways", "riviera travel",
        "fred olsen", "fred. olsen", "ambassador cruise", "virgin voyages", "silversea", "seabourn", "regent seven seas",
        "oceania cruises", "azamara", "hurtigruten", "havila", "windstar", "ponant", "holland america", "emerald cruises",
        "saga cruises", "marella", "explora journeys", "aurora expeditions", "swan hellenic", "tauck", "crystal cruises",
        "hx expeditions", "lindblad", "a-rosa", "croisieurope", "titan river",
    ),
    "Channel Islands": ("channel islands", "jersey", "guernsey", "alderney", "sark", "herm"),
}

# Only count when nothing else is mentioned ("Tourism Australia UK" is an Australia client).
WEAK = {"UK": ("uk", "united kingdom", "great britain", "britain", "british", "london")}

_TERMS = sorted(((t, r, False) for r, ts in PLACES.items() for t in ts), key=lambda x: -len(x[0]))
_WEAK_TERMS = sorted(((t, r, True) for r, ts in WEAK.items() for t in ts), key=lambda x: -len(x[0]))


def _norm(s: str) -> str:
    s = s.lower().replace("&", " & ").replace("’", "'")
    s = re.sub(r"https?://|www\.|\.(com|co|uk|org|net|travel|info|gov|tourism)\b", " ", s)
    return " " + re.sub(r"[^a-z0-9&'.]+", " ", s).replace(".", " ") + " "


def spot(text: str) -> list[tuple[str, str]]:
    """[(region, the words that showed it)] - each region once, strongest first."""
    t = _norm(text or "")
    found: dict[str, str] = {}
    for terms in (_TERMS, _WEAK_TERMS):
        if terms is _WEAK_TERMS and found:
            break
        for term, region, _weak in terms:
            needle = f" {_norm(term).strip()} "
            if needle in t:
                found.setdefault(region, term)
                t = t.replace(needle, " | ")
    # A cruise line that names a place ("Royal Caribbean", "Viking" river cruises in Europe) is a cruise client.
    if "Ocean and river cruise" in found:
        return [("Ocean and river cruise", found["Ocean and river cruise"])]
    return list(found.items())


def spot_website(url: str) -> list[tuple[str, str]]:
    """Regions in a web address, where words run together ("visitmalta.com"). Only places of 5 letters or more,
    so short ones don't turn up inside other words."""
    host = re.sub(r"^(https?://)?(www\.)?", "", (url or "").lower()).split("/")[0]
    label = host.split(".")[0] if host else ""
    if not label:
        return []
    found: dict[str, str] = {}
    for term, region, _weak in _TERMS:
        flat = re.sub(r"[^a-z]", "", term)
        if len(flat) >= 5 and flat in label:
            found.setdefault(region, term)
            label = label.replace(flat, "|")
    if "Ocean and river cruise" in found:
        return [("Ocean and river cruise", found["Ocean and river cruise"])]
    return list(found.items())
