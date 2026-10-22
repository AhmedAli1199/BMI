# Release notes for the Zoom reviewer (paste into "Release notes")

BMI Notetaker - first submission.

What it is: BMI Publishing's internal notetaker for its own sales staff, built into BMI Brain (BMI's CRM, https://bmi.rabtaai.com). A BMI salesperson connects their Zoom once; the notetaker then joins their Zoom meetings as a visible participant named "BMI Notetaker", on their behalf (On Behalf Of token), only while they are in the meeting, and writes up the notes (summary, actions, transcript) into BMI Brain. Only BMI staff can use it; the app is unlisted.

Test plan (step by step, about 15 minutes): https://bmi.rabtaai.com/zoom/test-plan
Test account: one role only (BMI salesperson) - login in "Test account and credentials". It sees test clients only.

Scopes and why:
- user:read:user - read the user's Zoom ID and account ID once, when they connect (GET /v2/users/me).
- user:read:token - get the On Behalf Of token for each meeting just before the notetaker joins (GET /v2/users/me/token?type=onbehalf&meeting_id=...). Required for notetakers joining meetings outside the developer account.

How to add: from our site (https://bmi.rabtaai.com/zoom, "Connect Zoom"); signed-out visitors are asked to sign in to BMI Brain first. Redirect URL: https://bmi.rabtaai.com/api/zoom/callback (signed state, 15 minutes).

How to remove: Disconnect in BMI Brain (revokes the token with POST https://zoom.us/oauth/revoke, then deletes it), or Manage > Added Apps > Remove in Zoom - we subscribe to "App deauthorized", verify x-zm-signature with the Secret Token, delete the user's sign-in and show them as disconnected. Documentation: https://bmi.rabtaai.com/support (#connect-zoom, #remove-zoom).

Data: refresh tokens encrypted at rest (Fernet), access tokens never stored; call audio encrypted at rest (AES-256-GCM) and deleted after 30 days with the transcript. Privacy: https://bmi.rabtaai.com/privacy. Terms: https://bmi.rabtaai.com/terms. Contact during review: ahmed@cybix.ai.

Note for testing: the notetaker can only enter once the connected user has joined the meeting, and it leaves when they leave (Zoom's OBF rule). Admit "BMI Notetaker" from the waiting room if there is one.
