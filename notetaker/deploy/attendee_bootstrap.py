"""Runs once on every deploy, inside the Attendee image (python manage.py shell < this file).

Sets Attendee up so nobody has to: an organisation and project for the Notetaker, an admin login
(only needed for debugging), the API key and the webhook secret. They're written to
/shared/attendee.json, which the Notetaker reads - no signing up, no copying keys.
Safe to run again: it reuses everything that already exists.
"""
import base64
import hashlib
import json
import os
import secrets
import uuid

from accounts.models import Organization, User
from allauth.account.models import EmailAddress
from bots.models import ApiKey, Project, WebhookSecret

OUT = "/shared/attendee.json"
data = {}
if os.path.exists(OUT):
    try:
        data = json.load(open(OUT))
    except ValueError:
        data = {}

org = Organization.objects.filter(name="Notetaker").first() or Organization.objects.create(name="Notetaker")
org.is_async_transcription_enabled = True   # lets TRANSCRIPTION_MODE=gemini work
org.is_webhooks_enabled = True
org.save()

email = os.environ.get("ATTENDEE_ADMIN_EMAIL", "admin@notetaker.local")
user = User.objects.filter(email=email).first()
if not user:
    data["admin_password"] = secrets.token_urlsafe(18)
    user = User.objects.create_user(username=str(uuid.uuid4()), email=email, password=data["admin_password"], organization=org)
EmailAddress.objects.update_or_create(user=user, email=email, defaults={"verified": True, "primary": True})

project = Project.objects.filter(organization=org, name="Notetaker").first() or Project.objects.create(organization=org, name="Notetaker")
secret, _ = WebhookSecret.objects.get_or_create(project=project)

key = data.get("api_key")
if not key or not ApiKey.objects.filter(key_hash=hashlib.sha256(key.encode()).hexdigest(), disabled_at__isnull=True).exists():
    _, key = ApiKey.create(project=project, name="notetaker-service")

data.update(api_key=key, webhook_secret=base64.b64encode(secret.get_secret()).decode(), admin_email=email,
            project_id=project.object_id)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f)
os.chmod(tmp, 0o644)
os.replace(tmp, OUT)
print("Notetaker: the meeting bot is set up.")
