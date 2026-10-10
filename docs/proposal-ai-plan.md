# Proposal AI: library, personal style and drafting agent (PARKED - build with the AI Hub chat)

Agreed with Ahmed on 10 Oct 2026: park until the remaining automations and BMI feedback items are done,
then build together with the AI Hub chat, since they share the same foundation (embeddings in Postgres,
a tool layer over BMI's data, an agent loop, figure checks). Don't start without Ahmed's go-ahead.

## Why
- BMI's big campaign proposals (e.g. "Selling Northern Territory - RFP Response", 14 pages, £25,000 net)
  are detailed: concept, strategy per element, audience figures, reach table, journey, data capture,
  measurement, dated timeline, investment table (rate card / net / discount), added value, the client's
  own response template (summary, deliverables + KPIs, measurement, inputs required, case studies).
- Most everyday proposals are short. Salespeople differ: some concise, some detailed.
- Goal: the AI drafts a full first version in the salesperson's own style, from a past proposal + the new
  client, and the salesperson only edits. **No extra input from salespeople just to train the AI.**

## Scope check against the original spec (docs/build-spec.txt)
- In scope already: SALES-020 "voice-matched" drafting (`voice_profile_id`); SALES-022 voice-matched templates;
  **SALES-023 "drawing on the strongest elements of prior similar pitches, in the owner's voice" with a pitch
  store, retrieval and indexing each new pitch back** (3-5 days); AI Hub chat RAG over notes/history/proposals (8-12 days).
- Beyond scope (a change request if built): uploading past proposals for a cold start, the tool-using drafting
  agent, learning from edits (draft vs sent), Quick / Standard / Full styles with data tables in Word, responding
  to a client brief (RFP) with a coverage checklist.

## Design
1. **Proposal library** per salesperson (mine / shared with the team): every proposal made in the system is
   saved automatically; optional upload of 5-10 past proposals (Word/PDF) per person for a cold start.
   Stored: original file, extracted text, structured version (sections, tables, products, prices, client,
   destination, date, owner), outcome (won = an order was made from it).
2. **Style profile** per salesperson, written by the AI from their library, in plain words, readable and
   editable ("I never include the history section"). A "house style" from won proposals for new people.
3. **Drafting agent** (tool loop, not a Codex-style agent with shell/file/web access). Tools, all over BMI data:
   client profile + history, search library (pgvector + filters: client, destination type, products, owner, won
   first), read a proposal, rate card, editorial plan (dates, deadlines, features, events), brand figures,
   style profile, price calculator (deterministic), timeline builder, write/revise section, check figures
   (every number must trace to a tool result). Workspace = the draft in our DB, section by section. Runs as a
   background job with live progress ("Reading the Northern Territory proposal... Checking the 2027 rate card...");
   ends with "what I assumed / what I need from you".
4. **Learning loop** (invisible): compare AI draft with what was sent; a background job updates the style
   profile; won proposals weigh more. No fine-tuning (too little data per person; long-context few-shot works).
5. **Proposal styles**: Quick (today's), Standard (+ audience, schedule table, investment table, added value),
   Full campaign (everything in the NT example). Section library: switch on/off, reorder. Data tables built
   from the system; written sections drafted at "short" or "detailed" length. Real tables in the Word file.
6. **Brief / RFP mode**: upload the client's brief, extract their required headings, build in their order,
   coverage checklist.
7. **Guardrails**: figures only from data, prices only from the calculator, libraries private unless shared,
   human review before sending, business API terms (no training on BMI data), cost limit per draft, full
   trace of tool calls. Evals: a fixed set of BMI proposals run before any AI change (figures 100% right, less
   editing over time).
8. **Provider**: keep behind one thin layer; bake-off on 5 real BMI proposals (Gemini already in use; OpenAI
   Agents SDK, Claude Agent SDK and Google's agent kit all fit the tool-loop design).

## Effort (rough, developer-days)
Library + upload/extraction 2-3 · style profiles 1-2 · drafting agent with tools, progress, checks 5-8 ·
styles, section library and Word tables 3-4 · learning loop + evals 2-4 · brief/RFP mode 2-3.
Total ~15-24 days; ~10-18 beyond what the spec already budgets (SALES-023 + voice matching).

## Needs from BMI before building
5-10 past proposals per salesperson who writes them (won/lost if known), 2-3 more campaign proposals like NT and
one "standard" one; which audience figures are current (12,463 print in the NT proposal vs 12,808 in the ACT
templates); AI provider choice + API key + monthly budget.
