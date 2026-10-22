# Zoom app review - Technical Design answers (BMI Notetaker)

Architecture diagram: `BMI-Notetaker-architecture.png` (made from `architecture.html` - edit that and re-shoot if it changes).

## Technology stack
BMI Notetaker is BMI Publishing's internal notetaker, used only by BMI staff on their own sales calls. It has three parts, all running in Docker on one server operated for BMI by Cybix, behind a Traefik reverse proxy that serves HTTPS (TLS 1.2+):

1. BMI Brain (https://bmi.rabtaai.com) - BMI's CRM where staff connect Zoom.
   - Web app: Next.js 16, React 19, TypeScript, Tailwind CSS.
   - API: Python 3.11, FastAPI, SQLAlchemy 2, Alembic, httpx, PostgreSQL 16.
   - Zoom: OAuth 2.0 authorization code flow (user-managed app); redirect URL https://bmi.rabtaai.com/api/zoom/callback, signed state valid 15 minutes. Stores only the link between a BMI user and their Zoom user ID (no Zoom tokens).
   - Calendar: Microsoft Graph and Google Calendar (read-only) to know when a staff member has a Zoom meeting.
2. Notetaker service - books the meeting bot, writes notes.
   - Python 3.11, FastAPI, SQLAlchemy 2, httpx, PostgreSQL 16, cryptography (Fernet) for secrets at rest.
   - Google Gemini API (google-genai) to write notes from the transcript text.
   - Sends results to BMI Brain by webhooks signed with HMAC-SHA256.
   - Holds each user's Zoom sign-in: OAuth code exchange and refresh (zoom.us/oauth/token), GET /v2/users/me, GET /v2/users/me/token?type=onbehalf&meeting_id={id}, POST zoom.us/oauth/revoke. Scopes: user:read:user, user:read:token. The refresh token is stored encrypted (Fernet / AES-128 with HMAC-SHA256); access tokens are short-lived and not stored.
3. Meeting bot - Attendee (open source, github.com/attendee-labs/attendee), self-hosted, unmodified.
   - Django 5.2 REST API, Celery 5.4 workers, Redis, PostgreSQL, SeaweedFS (S3-compatible private storage for call audio).
   - Zoom Meeting SDK for Linux (zoom-meeting-sdk) to join as a visible participant named "BMI Notetaker".
   - Asks the notetaker for the On Behalf Of token as it joins each Zoom call (signed request).

Zoom events: App deauthorized only (signed, checked with x-zm-signature). Disconnecting revokes the token at Zoom (POST /oauth/revoke). Zoom data is used only to join meetings on behalf of the BMI user who connected their Zoom, while they are in the meeting.

## Application development
1. SSDLC - No (answer Yes only with a written process to upload).
2. SAST/DAST - No (answer Yes only with tool reports to upload).
3. Third-party penetration testing - No.
4. Additional documents - upload the Privacy policy (https://bmi.rabtaai.com/privacy as PDF).

## Security
1. TLS 1.2 or above for all network traffic - Yes. Public endpoints (bmi.rabtaai.com, the notetaker) are HTTPS only via Traefik (minimum TLS 1.2); all calls to Zoom, Google and Microsoft are HTTPS. Traffic between our own containers stays on a private Docker network on the same server.
2. Verification token / x-zm-signature for Zoom webhooks - Yes: the only event used is App deauthorized, sent to https://<notetaker>/hooks/zoom/<app id>; every request is checked with x-zm-signature (HMAC-SHA256 of v0:{x-zm-request-timestamp}:{body} with the app's Secret Token, requests older than 5 minutes refused), and Zoom's endpoint.url_validation is answered.
3. Collect, store, log or retain Zoom user data, including OAuth tokens - Yes:
   - Zoom user ID and account ID (to know whose Zoom to use).
   - Refresh token, encrypted at rest in the meeting bot's database; deleted when the user disconnects.
   - For meetings the notetaker joins: audio, transcript, participant names and the written notes. Audio and transcript are deleted after 30 days; notes stay in BMI Brain as client history until BMI deletes them.
   - Tokens are never written to logs.

## How Zoom user data is protected at rest
- Zoom OAuth refresh tokens (and the Zoom app's client secret): encrypted field by field in the notetaker's PostgreSQL database with Fernet (AES-128-CBC + HMAC-SHA256). The key is a server setting (ENCRYPTION_KEY), not stored in the database. Zoom app keys passed to the meeting bot are encrypted the same way in its database (CREDENTIALS_ENCRYPTION_KEY). Access tokens are short-lived and never stored. Deleted when the user disconnects.
- Call audio: encrypted in object storage (SeaweedFS, -filer.encryptVolumeData) with AES-256-GCM and a separate key per chunk, kept apart from the data. Deleted after 30 days.
- Zoom user ID, transcripts and notes: in PostgreSQL databases that aren't reachable from the internet (private Docker network on one server), only by our services with their own credentials; staff see them only after signing in, limited by role. Transcripts are deleted after 30 days. Other secrets (app API keys, Gemini keys) are stored hashed or encrypted.
- Tokens and secrets are never written to logs.
