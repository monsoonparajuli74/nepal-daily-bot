# Privacy

Sajilo Nepal is a utility bot. It is built to collect as little as possible.

## What we store

| Data | Why | Retention |
| --- | --- | --- |
| Telegram user id (`tg_user_id`) | The platform requires it to deliver replies; also identifies preferences | Until opt-out, then 30 days |
| Display name | Only for a friendly welcome; never shown to others | Same as above |
| Language | To reply in English or Nepali | Same as above |
| Default zodiac sign | So the horoscope opens on the user's sign | Same as above |
| Digest preference | To send the morning digest only to users who asked for it | Same as above |
| Conversation state | To hold calculator input mid-flow | 10 minutes |
| Update records | To de-duplicate Telegram's retried webhook/polling deliveries | 24 hours |
| Analytics events | To count feature usage, keyed by a salted **hash** of the id | Rolling window |

## What we never store

* Message contents (typed or received).
* Phone numbers, location data.
* Any payment or financial account information.

A Telegram user id is a numeric account identifier, not a phone number, and is far less
sensitive than the identifier the previous WhatsApp build required. It is stored only to send
replies and remember preferences, is never written to logs, and is never sent anywhere except
Telegram's Bot API and this service's own database.

## Analytics

Usage events are stored against a **salted SHA-256 hash** of the user id, never the id itself.
The salt is set with `ANALYTICS_SALT` and is not shipped in the repository. This lets us count
daily active users and per-feature usage without identifying anyone. Set a strong, private salt
in production.

## Third parties

The bot fetches public data from: Nepal Rastra Bank, FENEGOSIDA, Nepal Oil Corporation,
Kalimati Market, Open-Meteo and public RSS feeds. These requests contain no user data — only a
descriptive User-Agent. No user data is sent to any third party.

Messages are delivered through the Telegram Bot API. Telegram processes the messages you send
to and receive from the bot as part of delivery; their handling is governed by Telegram's own
privacy policy.

## Your control

* Send **/stop** at any time to stop messages. We mark the account inactive and delete its
  preference data after the retention window. Any later message re-activates it.
* Send **/deletedata** to be forgotten immediately: your user row, conversation state and
  analytics events are erased at once.
* The morning digest is opt-in only: **/subscribe** to receive it, **/unsubscribe** to stop.

## Questions

This is a template privacy statement for a self-hosted deployment. The operator running this
instance is responsible for keeping it accurate for their jurisdiction (for example, Nepal's
Individual Privacy Act).
