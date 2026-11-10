# MODIFICATION PROMPT: Migrate "Everyday Nepal" to Telegram

**Context:** The project was specified as a Viber bot (original spec), then re-targeted to WhatsApp (migration prompt). Both channels cost too much, so the bot is now moving to **Telegram, whose Bot API is free**. Everything about the product (features, data sources, caching, i18n, tone) stays the same. **Only the messaging channel and the UI patterns change.**

How to apply this document:
- If Viber or WhatsApp code exists: refactor it as described below and **delete all Viber and WhatsApp code, config, docs and tests** when done.
- If the WhatsApp migration was already applied, the channel-agnostic `Reply` model and `Channel` protocol exist. Extend them (see §3). If not, create them as described.
- If nothing is built yet: apply this on top of the original spec, reading "Viber" as "Telegram".
- **Where this document conflicts with the original spec or the WhatsApp prompt, this document wins.** Ignore all WhatsApp-specific rules (3-button limit, 1024-char bodies, 24-hour window, templates, phone-number IDs, Meta compliance).

Work in the phases at the end. Record assumptions in `DECISIONS.md`. Do not stop to ask unless truly blocked.

---

## 1. What stays the same

- Product: horoscope, news, Nepali calendar, gold and silver, forex + remittance calculator, fuel, vegetables, weather and AQI, EN/NE language toggle, bilingual labels.
- Stack: Python 3.12, FastAPI, SQLAlchemy/Alembic, APScheduler, structlog, pytest/respx, Docker.
- The whole data layer: source adapters, snapshot cache, scheduler, staleness warnings, fixture-based parser tests, offline BS calendar, curated veg list, horoscope sourcing rules (pluggable, no scraping of sites that forbid it).
- The colour/emoji signal system, money rules (`Decimal`, Nepali digit grouping), Nepali-digit input parsing, and the principle **read from cache, never scrape on a user tap**. Every reply shows "Updated: <time NPT>".
- The original "two taps or fewer" rule and the 3x3 home grid, which Telegram can finally do properly (see §5).

## 2. What changes: platform differences

| Topic | Telegram Bot API |
|---|---|
| Cost | **Free.** Only hosting costs. No per-message fees, no 24-hour window, no templates |
| Home grid | **Persistent reply keyboard** (`ReplyKeyboardMarkup`, `is_persistent: true`, `resize_keyboard: true`), a true 3x3 grid under the chat |
| Sub-menus | **Inline keyboards** (`InlineKeyboardMarkup`) attached to messages; up to 8 buttons per row, 100 total |
| Button taps | Reply-keyboard taps arrive as ordinary **text messages** equal to the button label. Inline taps arrive as `callback_query` |
| `callback_data` | **1-64 BYTES** (not characters). Action IDs must be short (see §3.3) |
| Message length | Text max **4096** chars (after entity parsing) |
| Formatting | Use `parse_mode="HTML"` (`<b>`, `<i>`, `<code>`, `<a href>`). **HTML-escape all dynamic data** (`&`, `<`, `>`). Don't use MarkdownV2 (painful escaping) |
| Welcome | `/start` command (optionally with a deep-link payload), so a real welcome message exists again |
| User ID | Numeric Telegram user id (= chat id in private chats). **No phone number**, which is much less PII than WhatsApp |
| Webhook auth | `setWebhook` with a `secret_token`; Telegram sends it back in header `X-Telegram-Bot-Api-Secret-Token` |
| Dev mode | **Long polling** (`getUpdates`) works without a public URL or HTTPS |
| Rate limits | About 1 message/sec per chat (short bursts tolerated), about 30 messages/sec across all chats, 20/min per group |
| Blocked users | Sending to a user who blocked the bot returns **403**; also arrives as a `my_chat_member` update |

## 3. Architecture changes

### 3.1 Library choice
Use **aiogram 3.x** (async, well maintained) **as the API client and type layer only**: its `Bot` methods and `types`. Keep routing in our own `bot/router.py` through the channel-agnostic model below, so handlers never import aiogram. Use FastAPI for the webhook endpoint (feed `Update` objects into our pipeline) and aiogram's polling loop only in `TELEGRAM_MODE=polling`.

### 3.2 Channel-agnostic reply model (extend or create)

```python
@dataclass
class Btn:        text: str; action: str | None = None; url: str | None = None   # exactly one of action/url
@dataclass
class Reply:
    text: str                                   # HTML, <= 4096 after splitting
    inline: list[list[Btn]] | None = None       # rows of inline buttons
    reply_keyboard: list[list[str]] | None = None   # persistent home keyboard labels
    remove_keyboard: bool = False
    edit_message: bool = False                  # try editMessageText for in-place navigation
    preview: bool = False                       # link previews OFF by default
```

The Telegram renderer converts a `Reply` to API calls and **enforces limits**: callback_data ≤ 64 bytes, text split on paragraph boundaries under 4096, rows ≤ 8 buttons. Handlers return `Reply` objects only.

### 3.3 Short action IDs (64-byte budget)
Replace the long namespaced IDs with compact ones and a single codec in `bot/actions.py` (encode/decode, with a test that every ID ≤ 64 bytes):
`nav:home`, `lang:t`, `hs:m` (horoscope menu), `hs:s:leo`, `hs:save:leo`, `fx:r`, `fx:c`, `fx:cc:AED`, `fx:ca:2500`, `fx:cx` (type another), `fx:again`, `vg:m`, `vg:e`, `vg:g`, `vg:t`, `wx:m`, `wx:c:ktm`, `nw:l`, `cal:t`, `mt:t`, `fu:t`, `share:fx`, etc. Unknown or stale callbacks (old messages) must degrade to the home screen, never crash.

### 3.4 Layout changes
```
app/
  channels/
    base.py               # Channel protocol
    telegram/
      client.py           # aiogram Bot wrapper, send with retry/backoff, split, edit-or-send
      webhook.py          # POST /telegram/webhook (secret header check), polling runner
      renderer.py         # Reply -> API calls (+ limit enforcement)
      commands.py         # setMyCommands / descriptions at startup
  bot/                    # unchanged, handlers return Reply
scripts/
  set_webhook.py          # setWebhook with secret_token + allowed_updates
```
Delete `app/viber/` and any `app/channels/whatsapp/`.

## 4. Telegram integration requirements

- **Webhook mode (production):** `POST /telegram/webhook`. Check `X-Telegram-Bot-Api-Secret-Token` against `TELEGRAM_WEBHOOK_SECRET` (403 on mismatch). Return **200 immediately** and process in a background task. `scripts/set_webhook.py` calls `setWebhook` with `url`, `secret_token`, `allowed_updates=["message","callback_query","my_chat_member"]`, `drop_pending_updates=true`, and `max_connections` configurable. HTTPS on port 443 (or 80/88/8443).
- **Polling mode (dev):** `TELEGRAM_MODE=polling` runs `getUpdates` in-process with no public URL. `TELEGRAM_MODE=webhook` is the prod default. The same pipeline handles both.
- **Dedupe:** by `update_id` (store the highest processed id plus a short recent-ids set) because retries happen on slow or failed responses.
- **Update types handled:**
  - `message` with text, commands (`/start`, `/menu`, `/language`, `/help`, `/stop`, `/deletedata`, plus the module commands in §7) and reply-keyboard label text
  - `callback_query` (always call `answerCallbackQuery` first, even on error, to clear the spinner)
  - `my_chat_member` (status `kicked`/`left` -> mark user inactive; `member` -> reactivate)
  - Everything else (photos, stickers, voice, edited messages…) gets one gentle reply "Tap a button or send /menu" at most once per minute per user.
- **Reply-keyboard label routing:** a persistent keyboard sends its label as plain text. Build a normalised lookup (`strip` + case-fold + emoji-insensitive, **both languages always accepted**) mapping every home label to its action in `bot/labels.py`. Unit-test every EN and NE label round-trips. Unrecognised text outside an input state shows a short hint and re-sends the home keyboard.
- **Edit in place:** for in-flow navigation (horoscope sign pick, currency pick, veg filters, city pick, "Back"), use `editMessageText` on the callback's message so the chat stays clean. Fall back to sending a new message when edit fails (message too old/deleted); treat "message is not modified" as success.
- **Sending:** disable link previews by default (`link_preview_options={"is_disabled": true}`) to save data; send multi-part replies sequentially and in order with a small delay (respect ~1 msg/sec/chat); handle `429` by sleeping `retry_after`; on `403 bot was blocked` mark the user inactive and stop.
- **Startup tasks (idempotent):** `setMyCommands` (English default plus `language_code="ne"` localized descriptions), `setMyDescription` / `setMyShortDescription` (EN + NE), and set the chat menu button to commands.
- **BotFather steps** to document in the README: `/newbot`, set username, name, about, description, bot picture, and a `/setcommands` fallback.

## 5. UX redesign (screen by screen)

Telegram supports the **original 3x3 grid and 12-sign grid again**, so most of the original spec's layouts return.

### Home: persistent reply keyboard (3x3)
```
| 🔮 Daily Horoscope | 📰 Latest News   | 📅 Nepali Calendar |
| 💰 Gold & Silver   | 💵 Forex Rates   | ⛽ Fuel Prices     |
| 🥦 Vegetable Market| 🌤️ Weather & AQI | 🌐 Language / भाषा |
```
- `is_persistent: true`, `resize_keyboard: true`, `input_field_placeholder: "Choose an option / विकल्प छान्नुहोस्"`. In Nepali mode use the Nepali labels (दैनिक राशिफल, ताजा समाचार, नेपाली पात्रो, सुन तथा चाँदी, विदेशी मुद्रा, इन्धन मूल्य, तरकारी बजार, मौसम र वायु गुणस्तर, भाषा) and re-send the keyboard whenever the language changes.
- `/start` sends a 2-line welcome plus this keyboard (if the payload is a referral, e.g. `ref_xxx`, record the source in analytics only). `/menu` re-sends it any time.

### 🔮 Horoscope
- Inline **4x3 zodiac grid** with bilingual labels (`🐏 Aries / मेष` …) and `⬅️ Back`. If the user has a saved default sign, skip the grid and show the reading, with a `🔄 Change sign` button.
- Reading message buttons: `📌 Save as default` · `📤 Share` · `⬅️ Back`. (If already default, replace Save with `🔄 Change sign`.) Keep the "For entertainment purposes" footer.

### 💵 Forex + 🧮 Calculator
- Rates message (HTML, `<b>` headers, `<code>` for aligned numbers): buttons `🧮 Calculator` · `📤 Share`.
- Currency picker: inline grid USD, AED, SAR, QAR, MYR (+ `More…` for GBP, EUR, AUD, KRW, JPY, INR), and `⬅️ Back`.
- Amount step: inline quick amounts (500 · 1,000 · 2,500 · 5,000 · 10,000) and `✍️ Type another amount`. A quick amount shows the result with zero typing. "Type another" sets state `awaiting_amount` (10-minute TTL); the user types digits (Latin or Devanagari, commas allowed). Any `/command` or home-keyboard label cancels the state.
- Result: `🔄 Convert another` · `📤 Share`. Keep the "NRB official rate, real remittance rates and fees differ" note.

### 🥦 Vegetable Market
- Inline filters: `🍅 Daily Essentials` · `🥬 Leafy Greens` · `📈 Price Trends`. Result buttons: `⬅️ Back` · `📤 Share`.

### 🌤️ Weather & AQI
- Inline city grid (Kathmandu, Pokhara, Chitwan, Biratnagar, Janakpur, Birgunj, Butwal, Nepalgunj, Dhangadhi), 3 per row. Result buttons: `🔄 Other city` · `📤 Share`.

### 📅 Calendar, 💰 Gold & Silver, ⛽ Fuel
- Single result message with `📤 Share` (+ one contextual button where useful).

### 📰 News
- Text body with 5 headlines + sources, and **each headline also as its own inline URL button** (one per row), then `🔄 Refresh`. Headline, source and link only; no article text; previews off.

### 🌐 Language
- Toggles `en` <-> `ne`, persists, re-sends the persistent keyboard in the new language with a one-line confirmation in the new language.

Because the home keyboard is always visible, result screens don't need a "Menu" button; they only need `⬅️ Back` where there is a parent screen.

## 6. Sharing and growth (replaces Viber/WhatsApp share)

- `📤 Share` is an inline **URL button** to `https://t.me/share/url?url=<urlencoded bot link>&text=<urlencoded compact block>`, which opens Telegram's chat picker with prefilled text. The block is the key numbers plus "📲 Get daily rates free on Everyday Nepal: https://t.me/<BOT_USERNAME>?start=share". Users can also forward the bot's message natively.
- Deep-link payloads: `?start=share`, `?start=ref_<code>`. Parse in `/start`, store in `events` as the acquisition source only.
- Config: `BOT_USERNAME`.
- Analytics unchanged (counters only, salted hash of user id).

## 7. Group chats (new, small viral loop)

Families share rates in group chats, so support the bot being added to groups:
- Module commands that work in private chats and groups: `/horoscope [sign]`, `/news`, `/calendar`, `/gold`, `/forex`, `/fuel`, `/veg`, `/weather [city]`. Replies are **plain text, no reply keyboard**; add the Share/Start link as a final line.
- In groups, respond only to commands (and `@botusername` mentions), never to ordinary chat messages.
- Rate limit per group (e.g. max 6 replies/minute) and cache-only responses, so a busy group can't hurt performance.
- Register these with `setMyCommands` in both English and Nepali.

## 8. Optional: free daily digest (Phase 5, behind `FEATURE_DAILY_DIGEST`, default false)

Telegram makes the daily push free, so it's worth building but **strictly opt-in**:
- `/subscribe` and `/unsubscribe` commands (and a button on the home screen is not required). Store `digest_opt_in`, plus `digest_time` fixed at 07:00 NPT.
- Digest content: BS/AD date and any festival, default-sign horoscope (if saved), gold per tola, USD and AED forex, fuel changes, and the Kathmandu weather/AQI summary. All from cache, one message, under 4096 chars.
- Delivery: a queue throttled to **about 20 messages/second**, honouring `429 retry_after`. On `403` mark the user inactive. Never send to unsubscribed or inactive users. Log counts only.
- Never send promotional content. The digest is the product, not an ad.

## 9. Privacy, security and compliance

- Store only: Telegram user id, display name (optional), language, default zodiac, digest opt-in, active flag, timestamps. **No phone numbers.** Never log raw user ids (use the salted hash).
- `/deletedata` removes all stored data for the user immediately. `/stop` marks the user inactive and unsubscribes from the digest; data is purged after 30 days unless they return.
- Update `PRIVACY.md` and add a one-line notice to `/start` ("We store only your language and sign preference. /deletedata removes it.").
- Secrets only in env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_MODE`, `BOT_USERNAME`, `ANALYTICS_SALT`, `FEATURE_DAILY_DIGEST`. Remove all Viber and WhatsApp variables. Update `.env.example`. Never log the bot token or the full webhook URL.
- Rate limit per user (20 messages/min), input length caps, parameterised queries only, and a hard cap on typed amounts.
- Follow Telegram's Bot Terms and anti-spam rules: no unsolicited messages, no scraping of user data.

## 10. Data model changes

- Rename the user key to `tg_user_id` (BIGINT). Add `is_active` (bool), `digest_opt_in` (bool), `first_seen_at`, `last_seen_at`, `source` (acquisition payload). Keep `language`, `default_zodiac`.
- State table: `tg_user_id`, `state`, `context`, `expires_at`. Dedupe: `update_id` high-water mark.
- Add the Alembic migration (or a clean initial migration if no prior data exists).

## 11. Testing changes

- Replace channel fixtures with Telegram update fixtures: `/start` (with and without payload), reply-keyboard label text (EN and NE), `callback_query`, `my_chat_member` (kicked and member), unsupported media, edited message, group command, duplicate `update_id`, and a bad/missing secret header.
- Renderer tests: callback_data ≤ 64 bytes for **every** action (property test across all zodiac/currency/city values), HTML escaping of dynamic text, 4096 splitting on paragraph boundaries, in-order multi-part sends.
- Flow tests (Bot API mocked with `respx`): start -> horoscope grid -> sign -> save default -> revisit; forex -> currency -> quick amount; forex -> type another -> invalid -> valid; command or label cancels `awaiting_amount`; language toggle re-sends the keyboard; edit-in-place with "message is not modified"; blocked user (403) deactivates; group `/gold` works and ordinary group chat is ignored.
- Keep all existing data, parser, calendar and formatter tests.

## 12. Build order

1. **Channel layer:** `Reply` model, `Channel` protocol, Telegram client/renderer, webhook (secret check, dedupe, 200-fast) and polling mode, `/start` + home keyboard end to end, `set_webhook.py`, startup commands/descriptions, Docker/env/README.
2. **Port the bot engine:** router, action codec, label routing, state, i18n, language toggle, `/menu` `/help` `/stop` `/deletedata`, `my_chat_member` handling, rate limit.
3. **Port modules in this order:** Forex + calculator -> Gold/Silver -> Fuel -> Vegetables -> Weather -> Calendar -> News -> Horoscope.
4. **Share + deep links + analytics + group commands.**
5. **Optional daily digest** (feature-flagged).
6. **Cleanup:** delete Viber and WhatsApp code, update `README.md` (BotFather setup, polling for local dev, webhook for prod, deployment), `DECISIONS.md`, `PRIVACY.md`.

## 13. Acceptance criteria

- No Viber or WhatsApp code, config or docs remain.
- Every feature is reachable from the home keyboard in at most 2 taps (the calculator's optional typed amount excepted), and typing `/menu` always works.
- No callback_data exceeds 64 bytes, no message exceeds 4096 chars, and all dynamic text is HTML-escaped (enforced by tests).
- English and Nepali are complete for every screen, and both languages' labels are accepted at all times.
- Blocked or inactive users never cause errors or retry loops.
- No raw user ids in logs or analytics; no phone numbers stored.
- The bot token never appears in logs.
- `make test` and `make lint` pass, and `docker compose up` works from `.env.example` in polling mode with only a bot token.

## 14. Things I need to supply or confirm (list these at the end of your first response)

- A bot token from @BotFather and the chosen bot username.
- For production: a domain with HTTPS for the webhook, or confirmation that polling on a small VPS is acceptable.
- The horoscope content source (unchanged from the original spec).
- Whether to enable the daily digest after launch.

**Start with Phase 1 now. After each phase, summarise what changed, your assumptions, and anything I must verify or provide.**
