# Baseline snapshot before the LLM-tuning pass (2026-09-21)

Recorded before adding the Tier B/C filtering + LLM classification to
inbound_capture.py and bounce_handling.py, so a post-change rescan can be
checked against this: did the genuinely good ones survive, did the noise
actually drop. These rows already exist as pending review-queue items and
won't be retroactively changed - to re-test, dismiss/clear them and use
"Reset & rescan" on the relevant scan, same as the email-signals rework.

## Inbound capture - genuine/valuable leads identified in the 111-row sample

| id | sender | why it's genuine |
|---|---|---|
| 433deaba-4677-4582-88ac-4538582026dc | ian.watson@travelcounsellors.com | Self-registration: "I'm a new Travel Counsellor... asked to be added to the contact list" |
| 882e4457-6d85-49fa-8995-e774b9806f67 | marissa@wessco.net | New marketing manager introduced at an existing account |
| e5d97409-84c1-41bb-854b-6ed062b994c9 | kamariya.zhanabayeva@airastana.com | Fresh business enquiry (awards entry pricing questions) |
| b57bed8a-6e35-432e-9920-cd30bb9c1c0b | mike.pack@princesscruises.co.uk | Handover: predecessor named him/Anastasia as new contact |
| c3a19803-02cb-4f7d-90e7-91021db16008 | neil.whiting@sap.com | Covering for a departed colleague (Elisa), new point of contact |
| 508c5a90-d277-43e0-9060-b95cc6edd8e2 | hmiers@northcottglobalsolutions.com | Warm introduction of a new business contact via a mutual connection |
| 27f27075-fadf-4927-9d26-88c171cabf8d | juliet.howie@radissonhotels.com | Existing contact notifying of a company change |
| 2ddefe2f-d68c-4a61-80c1-6c4afeee5abd | josh@thrustcarbon.com | Fresh PR/press pitch (borderline - legitimate new sender, promotional content) |

Note: several of these (mike.pack, neil.whiting, hmiers, juliet.howie) are
replies within an existing email thread - the new "reply-to-existing-
thread" filter will likely also catch these as a false negative. That's a
known, accepted trade-off given how much noise the same filter removes;
worth checking after the rescan whether it's worth softening for the
handover/job-change case specifically.

## OOO scan - genuine cases in the 6-row sample

| id | sender/subject | why it's genuine |
|---|---|---|
| ae13750a-aea4-4af9-a24b-19048cc07943 | Sally Liptrott (Review Travel) | Genuine COVID-era remote-working redirect notice - no named replacement, but a real absence/redirect |
| f534ce38-8ae8-45e9-9ed4-c7677a8d20dd | Nikki | Genuine dated absence (18/09-02/10) - replacement names "Rebecca or Katie" stated in prose but not extracted (pre-fix bug) |

The other 4 OOO rows (Manager/routing-failure, Manager/Crystal Travel,
Manager/Pure Luxury Concierge, Carlos Ibanez/Soliman Travel) are the
false positives this pass is meant to fix - generic auto-acknowledgment
templates or (for the routing-failure one) a misclassified bounce.
