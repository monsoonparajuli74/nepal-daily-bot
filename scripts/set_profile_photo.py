"""Upload the bundled Nepal-themed avatar as the bot's profile photo.

Run once (or whenever the artwork changes)::

    .venv\\Scripts\\python.exe scripts\\set_profile_photo.py

Uses plain httpx so it does not depend on the bot process or the aiogram session.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
AVATAR = ROOT / "app" / "assets" / "avatar.png"


def _token() -> str:
    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set — add it to .env first.")
    return token


def main() -> int:
    if not AVATAR.exists():
        raise SystemExit(f"missing artwork: {AVATAR} (run scripts/make_art.py)")
    api = f"https://api.telegram.org/bot{_token()}"
    with httpx.Client(timeout=30) as client:
        me = client.get(f"{api}/getMe").json()
        if not me.get("ok"):
            raise SystemExit(f"getMe failed: {me}")
        with AVATAR.open("rb") as handle:
            response = client.post(
                f"{api}/setMyProfilePhoto",
                data={"photo": json.dumps({"type": "static", "photo": "attach://avatar"})},
                files={"avatar": (AVATAR.name, handle, "image/png")},
            )
        payload = response.json()
        if not payload.get("ok"):
            raise SystemExit(f"setMyProfilePhoto failed: {payload}")
        user = me["result"]
        print(f"Profile photo updated for @{user.get('username')} ({user.get('first_name')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
