# Design decisions

Short records of the choices that shaped the bot, and the reasoning behind them.

## Architecture

### Cache-first, never scrape on a tap
Telegram expects a prompt webhook response, and third-party sites (Kalimati, NOC) are slow,
fragile and rate-limited. Every source is fetched by an APScheduler job into a `snapshots`
row; handlers only ever read the newest **successful** snapshot. The "Updated" line shows
`checked_at`, so a user can tell how fresh the data is without a network call.

### Channel abstraction
Handlers never build platform payloads. They format HTML text plus a channel-agnostic `Reply`
(text + optional inline buttons + optional persistent reply keyboard) and call `ctx.reply`.
The `Channel` protocol (`app/channels/base.py`) owns parsing inbound events, verifying secrets
and rendering/sending. Only `app/channels/telegram/` knows the Bot API.

### aiogram as the client, httpx as the transport
We use aiogram 3's `Bot` and `types` for the Bot API method/type layer, but inject a custom
`HttpxSession` (`app/channels/telegram/session.py`) so every request still goes through a
single `httpx.AsyncClient`. This keeps aiogram's ergonomics **and** lets the whole suite be
mocked with `respx` (aiogram's default aiohttp session would not be). The AI client is a thin
adapter; the renderer, not aiogram, owns all Telegram limits.

### Telegram limits drive the UI
`app/channels/telegram/renderer.py` is the single place that enforces Telegram's limits:
`callback_data` ≤ **64 bytes** (not characters), text ≤ 4096 characters after entity parsing
(split on paragraph boundaries), ≤ 8 inline buttons per row and ≤ 100 per message. Titles are
clipped, extra buttons dropped with a warning, and edit failures fall back to a fresh
`sendMessage` (except "message is not modified", which is treated as success).

### Compact, namespaced action ids
`callback_data` is a hard 64-byte budget, so ids are short and namespaced
(`nav:home`, `hs:s:leo`, `fx:cc:AED`, `fx:ca:2500`). `app/bot/actions.py` is the single source
of truth for building/decoding them, and a test asserts every id fits the budget.

### Snapshot history, not just "latest"
We keep up to `MAX_SNAPSHOTS_PER_SOURCE` (10) rows per source. Comparing "today vs the
previous successful snapshot" powers the forex, fuel, metals and vegetable trend signals.
When payloads are byte-identical, we refresh `checked_at` on the existing row instead of
inserting a duplicate, so trends reflect real changes not noise.

### One adapter per source, swapped via a registry
Each source implements the same `fetch(etag, last_modified) -> Snapshot` interface and is
registered in `app/data/sources/__init__.py`. Adding or replacing a source is a local change;
nothing in the handlers or scheduler needs to move.

### Conditional requests + failure snapshots
Adapters pass the last ETag / Last-Modified header (stored with the snapshot) so a supportive
server short-circuits with `304`. On failure we write an `ok=False` snapshot so `/healthz` and
logs show the outage, while handlers keep serving the last good data.

## Data sources

### Forex — Nepal Rastra Bank JSON API
`https://www.nrb.org.np/api/forex/v1/rates` returns a clean JSON payload. Units matter: INR,
JPY and KRW are quoted per 10/100, so the quoted `unit` is stored per currency and used by
both the rate list and the calculator. **Buy** rate is used in the calculator
(`USE_BUY_RATE = True`), matching the product spec.

### Metals — FENEGOSIDA JSON API
`https://api.fenegosida.org/api/website/v1/Dashboard/today` returns four rows keyed by a
Devanagari `rateType`. We classify by script ("सुन" = gold, "चाँदी" = silver; "१० ग्राम" = per
10g, otherwise per tola) rather than by position, so ordering changes don't break us.
**Limitation:** the API does not expose Tejabi gold; that row is only rendered if a future
payload includes it.

### Fuel — Nepali Patro petrol-price page
`https://nepalipatro.com.np/petrol-price` loads its published rates from
`https://api.nepalipatro.com.np/api/noc/public/prices?lang=en`. The adapter uses only this
Nepali Patro endpoint, selects the region containing Kathmandu, and requires a valid update
date and all four supported products (petrol, diesel, kerosene, LP Gas). If the endpoint is
unavailable or its response changes, the adapter raises `SourceError`; it does not substitute
bundled or NOC-scraped prices.

### Vegetables — Kalimati market
`https://kalimatimarket.gov.np/price` is a Laravel + DataTables page: the table body is
populated after a dated POST carrying a CSRF `_token`, with session cookies. The adapter does
GET → extract token → POST with cookies, and falls back to parsing the bare page. If no rows
are found it raises `SourceError`. **This is the most fragile source** and is documented as
best-effort. Curated `essentials` and `greens` lists live in `config/vegetables.json` and are
matched by inclusive keywords against the scraped names.

### Weather & AQI — Open-Meteo
Free, keyless, and reliable. One snapshot holds every configured city (weather + US AQI), so a
tap never hits the network. Descriptions use the WMO code table in `i18n.py`; AQI uses
standard US EPA bands via `formatters.aqi_band`.

### News — RSS
Headlines, source name and link only — never article bodies (publisher copyright). Feeds are
configured per language in `config/news_feeds.json`; one dead feed does not kill the list.
Headlines are rendered as inline URL buttons (tap to open), so no numbered-input dance.

### Horoscope — authored seed content
No Nepali horoscope site offers a licensed feed, and scraping one would be a copyright
problem. We ship authored, neutral readings in `horoscope_seed/default.json` (with optional
date-specific files). Readings are also persisted per sign/date so a cold cache still answers.
Swapping in a licensed feed means writing one adapter against the same interface.

### Bikram Sambat calendar — table + anchor, no scraping
The BS calendar has no formula. We ship an explicit month-length table for BS 2000–2100
anchored at **BS 2000-01-01 = AD 1943-04-14**, verified against known dates (e.g.
BS 2081-01-01 = AD 2024-04-13).

## Bot UX

### Persistent home keyboard + inline flow keyboards
Telegram allows a real persistent 3×3 reply keyboard, so the home grid maps one-to-one to the
nine features/settings and is always available. Sub-screens use inline keyboards with a
`⬅️ Back` button where a parent exists (the 12-sign zodiac grid, the currency picker, the
weather city grid). Because the home keyboard is always visible, result screens omit a "menu"
button. Labels are routed by `app/bot/labels.py`, which accepts **both** languages at once
(emoji/punctuation-insensitive), so a Nepali-mode user can still tap an English-style label.

### Namespaced action-id routing + typed/slash commands
Every inline button carries a namespaced action id routed by `router.py` (exact + prefix
routes). Free text covers the keyboard labels, typed words ("menu", "rates", "stop", both
scripts), and `/` commands optionally with an argument (`/horoscope leo`, `/weather pokhara`).

### Central emoji-signal system
All colour/emoji meaning lives in `formatters.py` so the convention can't drift:
* Consumer prices (fuel, vegetables, LPG): cheaper = 🟢, costlier = 🔴, flat = ➖.
* Market value (forex): up = 🟢, down = 🔴.
* Metals: 📈 / 📉 / ➖ (colour would imply a good/bad side for buyer vs seller).
* AQI: standard US bands.

Dynamic third-party text (news titles, horoscope readings) is HTML-escaped before it is placed
in a `parse_mode=HTML` message (`formatters.esc`).

### Devanagari digits for the calendar only
Prices, rates and amounts stay in Latin digits (easiest to scan and match statements). The
Nepali calendar date is rendered in Devanagari when the user's language is Nepali. Number input
accepts both scripts and both separators via `utils/nepali_digits.py`.

### Sharing
Sharing uses Telegram's picker link `https://t.me/share/url?url=…&text=…`, prefilled with a
compact summary plus the bot's deep link (`https://t.me/<BOT_USERNAME>`). **Limitation:**
forwarding is client-side, so share taps aren't observable server-side; rendering the
shareable card is the proxy metric.

### Groups are answer-only
In group and supergroup chats the bot replies only to `/` commands and explicit
`@bot_username` mentions, and applies a stricter per-group rate limit. Plain chatter is
ignored.

### Opt-out and data deletion
`/stop` marks the user inactive and removes the keyboard; any later message reactivates them.
`/deletedata` erases the user row, conversation state and that user's analytics events. The
optional daily digest is strict opt-in via `/subscribe` (and `/unsubscribe`).

## Operations & reliability

### Dedupe on inbound `update_id`
Telegram retries webhook deliveries and polling can replay updates. We keep an in-memory
high-water mark plus a short recent-id set, and persist each processed `update_id` in
`telegram_updates` (24-hour TTL) so a restart cannot replay old updates.

### Rate limiting
A simple in-memory sliding window (default 20/min per user, 6/min per group) protects the
process from a chatty client. It is deliberately per-process; multi-worker deployments would
move this to a shared store.

### Per-chat send ordering
Outbound sends go through a tiny per-chat queue (`app/channels/telegram/client.py`) so a
multi-part reply arrives in order while different chats are handled concurrently. A `403`
means the user blocked the bot, so we deactivate them.

### Retention
Inactive users are purged after `USER_DATA_RETENTION_DAYS` (default 30); conversation state
expires after 10 minutes; update records after 24 hours. A nightly job does the cleanup.

### Viber → WhatsApp → Telegram
The bot was first specified for Viber, then WhatsApp Cloud API, and now Telegram. All product
behaviour, data sources, caching and i18n are unchanged. Channel-specific code (Viber, then
WhatsApp) was deleted; the bot engine depends only on `app/channels/base.py`. Because Telegram
identifies users by a numeric id rather than a phone number, `tg_user_id` is far less sensitive
than the old `wa_id`; it is still never logged, analytics store only a salted hash, and Alembic
revision `0001_initial` creates a clean schema (`tg_user_id`, `is_active`, digest fields,
`telegram_updates`).

### Webhook secret
Inbound POSTs are verified with `X-Telegram-Bot-Api-Secret-Token`: constant-time compared to
`TELEGRAM_WEBHOOK_SECRET`. An empty secret accepts every request, which is intended **only**
for local development. Production must set a secret.

### Testing
Tests use a temporary SQLite database and a fake Telegram channel (parsing/verification from
the real channel, delivery stubbed), so the suite runs offline and covers parsers, the BS
calendar, number formatting, the renderer/action-id limits, label routing, the cache, webhook
secret checks and full update flows (text, slash commands, button taps, unsupported media,
group gating, dedupe, opt-out, data deletion).
