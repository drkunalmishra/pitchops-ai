"""Narration per scene via Cloud Text-to-Speech (Chirp 3 HD), cached; cost logged to llm_calls (job demo_tts).
Run from pitchops-ai/:  .venv/bin/python scripts/demo/tts.py [--estimate]"""
import base64
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from scenes import DATA, SCENES, VOICE  # noqa: E402

PRICE_PER_CHAR = 30 / 1_000_000  # Chirp 3 HD list price; first 1M chars/month are free
OUT = DATA / "audio"


def main() -> None:
    chars = sum(len(s["text"]) for s in SCENES)
    print(f"{chars} characters → est ${chars * PRICE_PER_CHAR:.3f} (list price, before free tier)")
    if "--estimate" in sys.argv:
        return
    import google.auth
    import google.auth.transport.requests
    import httpx

    from pitchops.bq import insert_rows

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    OUT.mkdir(exist_ok=True)
    durs = {}
    for s in SCENES:
        if not s["text"]:
            continue
        f = OUT / f"{s['id']}.mp3"
        meta = OUT / f"{s['id']}.txt"
        if not (f.exists() and meta.exists() and meta.read_text() == s["text"]):
            t0 = time.monotonic()
            r = httpx.post("https://texttospeech.googleapis.com/v1/text:synthesize", timeout=120,
                           headers={"Authorization": f"Bearer {creds.token}",
                                    "x-goog-user-project": "pitchops-ai-2026"},
                           json={"input": {"text": s["text"]},
                                 "voice": {"languageCode": "en-US", "name": VOICE},
                                 "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 48000}})
            r.raise_for_status()
            f.write_bytes(base64.b64decode(r.json()["audioContent"]))
            meta.write_text(s["text"])
            now = datetime.now(UTC).isoformat()
            insert_rows("llm_calls", [{"ts": now, "job": "demo_tts", "model_id": VOICE, "prompt_version": s["id"],
                                       "tokens_in": len(s["text"]), "tokens_out": 0,
                                       "cost_usd_est": len(s["text"]) * PRICE_PER_CHAR,
                                       "latency_ms": int((time.monotonic() - t0) * 1000), "status": "OK",
                                       "run_id": "demo-video", "ingested_at": now}])
        durs[s["id"]] = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]).decode())
        print(f"{s['id']}: {durs[s['id']]:.1f}s")
    (OUT / "durations.json").write_text(json.dumps(durs, indent=1))
    clip = sum(s.get("dur", 0) for s in SCENES)
    print(f"narration {sum(durs.values()):.1f}s + clips {clip}s + padding ≈ {sum(durs.values()) + clip + 0.8 * len(SCENES):.0f}s")


if __name__ == "__main__":
    main()
