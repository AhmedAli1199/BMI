"""The help guides cover every Sales Orders button. If this fails after changing a screen: run
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


def _missing() -> dict[str, list[str]]:
    text = " ".join(g.body.lower() for g in knowledge.guides() if g.area == "sales-orders")
    m = knowledge.ui_map()
    files = {f for s in m["screens"] if s["route"].startswith("/sales") for f in s["files"]
             if f.startswith(("components/deals/", "components/sales/", "components/rate-card/", "components/commission", "app/(app)/sales/"))}
    out: dict[str, list[str]] = {}
    for e in m["elements"]:
        label = e["label"].strip()
        if e["file"] not in files or e["kind"] not in KINDS or label.lower() in GENERIC or label.lower() in NOT_LABELS or len(label) < 3:
            continue
        # the fixed words around anything that changes ("Save … prices"), without screen-reader extras
        parts = [p.strip(" ·:→").lower() for p in label.replace("(opens in a new tab)", "").split("…")]
        parts = [p for p in parts if len(p) >= 4]
        if parts and not all(p in text for p in parts):
            out.setdefault(e["file"], []).append(label)
    return out


def test_every_sales_orders_button_is_in_a_guide():
    missing = _missing()
    assert not missing, "Not mentioned in any Sales Orders guide:\n" + "\n".join(f"  {f}: {sorted(set(v))}" for f, v in sorted(missing.items()))
