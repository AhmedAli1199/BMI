"""Help tools: read a guide, search the guides, list what's on a screen."""
from __future__ import annotations

from app.brain import knowledge
from app.brain.registry import ToolEnv, ToolError, brain_tool


@brain_tool("Reading the guide")
def help_read_guide(env: ToolEnv, guide: str, section: str = "") -> dict:
    """Reads one help guide, or one section of it, when it isn't already known by heart.

    Args:
      guide: the guide id from the list of guides, e.g. "sales-orders/booking-page"
      section: optional heading to read just that part, e.g. "Common questions"
    """
    g = knowledge.guide(guide)
    if not g:
        raise ToolError(f"There's no guide called {guide!r}. Use one of the ids from the list of guides.")
    if section:
        want = section.strip().lower()
        hits = [s for s in g.sections if want in s.heading.lower()]
        if hits:
            return {"guide": g.id, "title": g.title, "sections": [{"heading": s.heading, "text": s.text.strip()} for s in hits[:3]]}
    return {"guide": g.id, "title": g.title, "screens": g.screens, "text": g.body}


@brain_tool("Searching the guides")
def help_search(env: ToolEnv, query: str) -> dict:
    """Finds the guide sections that best match some words - for questions that don't name a screen.

    Args:
      query: a few key words, e.g. "unlock booking accounts"
    """
    hits = knowledge.search(query)
    return {"results": [{"guide": g.id, "title": g.title, "heading": s.heading, "text": s.text.strip()[:1200]} for g, s in hits]}


@brain_tool("Checking what's on the screen")
def help_screen_elements(env: ToolEnv, page_path: str) -> dict:
    """Lists the buttons, links and hints that can appear on a page - use it before "Show me" when unsure a label exists.

    Args:
      page_path: the page address from <context>, e.g. "/sales/deals/1b2c..."
    """
    els = knowledge.elements_for_path(page_path)
    seen, out = set(), []
    for e in els:
        key = (e.get("kind"), e.get("label"))
        if e.get("label") and key not in seen:
            seen.add(key)
            out.append({"label": e["label"], "kind": e.get("kind")})
    return {"page": page_path, "elements": out[:150], "guides": [g.id for g in knowledge.guides_for_path(page_path)]}
