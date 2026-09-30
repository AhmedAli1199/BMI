# Questions for BMI — running list

Business decisions we can't make on our own behalf while building the
automations. Only things that actually block or meaningfully change a
build go here — not every minor ambiguity. Check items off (with the date
and the answer) once BMI confirms; don't delete answered ones, so we keep
a record of what was decided and why.

---

## Open

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
- [ ] **Do we have (or can BMI set up) an MS Teams "Incoming Webhook"
      URL for the business-card batch-confirm summary?** (SALES-002).
      Without it, the added/updated/skipped summary just gets logged
      server-side instead of posted to a channel - works either way, but
      BMI presumably wants it visible somewhere the team actually looks.
- [ ] **SOR commission rate - is 2% the standard, and what earns 5%?**
      Every per-rep "Commission payable" figure across the 2026 SOR works
      out to exactly 2% of that rep's booked total, except two that are 5%.
      Shared bookings do exist but are rare (e.g. BA/Hungary 2025, booked
      "SP/ST" and credited £3,000 each in the sheet's commission columns) -
      the register now stores a per-rep credit, taken from those columns.
      Commission statements assume 2% of each rep's credit unless a rate
      is set on the booking. Need BMI to confirm the rule (by title? by
      rep? new vs renewal?) before those statements are treated as
      authoritative.

## Answered

- [x] **Dedicated inbound-enquiry mailbox for SALES-011, and which database?**
      (Sep 2026) `enquiries@bmipublishing.co.uk`, monitored by Shani and Kay,
      shown on all three sites - sales, editorial and deadline mail mixed
      together. Configured as `enquiries@bmipublishing.co.uk:*` (not tied to
      one brand). Subscription forms (STM -> Shani, TBTM -> Kay) arrive via
      Wufoo into those two people's personal inboxes, not a shared mailbox.
- [x] **Which mailboxes receive bounces/OOO for CS-001/002/003?** (Sep 2026)
      `noreply@onboardhospitality.com` and `noreply@thebusinesstravelmag.com`
      (Kay) receive all OOO from OBH + TBTM mailings;
      `online-editor@sellingtravel.co.uk` (Shani) receives all OOO from STM
      and its associated products.
