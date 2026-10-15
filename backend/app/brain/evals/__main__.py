"""python -m app.brain.evals [--data] [--only N]: asks every question in questions.json (or, with --data,
data_questions.json - questions about real clients and figures, to fill in with Matt and Samantha: replace each
<client> and add what the right answer must say; each "check" says what to compare it with) for real.

Each check: "all" must all appear, at least one of "any" must appear, none of "none" may appear (case-insensitive).
Prints pass/fail, seconds and how much came from the prompt cache. A help answer that names the wrong button
fails here before anyone at BMI sees it."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from sqlalchemy import select

from app.brain import agent, runner
from app.core.identity import Identity
from app.db.session import SessionLocal
from app.models import User


def check(text: str, q: dict) -> list[str]:
    low = text.lower()
    bad = [f"missing “{w}”" for w in q.get("all", []) if w.lower() not in low]
    if q.get("any") and not any(w.lower() in low for w in q["any"]):
        bad.append("none of: " + ", ".join(q["any"]))
    bad += [f"shouldn't say “{w}”" for w in q.get("none", []) if w.lower() in low]
    return bad


async def main(only: int | None, data: bool = False) -> int:
    if not agent.configured():
        print("GEMINI_API_KEY isn't set - nothing to test against.")
        return 2
    db = SessionLocal()
    user = db.scalar(select(User).where(User.role == "admin").limit(1))
    identity = Identity(user_id=str(user.id), role="admin")
    qs = json.loads((Path(__file__).parent / ("data_questions.json" if data else "questions.json")).read_text())
    qs = [q for q in qs if "<client>" not in q["q"]]   # not filled in yet
    failed = 0
    for i, q in enumerate(qs, 1):
        if only and i != only:
            continue
        ctx = {"page_path": q["page"]}
        model_text = f"{q['q']}\n\n{runner.context_block(user, identity, ctx)}"
        t0, done = time.monotonic(), None
        async for ev in runner.run(user, identity, [], runner.Asked(question=q["q"], context=ctx), model_text):
            if ev["type"] == "done":
                done = ev
        bad = check(done["text"], q)
        tr = done["trace"]
        cache = f"{round(100 * tr['cached_tokens'] / tr['input_tokens'])}%" if tr.get("input_tokens") else "-"
        print(f"{'PASS' if not bad else 'FAIL'}  {i:>2}. {q['q'][:60]:<60} {time.monotonic() - t0:5.1f}s  cache {cache:>4}  {'; '.join(bad)}")
        if data and q.get("check"):
            print(f"      check by hand: {q['check']}\n      " + done["text"][:300].replace("\n", " "))
        if bad:
            failed += 1
            print("      " + done["text"][:400].replace("\n", " ") + "\n")
    print(f"\n{len(qs) - failed if not only else (0 if failed else 1)} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
    raise SystemExit(asyncio.run(main(n, "--data" in sys.argv)))
