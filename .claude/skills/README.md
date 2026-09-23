# UI polish skills — sourced for the `ui-polish-revamp` branch

Real, unmodified `SKILL.md` files fetched from their upstream repos, for the
full UI consistency/aesthetics pass discussed for this branch. Nothing here
was written by us — these are vendored as-is so Claude Code can load them via
the `Skill` tool. Update by re-fetching from the source URL below if the
upstream changes.

## 1. `webapp-testing` — screenshot/inspect the running app
Source: https://github.com/anthropics/skills/tree/main/skills/webapp-testing
Official Anthropic skill. Playwright-via-Python toolkit: navigate, wait for
`networkidle`, screenshot, read console logs. Includes its bundled
`scripts/with_server.py` (starts/stops the dev server around a script run).
Self-contained and ready to use as-is.

## 2. `playwright-skill` — alternative screenshot/browser-automation toolkit
Source: https://github.com/lackeyjb/playwright-skill (path:
`skills/playwright-skill/SKILL.md`)
MIT, Node 20+. Broader feature set than webapp-testing (responsive/breakpoint
checks, login-flow helpers, link checking) but depends on its own bundled
`run.js` + `lib/helpers.js` runtime, which were **not** vendored here (only
the SKILL.md doc was fetched). Treat as reference/inspiration for now, or
fetch the rest of https://github.com/lackeyjb/playwright-skill if we want it
runnable - `webapp-testing` above is the one that works out of the box.

## 3. `shadcn` — component/styling conventions + audit rules
Source: https://github.com/shadcn-ui/ui/tree/main/skills/shadcn (official,
lives in the shadcn/ui repo itself)
**The most directly useful one for this branch.** `rules/styling.md` in
particular is close to a checklist for exactly today's bugs (raw hex/utility
colors instead of semantic tokens, `space-x-*` instead of `gap-*`, missing
`cn()` for conditional classes, custom `<button>` markup instead of the
`Button` component). Also has `rules/composition.md`, `forms.md`,
`base-vs-radix.md`, `icons.md`, `chat.md`. Marked `user-invocable: false`
upstream (meant to be pulled in as reference/rules, not slash-invoked
directly) - use it as the audit checklist, per the frontmatter's own
component-doc framing.

## 4. `web-design-guidelines` — static audit pass
Source: https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines
Official Vercel skill. Fetches the current Vercel Web Interface Guidelines
and reports violations as terse `file:line` findings against a given set of
files/globs. Good second-opinion pass alongside the shadcn rules above.

## 5. `frontend-design` — aesthetic direction (secondary)
Source: https://github.com/anthropics/skills/tree/main/skills/frontend-design
Official Anthropic skill. About *creating/reshaping* visual design (type
scale, restrained motion, avoiding generic "AI-generated" tells), not
auditing existing consistency - useful if the pass turns into real
re-design decisions, secondary to the shadcn/web-design-guidelines pair for
a consistency-focused pass.

## Suggested order for the actual pass
1. Screenshot every route (light + dark, a couple of breakpoints) with
   `webapp-testing`.
2. Run the `shadcn` rules and `web-design-guidelines` as a checklist against
   the flagged screenshots + the component source.
3. Fix at the shared-component level first (Button/Badge/Card usage), not
   page-by-page - most of today's bugs were one bypassed primitive repeated
   in several places.
