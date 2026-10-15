# AI Hub chat + "Ask AI" help - the plan (approved by Ahmed, 15 Oct)

One assistant ("the Brain") with two jobs: answer questions about BMI's data, and teach people how to use
the app (sales orders first). Build order: phase 0 foundation, phase 1 SOR help, phase 2 CRM data,
phase 3 MCP door + actions, phase 4 voice. Status is kept at the bottom.

## Architecture

- **One tool layer, two doors.** Tools are plain Python functions (`app/brain/tools/`) with typed
  input/output, a plain description, `read_only`, and allowed roles; they run as the asking user and use
  the app's own visibility rules. Google's agent kit (ADK) calls them **in-process** (no network hop;
  ADK's MCP client re-lists tools on every request). The same registry is published over **MCP**
  (`/mcp`, phase 3) for outside clients.
- **Model:** Gemini through ADK. Flash runs the tool loop; Flash-Lite does routing and titles.
- **Sums are done in code**, never by the model: "booked", "invoiced", the July financial year and
  commission come from the existing functions, so chat figures match the screens (semantic-layer idea;
  dbt's 2026 benchmark: ~90% raw text-to-SQL vs ~98% with defined metrics).

## Token and speed techniques (what we use)

1. **Prompt caching** - Gemini implicit caching (90% off cached input, min 4,096 tokens on 3.x Flash)
   plus ADK `ContextCacheConfig` / `static_instruction`. Cached tokens are logged per reply.
2. **Stable prefix** (Manus) - nothing that changes at the top: no timestamps, user or page in the system
   prompt; those go at the END of each user turn. Date to the day only. Tool results serialised with
   sorted keys.
3. **Fixed tool list** - never add/remove tools mid-chat (breaks the cache). Permissions are checked
   inside each tool, which answers "you can't see that".
4. **Progressive disclosure (Agent Skills)** - the agent sees a ~100-token catalogue of help guides and
   loads one only when needed (`help_list_guides` / `help_read_guide`). When asked from an SOR page, the
   SOR guide's outline is put in the turn's context.
5. **Task-shaped tools** (Anthropic "writing tools for agents") - ~30 tools built around questions, not
   one per endpoint; concise by default, capped rows, ID + link for every record, plain errors with a
   hint for what to try next.
6. **Hybrid search** (phase 2) - pgvector + Postgres full-text fused with reciprocal rank fusion, access
   filters applied BEFORE search, **contextual chunk headers** ("Note · Caribbean Journal · Sarah · Mar
   2024") - Anthropic: 49% fewer misses, 67% with reranking.
7. **Thinking level per question** - Gemini 3 defaults to "high" (slow); help and lookups use "low",
   analysis "medium"/"high".
8. **Parallel tool calls** - run together, not one by one (tool calls are 30-80% of agent latency).
9. **Streaming with live steps** - words stream in; steps show ("Looking up the booking…").
10. **Page awareness** - the page, record and clicked element come with the question, so no search
    step is needed for "this booking".
11. **Clearing old tool results / summarising** long chats.
12. **Answer cache for help only** (same question, same screen) - never for data.
13. **Small model routing** - Flash-Lite decides help vs data vs small talk.

Deliberately not used now: code execution / programmatic tool calling (needs a sandbox, pays off at
hundreds of tools) and tool search (too few tools).

## Quality and safety

- Permissions in code, never in the prompt. Tools run as the user.
- **Ask, don't guess** (CRMArena-Pro: ~58% single-turn, ~35% multi-turn; half of failures were not
  asking for missing info) - ambiguous names come back as clickable choices.
- Every figure has a source link (opens in a new tab). Says "not in the data" instead of guessing.
- **Evals:** a fixed set of questions with known answers (`app/brain/evals/`), run before any prompt or
  model change. Help evals check the answer names the right buttons and facts.
- **Tracing:** every turn stores tools used, tokens, cached tokens and time; thumbs up/down; admin view.
- Read-only first. Actions (reminders, drafts) later, always with a confirmation card. MCP read-only /
  destructive hints mark which is which.

## Help assistant (SOR first)

- **A written guide** in `backend/app/brain/help/sales-orders/*.md` (inside the backend so it deploys with it), one file per screen: what it's for, every button by its
  exact label, the business rules (locks, accounts check, when to invoice, hand-offs, Xero), common
  questions, "why can't I…". Small enough to load whole for SOR pages.
- **Screen map:** the feedback loader already tags elements with `data-src="file:line"`; a script
  collects each screen's button labels and InfoHint texts (`backend/app/brain/help/ui_map.json`, `npm run help-map`) so a clicked
  button maps to its guide section and the AI can only "Show me" things that exist.
- **Coverage check:** a test fails if an SOR button label has no mention in the guide; CLAUDE.md rule:
  change SOR → update the guide.
- **Answers grounded in the real record:** `sales_order_explain(id)` runs the same lock / check /
  invoice / hand-off functions the app uses, so "why can't I edit this?" gets the actual reason.
- **"Ask AI" button** beside Feedback, reusing its capture: pick a button or area, marked-up screenshot,
  page and record, recent on-screen errors. Formatted answer: numbered steps, button names as chips,
  tip/warning boxes, links in new tabs, follow-up suggestions, **"Show me"** spotlight on the real
  button, **"This didn't help"** → becomes a feedback item.
- **Voice:** dictation now (existing `transcribe_audio`); full voice mode later via Gemini Live API +
  ADK bidi streaming, same tools.

## Code layout

```
backend/app/brain/
  tools/        registry (@brain_tool) · help.py · sales.py · (crm.py, editorial.py, calls.py in phase 2)
  knowledge.py  loads docs/help/** as guides (skills) + the screen map
  agent.py      ADK agent, cache config, model + thinking level per route
  runner.py     runs a turn, streams events, records the trace
  evals/        question set + runner
models: BrainConversation · BrainMessage (trace on assistant messages)
frontend/src/components/brain/  panel · ask capture (reuses feedback) · answer renderer · show-me overlay
```

## Phases

| Phase | What | Days |
|---|---|---|
| 0 | Foundation: registry, tracing, evals runner, streaming chat, panel | 2 |
| 1 | SOR help: guide, screen map, Ask AI, Show me, explainers, coverage test, dictation | 3-4 |
| 2 | CRM data: data tools, metrics, hybrid search, sources, eval set with Matt + Samantha | 5-7 |
| 3 | MCP door, actions with confirmation, memory | 2-3 |
| 4 | Voice mode (Live API) | later |

Open questions for BMI: pgvector on production Postgres (phase 2); who can see what in chat; sign-off on
sending CRM data to Gemini (paid tier, not used for training); keep the OpenAI fallback for chat?

## Status

- **Phase 0 + 1 built (15 Oct).** See HANDOFF "Ask AI". The whole Sales Orders manual (15 guides, ~47k tokens) sits
  in the fixed, cached instructions - cheaper and more reliable than searching it while it's this size. When more
  areas are added and it passes ~80k tokens, move areas out of `prompt.ALWAYS_LOADED_AREAS` (they're then read on
  demand with help_read_guide).
- Not yet run against real Gemini (no key in the build session): run `python -m app.brain.evals` once the key is set.
- **Phase 2 built (15 Oct):** client and figures tools, metrics in code (tested against the overview), hybrid search
  index with an incremental 15-minute job. Works without pgvector (keyword only); meaning search turns on by itself
  once the extension is on the production database. Data evals to fill in with Matt and Samantha.
- Next: phase 3 (MCP door, actions with a confirmation card, memory), then phase 4 (voice).
