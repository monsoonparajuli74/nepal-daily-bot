"""All user-facing strings, in English and Nepali. Nothing user-facing is hardcoded elsewhere."""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "ne"
SUPPORTED_LANGUAGES = ("en", "ne")

#: slug -> {"en": English, "ne": Nepali}
SIGN_NAMES: dict[str, dict[str, str]] = {
    "aries": {"en": "Aries", "ne": "मेष"},
    "taurus": {"en": "Taurus", "ne": "वृष"},
    "gemini": {"en": "Gemini", "ne": "मिथुन"},
    "cancer": {"en": "Cancer", "ne": "कर्कट"},
    "leo": {"en": "Leo", "ne": "सिंह"},
    "virgo": {"en": "Virgo", "ne": "कन्या"},
    "libra": {"en": "Libra", "ne": "तुला"},
    "scorpio": {"en": "Scorpio", "ne": "वृश्चिक"},
    "sagittarius": {"en": "Sagittarius", "ne": "धनु"},
    "capricorn": {"en": "Capricorn", "ne": "मकर"},
    "aquarius": {"en": "Aquarius", "ne": "कुम्भ"},
    "pisces": {"en": "Pisces", "ne": "मीन"},
}

STRINGS: dict[str, dict[str, str]] = {
    # ---- Home / navigation ----
    "welcome": {
        "en": "🙏 Namaste! Welcome to Sajilo Nepal.",
        "ne": "🙏 नमस्ते! सजिलो नेपालमा स्वागत छ।",
    },
    "welcome_hint": {
        "en": "Tap a button below 👇",
        "ne": "तलको बटन थिच्नुहोस् 👇",
    },
    "btn_horoscope": {"en": "🔮 Daily Horoscope", "ne": "🔮 दैनिक राशिफल"},
    "btn_news": {"en": "📰 Latest News", "ne": "📰 ताजा समाचार"},
    "btn_calendar": {"en": "📅 Nepali Calendar", "ne": "📅 नेपाली पात्रो"},
    "btn_metals": {"en": "💰 Gold & Silver", "ne": "💰 सुन तथा चाँदी"},
    "btn_forex": {"en": "💵 Forex Rates", "ne": "💵 विदेशी मुद्रा"},
    "btn_fuel": {"en": "⛽ Fuel Prices", "ne": "⛽ इन्धन मूल्य"},
    "btn_vegetables": {"en": "🥦 Vegetable Market", "ne": "🥦 तरकारी बजार"},
    "btn_weather": {"en": "🌤️ Weather & AQI", "ne": "🌤️ मौसम र वायु गुणस्तर"},
    "btn_language": {"en": "🌐 Language / भाषा", "ne": "🌐 Language / भाषा"},
    "btn_main_menu": {"en": "⬅️ Main Menu", "ne": "⬅️ मुख्य मेनु"},
    "btn_back": {"en": "⬅️ Back", "ne": "⬅️ पछाडि"},
    "btn_share": {"en": "📤 Share", "ne": "📤 सेयर"},
    "btn_cancel": {"en": "⬅️ Cancel", "ne": "⬅️ रद्द गर्नुहोस्"},
    # ---- Home menus ----
    "home_menu_title": {
        "en": "🙏 Sajilo Nepal\nDaily essentials, one tap away.",
        "ne": "🙏 सजिलो नेपाल\nदैनिक जानकारी, एक ट्यापमा।",
    },
    "home_menu_footer": {
        "en": "Reply 'menu' any time, or 'stop' to opt out.",
        "ne": "कुनै पनि बेला 'menu' लेख्नुहोस्, बन्द गर्न 'stop'।",
    },
    "menu_open": {"en": "Open menu", "ne": "मेनु खोल्नुहोस्"},
    "sec_everyday": {"en": "⛅ Everyday", "ne": "⛅ दैनिक"},
    "sec_settings": {"en": "⚙️ Settings", "ne": "⚙️ सेटिङ"},
    "sec_zodiac": {"en": "♈ Zodiac signs", "ne": "♈ राशि"},
    "sec_cities": {"en": "🏙️ Cities", "ne": "🏙️ सहरहरू"},
    "desc_horoscope": {"en": "Today's reading", "ne": "आजको राशिफल"},
    "desc_news": {"en": "Top headlines", "ne": "मुख्य समाचार"},
    "desc_calendar": {"en": "Today's BS date & festivals", "ne": "आजको मिति र चाड"},
    "desc_metals": {"en": "Today's gold & silver", "ne": "आजको सुन र चाँदी"},
    "desc_forex": {"en": "NRB rates & remittance", "ne": "राष्ट्र बैंक दर र रेमिट्यान्स"},
    "desc_fuel": {"en": "Petrol, diesel, gas", "ne": "पेट्रोल, डिजेल, ग्यास"},
    "desc_vegetables": {"en": "Kalimati market", "ne": "कलिमाटी बजार"},
    "desc_weather": {"en": "Weather & air quality", "ne": "मौसम र वायु गुणस्तर"},
    "desc_language": {"en": "Switch English / नेपाली", "ne": "English / नेपाली परिवर्तन"},
    "row_more_signs": {"en": "…more signs", "ne": "…थप राशि"},
    "desc_more_signs": {"en": "Capricorn, Aquarius, Pisces", "ne": "मकर, कुम्भ, मीन"},
    "row_more_currencies": {"en": "More currencies", "ne": "थप मुद्रा"},
    "share_footer": {"en": "📤 Share this: {link}", "ne": "📤 सेयर गर्नुहोस्: {link}"},
    "btn_calculator_short": {"en": "🧮 Calculator", "ne": "🧮 क्याल्कुलेटर"},
    # ---- Text commands / lifecycle ----
    "help_text": {
        "en": "Send 'menu' for the main menu, a number to pick a news item, or 'stop' to opt out.",
        "ne": "मुख्य मेनुका लागि 'menu', समाचार छान्न नम्बर, बन्द गर्न 'stop' लेख्नुहोस्।",
    },
    "opt_out_done": {
        "en": "👋 You've been unsubscribed. No messages will be sent until you write to us again. Send 'menu' to restart.",
        "ne": "👋 तपाईंले सदस्यता रद्द गर्नुभयो। तपाईं फेरि लेख्नुभएसम्म कुनै सन्देश पठाइने छैन। पुनः सुरु गर्न 'menu' लेख्नुहोस्।",
    },
    "opt_in_done": {
        "en": "✅ You're back. Welcome!",
        "ne": "✅ तपाईं फर्किनुभयो। स्वागत छ!",
    },
    "welcome_back": {
        "en": "👋 Welcome back!",
        "ne": "👋 पुनः स्वागत छ!",
    },
    # ---- Common ----
    "updated": {"en": "Updated: {time} (NPT)", "ne": "अद्यावधिक: {time} (NPT)"},
    "stale_prefix": {
        "en": "⚠️ Data may be out of date.\n",
        "ne": "⚠️ तथ्याङ्क पुरानो हुन सक्छ।\n",
    },
    "error_generic": {
        "en": "This section is refreshing in the background — please try again in a moment.",
        "ne": "यो खण्ड पृष्ठभूमिमा अद्यावधिक हुँदैछ — केही क्षणमा फेरि हेर्नुहोस्।",
    },
    "error_no_data": {
        "en": "Fresh figures are on their way — check back in a few minutes.",
        "ne": "नयाँ विवरण आउँदैछ — केही मिनेटपछि हेर्नुहोस्।",
    },
    "unknown_hint": {
        "en": "I didn't get that. Here's the main menu 👇",
        "ne": "बुझिएन। यो मुख्य मेनु हो 👇",
    },
    "rate_limited": {
        "en": "⏳ You're sending messages too fast. Please slow down a little.",
        "ne": "⏳ तपाईं धेरै छिटो सन्देश पठाउँदै हुनुहुन्छ। कृपया अलिकति ढिलो गर्नुहोस्।",
    },
    "unsupported_message": {
        "en": "Please use the buttons below 👇",
        "ne": "कृपया तलका बटनहरू प्रयोग गर्नुहोस् 👇",
    },
    "language_set": {
        "en": "✅ Language set to English.",
        "ne": "✅ भाषा नेपालीमा परिवर्तन भयो।",
    },
    # ---- Horoscope ----
        "horo_title": {"en": "?? Daily Horoscope", "ne": "?? ????? ??????"},
    "horo_pick_sign": {
        "en": "Pick your zodiac sign:",
        "ne": "आफ्नो राशि छान्नुहोस्:",
    },
    "horo_footer": {
        "en": "📖 Source: Nepali Patro · For entertainment purposes.",
        "ne": "📖 स्रोत: नेपाली पात्रो · मनोरञ्जनको उद्देश्यले मात्र।",
    },
    "horo_change_sign": {"en": "🔄 Change Sign", "ne": "🔄 राशि परिवर्तन"},
    "btn_save_default": {"en": "📌 Save as Default", "ne": "📌 पूर्वनिर्धारित"},
    "horo_saved": {
        "en": "📌 {sign} saved as your default sign.",
        "ne": "📌 {sign} तपाईंको पूर्वनिर्धारित राशि बनाइयो।",
    },
    "horo_no_reading": {
        "en": "The stars are still writing this one — check back in a little while.",
        "ne": "ताराहरूले यो अझै लेखिरहेका छन् — केही बेरपछि फेरि हेर्नुहोस्।",
    },
    # ---- Horoscope periods ----
    "horo_period_today": {"en": "📅 Today", "ne": "📅 आज"},
    "horo_period_week": {"en": "🗓 This Week", "ne": "🗓 यो हप्ता"},
    "horo_period_month": {"en": "🗓 This Month", "ne": "🗓 यो महिना"},
    "horo_period_year": {"en": "🌟 This Year", "ne": "🌟 यो वर्ष"},
    "horo_weekly_title": {"en": "🗓 Weekly Horoscope", "ne": "🗓 साप्ताहिक राशिफल"},
    "horo_monthly_title": {"en": "🗓 Monthly Horoscope", "ne": "🗓 मासिक राशिफल"},
    "horo_yearly_title": {"en": "🌟 Yearly Horoscope", "ne": "🌟 वार्षिक राशिफल"},
    # ---- Forex ----
    "fx_title": {"en": "💵 Official NRB Exchange Rates", "ne": "💵 नेपाल राष्ट्र बैंकको आधिकारिक विनिमय दर"},
    "fx_disclaimer": {
        "en": "Source: Nepal Rastra Bank. Rates in NPR.",
        "ne": "स्रोत: नेपाल राष्ट्र बैंक। दर नेपाली रुपैयाँमा।",
    },
    "fx_buy": {"en": "Buy", "ne": "खरिद"},
    "fx_sell": {"en": "Sell", "ne": "बिक्री"},
    "btn_calculator": {"en": "🧮 Remittance Calculator", "ne": "🧮 रेमिट्यान्स क्याल्कुलेटर"},
    "btn_more_currencies": {"en": "More currencies", "ne": "थप मुद्रा"},
    "fx_calc_pick": {
        "en": "🧮 Which currency are you sending?",
        "ne": "🧮 तपाईं कुन मुद्रा पठाउँदै हुनुहुन्छ?",
    },
    "calc_prompt": {
        "en": "Send the amount in {currency} (numbers only), or tap a quick amount:",
        "ne": "{currency} मा रकम पठाउनुहोस् (अंक मात्र), वा छिटो रकम थिच्नुहोस्:",
    },
    "calc_type_hint": {
        "en": "✍️ Type the amount in the message box below, then send it.",
        "ne": "✍️ तलको सन्देश बक्समा रकम टाइप गरी पठाउनुहोस्।",
    },
    "calc_type_now": {
        "en": "✍️ Send the amount in {currency}.\nType it in the message box below and press send.",
        "ne": "✍️ {currency} मा रकम पठाउनुहोस्।\nतलको सन्देश बक्समा लेखेर पठाउनुहोस्।",
    },
    "calc_invalid": {
        "en": "That doesn't look like a valid amount. Please enter a positive number up to 1,00,00,000.",
        "ne": "यो मान्य रकम जस्तो देखिएन। कृपया १,००,००,००० सम्मको धनात्मक संख्या लेख्नुहोस्।",
    },
    "calc_title": {"en": "🧮 Conversion Summary", "ne": "🧮 रूपान्तरण सारांश"},
    "calc_foreign_amount": {"en": "Foreign Amount", "ne": "विदेशी रकम"},
    "calc_today_rate": {"en": "Today's Rate", "ne": "आजको दर"},
    "calc_total": {"en": "Total Value", "ne": "कुल मूल्य"},
    "calc_disclaimer": {
        "en": "ℹ️ Based on NRB's official rate. Remittance companies' actual rates and fees differ.",
        "ne": "ℹ️ यो नेपाल राष्ट्र बैंकको आधिकारिक दरमा आधारित छ। रेमिट्यान्स कम्पनीको वास्तविक दर र शुल्क फरक हुन्छ।",
    },
    "btn_convert_again": {"en": "🔄 Convert Another", "ne": "🔄 फेरि रूपान्तरण"},
    # ---- Vegetables ----
    "veg_title": {"en": "🥦 Kalimati Vegetable Prices", "ne": "🥦 कलिमाटी तरकारी मूल्य"},
    "veg_pick": {"en": "🥦 What would you like to see?", "ne": "🥦 तपाईं के हेर्न चाहनुहुन्छ?"},
    "veg_essentials_title": {"en": "🍅 Daily Essentials", "ne": "🍅 दैनिक आवश्यक"},
    "veg_vegetables_title": {"en": "🥦 Vegetables", "ne": "🥦 तरकारी"},
    "veg_fruits_title": {"en": "🍎 Fruits", "ne": "🍎 फलफूल"},
    "veg_greens_title": {"en": "🥬 Leafy Greens", "ne": "🥬 सागसब्जी"},
    "veg_trends_title": {"en": "📈 Price Trends (vs yesterday)", "ne": "📈 मूल्य प्रवृत्ति (हिजोको तुलनामा)"},
    "btn_essentials": {"en": "🍅 Essentials", "ne": "🍅 दैनिक आवश्यक"},
    "btn_veg_list": {"en": "🥦 Vegetables", "ne": "🥦 तरकारी"},
    "btn_fruit_list": {"en": "🍎 Fruits", "ne": "🍎 फलफूल"},
    "btn_greens": {"en": "🥬 Leafy Greens", "ne": "🥬 सागसब्जी"},
    "btn_trends": {"en": "📈 Trends", "ne": "📈 प्रवृत्ति"},
    "veg_no_items": {
        "en": "Today's market list doesn't include this selection — try another section.",
        "ne": "आजको बजार सूचीमा यी सामान छैनन् — अर्को खण्ड हेर्नुहोस्।",
    },
    "veg_more_title": {"en": "🥦 More Vegetables", "ne": "🥦 थप तरकारी"},
    "btn_more_veg": {"en": "🥦 More", "ne": "🥦 थप"},
    "veg_range_note": {
        "en": "Today's price ranges (yesterday's comparison is still being collected):",
        "ne": "आजको मूल्य दायरा (हिजोको तुलना अझै संकलन हुँदैछ):",
    },
    "veg_no_compare": {
        "en": "A day of history is still being collected — trends will appear soon.",
        "ne": "अझै एक दिनको इतिहास संकलन हुँदैछ — प्रवृत्ति चाँडै देखिनेछ।",
    },
    "veg_up": {"en": "pricier", "ne": "महँगो"},
    "veg_down": {"en": "cheaper", "ne": "सस्तो"},
    # ---- Weather ----
    "wx_title": {"en": "🌤️ {city} Weather & Air Quality", "ne": "🌤️ {city} मौसम र वायु गुणस्तर"},
    "wx_pick": {"en": "🌤️ Choose a city:", "ne": "🌤️ सहर छान्नुहोस्:"},
    "wx_now": {"en": "Now: {temp}°C | {desc}", "ne": "अहिले: {temp}°C | {desc}"},
    "wx_feels": {"en": "Feels like {temp}°C", "ne": "अनुभूति {temp}°C"},
    "wx_humidity": {"en": "💧 Humidity {value}%", "ne": "💧 आर्द्रता {value}%"},
    "wx_wind": {"en": "🌬️ Wind {value} km/h", "ne": "🌬️ हावा {value} किमी/घण्टा"},
    "wx_uv": {"en": "☀️ UV index {value}", "ne": "☀️ युवी सूचक {value}"},
    "wx_sun": {"en": "🌅 Sunrise {rise} · Sunset {sett}", "ne": "🌅 सूर्योदय {rise} · सूर्यास्त {sett}"},
    "wx_today": {
        "en": "Today: {low}°C - {high}°C | Rain chance {rain}%",
        "ne": "आज: {low}°C - {high}°C | वर्षाको सम्भावना {rain}%",
    },
    "wx_aqi": {"en": "AQI: {aqi} {band}", "ne": "वायु गुणस्तर: {aqi} {band}"},
    "wx_aqi_unknown": {"en": "AQI: waiting for the next reading", "ne": "वायु गुणस्तर: अर्को मापनको प्रतीक्षामा"},
    "btn_terai_hubs": {"en": "☀️ Terai Hubs", "ne": "☀️ तराई क्षेत्र"},
    "city_kathmandu": {"en": "🏔️ Kathmandu", "ne": "🏔️ काठमाडौं"},
    "city_pokhara": {"en": "🌊 Pokhara", "ne": "🌊 पोखरा"},
    "city_chitwan": {"en": "🚜 Chitwan", "ne": "🚜 चितवन"},
    "city_biratnagar": {"en": "Biratnagar", "ne": "विराटनगर"},
    "city_janakpur": {"en": "Janakpur", "ne": "जनकपुर"},
    "city_birgunj": {"en": "Birgunj", "ne": "वीरगन्ज"},
    "city_butwal": {"en": "Butwal", "ne": "बुटवल"},
    "city_nepalgunj": {"en": "Nepalgunj", "ne": "नेपालगन्ज"},
    "city_dhangadhi": {"en": "Dhangadhi", "ne": "धनगढी"},
    "aqi_band_good": {"en": "🟢 Good", "ne": "🟢 राम्रो"},
    "aqi_band_moderate": {"en": "🟡 Moderate", "ne": "🟡 मध्यम"},
    "aqi_band_sensitive": {"en": "🟠 Unhealthy for Sensitive Groups", "ne": "🟠 संवेदनशील समूहका लागि अस्वस्थ"},
    "aqi_band_unhealthy": {"en": "🔴 Unhealthy", "ne": "🔴 अस्वस्थ"},
    "aqi_band_very_unhealthy": {"en": "🟣 Very Unhealthy", "ne": "🟣 धेरै अस्वस्थ"},
    "aqi_band_hazardous": {"en": "🟤 Hazardous", "ne": "🟤 खतरनाक"},
    "aqi_advice_good": {
        "en": "Air quality is good. Enjoy outdoor activities.",
        "ne": "वायु गुणस्तर राम्रो छ। बाहिरी गतिविधि रमाइलोसँग गर्नुहोस्।",
    },
    "aqi_advice_moderate": {
        "en": "Air is acceptable. Very sensitive people should take it easy.",
        "ne": "हावा स्वीकार्य छ। अति संवेदनशील व्यक्तिले सतर्कता अपनाउनुहोस्।",
    },
    "aqi_advice_sensitive": {
        "en": "Sensitive groups: limit long or heavy outdoor activity.",
        "ne": "संवेदनशील समूह: लामो वा भारी बाहिरी गतिविधि घटाउनुहोस्।",
    },
    "aqi_advice_unhealthy": {
        "en": "Wear an N95 mask outdoors and limit outdoor activity.",
        "ne": "बाहिर N95 मास्क लगाउनुहोस् र बाहिरी गतिविधि सीमित गर्नुहोस्।",
    },
    "aqi_advice_very_unhealthy": {
        "en": "Avoid outdoor activity. Keep windows closed and use a mask if you must go out.",
        "ne": "बाहिरी गतिविधि नगर्नुहोस्। झ्याल बन्द राख्नुहोस्, निस्कनै परे मास्क लगाउनुहोस्।",
    },
    "aqi_advice_hazardous": {
        "en": "Emergency conditions. Stay indoors and avoid all outdoor activity.",
        "ne": "आपतकालीन अवस्था। घरभित्रै बस्नुहोस्, बाहिरी गतिविधि पूर्ण रूपमा नगर्नुहोस्।",
    },
    # ---- Calendar ----
    "cal_title": {"en": "🇳🇵 Nepali Calendar", "ne": "🇳🇵 नेपाली पात्रो"},
    "cal_today": {"en": "Today: {weekday}, {bs} BS | {ad}", "ne": "आज: {weekday}, {bs} बि.सं. | {ad}"},
    "cal_festival_today": {"en": "🎉 Today: {name}", "ne": "🎉 आज: {name}"},
    "cal_upcoming": {"en": "Upcoming:", "ne": "आउँदै:"},
    "cal_no_festival": {"en": "A quiet day on the calendar — no festivals or holidays today.", "ne": "पात्रोमा शान्त दिन — आज कुनै चाड वा बिदा छैन।"},
    "cal_none_upcoming": {"en": "Festival dates will appear here as the year unfolds.", "ne": "वर्ष अगाडि बढ्दै जाँदा चाडपर्वका मिति यहाँ देखिनेछन्।"},
    # ---- News ----
    "news_title": {"en": "📰 Latest News", "ne": "📰 ताजा समाचार"},
    "btn_more_news": {"en": "More News", "ne": "थप समाचार"},
    "news_no_items": {"en": "Headlines are updating — check back in a minute.", "ne": "शीर्षकहरू अद्यावधिक हुँदैछन् — एक मिनेटपछि हेर्नुहोस्।"},
    "news_tap": {"en": "Tap a number to read the full story.", "ne": "पूरा समाचार पढ्न नम्बर थिच्नुहोस्।"},
    # ---- Metals ----
    "metals_title": {"en": "💰 Gold & Silver (FENEGOSIDA)", "ne": "💰 सुन तथा चाँदी (फेनेगोसिडा)"},
    "metals_hallmark": {"en": "Hallmark Gold", "ne": "छापावाल सुन"},
    "metals_tejabi": {"en": "Tejabi Gold", "ne": "तेजाबी सुन"},
    "metals_silver": {"en": "Silver", "ne": "चाँदी"},
    "metals_per_tola": {"en": "per tola", "ne": "प्रति तोला"},
    "metals_per_10g": {"en": "per 10g", "ne": "प्रति १० ग्राम"},
    "metals_effective": {"en": "Effective: {date}", "ne": "लागू: {date}"},
    # ---- Fuel ----
    "fuel_title": {"en": "⛽ Fuel Prices - Kathmandu", "ne": "⛽ इन्धन मूल्य - काठमाडौं"},
    "fuel_petrol": {"en": "Petrol", "ne": "पेट्रोल"},
    "fuel_diesel": {"en": "Diesel", "ne": "डिजेल"},
    "fuel_kerosene": {"en": "Kerosene", "ne": "मट्टितेल"},
    "fuel_lpg": {"en": "LPG (14.2 kg)", "ne": "ग्यास (१४.२ के.जी.)"},
    "fuel_per_litre": {"en": "/litre", "ne": "/लिटर"},
    "fuel_effective": {"en": "Effective: {date}", "ne": "लागू: {date}"},
    # ---- Telegram-specific ----
    "welcome_body": {
        "en": "🙏 Namaste! I'm Sajilo Nepal — your daily companion for horoscope, news, the Nepali calendar, gold, forex, fuel, vegetables and weather.",
        "ne": "🙏 नमस्ते! म सजिलो नेपाल हुँ — राशिफल, समाचार, नेपाली पात्रो, सुन, विदेशी मुद्रा, इन्धन, तरकारी र मौसमको दैनिक साथी।",
    },
    "privacy_notice": {
        "en": "We store only your language and sign preference. /deletedata removes it.",
        "ne": "हामी तपाईंको भाषा र राशि मात्र राख्छौं। /deletedata ले यो मेटाउँछ।",
    },
    "unsupported_media_hint": {
        "en": "🤔 I can only read text. Tap a button or send /menu.",
        "ne": "🤔 म पाठ मात्र पढ्न सक्छु। बटन थिच्नुहोस् वा /menu पठाउनुहोस्।",
    },
    "group_share_line": {
        "en": "📲 Sajilo Nepal: {link}",
        "ne": "📲 सजिलो नेपाल: {link}",
    },
    "btn_refresh": {"en": "🔄 Refresh", "ne": "🔄 ताजा"},
    "btn_other_city": {"en": "🔄 Other city", "ne": "🔄 अर्को सहर"},
    "btn_type_another": {"en": "✍️ Type another amount", "ne": "✍️ अर्को रकम लेख्नुहोस्"},
    "calc_quick_hint": {
        "en": "Tap a quick amount, or type the amount and send it:",
        "ne": "छिटो रकम थिच्नुहोस्, वा रकम लेखेर पठाउनुहोस्:",
    },
    "deletedata_done": {
        "en": "🗑️ All your data has been deleted. Send /start to begin again.",
        "ne": "🗑️ तपाईंको सबै डाटा मेटाइयो। फेरि सुरु गर्न /start पठाउनुहोस्।",
    },
    "stopped_notice": {
        "en": "👋 You won't receive daily digests. Send /start or any message to come back.",
        "ne": "👋 तपाईंले दैनिक डाइजेस्ट पाउनुहुने छैन। फर्किन /start वा कुनै सन्देश पठाउनुहोस्।",
    },
    # ---- Daily digest ----
    "digest_subscribed": {
        "en": "✅ Subscribed. You'll get one free morning summary at 7:00 AM NPT.",
        "ne": "✅ सदस्यता लिनुभयो। बिहान ७:०० बजे एक निःशुल्क सारांश पाउनुहुनेछ।",
    },
    "digest_unsubscribed": {
        "en": "🔕 Unsubscribed from the daily digest.",
        "ne": "🔕 दैनिक डाइजेस्टको सदस्यता रद्द भयो।",
    },
    "digest_disabled": {
        "en": "The daily digest returns with the next morning update.",
        "ne": "दैनिक डाइजेस्ट अर्को बिहानको अद्यावधिकसँगै फर्किनेछ।",
    },
    "digest_header": {"en": "☀️ Good morning — Sajilo Nepal", "ne": "☀️ शुभ बिहानी — सजिलो नेपाल"},
    "digest_date": {
        "en": "{weekday}, {bs} BS · {ad}",
        "ne": "{weekday}, {bs} बि.सं. · {ad}",
    },
    "briefing_headlines": {"en": "📰 Top headlines", "ne": "📰 मुख्य समाचार"},
    "briefing_no_headlines": {
        "en": "Headlines are temporarily unavailable.",
        "ne": "समाचार शीर्षकहरू अहिले उपलब्ध छैनन्।",
    },
    "briefing_snapshot": {"en": "📊 Nepal snapshot", "ne": "📊 नेपालको अवस्था"},
    "briefing_calendar_date": {
        "en": "🇳🇵 Calendar: {weekday}, {bs} BS",
        "ne": "🇳🇵 पात्रो: {weekday}, {bs} बि.सं.",
    },
    "briefing_calendar_event": {"en": "🇳🇵 Today: {event}", "ne": "🇳🇵 आज: {event}"},
    "briefing_forex": {
        "en": "💵 USD/NRB: buy रू {buy}, sell रू {sell} (rate date: {date})",
        "ne": "💵 अमेरिकी डलर/राष्ट्र बैंक: खरिद रू {buy}, बिक्री रू {sell} (दर मिति: {date})",
    },
    "briefing_metals": {
        "en": "💰 Gold रू {gold}/tola · Silver रू {silver}/tola (effective: {date})",
        "ne": "💰 सुन रू {gold}/तोला · चाँदी रू {silver}/तोला (लागू मिति: {date})",
    },
    "briefing_vegetables": {
        "en": "🥦 Kalimati: {prices}",
        "ne": "🥦 कालिमाटी: {prices}",
    },
    "briefing_fuel": {
        "en": "⛽ Fuel (Nepali Patro): petrol रू {petrol}/L · diesel रू {diesel}/L (effective: {date})",
        "ne": "⛽ इन्धन (नेपाली पात्रो): पेट्रोल रू {petrol}/लि. · डिजेल रू {diesel}/लि. (लागू मिति: {date})",
    },
    "briefing_weather": {
        "en": "🌤️ Kathmandu today: {low}–{high}°C · rain chance {rain}%",
        "ne": "🌤️ आज काठमाडौं: {low}–{high}°C · वर्षाको सम्भावना {rain}%",
    },
    "briefing_share_market_unavailable": {
        "en": "📈 Share market: no live NEPSE data source is configured.",
        "ne": "📈 सेयर बजार: NEPSE को प्रत्यक्ष तथ्याङ्क स्रोत जडान गरिएको छैन।",
    },
    # ---- Bot profile / command descriptions ----
    "bot_description": {
        "en": "Free daily essentials for Nepal: horoscope, news, Nepali calendar, gold & silver, forex, fuel, vegetables, weather and air quality. English or Nepali.",
        "ne": "नेपालका लागि निःशुल्क दैनिक जानकारी: राशिफल, समाचार, पात्रो, सुन-चाँदी, विदेशी मुद्रा, इन्धन, तरकारी, मौसम र वायु गुणस्तर। अंग्रेजी वा नेपाली।",
    },
    "bot_short_description": {
        "en": "Free daily Nepal essentials in one bot.",
        "ne": "एकै बोटमा दैनिक नेपाली जानकारी।",
    },
    "cmd_desc_start": {"en": "Open the main menu", "ne": "मुख्य मेनु खोल्नुहोस्"},
    "cmd_desc_menu": {"en": "Show the main menu", "ne": "मुख्य मेनु देखाउनुहोस्"},
    "cmd_desc_horoscope": {"en": "Daily horoscope", "ne": "दैनिक राशिफल"},
    "cmd_desc_news": {"en": "Top headlines", "ne": "मुख्य समाचार"},
    "cmd_desc_calendar": {"en": "Today's Nepali date & festivals", "ne": "आजको मिति र चाड"},
    "cmd_desc_gold": {"en": "Gold & silver rates", "ne": "सुन र चाँदीको दर"},
    "cmd_desc_forex": {"en": "NRB forex rates", "ne": "राष्ट्र बैंक विनिमय दर"},
    "cmd_desc_fuel": {"en": "Fuel prices", "ne": "इन्धन मूल्य"},
    "cmd_desc_veg": {"en": "Kalimati vegetable prices", "ne": "कलिमाटी तरकारी मूल्य"},
    "cmd_desc_weather": {"en": "Weather & air quality", "ne": "मौसम र वायु गुणस्तर"},
    "cmd_desc_language": {"en": "Switch language", "ne": "भाषा परिवर्तन"},
    "cmd_desc_help": {"en": "How to use the bot", "ne": "बोट कसरी प्रयोग गर्ने"},
    "cmd_desc_stop": {"en": "Stop messages", "ne": "सन्देश बन्द गर्नुहोस्"},
    "cmd_desc_deletedata": {"en": "Delete my data", "ne": "मेरो डाटा मेटाउनुहोस्"},
    "cmd_desc_subscribe": {"en": "Subscribe to the morning digest", "ne": "बिहानको सारांश सदस्यता"},
    "cmd_desc_unsubscribe": {"en": "Unsubscribe from the digest", "ne": "सारांश सदस्यता रद्द"},
}

#: Emoji per zodiac sign, for the 4x3 picker grid.
SIGN_EMOJI: dict[str, str] = {
    "aries": "🐏",
    "taurus": "🐂",
    "gemini": "👥",
    "cancer": "🦀",
    "leo": "🦁",
    "virgo": "👩",
    "libra": "⚖️",
    "scorpio": "🦂",
    "sagittarius": "🏹",
    "capricorn": "🐐",
    "aquarius": "🏺",
    "pisces": "🐟",
}

#: WMO weather-code descriptions (Open-Meteo uses WMO codes).
WMO_CODES: dict[int, dict[str, str]] = {
    0: {"en": "Clear sky", "ne": "सफा आकाश"},
    1: {"en": "Mainly clear", "ne": "प्रायः सफा"},
    2: {"en": "Partly cloudy", "ne": "आंशिक बदली"},
    3: {"en": "Overcast", "ne": "बादलले ढाकिएको"},
    45: {"en": "Fog", "ne": "कुहिरो"},
    48: {"en": "Depositing rime fog", "ne": "जम्ने कुहिरो"},
    51: {"en": "Light drizzle", "ne": "हल्का सिरसिर"},
    53: {"en": "Moderate drizzle", "ne": "मध्यम सिरसिर"},
    55: {"en": "Dense drizzle", "ne": "बाक्लो सिरसिर"},
    61: {"en": "Slight rain", "ne": "हल्का वर्षा"},
    63: {"en": "Moderate rain", "ne": "मध्यम वर्षा"},
    65: {"en": "Heavy rain", "ne": "भारी वर्षा"},
    66: {"en": "Freezing rain", "ne": "जम्ने वर्षा"},
    67: {"en": "Heavy freezing rain", "ne": "भारी जम्ने वर्षा"},
    71: {"en": "Slight snow", "ne": "हल्का हिमपात"},
    73: {"en": "Moderate snow", "ne": "मध्यम हिमपात"},
    75: {"en": "Heavy snow", "ne": "भारी हिमपात"},
    77: {"en": "Snow grains", "ne": "हिउँका दाना"},
    80: {"en": "Slight rain showers", "ne": "हल्का वर्षा"},
    81: {"en": "Moderate rain showers", "ne": "मध्यम वर्षा"},
    82: {"en": "Violent rain showers", "ne": "अत्यधिक वर्षा"},
    85: {"en": "Slight snow showers", "ne": "हल्का हिमपात"},
    86: {"en": "Heavy snow showers", "ne": "भारी हिमपात"},
    95: {"en": "Thunderstorm", "ne": "चट्याङसहित आँधीबेहरी"},
    96: {"en": "Thunderstorm with slight hail", "ne": "असिनासहित चट्याङ"},
    99: {"en": "Thunderstorm with heavy hail", "ne": "भारी असिनासहित चट्याङ"},
}


def normalise_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def translate(lang: str, key: str, **kwargs: Any) -> str:
    """Look up a string in the requested language and format placeholders."""
    lang = normalise_language(lang)
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANGUAGE, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):  # pragma: no cover - defensive
            return text
    return text


def make_translator(lang: str):
    """Return a callable ``t(key, **kwargs)`` bound to one language."""
    language = normalise_language(lang)

    def _t(key: str, **kwargs: Any) -> str:
        return translate(language, key, **kwargs)

    return _t


def sign_name(slug: str, lang: str) -> str:
    entry = SIGN_NAMES.get(slug, {})
    return entry.get(normalise_language(lang)) or entry.get(DEFAULT_LANGUAGE) or slug


def sign_label(slug: str, lang: str) -> str:
    """Emoji + the sign name in the requested language only."""
    emoji = SIGN_EMOJI.get(slug, "")
    return f"{emoji} {sign_name(slug, lang)}".strip()


def wmo_description(code: int | None, lang: str) -> str:
    if code is None:
        return translate(lang, "wx_aqi_unknown").split(":")[0]
    entry = WMO_CODES.get(code, {"en": "Unknown", "ne": "अज्ञात"})
    return entry.get(normalise_language(lang), entry["en"])
