"""Runs every 30 seconds inside the Attendee image (the attendee-sync container): gives each notetaker app that has
its own Zoom keys its own project in the meeting bot.

Why: the meeting bot holds one set of Zoom keys per project, and Zoom keys belong to each app (a Zoom app is made
by whoever owns the project using the notetaker). So the notetaker stays generic: an admin pastes an app's Zoom
Client ID and Secret in the console, and within a minute that app's Zoom calls work - no settings on the server.

It asks the notetaker which apps need a project (GET /internal/bot-projects), makes or updates the project, its API
key, webhook secret and Zoom app (checking the keys with Zoom only when they change), and reports back
(POST /internal/bot-projects/<app>). Uses the meeting bot's own models, like attendee_bootstrap.py; the meeting bot
itself is unchanged. Safe to run again and again.
"""
import base64
import os

import requests
from accounts.models import Organization
from bots.models import ApiKey, Project, WebhookSecret, ZoomOAuthApp, ZoomOAuthConnection
from bots.zoom_oauth_connections_utils import client_id_and_secret_is_valid

NOTETAKER = os.environ.get("NOTETAKER_INTERNAL_URL", "http://notetaker-api:8080").rstrip("/")
HEADERS = {"X-Internal-Token": os.environ.get("INTERNAL_TOKEN", "")}

org = Organization.objects.filter(name="Notetaker").first()
if org is None:
    print("attendee-sync: waiting for the set-up step (no Notetaker organisation yet).")
else:
    r = requests.get(f"{NOTETAKER}/internal/bot-projects", headers=HEADERS, timeout=20)
    r.raise_for_status()
    for a in r.json().get("apps", []):
        out = {}
        try:
            project = Project.objects.filter(organization=org, object_id=a.get("project_id")).first() if a.get("project_id") else None
            if project is None:
                project = Project.objects.create(organization=org, name=f"App: {a['name']}"[:255])
            secret, _ = WebhookSecret.objects.get_or_create(project=project)
            out["project_id"] = project.object_id
            out["webhook_secret"] = base64.b64encode(secret.get_secret()).decode()
            if not a.get("key_hash") or not ApiKey.objects.filter(project=project, key_hash=a["key_hash"], disabled_at__isnull=True).exists():
                _, out["api_key"] = ApiKey.create(project=project, name="notetaker-service")

            zid, zsecret = (a.get("zoom_client_id") or "").strip(), (a.get("zoom_client_secret") or "").strip()
            zoom_app = ZoomOAuthApp.objects.filter(project=project).first()
            if not (zid and zsecret):
                out["zoom"] = "off"
            elif zoom_app and zoom_app.client_id == zid and zoom_app.client_secret == zsecret:
                out["zoom"] = "ready"
            elif not client_id_and_secret_is_valid(zid, zsecret):
                out["zoom"] = "error"
                out["error"] = ("Zoom didn't accept this Client ID and Client Secret. Copy both again from the Zoom app's "
                                "Basic Information page (App Credentials) and save.")
            else:
                if zoom_app and zoom_app.client_id != zid:
                    # a different Zoom app: the old one's sign-ins can't be used with it
                    ZoomOAuthConnection.objects.filter(zoom_oauth_app=zoom_app).delete()
                    zoom_app.delete()
                    zoom_app = None
                zoom_app = zoom_app or ZoomOAuthApp(project=project, client_id=zid)
                zoom_app.client_id = zid
                zoom_app.set_credentials({"client_secret": zsecret, "webhook_secret": ""})
                out["zoom"] = "ready"
        except Exception as e:   # one app's problem mustn't stop the others
            out = {"zoom": "error", "error": "The meeting bot couldn't set up Zoom for this app. See the attendee-sync logs."}
            print(f"attendee-sync: {a.get('app_id')}: {e!r}")
        requests.post(f"{NOTETAKER}/internal/bot-projects/{a['app_id']}", json=out, headers=HEADERS, timeout=20)
