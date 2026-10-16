"""D17 — 8 fictional bilingual presenters. Names and looks are invented; portraits must not resemble real people.
voice = closest Cloud TTS English voice (Neural2) by presentation/accent; Veo voice is described in words."""

from __future__ import annotations

AVATARS: dict[str, dict[str, str]] = {
    "avatar_in": {"name": "Aanya", "heritage": "Indian", "languages": "English / Hindi", "presentation": "woman",
                  "voice": "en-IN-Neural2-A", "veo_voice": "warm Indian-English female voice"},
    "avatar_me": {"name": "Omar", "heritage": "Middle Eastern", "languages": "English / Arabic", "presentation": "man",
                  "voice": "en-GB-Neural2-B", "veo_voice": "calm Middle-Eastern-accented English male voice"},
    "avatar_na": {"name": "Jordan", "heritage": "North American", "languages": "English / Spanish", "presentation": "man",
                  "voice": "en-US-Neural2-J", "veo_voice": "friendly North-American male voice"},
    "avatar_ea": {"name": "Mei", "heritage": "East Asian", "languages": "English / Mandarin", "presentation": "woman",
                  "voice": "en-US-Neural2-F", "veo_voice": "clear, poised East-Asian-accented English female voice"},
    "avatar_af": {"name": "Kofi", "heritage": "West African", "languages": "English / French", "presentation": "man",
                  "voice": "en-GB-Neural2-D", "veo_voice": "confident West-African-accented English male voice"},
    "avatar_ru": {"name": "Alina", "heritage": "Russian", "languages": "English / Russian", "presentation": "woman",
                  "voice": "en-GB-Neural2-A", "veo_voice": "composed Russian-accented English female voice"},
    "avatar_eu": {"name": "Lukas", "heritage": "Central European", "languages": "English / German", "presentation": "man",
                  "voice": "en-GB-Neural2-O", "veo_voice": "measured German-accented English male voice"},
    "avatar_sa": {"name": "Sofia", "heritage": "South American", "languages": "English / Portuguese",
                  "presentation": "woman", "voice": "en-AU-Neural2-C",
                  "veo_voice": "bright Brazilian-accented English female voice"},
}

PORTRAIT_PROMPT = (
    "Photorealistic studio portrait of a fictional 35-year-old {heritage} real-estate advisor, a {presentation}, warm "
    "confident expression, business-smart attire, chest-up, facing camera, soft key light, modern Dubai office with "
    "blurred skyline in background, 16:9, high detail, no text, no logos. Not a real or famous person.")
