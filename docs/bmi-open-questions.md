# Questions for BMI — running list

Business decisions we can't make on our own behalf while building the
automations. Only things that actually block or meaningfully change a
build go here — not every minor ambiguity. Check items off (with the date
and the answer) once BMI confirms; don't delete answered ones, so we keep
a record of what was decided and why.

---

## Open

- [ ] **Does a dedicated inbound-enquiry mailbox exist for SALES-011?**
      We need the address of an inbox that receives first-contact emails
      from people not already in the CRM (something like `enquiries@` /
      `info@` / `sales@`), separate from any salesperson's personal inbox
      and from the bounce-handling shared mailbox. Without this, SALES-011
      (inbound contact capture) has nothing to scan.
- [ ] **Which Act! database (Prospects / OnBoard / SellingTravel) does
      each such mailbox belong to?** Companies and Groups live in
      separate per-database tables, so a lead's suggested company/group
      depends on knowing which brand's mailbox it came in on. Needed as a
      `mailbox → database` mapping for every mailbox SALES-011 watches.
- [ ] **What is BMI's real "proposal sent" convention?** (SALES-009 -
      Proposal Logging). Do reps send proposals from a specific mailbox
      folder, with a consistent subject-line pattern, or a template? Or
      should we discover this by mining historical `notes`/`history_entries`
      for existing "proposal"/"quote" mentions instead of asking? Either
      answer unblocks SALES-009 - right now we don't have enough to know
      what a "proposal was sent" event actually looks like in their inbox.
- [ ] **Confirm which mailboxes are safe to add to the email-summary scan
      (SALES-010-lite) as genuine 1:1 salesperson mailboxes**, i.e. not
      shared/internal/management inboxes. We built a same-domain filter
      to catch obviously-internal threads automatically, but a
      BMI-confirmed list is more reliable than us inferring it from
      traffic patterns after the fact (see the David Wilcox finding below).

## Answered

*(none yet)*
