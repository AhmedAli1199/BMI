"""The Brain's tools: plain Python functions the agent can call, written once.

    @brain_tool("Looking up the booking")
    def sales_order_explain(env: ToolEnv, booking: str) -> dict:
        '''One line on what it does (the model reads this).

        Args:
          booking: the booking number or id
        '''

Every tool runs as the person who asked (env.identity / env.user), with its own database session, and
returns a small dict. Tools never raise to the model: a ToolError becomes {"error": "<plain sentence>"} and
anything unexpected becomes a plain "didn't work" (and goes in the log). Each call is timed and recorded in
the turn's trace. The list of tools never changes between turns (that keeps the prompt cache warm) - a
tool someone may not use answers "you can't see that" instead of disappearing.

The same registry is what the MCP door publishes later (docs/ai-hub-plan.md, phase 3).
"""
from __future__ import annotations

import inspect
import json
import logging
import time
import typing
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.identity import Identity

log = logging.getLogger("app.brain")


class ToolError(Exception):
    """A plain sentence for the model to pass on (or act on), e.g. "There's no booking 1234"."""


@dataclass
class ToolEnv:
    db: Session
    identity: Identity
    user: Any   # app.models.User
    session_id: str | None = None        # this turn (action cards are collected under it - app/brain/actions.py)
    conversation_id: str | None = None


@dataclass
class BrainTool:
    name: str
    label: str            # the live step shown while it runs ("Looking up the booking")
    fn: Callable
    read_only: bool = True
    adk_fn: Callable | None = None


TOOLS: dict[str, BrainTool] = {}


def _default_session():
    from app.db.session import SessionLocal
    return SessionLocal()


# How a tool gets its database session (tests point this at their own session).
session_factory: Callable[[], Session] = _default_session
# session id -> steps recorded by the tools during that turn (read by the runner)
TRACES: dict[str, list[dict]] = {}


def identity_state(identity: Identity) -> dict:
    return {"user_id": identity.user_id, "role": identity.role, "access": [list(a) for a in identity.access]}


def _identity(state) -> Identity:
    return Identity(user_id=state.get("user_id"), role=state.get("role"),
                    access=[(a[0], a[1]) for a in state.get("access") or []])


def _clean(value):
    """Same input -> byte-identical text for the model (sorted keys), so replies stay cacheable."""
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def brain_tool(label: str, read_only: bool = True):
    def deco(fn: Callable) -> Callable:
        from google.adk.tools import ToolContext

        hints = typing.get_type_hints(fn)
        params = [p for name, p in inspect.signature(fn).parameters.items() if name != "env"]

        def run(tool_context: ToolContext, **kwargs) -> dict:
            from app.models import User
            started = time.monotonic()
            ok = True
            state = tool_context.state
            identity = _identity(state)
            db = session_factory()
            try:
                user = db.get(User, uuid.UUID(state["user_id"])) if state.get("user_id") else None
                out = fn(ToolEnv(db=db, identity=identity, user=user, session_id=tool_context.session.id,
                                 conversation_id=state.get("conversation_id")), **kwargs)
            except ToolError as e:
                ok, out = False, {"error": str(e)}
            except Exception:
                log.exception("brain tool %s failed", fn.__name__)
                ok, out = False, {"error": "That lookup didn't work just now. Say so plainly and suggest trying again."}
            finally:
                db.rollback()
                db.close()
            TRACES.setdefault(tool_context.session.id, []).append(
                {"tool": fn.__name__, "label": label, "args": _clean(kwargs), "ms": int((time.monotonic() - started) * 1000), "ok": ok})
            return _clean(out)

        run.__name__ = fn.__name__
        run.__doc__ = fn.__doc__
        run.__signature__ = inspect.Signature(
            [*params, inspect.Parameter("tool_context", inspect.Parameter.KEYWORD_ONLY, annotation=ToolContext)],
            return_annotation=dict)
        run.__annotations__ = {**{p.name: hints[p.name] for p in params if p.name in hints}, "tool_context": ToolContext, "return": dict}
        TOOLS[fn.__name__] = BrainTool(name=fn.__name__, label=label, fn=fn, read_only=read_only, adk_fn=run)
        return fn
    return deco


def adk_tools() -> list:
    from google.adk.tools import FunctionTool

    from app.brain import tools  # noqa: F401  (registers them)
    return [FunctionTool(t.adk_fn) for t in sorted(TOOLS.values(), key=lambda t: t.name)]


def label_for(name: str) -> str:
    t = TOOLS.get(name)
    return t.label if t else "Working on it"
