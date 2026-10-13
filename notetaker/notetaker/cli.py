"""python -m notetaker.cli create-client "BMI Brain" https://bmi.example.com/api/notetaker/webhook"""
from __future__ import annotations

import sys

from notetaker.clients import create_client
from notetaker.db import init_db, session_scope


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[0] != "create-client":
        print(__doc__)
        raise SystemExit(1)
    init_db()
    with session_scope() as db:
        c, key = create_client(db, argv[1], argv[2] if len(argv) > 2 else None)
        print(f"client id:      {c.id}\napi key:        {key}\nwebhook secret: {c.webhook_secret}\n(save the key now - it isn't shown again)")


if __name__ == "__main__":
    main(sys.argv[1:])
