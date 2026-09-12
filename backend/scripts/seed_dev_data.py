"""Seed the local dev database with small, fake, realistic-shaped data -
NOT real BMI data. This is what Claude (or any developer) should be
building and testing against day to day; real migrated data only ever
lives in staging/production, never here.

Usage:
    python -m scripts.seed_dev_data          # adds 50 companies / 200 contacts
    python -m scripts.seed_dev_data --wipe    # clears existing dev data first

Safe to run repeatedly - everything it creates is tagged
source_db="devseed" so it's trivially identifiable and separable from any
real migrated rows that might also be present.
"""
import argparse
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Company, Contact, Group, GroupMembership  # noqa: E402
from app.models.contact_channel import Email, Phone  # noqa: E402

SOURCE = "devseed"

FIRST_NAMES = ["Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Drew", "Cameron"]
LAST_NAMES = ["Smith", "Jones", "Patel", "Nguyen", "Garcia", "Muller", "Rossi", "Kowalski", "Chen", "Okafor"]
COMPANY_WORDS = ["Global", "Summit", "Harbor", "Alpine", "Meridian", "Falcon", "Cedar", "Beacon", "Orbit", "Vertex"]
COMPANY_SUFFIXES = ["Hotels", "Resorts", "Travel Group", "Hospitality", "Tours", "Media"]
JOB_TITLES = ["Sales Director", "Marketing Manager", "Owner", "Procurement Lead", "General Manager"]


def rand_date(days_back=1500):
    return datetime.now(timezone.utc) - timedelta(days=random.randint(0, days_back))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wipe", action="store_true", help="delete existing devseed rows first")
    parser.add_argument("--companies", type=int, default=50)
    parser.add_argument("--contacts", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.wipe:
            # Children before parents, or the FK constraints reject the delete.
            # GroupMembership has no source_db of its own - scope it via the
            # devseed contacts/groups it points at instead.
            devseed_contact_ids = db.query(Contact.id).filter(Contact.source_db == SOURCE)
            db.query(GroupMembership).filter(GroupMembership.contact_id.in_(devseed_contact_ids)).delete(
                synchronize_session=False
            )
            for model in (Phone, Email, Contact, Group, Company):
                db.query(model).filter(model.source_db == SOURCE).delete()
            db.commit()
            print("Wiped existing devseed rows.")

        companies = []
        for i in range(args.companies):
            c = Company(
                id=uuid.uuid4(), source_db=SOURCE, source_act_id=f"devseed-company-{i}",
                name=f"{random.choice(COMPANY_WORDS)} {random.choice(COMPANY_SUFFIXES)}",
                industry=random.choice(["Hospitality", "Travel", "Media", "Retail"]),
                custom_fields={}, act_created_at=rand_date(),
            )
            companies.append(c)
        db.add_all(companies)
        db.flush()

        groups = [
            Group(id=uuid.uuid4(), source_db=SOURCE, source_act_id=f"devseed-group-{i}", name=name, custom_fields={})
            for i, name in enumerate(["Newsletter Subscribers", "VIP Accounts", "Cold Leads", "2026 Renewals"])
        ]
        db.add_all(groups)
        db.flush()

        contacts = []
        for i in range(args.contacts):
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            company = random.choice(companies) if random.random() < 0.85 else None
            c = Contact(
                id=uuid.uuid4(), source_db=SOURCE, source_act_id=f"devseed-contact-{i}",
                company_id=company.id if company else None,
                first_name=first, last_name=last, full_name=f"{first} {last}",
                job_title=random.choice(JOB_TITLES),
                custom_fields={"bmi_notes": "" if random.random() < 0.7 else "Met at conference 2025"},
                act_created_at=rand_date(),
            )
            contacts.append(c)
        db.add_all(contacts)
        db.flush()

        for c in contacts:
            db.add(Email(
                id=uuid.uuid4(), source_db=SOURCE, source_act_id=f"devseed-email-{c.id}",
                contact_id=c.id, address=f"{c.first_name}.{c.last_name}@example.com".lower(), is_primary=True,
            ))
            if random.random() < 0.6:
                db.add(Phone(
                    id=uuid.uuid4(), source_db=SOURCE, source_act_id=f"devseed-phone-{c.id}",
                    contact_id=c.id, number=f"+44 20 7{random.randint(1000000, 9999999)}", is_primary=True,
                ))
            for g in random.sample(groups, k=random.randint(0, 2)):
                db.add(GroupMembership(id=uuid.uuid4(), group_id=g.id, contact_id=c.id))

        db.commit()
        print(f"Seeded {len(companies)} companies, {len(contacts)} contacts, {len(groups)} groups.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
