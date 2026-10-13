"""P1 smoke tests a–d, f, g (e is yt_search_pick.py). Writes docs/adr/smoke_results.json.

Usage: uv run python -m scripts.smoke.run_smoke --short VIDEO_ID --long VIDEO_ID [--only a,b,...]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from google.genai import types

from pitchops.config import get_settings
from pitchops.gemini.client import MEDIA_RES, GeminiClient, youtube_part
from pitchops.jobrun import new_run_id

OUT = Path(__file__).resolve().parents[2] / "docs" / "adr" / "smoke_results.json"
YT = "https://www.youtube.com/watch?v={}"

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary_3_sentences": {"type": "string"},
        "on_screen_text": {"type": "array", "items": {"type": "string"}},
        "last_timestamp_seen_sec": {"type": "number"},
    },
    "required": ["summary_3_sentences", "on_screen_text", "last_timestamp_seen_sec"],
}
TAG_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "property_type": {"type": "string", "enum": ["apartment", "villa", "townhouse", "penthouse", "plot",
                                                       "commercial", "mixed", "unknown"]},
        "seller_tactics": {"type": "array", "items": {"type": "string"}},
        "language": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["topic", "property_type", "seller_tactics", "language", "confidence"],
}
PROMPT_A = ("Summarize this Dubai real-estate video in exactly 3 sentences, list every piece of on-screen text "
            "you can read, and give the last timestamp (seconds) you observed.")


def r_call(res: Any) -> dict[str, Any]:
    return {"tokens_in": res.tokens_in, "tokens_out": res.tokens_out, "cost_usd_est": res.cost_usd_est,
            "latency_ms": res.latency_ms, "model_id": res.model_id, "attempts": res.attempts}


def smoke_a(g: GeminiClient, short_id: str) -> dict[str, Any]:
    s = get_settings()
    res = g.generate_json(s.gemini_model_flash, [youtube_part(YT.format(short_id)), PROMPT_A], SUMMARY_SCHEMA,
                          media_resolution="low", prompt_version="smoke_a")
    return {"ok": True, "video_id": short_id, **r_call(res), "output": res.data}


def smoke_b(g: GeminiClient, long_id: str) -> dict[str, Any]:
    s = get_settings()
    off = g.generate_json(s.gemini_model_flash, [youtube_part(YT.format(long_id), 0, 120), PROMPT_A],
                          SUMMARY_SCHEMA, media_resolution="low", prompt_version="smoke_b_offset")
    full = g.generate_json(s.gemini_model_flash, [youtube_part(YT.format(long_id)), PROMPT_A],
                           SUMMARY_SCHEMA, media_resolution="low", prompt_version="smoke_b_full")
    ratio = off.tokens_in / max(1, full.tokens_in)
    honoured = ratio < 0.6 and off.data["last_timestamp_seen_sec"] <= 150
    return {"ok": True, "video_id": long_id, "offsets_accepted_by_api": True, "offsets_honoured": honoured,
            "token_ratio_offset_vs_full": round(ratio, 3),
            "offset_call": {**r_call(off), "last_ts": off.data["last_timestamp_seen_sec"]},
            "full_call": {**r_call(full), "last_ts": full.data["last_timestamp_seen_sec"]}}


def smoke_c(g: GeminiClient) -> dict[str, Any]:
    s = get_settings()
    meta = ("Title: 2BR apartment in Dubai Marina, 8% ROI, 1% monthly payment plan, only 3 units left!\n"
            "Description: Golden visa eligible. Book a viewing today. Tags: dubai, investment, marina")
    res = g.generate_json(s.gemini_model_lite, [f"Classify this YouTube video metadata.\n{meta}"], TAG_SCHEMA,
                          prompt_version="smoke_c")
    return {"ok": True, **r_call(res), "output": res.data}


def smoke_d(g: GeminiClient) -> dict[str, Any]:
    t0 = time.monotonic()
    vecs = g.embed(["Urgency and scarcity pitch for an off-plan apartment", "عقار للبيع في دبي مارينا"])
    return {"ok": True, "model_id": get_settings().embedding_model_id, "dimension": len(vecs[0]),
            "n": len(vecs), "latency_ms": int((time.monotonic() - t0) * 1000)}


def smoke_f(run_id: str) -> dict[str, Any]:
    from google.cloud import texttospeech

    from pitchops.gcs import upload_bytes

    tts = texttospeech.TextToSpeechClient()
    voices = [v.name for v in tts.list_voices(language_code="en-US").voices]
    voice = next((v for v in voices if "Neural2" in v), None) or next(v for v in voices if "Studio" in v)
    resp = tts.synthesize_speech(
        input=texttospeech.SynthesisInput(text="Welcome to PitchOps AI: compliant property pitches in minutes."),
        voice=texttospeech.VoiceSelectionParams(language_code="en-US", name=voice),
        audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3))
    uri = upload_bytes(f"tmp/smoke/{run_id}.mp3", resp.audio_content, "audio/mpeg")
    return {"ok": True, "voice": voice, "bytes": len(resp.audio_content), "gcs_uri": uri}


def smoke_g(run_id: str) -> dict[str, Any]:
    from pitchops.fs import client

    ref = client().collection("_smoke").document(run_id)
    ref.set({"hello": "pitchops", "run_id": run_id})
    read_ok = (ref.get().to_dict() or {}).get("hello") == "pitchops"
    ref.delete()
    return {"ok": read_ok and not ref.get().exists, "database": get_settings().firestore_database,
            "write": True, "read": read_ok, "delete": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--short", required=True)
    ap.add_argument("--long", required=True)
    ap.add_argument("--only", default="a,b,c,d,f,g")
    a = ap.parse_args()
    run_id = new_run_id("smoke")
    g = GeminiClient("smoke", run_id)
    results: dict[str, Any] = json.loads(OUT.read_text()) if OUT.exists() else {}
    steps = {"a": lambda: smoke_a(g, a.short), "b": lambda: smoke_b(g, a.long), "c": lambda: smoke_c(g),
             "d": lambda: smoke_d(g), "f": lambda: smoke_f(run_id), "g": lambda: smoke_g(run_id)}
    for k in a.only.split(","):
        try:
            results[k] = {"run_id": run_id, **steps[k]()}
        except Exception as e:
            results[k] = {"run_id": run_id, "ok": False, "error": f"{type(e).__name__}: {e}"[:1500],
                          "trace": traceback.format_exc()[-1500:]}
        print(k, json.dumps(results[k], ensure_ascii=False)[:600])
    results["_media_resolution"] = str(MEDIA_RES["low"])
    results["_note"] = "cost_usd_est values are estimates from token counts x price table in pitchops/config.py"
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    _ = types  # keep import for type users
    return 0


if __name__ == "__main__":
    sys.exit(main())
