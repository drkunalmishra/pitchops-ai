# P7 — Property Walkthrough Videos with Digital Avatars (approval-gated)

**When:** build Fri 16 Oct evening; generate Sat 17 Oct after your approvals · **Depends on:** P4 (40 media properties), P6 (approved scripts) · **Budget cap:** media ≤ **$120** (D15), project total ≤ $200

**Deliverable:** 40 videos for 40 different properties:
- 20 × **16:9 walkthroughs** (≤ 2 min)
- 20 × **9:16 Shorts** (≤ 55 s)

Each is presented by one of **8 fictional bilingual avatars**. Nothing is generated without your approval in the web app (D16).

## Cost model per video (verify Veo prices at build time)

| Format | Veo with audio (avatar speaking) | Veo, no audio (aerial/walkthrough from real photos) | Free parts | Est. cost |
|---|---|---|---|---|
| 16:9 ≤ 2 min | intro 8 s + outro 8 s | 2 hero clips × 8 s | photo motion sequences, Cloud TTS narration, captions, fact cards, branding (FFmpeg) | ≈ $4.00 |
| 9:16 ≤ 55 s | intro 8 s | 1 hero clip × 8 s | same | ≈ $2.00 |
| **40 videos** | | | | **≈ $120** at list prices (Veo Fast: $0.15/s with audio, $0.10/s without) |

Every plan shows its own estimate. The approval page refuses any plan that would exceed the remaining media budget. A **free preview** (photos + TTS only, no Veo) is rendered first, so you can judge the story before paying for any Veo shots.

---

````text
You are building Phase P7 of PitchOps AI. Read CLAUDE.md (§2 cost guardrails, §11 D14–D21). Media generation is the most expensive step: nothing calls Veo or Imagen without an APPROVED plan record and a passing budget check. Check the current Vertex AI docs and pricing for Veo (image-to-video, aspect ratios 16:9 and 9:16, max clip length, audio/dialogue support, person-generation settings) and Imagen before coding; put model IDs and prices in config (VEO_MODEL_ID, VEO_PRICE_AUDIO_PER_SEC, VEO_PRICE_SILENT_PER_SEC, IMAGEN_MODEL_ID, IMAGEN_PRICE). Prefer the cheapest Veo "fast" model that supports image-to-video and dialogue audio.

1. Property image library (D18)
   - For each of the 40 media properties, fetch image URLs from the verified official developer/project pages in property_sources (robots.txt respected, ≤ 5 pages per site, ≤ 40 images, min 1280 px wide, skip logos/icons/floor-plan PDFs unless useful).
   - Store originals in the PRIVATE bucket gs://…/media/properties/{property_id}/raw/ (never in git).
   - Rank and tag images with Gemini Flash-Lite vision (low res): aerial, exterior_facade, skyline_view, interior_living, interior_bedroom, kitchen, bathroom, pool_amenity, gym_amenity, lobby, community, masterplan, other; quality 0–1; select the best 8–15 per property covering aerial/exterior + interiors + amenities.
   - Admin page "Property Images": view/select/deselect, and MANUAL UPLOAD of images (drag-drop to the private bucket) for properties with missing or weak images.

2. Avatar studio (D17) — 8 fictional, bilingual presenters
   - Avatar profiles (config/avatars.yaml): id, display name (fictional), heritage descriptor, languages (English + second language), age range 30–45, attire (business smart), backdrop (modern Dubai office / terrace with skyline), TTS voice id (closest Cloud TTS English voice by gender/accent: e.g., en-IN, en-GB, en-US, en-AU), Veo voice description.
       A1 Indian (English/Hindi) · A2 Middle Eastern (English/Arabic) · A3 North American (English/Spanish) · A4 East Asian (English/Mandarin) · A5 African (English/French) · A6 Russian (English/Russian) · A7 European (English/German) · A8 South American (English/Portuguese)
   - Imagen: generate 4 candidate portraits per avatar (photoreal, fictional person, neutral expression, front-facing, chest-up, professional lighting, plain modern background) → admin picks one (approval) → stored as the avatar's reference frame.
   - Portrait prompt template (fill per avatar, avoid stereotypes, no real-person likeness, no logos/text):
     "Photorealistic studio portrait of a fictional {age_range}-year-old {heritage} real-estate advisor, {gender_presentation}, warm confident expression, business-smart attire, chest-up, facing camera, soft key light, modern Dubai office with blurred skyline in background, 16:9, high detail, no text, no logos."
   - If person generation is restricted for the account/region, fall back to voice-only presenters with a branded lower-third and report it.

3. Veo prompt library (prompts/veo_v1.yaml) — every shot uses a selected property photo as the FIRST FRAME (image-to-video) so the result stays faithful to the real project
   - aerial_orbit: "Cinematic drone shot slowly orbiting the building shown, smooth 30-degree arc, golden-hour light, clear sky, gentle parallax on surrounding towers and roads, realistic architecture preserved exactly, no new buildings, no text, 8 seconds."
   - aerial_approach: "Slow forward drone approach toward the tower from mid-altitude, slight descent, Dubai skyline in the distance, stable horizon, realistic, no text."
   - facade_rise: "Low-angle camera rising smoothly up the façade, reflections on glass, steady motion, realistic, no text."
   - interior_glide: "Smooth gimbal glide through the living room shown toward the window view, natural daylight, subtle parallax, furniture and layout preserved exactly, no people, no text."
   - amenity_reveal: "Slow lateral dolly along the pool deck/amenity shown, soft shimmering water, calm atmosphere, realistic, no text."
   - skyline_sunset: "Gentle push-in from the balcony toward the skyline view at sunset, warm light, realistic, no text."
   - Avatar intro (with audio, avatar portrait as first frame): "The presenter shown looks into the camera and says in clear, friendly English: '{avatar_intro_line}'. Natural lip movement and subtle hand gesture, modern office with Dubai skyline behind, steady medium shot, no on-screen text."
   - Avatar outro: same with '{avatar_outro_line}'.
   - Negative guidance (where supported): distorted architecture, extra floors, warped text, logos, watermarks, people in property shots.
   - Aspect ratio per format (16:9 or 9:16); clip length = 8 s (or the model's supported max ≤ 8 s).

4. Video plans + approval workflow (D16)
   - Firestore video_plans/{plan_id}: property_id, format (16x9|9x16), approved script_id + version, avatar_id, shot list (ordered: avatar_intro → hero clips → photo-motion segments with narration → hero clip → avatar_outro → CTA card), each shot with source image(s), Veo prompt key, duration, audio flag, est_cost; totals: duration (16:9 ≤ 120 s, 9:16 ≤ 55 s), est_cost_usd.
   - States: DRAFT → PREVIEW_READY → AWAITING_APPROVAL → APPROVED → GENERATING → COMPOSING → REVIEW → DONE | REJECTED | FAILED.
   - Auto-planner job creates 40 DRAFT plans (20 + 20, matching each property to an approved script in the right format and rotating the 8 avatars so each is used ~5 times).
   - FREE PREVIEW (no Veo/Imagen): render a low-res composition using photo-motion + Cloud TTS + captions + placeholder cards for Veo shots → PREVIEW_READY.
   - Web page "Media Approvals": plan list with property, format, avatar, script, duration, est. cost, preview player; edit shot list (swap images, change avatar, add/remove a hero clip with live cost update); buttons Approve (shows cost and remaining media budget; disabled if it would exceed MEDIA_BUDGET_USD=120 or TOTAL_PROJECT_CAP_USD=200) and Reject.
   - Approval writes approvals record (uid, time, plan hash, est_cost) and audit row; only then can the generator run.

5. Generation + composition
   - Cloud Run Job "media" (2 vCPU, 4 GiB, timeout 3600 s, parallelism 1): for APPROVED plans, submit Veo long-running operations (concurrency ≤ 3), poll, write outputs to the private bucket; one automatic retry per failed clip, then mark shot FAILED and fall back to photo-motion for that shot (cost of failed attempts logged).
   - Narration: Cloud TTS (avatar's voice id) with SSML pauses; captions burned in from script lines with timing from TTS timepoints.
   - Compose with FFmpeg: 1920×1080 (16:9) or 1080×1920 (9:16), 30 fps, H.264/AAC, loudness normalized (-14 LUFS); photo-motion = Ken Burns pan/zoom per image (3–5 s); lower-third with property name + area; on-screen fact cards (only facts with fact_ids); final CTA card: "PitchOps Demo Realty · DEMO-PERMIT".
   - QC (automatic): duration limits, aspect ratio, audio present, captions within safe area, no black frames > 0.5 s (ffprobe/blackdetect); failures → REVIEW with reasons.
   - Output: media/{plan_id}/final.mp4 + thumbnail; signed URL playback in the app; a "Video Library" page (filter by format/avatar/property; download).

6. FinOps
   - Ledger every Imagen image, Veo second (by audio flag) and TTS character; show actual vs estimate per plan; media spend tile on the FinOps dashboard; hard stop at MEDIA_BUDGET_USD.

ACCEPTANCE
- 8 avatars approved (portraits stored), 40 DRAFT plans created, 40 free previews rendered at $0 Veo cost.
- Only APPROVED plans generate; an attempt to generate an unapproved plan is rejected (test).
- Budget guard blocks an approval that would exceed the media cap (test with a temporary low cap).
- Rendered videos pass QC: 16:9 ≤ 120 s, 9:16 ≤ 55 s, captions, audio, CTA card.
- FinOps: media actual spend ≤ $120; cumulative ≤ $200.
````

## Your role in P7
1. Pick one portrait per avatar.
2. Swap or upload images for any weak properties.
3. Watch the free previews.
4. Approve the plans you like, in batches, while keeping an eye on the remaining-budget counter.
