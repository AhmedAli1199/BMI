# Cybix Notetaker

A self-hosted notetaker for any of our apps. Your app sends a Google Meet or Teams link; a bot joins the call, records it,
and your app gets back the transcript (with each speaker's name) and notes written by Gemini: summary, decisions,
who's doing what, money and dates mentioned, and the next step.

There's **one Notetaker for the whole company**. Each project connects to it with its own key. Nobody deploys it twice.

- **Connecting an app:** open `https://<notetaker address>/guide`. It takes about 10 minutes: create the app in the console,
  set 3 settings, add one request and one webhook route.
- **Running it:** the console at `https://<notetaker address>/` checks that everything works and lets you manage apps, keys,
  webhook deliveries and test calls.

---

## Deploy it (once, about 15 minutes)

1. **Make the settings.** In a copy of this repository, run:
   ```
   python3 deploy/generate_env.py notetaker.yourcompany.com
   ```
   It prints a complete settings file with every secret generated. Fill in `GEMINI_API_KEY`; use a key on a project with
   billing turned on, so call content isn't used to train Google's models. Keep `ADMIN_TOKEN` handy: it's the console password.
2. **Create the service in Dokploy.** Create Service → **Compose**, choose this repository and branch, compose path `./docker-compose.yml`.
   Paste the settings into **Environment**.
3. **Add one domain.** Under Domains, choose service `notetaker-api`, port `8080`, your host name, and HTTPS on.
   Point the name's DNS at the server first.
4. **Deploy.** The first build takes about 10 minutes, because it builds the bot's Chrome image.
   Then open `https://notetaker.yourcompany.com`, sign in with `ADMIN_TOKEN`, and check that every item on **Overview** has a tick.

That's all. The bot's own setup (its account, API key and webhook secret) happens by itself on every deploy, in the
`attendee-bootstrap` container. You never sign up anywhere or copy keys between services.

**Server size.** When no calls are running, the stack uses about 2 GB of memory and almost no CPU. Each call in progress
uses roughly 1–2 CPU cores and up to 3 GB while it lasts. Two calls can run at once by default; to allow more, raise
`MAX_CONCURRENT_BOTS` and add matching `attendee-worker-N` services.

---

## How it fits together

```
 Your app ──POST /v1/meetings──►  notetaker-api ── Postgres ── notetaker-worker
    ▲                                  │ MeetingBot adapter          │ writes the notes (Gemini)
    │                                  ▼                             │ delivers webhooks (retries)
    └── signed webhook ◄────────  Attendee (open source, unchanged)  ┘
                                  bootstrap · app · scheduler · worker×2 · storage
                                  └─ a hidden Chrome window joins the call and records it
```

| Part | What it does |
|---|---|
| `notetaker/api/app.py` | The API for apps (`/v1/...`), the bot's webhooks, the transcription endpoint, and the console and guide pages |
| `notetaker/api/console.py` | The console's API: sign-in, set-up checks, apps, keys, deliveries, test calls |
| `notetaker/service.py` | Booking a bot, following its updates, writing the notes, the once-a-minute safety check |
| `notetaker/states.py` | The meeting's steps; only forward moves are allowed, so a late update can't undo a finished call |
| `notetaker/bots/` | **Adapter**: `AttendeeBot` today; another bot service can plug in without changes elsewhere |
| `notetaker/transcribe/` | **Strategy**: Gemini today; could be Whisper or another provider |
| `notetaker/styles.py` | Notes styles: general, sales call, interview, stand-up, support call |
| `notetaker/outbox.py` | **Outbox**: webhooks are saved first, then delivered and retried until the app confirms |
| `notetaker/engine.py` | Reads the bot credentials that the bootstrap writes |
| `deploy/attendee_bootstrap.py` | Sets the bot up by itself on every deploy |

**Transcription (`TRANSCRIPTION_MODE`):**
- `captions` (default): uses the meeting's own live captions. Free, and Meet or Teams provide the speaker names.
- `gemini`: Gemini transcribes each speaker's audio, at about 10–15 cents per hour.

---

## Good to know

- **Zoom** isn't supported yet; Zoom has to approve the app first.
- **Meet's "may not be who they say" warning** shows because the bot joins as a guest. Giving it a signed-in Google Workspace
  account removes the warning; see Attendee's "signed-in bots" docs.
- **The bot's own admin page** isn't on a public address, and you don't need it. If you want it for debugging, add a domain
  for `attendee-app` (port 8000) and set `ATTENDEE_PUBLIC_URL`. Its login is shown in the console under Overview.
- **Moving from the first manual setup:** remove `ATTENDEE_API_KEY` and `ATTENDEE_WEBHOOK_SECRET` from Environment and
  redeploy. The bootstrap takes over. If those values are set, they win.

## Developing

```
pip install -r requirements.txt
BOT_PROVIDER=fake AI_PROVIDER=fake ADMIN_TOKEN=dev uvicorn notetaker.api.app:app --port 8080
python -m notetaker.worker               # in another terminal
python -m pytest -q tests
```

With `BOT_PROVIDER=fake`, posting `{"bot_id": ..., "status": "processing"}` to `/hooks/fake` pretends a call has ended.
That lets you try the whole flow without a real meeting.
