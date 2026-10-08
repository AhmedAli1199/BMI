# BMI Brain

Before doing anything in this repo, read `docs/HANDOFF.md`. It covers the working rules, current state, business logic, and the UI/UX rulebook every new screen must follow. Also see `CONTEXT.md` and `docs/build-spec.txt`.

Key rules, in short:
- Push to `ui-polish-revamp`.
- Don't put model names in commits or code.
- Write standups in plain language.
- Use theme tokens only (no hardcoded colours), and reuse the existing patterns (data-view filters, InfoHint, HubHeader, side-sheet editors).
- Write user-facing copy in plain, jargon-free language.
- **Review queue cards: every record a card mentions (booking, company, contact, invoice...) must have a link that opens it in a NEW tab, so a reviewer can check it without losing their place. Always do this for any review kind you build or change. Also give each kind filters (`ReviewKind.facets`) and, where it has a date, a date sort (`date_sort_label`).**
- Contact fields live in ONE registry (`backend/app/contacts/fields.py`); search, export, bulk update and import all read it - never hard-code a field list elsewhere. Custom-field names are set there (see HANDOFF §2).
- Don't start the AI chat until Ahmed approves a plan.
- **Never show internal errors to users.** Every error shown on screen goes through `friendlyError(e, "plain fallback")` (frontend/src/lib/errors.ts); backend error messages must be plain sentences with no exception text, status codes or system names. Big actions (copy, export, bulk) must handle very large selections gracefully.
