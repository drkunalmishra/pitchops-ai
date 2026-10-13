# ADR-001 — Video understanding via Vertex AI Gemini on public YouTube URLs

**Status:** Accepted · **Date:** 13 Oct 2026 · **Raw results:** `docs/adr/smoke_results.json`

## Decision
Analyse videos with **Vertex AI Gemini** (`google-genai`, `vertexai=True`), passing the public YouTube URL as
`file_data(file_uri=…, mime_type="video/*")` at **low media resolution**. No media is downloaded. Metadata, stats
and comments come only from the YouTube Data API v3 through `QuotaLedger`.

## Answers
| Question | Answer |
|---|---|
| **Do YouTube URLs work on Vertex Gemini?** | **YES** (`gemini-3.8-flash`, Short + long-form) |
| **Are `video_metadata` start/end offsets accepted for YouTube URLs?** | **YES — accepted and honoured** |

Evidence for offsets: the 0–120 s clip of a 443 s video used **11,088** input tokens vs **40,476** for the full video
(ratio 0.274 ≈ 120/443), and the model's last observed timestamp was 120 s (full run: 442 s).
→ CLAUDE.md §8 T3 plan stands: Shorts whole; long-form ≤ 15 min as first 120 s + 60 s from the middle.

## Important finding — endpoint location
Gemini 3.x models (`gemini-3.8-flash`, `gemini-3.5-flash-lite`, …) return **404 in `us-central1`** and are served
only from the Vertex **`global`** endpoint. Generation therefore uses `GEMINI_LOCATION=global` (still Vertex AI, billed
to the project and covered by trial credits — *not* AI Studio). Embeddings (`gemini-embedding-001`) work in
`us-central1`. All other resources stay in us-central1.

## Smoke results (a–g)
| # | Test | Result | Tokens in/out | Est. cost | Latency |
|---|---|---|---|---|---|
| a | Flash + YouTube Short (11 s): 3-sentence summary + on-screen text | ✅ | 1,170 / 318 | $0.0015 | 8.6 s |
| b | Flash + long-form (443 s) with offsets 0–120 s | ✅ offsets honoured | 11,088 / 680 | $0.0076 | 14.4 s |
| b′ | Same video, no offsets (control) | ✅ | 40,476 / 1,293 | $0.0241 | 25.3 s |
| c | Structured JSON with `gemini-3.5-flash-lite` (schema-validated) | ✅ first attempt | 261 / 91 | $0.00006 | 1.1 s |
| d | Embeddings `gemini-embedding-001` | ✅ **dimension 3072** | — | ~$0 | 4.3 s |
| e | YouTube Data API `channels.list` (1 unit, via QuotaLedger) | ✅ `@andradaion` resolved | — | free | — |
| f | Cloud TTS `en-US-Neural2-A` → `gs://…/tmp/smoke/*.mp3` (37 KB) | ✅ | — | ~$0 | — |
| g | Firestore (database `pitchops`) write / read / delete | ✅ | — | ~$0 | — |

Observations: low-resolution video costs ≈ **92 input tokens per second**. A 60 s Short ≈ 5.5k tokens (≈ $0.003);
a 180 s long-form sample ≈ 16.5k tokens (≈ $0.01). 2,000 T3 videos ≈ **$10–20** at the configured (conservative)
prices. The Short in (a) returned no on-screen text at low resolution; if text overlays matter for a tier,
consider `media_resolution="medium"` on a subset only.

Cost figures are **estimates** (token counts × price table in `pitchops/config.py`). Real spend: Billing → Reports.
