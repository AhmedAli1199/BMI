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
   It prints a complete settings file with every secret generated, so there's nothing to fill in. Keep `ADMIN_TOKEN` handy:
   it's the console password. There's no Gemini key here, because each app adds its own in the console.
2. **Create the service in Dokploy.** Create Service → **Compose**, choose this repository and branch, compose path `./docker-compose.yml`.
   Paste the settings into **Environment**.
3. **Add one domain.** Under Domains, choose service `notetaker-api`, port `8080`, your host name, and HTTPS on.
   Point the name's DNS at the server first.
4. **Deploy.** The first build takes about 10 minutes, because it builds the bot's Chrome image.
   Then open `https://notetaker.yourcompany.com`, sign in with `ADMIN_TOKEN`, and check that every item on **Overview** has a tick.

That's all. The bot's own setup (its account, API key and webhook secret) happens by itself on every deploy, in the
`attendee-bootstrap` container. You never sign up anywhere or copy keys between services.

**Sharing between apps.** Every app uses this one service. Each has its own key, settings, calls and Gemini key, so
its AI costs go to its own Google project. The bot workers are shared, first come first served:
- Each booking holds a bot from its `join_at` to its `end_at` (an hour by default).
- A booking that would go over the overall limit, or the app's own limit (set in the console), is refused straight away
  with a plain reason. So nobody finds out at meeting time.
- The console's **Calls → Booked and running** shows who has the bots and when.
- **Apps** shows each app's calls, hours and AI tokens this month.

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

**Each app's Gemini key** is stored encrypted, with `ENCRYPTION_KEY`, and checked with Google when it's saved. It's used for
that app's notes, and for its transcripts in `gemini` mode. The server's own `GEMINI_API_KEY`, if one is still set, is never
used for any app.

**Transcription (`TRANSCRIPTION_MODE`):**
- `captions` (default): uses the meeting's own live captions. Free, and Meet or Teams provide the speaker names.
- `gemini`: Gemini transcribes each speaker's audio, at about 10–15 cents per hour.

---

## Good to know

- **Zoom** works once the Zoom app's keys are added (see "Zoom" below). Zoom only lets a notetaker in **on behalf of** a
  signed-in person who is in the call: it joins once they do (waiting up to 10 minutes), and the recording ends if they
  leave. Until Zoom has reviewed the app, it can only join meetings hosted by the Zoom account that made the app.
- **Meet's "may not be who they say" warning** shows because the bot joins as a guest. Giving it a signed-in Google Workspace
  account removes the warning; see Attendee's "signed-in bots" docs.
- **The bot's own admin page** isn't on a public address, and you don't need it. If you want it for debugging, add a domain
  for `attendee-app` (port 8000) and set `ATTENDEE_PUBLIC_URL`. Its login is shown in the console under Overview.
- **Moving from the first manual setup:** remove `ATTENDEE_API_KEY` and `ATTENDEE_WEBHOOK_SECRET` from Environment and
  redeploy. The bootstrap takes over. If those values are set, they win.
- **Upgrading to keys for each app:** add `ENCRYPTION_KEY` (generate one with `generate_env.py`). Then in the console,
  Apps → Edit each app and paste its Gemini key. Until you do, that app's calls come back as transcripts only.

## Zoom

Zoom keys belong to **each app**, not the server: whoever owns a project makes their own Zoom app and pastes its keys
into that app in the console. Nothing is set in Environment.

1. In the Zoom App Marketplace (signed in as the account that will own the app): **Develop → Build App → General App**,
   **User-managed**. Redirect URL and OAuth allow list: the app's own callback (BMI Brain:
   `https://<its address>/api/zoom/callback`).
2. **Features → Embed**: switch on **Meeting SDK**, and **"Are you developing a meeting bot or AI notetaker use case?"**.
   This is what the notetaker is, and it means Zoom's "on behalf of" sign-in rather than a shared account.
3. **Scopes**: `user:read:user` ("View a user") and `user:read:token` ("View a user's token").
4. **Features → Access**: copy the **Secret Token**, switch on **Event Subscription**, add the event **App deauthorized**
   and, as the endpoint, the app's event address from its card in the console (`https://<notetaker>/hooks/zoom/<app id>`).
   Zoom checks the address when you save; the notetaker answers that check.
5. In the console: **Apps → Edit** the app, paste its **Client ID**, **Client Secret** and **Secret Token**, and **Save**. Use the Development
   keys until Zoom approves the app, then the Production ones. Within a minute the app's card says **Zoom: on**, or why
   Zoom refused the keys.
6. Each person connects their Zoom from their app. The app sends them to Zoom's sign-in
   (`https://zoom.us/oauth/authorize?response_type=code&client_id=<GET /v1/zoom's client_id>&redirect_uri=<its callback>`),
   then hands the code to the notetaker:

```
GET    /v1/zoom                              {"available": true, "client_id": "..."} for this app
POST   /v1/zoom/connections                  {"authorization_code", "redirect_uri", "external_user"} -> {"zoom_user_id", "state"}
GET    /v1/zoom/connections/{zoom_user_id}   is it still connected?
DELETE /v1/zoom/connections/{zoom_user_id}   disconnect
POST   /v1/meetings                          {"meeting_url": "<zoom link>", "zoom_user_id": "...", ...}
```

**Who holds the Zoom sign-ins.** The notetaker does (`notetaker/zoomapi.py`): it swaps the code for tokens with the app's
own Zoom keys, keeps the refresh token encrypted (Zoom gives a new one each refresh), and hands the meeting bot a fresh
"on behalf of" token for each Zoom call when it asks (`POST /hooks/zoom-tokens`, signed by the bot). Disconnecting
revokes the token at Zoom. If someone removes the app in Zoom, Zoom's `app_deauthorized` event (checked with
`x-zm-signature`) deletes their sign-in, and the app gets a `zoom.disconnected` webhook.

**How it works inside.** The meeting bot (Attendee) holds one set of Zoom keys per "project". So an app with Zoom keys
gets a project of its own there, and all of that app's bots run in it. The `attendee-sync` container
(`deploy/attendee_sync.py`, every 30 seconds) asks the notetaker which apps need one (`/internal/bot-projects`). It makes
or updates the project, its key, its webhook secret and its Zoom app, checking new keys with Zoom, and reports back. Apps
without Zoom keys keep using the main project. The console's Overview shows a **Zoom** check once any app has Zoom keys.

## Developing

```
pip install -r requirements.txt
BOT_PROVIDER=fake AI_PROVIDER=fake ADMIN_TOKEN=dev uvicorn notetaker.api.app:app --port 8080
python -m notetaker.worker               # in another terminal
python -m pytest -q tests
```

With `BOT_PROVIDER=fake`, posting `{"bot_id": ..., "status": "processing"}` to `/hooks/fake` pretends a call has ended.
That lets you try the whole flow without a real meeting.
