"""Prints a complete .env for the notetaker, with every secret generated. Usage:

    python3 deploy/generate_env.py notetaker.yourcompany.com

Paste the output into Dokploy → your compose service → Environment. Nothing is left to fill in: each app
adds its own Gemini key in the console.
"""
import base64
import os
import secrets
import sys

host = (sys.argv[1] if len(sys.argv) > 1 else "notetaker.example.com").removeprefix("https://").strip("/")
h = lambda n=32: secrets.token_hex(n)
fernet = base64.urlsafe_b64encode(os.urandom(32)).decode()
enc = base64.urlsafe_b64encode(os.urandom(32)).decode()
print(f"""# ---- Generated - keep them as they are ----
PUBLIC_URL=https://{host}
ADMIN_TOKEN={h(16)}
INTERNAL_TOKEN={h()}
ENCRYPTION_KEY={enc}
DJANGO_SECRET_KEY={h(40)}
CREDENTIALS_ENCRYPTION_KEY={fernet}
POSTGRES_PASSWORD={h(24)}
MINIO_USER=notetaker
MINIO_PASSWORD={h(24)}

# ---- Defaults you can change later ----
BOT_PROVIDER=attendee
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.6-flash
TRANSCRIPTION_MODE=captions
DEFAULT_BOT_NAME=Notetaker
MAX_CONCURRENT_BOTS=2
SITE_DOMAIN={host}
""")
