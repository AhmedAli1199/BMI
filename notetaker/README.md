# Cybix Notetaker

A self-hosted service that sends a notetaker into **Google Meet** and **Microsoft Teams** calls,
collects the transcript (with each speaker's real name) and writes up the notes with Gemini.
Results go back to the app that asked by a signed webhook. It knows nothing about any one project,
so any app can use it with its own API key. BMI Brain is the first.

Zoom isn't supported yet: Zoom has to approve the app before a bot may join other people's calls.

## How it fits together

```
 Client app (e.g. BMI Brain)
   │ POST /v1/meetings  {meeting_url, join_at, external_id, metadata}
   ▼
 notetaker-api (FastAPI) ── Postgres ── notetaker-worker
   │  MeetingBot adapter                  │ writes up finished calls (Gemini)
   ▼                                      │ delivers webhooks (outbox, retries)
 Attendee (open source, unchanged)        ▼
   attendee-app · scheduler · worker×2    Client app  ← meeting.status_changed / meeting.completed / meeting.failed
   └─ headless Chrome joins the call, records, takes the meeting's captions
```

| Part | What it is |
|---|---|
| `notetaker/api/app.py` | The HTTP API, the bot webhook receiver, the transcription endpoint and the dashboard |
| `notetaker/service.py` | The core logic: schedule, react to bot updates, write up the notes |
| `notetaker/states.py` | The meeting state machine - only allowed moves, so a late webhook can't undo a finished call |
| `notetaker/bots/` | **Adapter**: `MeetingBot` interface; `AttendeeBot` today, `FakeBot` for tests and demos |
| `notetaker/transcribe/` | **Strategy**: the AI step; `GeminiAI` today, swappable for Whisper or another provider |
| `notetaker/outbox.py` | **Outbox**: webhooks are saved first, then delivered and retried with growing gaps |
| `notetaker/worker.py` | Background loop; several can run side by side (`SKIP LOCKED` on Postgres) |

### Meeting states

`scheduled → joining → waiting_room → recording → processing → completed`.
A call can also end as `not_admitted` (nobody let the bot in), `failed` or `cancelled`. Every move is kept in a timeline.

### Transcription modes (`TRANSCRIPTION_MODE`)

- `captions` (default): the bot reads the meeting's own live captions. Speaker names come from Meet or Teams. No extra cost.
- `gemini`: Attendee sends each speaker's audio to `/internal/transcribe`, and Gemini transcribes it. Use it when captions aren't good enough. The cost is about 10-15 cents per hour.

The notes are always written by Gemini as structured JSON: summary, key points, decisions, action items (who and when), money and dates mentioned, the next step and the client's interest.

## API

All client calls use `Authorization: Bearer <api key>`. The full reference is at `/docs`.

```
POST   /v1/meetings            {meeting_url, join_at?, title?, external_id?, bot_name?, metadata?}
GET    /v1/meetings            ?status=completed
GET    /v1/meetings/{id}       transcript, notes, timeline
DELETE /v1/meetings/{id}       stop / cancel the bot
GET    /health
```

- `external_id` makes scheduling safe to repeat. Sending the same calendar event twice gives back the first meeting instead of a second bot.
- `metadata` is returned in every webhook, so you can tie the result back to your own records.

### Webhooks to your app

```
POST <your webhook_url>
X-Notetaker-Event:     meeting.completed | meeting.failed | meeting.status_changed
X-Notetaker-Delivery:  <id - the same on retries; ignore ones you've seen>
X-Notetaker-Timestamp: <unix seconds>
X-Notetaker-Signature: sha256=<hex HMAC-SHA256 of "<timestamp>.<raw body>" using your webhook secret>

{"id": "...", "event": "meeting.completed", "data": {meeting with transcript and notes}}
```

Answer with any 2xx. Anything else is retried (10s, 20s, 40s ... up to an hour, 12 tries).

## Running it on Dokploy

1. Create a **Compose** service from this folder (repository + branch, compose path `notetaker/docker-compose.yml`).
2. Copy `.env.example` into the service's environment and fill in the secrets.
3. Add two domains: `notetaker-api` port 8080 (for example `notetaker.rabtaai.com`) and `attendee-app` port 8000 (for example `attendee.rabtaai.com`). Both need HTTPS: Attendee only sends webhooks to `https://` addresses.
4. Deploy. The first build of the Attendee image takes about 5-10 minutes.

**Memory:** the API, worker and database use about 1.5 GB together. Each `attendee-worker` can take up to 3 GB while it's in a call, and very little when idle. Two workers means two calls at once; keep `MAX_CONCURRENT_BOTS` equal to the number of workers.

### First-time set-up (about 5 minutes)

1. Open `https://attendee.rabtaai.com`, sign up, and confirm the account. Email is off, so the confirmation link is printed in the `attendee-app` logs.
2. In Attendee, create an API key and copy the webhook secret (Settings → Webhooks). Put them in `ATTENDEE_API_KEY` and `ATTENDEE_WEBHOOK_SECRET`, then redeploy.
3. Optional, but recommended for Google Meet: add a Google account for the bot in Attendee (signed-in bots). That avoids the "unverified" warning and gets into meetings that only allow signed-in users.
4. Create a client app:
   ```
   curl -X POST https://notetaker.rabtaai.com/admin/clients -H "X-Admin-Token: $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"BMI Brain","webhook_url":"https://bmi.rabtaai.com/api/notetaker/webhook","bot_name":"BMI Notetaker","chat_message":"Hi - I am taking notes for BMI. This call is recorded for notes only."}'
   ```
   Save the returned `api_key` and `webhook_secret`; the key isn't shown again.
5. Open `https://notetaker.rabtaai.com`, paste the API key, paste a meeting link and press **Send the notetaker**.

## Developing

```
pip install -r requirements.txt
BOT_PROVIDER=fake AI_PROVIDER=fake ADMIN_TOKEN=dev uvicorn notetaker.api.app:app --port 8080
python -m notetaker.worker        # in another terminal
python -m pytest -q tests
```

With `BOT_PROVIDER=fake`, `POST /hooks/fake {"bot_id": ..., "status": "processing"}` pretends a call has ended, so the whole flow can be shown without a real meeting.

## Moving it to its own repository

The folder is self-contained:

```
git subtree split -P notetaker -b notetaker-only
```

Then push that branch to a new repository.
