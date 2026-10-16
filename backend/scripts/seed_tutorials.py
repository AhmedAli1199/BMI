"""Sets up the data the tutorial videos are recorded on (docs/tutorials/), so every recording shows the same
clients, issues and prices as the script says. Safe to re-run: it only adds what's missing.

NEVER run this against the live database - it creates demo accounts with a known password.

    DATABASE_URL=postgresql+psycopg://.../bmi_demo python -m scripts.seed_tutorials --yes

What it makes:
- the reference data (titles, salespeople) and the 2026 rate cards and editorial plans for every brand
- Onboard Hospitality Issue 108 (10 Dec 2026, advertising deadline 2 Dec) and Issue 109 (Mar 2027)
- Gate Gourmet (company, Onboard database) with Daniel Weber, Head of Marketing
- two sign-ins (password below): Sally Parker (Sales, linked to salesperson SP) and Samantha Elmer (Accounts)

Every run also removes the bookings made for Gate Gourmet in earlier takes (and their review cards and alerts), so
each recording starts from the same screen - the form shows "Invoice details filled in from their last booking"
once a booking exists, which moves everything below it down.
"""
import os
import sys
import uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import Text, cast, or_, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Notification, ReviewQueueItem, SalesDeal, SalesOrder
from app.models import Company, Contact, Email, SalesEdition, SalesRate, SalesRep, SalesTitle, User, UserAccess  # noqa: E402

PASSWORD = "BMI-tutorial-2026"
PEOPLE = [
    # name, email, role, can approve bookings (Accounts), database access, salesperson code to link
    ("Sally Parker", "sally.parker@tutorial.bmi", "sales", False, [("onboard", None)], "SP"),
    ("Samantha Elmer", "samantha.elmer@tutorial.bmi", "data_manager", True, [("onboard", None), ("sellingtravel", None)], None),
]


def main() -> None:
    if "--yes" not in sys.argv:
        sys.exit("This creates demo sign-ins with a known password. Run it only on a demo database, with --yes.")
    if settings.environment == "production" or not any(w in settings.database_url for w in ("demo", "tutorial", "test")):
        sys.exit("Refusing: the database name must contain 'demo', 'tutorial' or 'test'.")
    from app.sales import editorial_seed, rate_card_seed
    from app.sales.reference import ensure_reference_data
    db = SessionLocal()
    try:
        ensure_reference_data(db)
        for brand in ("obh", "stm", "tbtm"):
            titles = [t.id for t in db.scalars(select(SalesTitle).where(SalesTitle.slug.like(f"{'selling' if brand == 'stm' else brand}%")))]
            if not db.scalar(select(SalesRate.id).where(SalesRate.title_id.in_(titles), SalesRate.year == 2026).limit(1)):
                rate_card_seed.load_seed(db, brand, 2026)
            try:
                editorial_seed.load_seed(db, brand, 2026)
            except Exception:
                db.rollback()   # already loaded
        obh = db.scalar(select(SalesTitle).where(SalesTitle.slug == "obh"))
        for name, year, pub, ad, copy in (("108", 2026, date(2026, 12, 10), date(2026, 12, 2), date(2026, 12, 4)),
                                          ("109", 2027, date(2027, 3, 18), date(2027, 3, 10), date(2027, 3, 12))):
            e = db.scalar(select(SalesEdition).where(SalesEdition.title_id == obh.id, SalesEdition.name == name))
            if not e:
                e = SalesEdition(id=uuid.uuid4(), title_id=obh.id, year=year, name=name, kind="issue", status="open")
                db.add(e)
            e.edition_date, e.ad_deadline, e.copy_deadline = pub, ad, copy
        co = db.scalar(select(Company).where(Company.name == "Gate Gourmet", Company.source_db == "onboard"))
        if not co:
            co = Company(id=uuid.uuid4(), name="Gate Gourmet", industry="Airline catering", source_db="onboard",
                         source_act_id=f"tutorial-{uuid.uuid4()}")
            db.add(co)
            db.flush()
        c = db.scalar(select(Contact).where(Contact.full_name == "Daniel Weber", Contact.source_db == "onboard"))
        if c:
            c.company_id = co.id
        else:
            c = Contact(id=uuid.uuid4(), full_name="Daniel Weber", first_name="Daniel", last_name="Weber", job_title="Head of Marketing",
                        company_id=co.id, source_db="onboard", source_act_id=f"tutorial-{uuid.uuid4()}")
            db.add(c)
            db.flush()
            db.add(Email(id=uuid.uuid4(), contact_id=c.id, address="daniel.weber@gategourmet.example", is_primary=True,
                         source_db="onboard", source_act_id=f"tutorial-{uuid.uuid4()}"))
        # earlier takes: delete them so the form looks the same every time
        for d in db.scalars(select(SalesDeal).where(SalesDeal.company_id == co.id)).all():
            key = str(d.id)
            for o in db.scalars(select(SalesOrder).where(SalesOrder.deal_id == d.id)).all():
                db.delete(o)
            for r in db.scalars(select(ReviewQueueItem).where(or_(ReviewQueueItem.entity_id == d.id, cast(ReviewQueueItem.payload, Text).contains(key)))).all():
                db.delete(r)
            for n in db.scalars(select(Notification).where(Notification.link.contains(key))).all():
                db.delete(n)
            db.delete(d)
        db.flush()
        for name, email, role, approves, access, rep_code in PEOPLE:
            u = db.scalar(select(User).where(User.email == email))
            if not u:
                u = User(id=uuid.uuid4(), email=email, name=name, role=role, hashed_password=hash_password(PASSWORD), is_active=True)
                db.add(u)
                db.flush()
                for source_db, group in access:
                    db.add(UserAccess(user_id=u.id, source_db=source_db, group_id=group))
            u.can_approve_bookings = approves
            if rep_code:
                rep = db.scalar(select(SalesRep).where(SalesRep.code == rep_code))
                if rep:
                    rep.user_id = u.id
        db.commit()
        print(f"Tutorial data ready. Sign in as sally.parker@tutorial.bmi or samantha.elmer@tutorial.bmi, password {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
