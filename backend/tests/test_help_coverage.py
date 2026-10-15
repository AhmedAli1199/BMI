"""The help guides cover every button in the app (Sales Orders, CRM, editorial plan, automations, settings). If this fails after changing a screen: run
`npm run help-map` in frontend/, then add the new button (by its exact label) to the right guide in
app/brain/help/sales-orders/ - see CLAUDE.md."""
from app.brain import knowledge

# Words that mean the same everywhere and don't need explaining.
GENERIC = {"close", "cancel", "save", "done", "search", "more", "back", "next", "previous", "ok", "yes", "no", "remove", "edit",
           "delete", "clear", "apply", "add", "open", "show", "hide", "undo", "retry", "try again", "copy", "keep", "not now",
           "start", "change", "send", "reset", "select", "upload", "download", "print", "export", "view", "more options",
           # what a button says while it's busy
           "creating", "drafting", "writing it down", "saving", "sending", "loading"}
KINDS = {"button", "menu item", "tab", "link"}
# Bits of text the map picks up that aren't really button labels (pieces of a sentence around a number).
NOT_LABELS = {"price offer", "booking · linked"}


# Each help area and the screens (by address) and code it has to cover.
AREAS = {
    "sales-orders": (("/sales",), ("components/deals/", "components/sales/", "components/rate-card/", "components/commission", "app/(app)/sales/")),
    "crm": (("/contacts", "/companies", "/groups", "/activities", "/reminders", "/mail-merge", "/calls"),
            ("components/contacts", "components/companies", "components/groups", "components/calls", "components/mail-merge",
             "app/(app)/contacts", "app/(app)/companies", "app/(app)/groups", "app/(app)/activities", "app/(app)/reminders",
             "app/(app)/mail-merge", "app/(app)/calls")),
    "editorial": (("/editorial",), ("components/editorial", "app/(app)/editorial")),
    "automations": (("/automations",), ("components/automations", "app/(app)/automations")),
    "platform": (("/settings", "/feedback", "/data-health", "/brain"),
                 ("components/settings", "components/feedback", "components/brain", "app/(app)/settings", "app/(app)/feedback",
                  "app/(app)/data-health", "app/(app)/brain")),
}


def _missing(area: str = "sales-orders") -> dict[str, list[str]]:
    routes, prefixes = AREAS[area]
    text = " ".join(g.body.lower() for g in knowledge.guides() if g.area == area)
    m = knowledge.ui_map()
    files = {f for s in m["screens"] if s["route"].startswith(routes) for f in s["files"] if f.startswith(prefixes)}
    out: dict[str, list[str]] = {}
    for e in m["elements"]:
        label = e["label"].strip()
        if e["file"] not in files or e["kind"] not in KINDS or label.lower() in GENERIC or label.lower() in NOT_LABELS or len(label) < 3:
            continue
        # the fixed words around anything that changes ("Save … prices"), without screen-reader extras
        if len(label) > 50:   # a card or link with its description: its heading is enough
            label = " ".join(label.split()[:3])
        parts = [p.strip(" ·:→").lower() for p in label.replace("(opens in a new tab)", "").split("…")]
        parts = [p for p in parts if len(p) >= 4]
        if parts and not all(p in text for p in parts):
            out.setdefault(e["file"], []).append(label)
    return out


import pytest  # noqa: E402


@pytest.mark.parametrize("area", sorted(AREAS))
def test_every_button_is_in_a_guide(area):
    missing = _missing(area)
    assert not missing, f"Not mentioned in any {area} guide:\n" + "\n".join(f"  {f}: {sorted(set(v))}" for f, v in sorted(missing.items()))
