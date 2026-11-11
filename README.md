# Sajilo Nepal 🇳🇵

A free, daily-utility **Telegram bot** (Telegram Bot API) for Nepal and the Nepali diaspora.
One bot, two languages (English + Nepali), eight everyday answers — each reachable in two
taps or fewer.

| Feature | What you get |
| --- | --- |
| 🔮 Horoscope | Daily reading for all 12 signs (authored content, no scraping) |
| 📰 News | Top headlines from major Nepali outlets, in your language |
| 📅 Nepali Calendar | Today's Bikram Sambat date, festivals and public holidays |
| 💰 Gold & Silver | FENEGOSIDA daily hallmark gold and silver rates |
| 💵 Forex + Calculator | Nepal Rastra Bank rates + a remittance calculator (NPR) |
| ⛽ Fuel Prices | Nepali Patro's Kathmandu-area published fuel prices |
| 🥦 Vegetable Market | Kalimati essentials, leafy greens and day-on-day trends |
| 🌤️ Weather & AQI | Current weather, today's range and live air quality |

---

## How it works

The bot is a small FastAPI service that receives Telegram updates (webhook in production,
long-polling for local dev) and never scrapes a source while a user is waiting.

```
Telegram ──update──▶ /telegram/webhook ──▶ handler ──▶ reads cache ──▶ Reply ──▶ Bot API
   │                                          ▲
   └── (or getUpdates polling)                │
              background scheduler ───────────┘  (fetches sources, stores snapshots)
```

* **Cache-first.** A tap reads the newest *successful* snapshot from the database. The
  scheduler refreshes sources in the background on per-source intervals.
* **Two taps max.** Home is a persistent 3×3 reply keyboard; submenus use inline keyboards
  (e.g. the 12-sign zodiac grid). Every feature is also reachable by a typed command
  (`/horoscope leo`, `menu`, `rates`, `weather`, `भाषा`, …) in English or Nepali.
* **Graceful degradation.** A stale snapshot is still served with an "Updated" line; a
  dead source never crashes the bot. `/healthz` reports per-source freshness.

---

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

Copy-Item .env.example .env
# edit .env: set TELEGRAM_BOT_TOKEN, BOT_USERNAME and PUBLIC_BASE_URL.
# For local development set TELEGRAM_MODE=polling (no public URL needed).

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

For **webhook mode**, expose the app over HTTPS (e.g.
`cloudflared tunnel --url http://localhost:8000` or `ngrok http 8000`) and register the
webhook:

```powershell
.\.venv\Scripts\python.exe scripts/set_webhook.py
```

The webhook endpoint is `{PUBLIC_BASE_URL}/telegram/webhook`; Telegram echoes
`TELEGRAM_WEBHOOK_SECRET` back in the `X-Telegram-Bot-Api-Secret-Token` header.

Local SQLite is used by default, and tables are auto-created. For production, use the
included Docker Compose stack (app + PostgreSQL) and Alembic migrations:

```powershell
docker compose up -d --build
# For a database previously initialized by AUTO_CREATE_TABLES, baseline it once:
docker compose exec bot python -m alembic stamp 0001_initial
docker compose exec bot python -m alembic upgrade head
```

Skip the `stamp` command when Alembic already reports a current revision. On a fresh
database, run migrations before starting the application instead of stamping a baseline.

---

## Configuration

Everything is environment-driven (see `.env.example`). The important ones:

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Secret echoed by Telegram; blank accepts all requests (dev only) |
| `TELEGRAM_MODE` | `webhook` (default) or `polling` (local dev) |
| `BOT_USERNAME` | Bot username (no `@`), used for `t.me` share/deep links |
| `PUBLIC_BASE_URL` | Public HTTPS base URL; webhook is `{base}/telegram/webhook` |
| `DATABASE_URL` | `sqlite+aiosqlite:///…` (dev) or `postgresql+asyncpg://…` (prod) |
| `SCHEDULER_ENABLED` | Turn background refresh on/off |
| `REFRESH_*_HOUR_NPT`, `REFRESH_*_MINUTE_NPT` | Daily scheduled market refresh times in Nepal Time |
| `REFRESH_NEWS_HOURS` | News refresh cadence (default: every 2 hours) |
| `RATE_LIMIT_PER_MINUTE` | Per-user messages/minute |
| `GROUP_RATE_LIMIT_PER_MINUTE` | Per-group messages/minute (bot only answers commands/mentions) |
| `FEATURE_DAILY_DIGEST` | Send a 7:00 AM NPT briefing to active users; `/unsubscribe` opts out |
| `ANALYTICS_SALT` | Salt for the hashed user id in analytics |
| `ADMIN_TELEGRAM_ID` | Numeric Telegram id(s) allowed to use `/stats` (comma-separated list allowed) |
| `FEATURE_ADMIN_DAILY_SUMMARY` | DM the admin a stats summary at 21:00 NPT (needs `ADMIN_TELEGRAM_ID`) |
| `EVENTS_RETENTION_DAYS` | Delete analytics events older than this (default 180) |

Editable **data files** let you change content without code:

* `app/data/config/vegetables.json` — curated essentials and leafy greens
* `app/data/config/cities.json` — weather cities
* `app/data/config/news_feeds.json` — RSS sources per language
* `app/data/festivals_<BS year>.json` — festivals and public holidays
* `app/data/horoscope_seed/*.json` — authored horoscope readings

The default schedule refreshes vegetables at 5:30 AM, fuel at 6:00 AM, horoscope at
5:00 AM, gold/silver at 10:30 AM, and forex at 11:15 AM NPT. News refreshes every two
hours; weather refreshes every 30 minutes. The Nepali date/calendar is computed locally,
so it updates automatically and does not need a remote refresh. The morning briefing uses
the latest available headlines and source snapshots; NEPSE data is not included unless a
share-market source is configured. Fuel may be marked stale when Nepali Patro's price API is
unreachable.

---

## Project layout

```
app/
  main.py            FastAPI app: webhook/polling, dedupe, health, background processing
  config.py          Settings (pydantic-settings)
  db.py              Async engine/session
  bot/
    i18n.py          All strings (en + ne) and WMO/AQI text
    formatters.py    Central emoji-signal system + date/updated formatting + HTML escape
    context.py       Channel-agnostic BotContext (reply/send/track)
    processor.py     Dedupe, group gating, rate limits, context assembly, routing
    menus.py         Home keyboard, inline grids, share buttons
    actions.py       Compact (<=64-byte) callback_data codec
    labels.py        Reply-keyboard label -> action routing (both languages)
    textcmd.py       Typed-command -> action-id map (en + ne)
    router.py        Action-id / text dispatch
    handlers/        One module per feature
    state.py         Conversation state (10-min TTL)
  channels/
    base.py          Channel protocol + Reply/Btn model
    telegram/        Update parsing, renderer, Bot API client, commands, webhook
  data/
    models.py        ORM models
    cache.py         Snapshot cache (no scraping on tap)
    scheduler.py     APScheduler jobs
    digest.py        Opt-in morning digest
    sources/         One adapter per data source
    config/          Editable JSON data
  utils/             BS calendar, Nepali digits, share links, time helpers
migrations/          Alembic
scripts/             set_webhook, stats, import_horoscope
tests/               Unit + webhook end-to-end tests
```

---

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest            # tests
.\.venv\Scripts\python.exe -m ruff check .      # lint
.\.venv\Scripts\python.exe scripts/stats.py     # admin analytics report
```

Tests use a temporary SQLite database and a fake Telegram channel, so they never touch the
network.

---

## Notes and limitations

* **Kalimati** prices come from a Laravel/DataTables page that requires a CSRF dance; the
  adapter is best-effort and raises rather than publishing empty data.
* **FENEGOSIDA**'s public API does not expose Tejabi gold; the field is only shown if a
  future payload provides it.
* **Sharing** uses Telegram's `https://t.me/share/url` picker, prefilled with a compact
  summary and the bot's deep link; forwarding is a client action, not observable server-side.
* **No unsolicited messages.** The bot answers only inside Telegram's rules; the optional
  daily digest is sent **only** to users who ran `/subscribe`.
* **Horoscope** content is authored seed data, not scraped. Swap in a licensed feed by
  implementing the same adapter interface.
* Festival dates are curated approximations — verify before relying on them legally.

See `DECISIONS.md` for the reasoning behind each data source, and `PRIVACY.md` for what
we store (very little).
