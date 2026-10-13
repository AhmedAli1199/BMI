"""Notes styles: what the write-up should pull out, by kind of call. Each app picks one; its own
extra instructions are added on top."""
STYLES: dict[str, tuple[str, str]] = {
    "general": ("General", "Write balanced notes for any kind of meeting."),
    "sales": ("Sales call", "This is a sales conversation. Pull out the client's needs, objections, budget, prices and products discussed, "
                            "deadlines, buying signals and the agreed next step. Note who on the client side makes the decision."),
    "interview": ("Interview", "This is a job interview. Summarise the candidate's experience, strengths, concerns, answers to key questions, "
                               "salary or notice period if mentioned, and the agreed next step. Stay factual and neutral."),
    "standup": ("Team stand-up", "This is an internal team meeting. List what each person is working on, blockers, decisions and owners."),
    "support": ("Support call", "This is a customer support call. Capture the problem, steps already tried, the fix or workaround, "
                                "whether it's resolved, and any follow-up promised."),
}


def instructions(style: str | None, extra: str | None) -> str | None:
    base = STYLES.get(style or "general", STYLES["general"])[1]
    return f"{base} {extra}".strip() if extra else base
