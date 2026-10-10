"""The sales email templates Clare sent from ACT! (Oct 2026), ready to load with one button.

They're brought over as drafts marked "needs a check": the figures and links that every email
repeats ("12,808 in print", "26,000 email database", the video and media pack links) became merge
fields filled from the brand's settings, so they're kept up to date in one place; ACT!'s
<Salutation> became {{salutation}} and the signature {{my_name}}. Obvious typos were fixed.
Anything dated (2024 issue links, Covid, old event dates and prices) is kept but called out in
the template's description for the salesperson to update.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EditorialSetting, SalesRep, SalesTitle
from app.models.messaging import MailTemplate

STM_FACTS = {
    "print_run": "12,808",
    "email_database": "26,000",
    "readership": "travel professionals throughout the UK",
    "video": "https://www.sellingtravel.co.uk/advertise/",
    "media_pack": "www.sellingtravelmedia.co.uk",
}

STM_PITCH = (
    "Check out our short video which offers a great overview of Selling Travel: {{video}}\n\n"
    "The leading travel trade publication since its launch in 1990, Selling Travel has provided travel retailers with the tools, "
    "information and inspiration they need to sell more travel. We reach travel professionals throughout the UK including all travel "
    "agencies, homeworkers, online agencies and tour operator reservations and contracting departments:\n"
    "- {{print_run}} in print\n- {{email_database}} email database"
)

TEMPLATES: list[dict] = [
    dict(name="Feature pitch: first email", rep="ST", kind="pitch", title="selling-travel",
         description="From Steve's \"Japan July 24\". Choose the issue and type the feature when you use it. "
                     "The paragraph describing the feature was about Japan - check it fits.",
         subject="{{feature|Our next feature}} in the {{issue|next issue}} of Selling Travel",
         body=("Hi {{salutation|there}},\n\nI hope all is well?\n\n"
               "We are currently working on our {{issue|next issue}}, out on {{issue_date|soon}}. I am pleased to announce that we have chosen "
               "{{feature|a destination close to your heart}} as one of our main features - would advertising against very relevant editorial be of interest?\n\n"
               "The feature will compare and contrast the trip options on offer, with an update on the destination including regional news, "
               "tour operator insight, new tours and hotel openings.\n\n" + STM_PITCH + "\n\n"
               "Improving agent product knowledge is now more important than ever to increase sales. Selling Travel can help, through its "
               "ever-expanding range of print, digital and tailor-made packages, including editorial coverage - all designed to do one thing: "
               "help agents sell more holidays.\n\n"
               "If you haven't seen the magazine in a little while, I would be more than happy to discuss how we have evolved to even better "
               "meet the needs of all the UK trade.\n\nI look forward to hearing from you.\n\nRegards\n{{my_name}}")),
    dict(name="Feature pitch: cruise and touring", rep="SDB", kind="pitch", title="selling-travel",
         description="From Stella's \"Cruise general 24\". Choose the issue. It linked to the January/February 2024 issue - "
                     "add the latest issue link to Selling Travel's settings.",
         subject="{{feature|Cruise}} in the {{issue|next issue}} of Selling Travel",
         body=("Hi {{salutation|there}},\n\nI hope all is well.\n\n"
               "Just a quick note to see if you would be interested in taking part in our {{issue|next issue}} of Selling Travel. It would go "
               "against a feature about {{feature|holidays aboard cruise ships with varied itineraries}}. I would love to catch up on your plans, "
               "aims and objectives, and ways we might be able to help. Readers of Selling Travel - travel agents across the UK, all "
               "{{email_database}} of them - would love to hear about it.\n\n"
               "The feature will inspire, advise, update and encourage agents to book, ensuring that they are better prepared to sell and are able "
               "to offer a wide product to entice their customers.\n\n"
               "Here is a link to our latest copy: {{latest_issue|available on request}}\n\n"
               "Selling Travel's readers are travel professionals throughout the UK and so, if they are up to speed on your product, it presents "
               "you with a huge opportunity to increase your future sales. The feature will reach all travel agencies, homeworkers, online agencies "
               "and tour operator reservation and contracting departments - currently {{print_run}} per issue.\n\n"
               "Check out our short video which offers a great overview of Selling Travel: {{video}}\n\n"
               "I look forward to hearing from you and do let me know if you need any more information.\n\nBest wishes,\n{{my_name}}")),
    dict(name="Feature pitch: second email", rep="SDB", kind="follow_up", title="selling-travel",
         description="From Stella's \"Malta Jan 24 Second email\" - the follow-up when there's been no reply. Choose the issue and type the feature.",
         subject="Still time to join our {{feature|feature}} in the {{issue|next issue}}",
         body=("Hi {{salutation|there}},\n\nI hope all is well.\n\n"
               "As we are coming to the end of working on our next issue, you still have time to take part in this exciting feature.\n\n"
               "Just a quick note to see if you would be interested in taking part in our {{issue|next issue}} of Selling Travel. It would go "
               "against a feature about {{feature|your destination}}. I would love to catch up on your plans, aims and objectives, and ways we might be able to help.\n\n"
               "Check out our short video which offers a great overview of Selling Travel: {{video}}\n\n"
               "- Print {{print_run}}\n- Online database {{email_database}}\n\n"
               "The feature will inspire, advise, update and encourage agents to book, ensuring that they are better prepared to sell a holiday "
               "and are able to offer a wide product to entice their customers.\n\n"
               "Here is a link to our latest copy: {{latest_issue|available on request}}\n\n"
               "I look forward to hearing from you and do let me know if you need any more information.\n\nBest wishes,\n{{my_name}}")),
    dict(name="New title launch: Selling Australia", rep="SDB", kind="launch", title="selling-australia",
         description="From Stella's \"Selling Australia First 24\". Mentions the Editor's trip to Melbourne and \"2025\" - update both. "
                     "It linked to the 2024 media kit: put the current one in Selling Travel's settings.",
         subject="Introducing Selling Australia",
         body=("Hi {{salutation|there}},\n\n"
               "I am excited to present to you the upcoming launch of our new trade publication that will inspire and encourage UK travel "
               "professionals to sell more Australia holidays and experiences.\n\n"
               "Written and designed by our award-winning team at Selling Travel, our flagship trade magazine - which has been a leading source of "
               "information and news for travel agents for 35 years - Selling Australia will include a range of features and articles that will "
               "showcase Australia's fabulous attractions, its 'wow moments', touring itineraries, experiences and activities. In short, it will be "
               "packed with holiday suggestions and touring ideas.\n\n"
               "Available in both a print and digital version, Selling Australia will also include new developments and experiences from around the "
               "states and territories and comments from the tourism industry's leading players: an A-Z of the reasons why the destination should be "
               "on the 'must sell' list of all UK and Irish travel agents in 2025.\n\n"
               "How do we reach our audience? The print edition will be distributed to travel professionals throughout the UK including travel agents, "
               "homeworkers, online agencies and tour operator reservation and contracting departments. It will also be promoted heavily on Selling "
               "Travel's website, in our weekly email, as a solus email to our online database, and via our popular social media channels.\n\n"
               "Our Editor, Jessica Alexander, was in Melbourne last week, discovering all that is new in Australia's tourism sector and meeting "
               "destinations and providers of tourism experiences - our goal is to provide the most relevant and 'salesworthy' information for our readers.\n\n"
               "I hope this email has piqued your interest in a project we are hugely excited about. We would love for you to feature in our "
               "publication - and there are many ways you can.\n\n"
               "This link will take you to the media kit which has all the latest information: {{media_pack}}. Please take a look and let me know if "
               "I can provide you with any more information.\n\nThanks\n{{my_name}}")),
    dict(name="Magazine update: monthly email", rep="ST", kind="general", title="selling-travel",
         description="From Steve's \"Monthly Email B\". Written for the November/December relaunch during Covid - rewrite it for today, "
                     "or delete it if it's no longer used.",
         subject="Selling Travel: what's new",
         body=("Hi {{salutation|there}},\n\nI hope all is well?\n\n"
               "Selling Travel is coming back this November with a fresh new look which represents an evolution of our position as British travel "
               "professionals' favourite travel trade magazine.\n\n"
               "The new-look Selling Travel will be a joint November/December issue and continue to offer the same premium-look, inspirational "
               "destination-focused content which agents cited as their number one reason to read us, but alongside this we will be putting much "
               "more focus on travel trends - cited as a close second reason to read Selling Travel. We will be featuring more future-scoping "
               "features and insights from travel industry insiders to help our readers get ahead of the game when it comes to selling travel in "
               "these difficult Covid-19 times.\n\n"
               "Nearly {{print_run}} UK travel agents receive printed copies of our award-winning Selling Travel magazine, and we want to be sure "
               "our readers have all they need to confirm the deals with their clients.\n\n"
               "Our research has shown us that more than half of our readers are so engaged with our content that they are looking at Selling "
               "Travel in their own time, and that agents are more likely to keep Selling Travel for 6 months or even longer than any other trade magazine.\n\n"
               "Our full media pack can be found at: {{media_pack}}\n\n"
               "I hope to hear from you soon and look forward to working with you in our first issue back.\n\nRegards\n{{my_name}}")),
    dict(name="Event invitation: Selling Travel Dialogue (Luxury)", rep="ST", kind="event", title="selling-travel-events",
         description="From Steve's \"STD Luxury\". The dates (8 and 9 May), cities, timings and the £1,555 price are from a past year - "
                     "update them before sending. Choose the event to fill in its name and date.",
         subject="Selling Travel Dialogue - Luxury: join us",
         body=("Hi {{salutation|there}},\n\nI hope all is well?\n\n"
               "Due to previous success, Selling Travel is pleased to announce two more exciting UK travel trade events to be held in May. Our "
               "'Selling Travel Dialogue - Luxury' events will turn the spotlight on this lucrative sector to help more agents sell luxury, high-end "
               "holidays to their clients - this includes hotels, cruises and flights.\n\n"
               "**What is it?** The event will follow our usual Selling Travel Dialogue format, helping agents learn more with an open forum, "
               "presentations and debate, plus an opportunity for speed dating. Great food and drinks will be served and there will be a range of "
               "prize give-aways to help encourage a good attendance. We have run around 150 of these agent-focused training events over the last "
               "few years and have received positive feedback from both agents and suppliers.\n\n"
               "**When and where?**\n- 8th May - Manchester\n- 9th May - London\n\n"
               "**The event format**\n- 5.30pm Partner set-up\n- 6.00 - 7.30pm Agent speed dating\n- 7.30 - 8.00pm Food, drink and open networking\n"
               "- 8.00 - 8.55pm Panel discussion / luxury debate\n- 8.55 - 9.00pm Prize draws\n- 9.00pm Finish\n\n"
               "**Why get involved?** Our events will give you the chance to promote your products and meet agents who specialise in selling luxury "
               "products, or have shown an interest in learning more about this potentially lucrative sector of the travel industry. The aim of the "
               "event is to highlight what is new in luxury, how to sell and up-sell, and help agents learn about the different products available - "
               "encouraging the trade to broaden their range of professional contacts, and so improving their luxury product sales.\n\n"
               "You will be given a table from which to promote your products and be invited to sit on the panel for the luxury debate - you can "
               "further raise your profile by offering items for the prize draw at the end of the evening.\n\n"
               "**Cost:** £1,555 for both. This also includes editorial coverage within the four-page article showcasing the event in the June issue "
               "of Selling Travel magazine - increasing the profile of your company to the full Selling Travel database.\n\n"
               "Supplier places are limited, so please get in touch as soon as possible as they will be allocated on a first come, first served basis.\n\n"
               "I look forward to hearing from you and welcoming you at what is set to be a great event.\n\nRegards\n{{my_name}}")),
    dict(name="Event invitation: Selling Travel Connect", rep="ST", kind="event", title="stm-connect-events",
         description="From Steve's \"STM Connect North Am\". The cities, dates (September), timings and the £995 table price are from a past "
                     "year - update them. Choose the event to fill in its name.",
         subject="{{issue|Selling Travel Connect}}: take a table",
         body=("Hi {{salutation|there}},\n\nI hope all is well?\n\n"
               "**{{issue|Selling Travel Connect: North America}}**\n\n"
               "This big travel trade event will bring together enthusiastic, forward-thinking agents and a select number of trade suppliers. Agents "
               "have the chance to update their existing knowledge and learn about destinations and products, to improve their sales and broaden their "
               "range of professional contacts. Taking a table is an opportunity for you to talk to these agents directly.\n\n"
               "**The dates and cities are as follows:**\n- Glasgow - 18th September (new date)\n- Leeds - 25th September\n- Birmingham - 26th September\n"
               "- London - 27th September (sold out)\n\n"
               "**The event format is:**\n- 5.30 - 6.00pm Supplier set-up with food and drink service\n- 6.00 - 6.30pm Agents arrive, networking with food and drink\n"
               "- 6.30 - 7.45pm Agent speed-dating\n- 7.45 - 8.00pm Break\n- 8.00 - 8.45pm Q&A with suppliers\n- 8.45 - 9.00pm Prize draws\n- 9.00pm Finish\n"
               "(times are approximate)\n\n"
               "A table is £995 per event. The promotional package for the event also includes:\n"
               "- Event report in the November/December issue of Selling Travel\n- Online event review\n"
               "- Online photo gallery (all available on the website for one year)\n- Lead story on the event in the Selling Travel e-newsletter\n"
               "- Social media activity before, during and after the event\n- A place in the 60-second reel\n\n"
               "I look forward to hearing from you.\n\nCheers\n{{my_name}}")),
]


def act_template_count(db: Session) -> int:
    return len(db.scalars(select(MailTemplate.id).where(MailTemplate.source == "act")).all())


def load(db: Session) -> int:
    """Adds the templates not already loaded (by name), and Selling Travel's figures where they're still blank. Returns how many were added."""
    titles = {t.slug: t.id for t in db.scalars(select(SalesTitle))}
    reps = {r.code: r.user_id for r in db.scalars(select(SalesRep))}
    have = set(db.scalars(select(MailTemplate.name).where(MailTemplate.source == "act")))
    n = 0
    for t in TEMPLATES:
        if t["name"] in have:
            continue
        db.add(MailTemplate(id=uuid.uuid4(), name=t["name"], subject=t["subject"], body=t["body"], shared=True,
                            owner_user_id=reps.get(t["rep"]), brand="stm", title_id=titles.get(t["title"]), kind=t["kind"],
                            description=t["description"], source="act", needs_check=True))
        n += 1
    st = db.get(EditorialSetting, "stm")
    if st is None:
        st = EditorialSetting(brand="stm", deadline_rules=[], regular_sections=[], facts={})
        db.add(st)
    facts = dict(st.facts or {})
    for k, v in STM_FACTS.items():
        facts.setdefault(k, v)
    st.facts = facts
    db.flush()
    return n
