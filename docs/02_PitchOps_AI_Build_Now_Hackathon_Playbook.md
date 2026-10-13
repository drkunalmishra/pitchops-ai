<!-- Converted from the corresponding PDF blueprint. Content, section order, tables, formulas, checklists and source references are preserved for editing. -->

# PITCHOPS AI - BUILD NOW | AI BUILDER CUP 2026 HACKATHON MVP DELIVERY PLAYBOOK

| Field | Value |
| --- | --- |
| Purpose | Translate the future-product vision into a fresh, Google Cloud deployed, end-to-end hackathon prototype with the strongest possible three-minute demonstration. |
| Build window | 06 October to 18 October 2026. Team formation closes 11 October; prototype submission closes 18 October [S2]. |
| Selected theme | Future of Work and Enterprise Productivity [S1]. |
| MVP user | UAE real-estate broker/marketing manager creating a compliant multilingual pitch for one property and buyer persona. |
| Hero flow | YouTube/upload analysis -> explainable content patterns -> verified property brief -> grounded script variants -> UAE compliance correction -> human approval -> channel-ready video preview. |
| Deployment rule | Working prototype on Google Cloud using Gemini/Gemma or approved agentic platform and deployed through Cloud Run/ GCP/Firebase [S1][S2]. |
| Submission rule | Deployed link, public GitHub repository, under-three-minute demo video and detailed deck [S2]. |
| Scope discipline | P0 capabilities only must work reliably. P1 improves judging strength. P2 is demonstrable architecture/future roadmap, not code required for submission. |

> **Winning thesis.** prove that a brokerage can move from scattered market content and property facts to an evidence-linked, compliance-reviewed sales video in minutes - without copying a creator or pretending public engagement equals conversion.

> **Immediate gate.** Confirm team eligibility and composition before 11 October. Because the rules exclude students, obtain written organizer confirmation for any participant enrolled in an executive/part-time DBA/FPM before relying on that person as an eligible team member [S2].

## 1. COMPETITION ALIGNMENT AND DESIGN TARGET

| Judging criterion | Weight | What the prototype must visibly prove |
| --- | --- | --- |
| Technical Merit and GenAI Implementation | 40% | Real Gemini multimodal video analysis; structured evidence; grounded generation; deterministic scoring/checks; deployed asynchronous flow; reliable end-to-end state and error handling. |
| Problem Alignment and Impact | 25% | Specific brokerage workflow, measured baseline, faster completion, fewer manual tools, cited property facts and pre-publication compliance checks. |
| Innovation and Creativity | 25% | Pattern-not-person learning, evidence-linked content generation, identity-safe media and closed-loop product path rather than a generic avatar/video tool. |
| User Experience and Solution Design | 10% | Simple wizard, visual timeline/pattern cards, editable script, clear pass/warn/block states, progress, approval and polished output. |

The official challenge asks for a functional prototype, meaningful Google AI use and Cloud Run/Firebase deployment; a mockup or deck alone is insufficient [S1][S2].

### 1.1 MVP success statement

A judge can open the deployed application, use a prepared demo account, analyze a sample video or load a precomputed analysis, select a UAE property and persona, generate three scripts, see evidence and compliance findings, approve one script and obtain a playable 9:16 video or robust preview - all within the demo flow.

## 2. SCOPE LOCK: P0, P1 AND DEFERRED

| Priority | Capability | Definition |
| --- | --- | --- |
| P0 | Authentication and project workspace | Simple Firebase Auth/demo login; create/select campaign; persistent job status. |
| P0 | Video input | One public YouTube URL or one uploaded MP4; provide preloaded samples to avoid live-source risk. |
| P0 | Gemini multimodal analysis | Timestamped transcript/scene summary, hook, value proposition, evidence, objection, CTA, pace/tone and risk claims in validated JSON [S3]. |
| P0 | Explainable scoring | Observed Performance Index from available metadata plus Content Effectiveness Score with evidence; never label as conversion probability. |
| P0 | Property campaign brief | Structured facts plus optional brochure upload; buyer persona, language, objective, CTA and mandatory permit/QR fields. |
| P0 | Grounded script variants | Three 30-45 second scripts linked line-by-line to facts/patterns; duration estimate and similarity check. |
| P0 | UAE compliance check | Pass/warn/block for missing evidence, guarantee/ROI language, permit/QR and required property/developer fields; reviewer remediation. |
| P0 | Human approval | Edit, resolve findings and approve immutable script version before rendering. |
| P0 | Media output | At minimum: synthetic/stock voice + property images + captions + brand/permit/QR overlays assembled as MP4. Avatar is optional adapter. |
| P0 | Evidence and audit | Show source timestamps, fact citations, model/prompt version, approval and job trace. |
| P1 | English and Arabic variants | Generate both; judges may see side-by-side script and one rendered language. |
| P1 | Comment intent | Analyze a small supplied comment set for information-seeking/buying-intent cues. |
| P1 | Veo B-roll or licensed avatar | One short optional visual enhancement with reliable fallback [S11]. |
| P1 | Evaluation dashboard | Show schema pass, citations, compliance, latency/cost and user time saved. |
| P2/Defer | Seven social connectors, auto-publishing, CRM attribution, custom model training, multi-agent platform, production multi-tenancy, predictive conversion model and public-person cloning. | Describe as future architecture only; do not risk the working P0. |

## 3. HERO USER AND DEMO SCENARIO

| Element | Demo definition |
| --- | --- |
| Persona | A marketing manager at a Dubai brokerage supporting multiple brokers. |
| Task | Create a 35-second video pitch for an off-plan one-bedroom apartment aimed at an Indian professional seeking a UAE investment. |
| Inputs | Three prepared public/authorized sample videos; property fact sheet/brochure; brand guidance; mock/valid-format permit number and Madmoun QR asset; English/Arabic target. |
| Pain baseline | Research, transcription, scripting, validation, localization, approval and media assembly require multiple tools and roughly 90-120 minutes in the demonstrative baseline. |
| AI outcome | The application identifies evidence-backed patterns, generates grounded scripts, catches an unsupported guarantee and missing permit/QR item, then creates an approved video preview. |
| Impact claim | For the prototype test, compare completion time and defects against the manual baseline. State results as measured demo findings or targets, not broad production guarantees. |

### 3.1 Three-minute narrative

- Problem: one slide/sentence - fragmented knowledge and slow, risky content production.
- Analyze: show timestamps and extracted patterns from an actual video.
- Decide: select a pattern based on explainable scores and audience fit.
- Create: generate three grounded scripts from verified property facts.
- Trust: show a risky guaranteed-return claim blocked and permit/QR omission identified.
- Execute: approve and play a polished 9:16 output.
- Impact: show elapsed time, facts cited, issues caught and future CRM learning loop.

## 4. MVP END-TO-END WORKFLOW AND ACCEPTANCE

| Step | User action | System behavior | Acceptance test |
| --- | --- | --- | --- |
| 1 | Start campaign. Sign in; select New Campaign. | Create tenant/user/campaign context and default status DRAFT. | Campaign persists after refresh; unauthorized users cannot access it. |
| 2 | Add source. Paste YouTube URL or upload MP4; optionally enter public metrics. | Validate source, create hash, store metadata/object, enqueue ANALYZE. | Invalid source produces actionable error; duplicate content reuses analysis. |
| 3 | Analyze. Wait on progress screen or load prepared result. | Gemini extracts structured fields with timestamps; validator stores analysis or retry/error [S3]. | JSON schema passes; at least hook, proposition, CTA and two evidence timestamps are present. |
| 4 | Compare patterns. Select up to three analyzed videos. | Calculate OPI and CES; render pattern cards and limitations. | Score components are visible; missing metrics reduce confidence; no conversion claim. |
| 5 | Build brief. Choose property, persona, language, goal, tone and CTA. | Extract/validate facts; require key fields and evidence source. | Every mandatory field has value or explicit unknown; unsupported fact cannot be silently added. |
| 6 | Generate scripts. Click Generate Variants. | Retrieve selected patterns/facts/policy; create three scripts and line mappings. | Each factual line has fact_id; word count fits 30-45 seconds; similarity below threshold. |
| 7 | Review compliance. Open findings and apply suggested fix. | Rules plus Gemini explanation mark pass/warn/block; rerun after edit. | Guaranteed-return phrase blocks; missing permit/QR warns or blocks per demo policy. |
| 8 | Approve. Reviewer confirms final script. | Freeze version, reviewer, time, policy and fact set. | Render endpoint rejects unapproved or blocked version. |
| 9 | Render. Choose voice/template and Generate Video. | Create TTS, scene images/slides, captions and overlays; async compose MP4. | Playable 9:16 MP4/preview, correct text, disclosure and QR; fallback path works. |
| 10 | Results. Open impact summary. | Show elapsed time, source/fact coverage, findings, scores and future outcome loop. | Metrics are reproducible from stored run and clearly labeled measured/estimated. |

## 5. BUILD-NOW ARCHITECTURE

| 1. User experience | 2. API and workflow | 3. AI/analytics | 4. Data/media | 5. Operations |
| --- | --- | --- | --- | --- |
| React/Next.js web on Firebase Hosting; Firebase Auth; campaign wizard; analysis cards; script editor; compliance desk; video preview. | Cloud Run API; Firestore workflow state; Cloud Tasks for async analysis/render; optional Cloud Run Job for FFmpeg; strict state transitions and idempotency [S4][S5]. | Vertex AI Gemini multimodal extraction and script generation; Python scoring; rule engine; similarity check; optional TTS/ Veo/avatar adapter [S3][S10] [S11]. | Cloud Storage for uploads, documents, audio and MP4; Firestore collections for campaign, source, analysis, facts, scripts, checks, jobs and audit. | Secret Manager; IAM service accounts; Logging/Monitoring; budget alert; GitHub Actions/Cloud Build; public repo with no secrets. |

```text
Browser
  -> Firebase Hosting / Firebase Auth
  -> Cloud Run API
      -> Firestore workflow status
      -> Cloud Tasks -> Analysis Worker -> Gemini -> Validated Analysis
      -> Scoring and Pattern Selection
      -> Fact Extraction -> Script Generation -> Rules/Compliance -> Approval
      -> Render Task/Job -> TTS/Assets/FFmpeg -> Cloud Storage MP4
      -> Short-lived Signed Playback URL

Every step writes correlation_id, campaign_id, state, timestamps,
model/config version and error details.
```

### 5.1 State machine

```text
DRAFT
  -> SOURCE_READY
  -> ANALYZING
  -> ANALYZED
  -> BRIEF_READY
  -> GENERATING
  -> REVIEW_REQUIRED
  -> APPROVED
  -> RENDERING
  -> COMPLETE

Failure states:
ANALYSIS_FAILED | GENERATION_FAILED | COMPLIANCE_BLOCKED | RENDER_FAILED
```

Only explicit endpoints may transition state. Retrying a job uses the same idempotency key and must not create duplicate versions or media.

## 6. SERVICE AND COMPONENT BREAKDOWN

| Component | Responsibility | Build choice |
| --- | --- | --- |
| Web app | Wizard, tables/cards, editing, polling/realtime status and playback. | Next.js/React + Firebase SDK; prioritize desktop responsive layout. |
| API/BFF | Auth verification, tenant/campaign context, validation, CRUD, task enqueue and signed URLs. | Python FastAPI or Node/TypeScript on Cloud Run; choose team-strength stack. |
| Analysis worker | Fetch permitted media reference, call Gemini, validate schema and persist output. | Private Cloud Run service invoked through Cloud Tasks [S4]. |
| Scoring service | Compute public-signal and content-rubric scores deterministically. | Python module in API/worker; pure functions and unit tests. |
| Knowledge/fact service | Parse property brief/brochure, normalize facts, source and effective date. | Structured form first; Gemini document extraction is P1 convenience. |
| Generation service | Create strategies/scripts with fact/pattern links and duration. | Gemini structured output; low temperature; prompt and schema versioned. |
| Compliance service | Run deterministic rules, then use Gemini for explanation/rewrite. | Rules remain source of pass/warn/block; model cannot silently downgrade severity. |
| Approval service | Freeze script/facts/policy and capture reviewer. | API transaction/update with immutable approved_version reference. |
| Media worker | Generate voice, captions, visual sequence and MP4. | TTS plus FFmpeg; optional provider adapter; Cloud Run Job if task exceeds request timeout [S5][S10]. |
| Evaluation/telemetry | Log quality, latency, token/cost estimate and test outcomes. | Structured logs and Firestore evaluation result; simple dashboard. |

## 7. FIRESTORE, STORAGE AND EVENT MODEL

| Collection/document | Key fields |
| --- | --- |
| users/{userId} | display_name, email, roles, tenant_id, eligibility_note, created_at. |
| tenants/{tenantId} | name, market=UAE, brand, plan=hackathon, allowed_languages, settings. |
| campaigns/{campaignId} | tenant_id, owner_id, title, persona, objective, channel, language, state, selected_source_ids, selected_script_id, created_at, updated_at. |
| sources/{sourceId} | campaign_id, type, url/object_uri, platform, hash, rights_basis, metrics, status, error. |
| analyses/{analysisId} | source_id, schema_version, model_id, prompt_version, transcript, scenes, features, claims, evidence, confidence, created_at. |
| properties/{propertyId} | campaign_id, name, developer, project, location, price, currency, specifications, approved_claims, permit_no, qr_uri, facts[], source_uri. |
| patterns/{patternId} | campaign_id, type, statement, source_evidence[], OPI_component, CES_component, confidence, selected. |
| scripts/{scriptId} | campaign_id, version, language, delivery_style, lines[], fact_links[], pattern_links[], word_count, duration_sec, similarity, status. |
| compliance/{checkId} | script_id, policy_version, findings[], overall_status, checked_at, reviewer_id, resolution. |
| approvals/{approvalId} | campaign_id, script_id, approved_hash, reviewer_id, decision, timestamp, note. |
| jobs/{jobId} | type, campaign_id, state, attempt, progress, idempotency_key, correlation_id, started_at, ended_at, error_code. |
| media/{mediaId} | campaign_id, script_id, type, object_uri, mime, duration, checksum, renderer, consent/disclosure, status. |
| audit/{eventId} | campaign_id, user/service, action, object_type/id, version, timestamp, correlation_id, metadata. |

### 7.1 Storage layout

```text
gs://<bucket>/<tenant_id>/campaigns/<campaign_id>/sources/<source_id>/input.mp4
gs://<bucket>/<tenant_id>/campaigns/<campaign_id>/documents/property_brief.pdf
gs://<bucket>/<tenant_id>/campaigns/<campaign_id>/renders/<render_id>/voice.wav
gs://<bucket>/<tenant_id>/campaigns/<campaign_id>/renders/<render_id>/captions.srt
gs://<bucket>/<tenant_id>/campaigns/<campaign_id>/renders/<render_id>/output_9x16.mp4
```

Use short-lived signed URLs; the bucket is not public.

### 7.2 Minimal event envelope

```json
{
  "event_id": "uuid",
  "event_type": "analysis.requested",
  "schema_version": "1.0",
  "tenant_id": "t_demo",
  "campaign_id": "c_001",
  "object_id": "s_001",
  "idempotency_key": "analysis:s_001:v1",
  "correlation_id": "uuid",
  "actor": {
    "type": "user|service",
    "id": "..."
  },
  "occurred_at": "ISO-8601",
  "payload": {
    "analysis_schema": "video-analysis-1.0",
    "prompt_version": "p1"
  }
}
```

## 8. API CONTRACT

| Method/path | Purpose | Validation/result |
| --- | --- | --- |
| POST /v1/campaigns | Create campaign. | Authenticated tenant; return campaign and DRAFT state. |
| GET /v1/campaigns/{id} | Load complete workflow summary. | Tenant check; aggregate references, not large media payloads. |
| POST /v1/campaigns/{id}/sources | Register YouTube URL/upload metadata. | URL/type/rights required; dedupe hash; return source. |
| POST /v1/sources/{id}:analyze | Enqueue analysis. | Allowed source; idempotency key; return job_id/status URL. |
| GET /v1/jobs/{id} | Poll progress/error. | Tenant check; percent and user-safe message. |
| POST /v1/campaigns/{id}/brief | Save property/persona brief. | Required fact fields, source and permit/QR state. |
| POST /v1/campaigns/{id}/scripts:generate | Generate three variants. | ANALYZED + BRIEF_READY; selected pattern IDs; enqueue or synchronous bounded call. |
| PATCH /v1/scripts/{id} | Edit script. | Create new version; never overwrite approved version. |
| POST /v1/scripts/{id}:check | Run compliance. | Return finding IDs, severity, evidence, remediation and overall status. |
| POST /v1/scripts/{id}:approve | Approve final version. | Reviewer role; no unresolved block; store hash and policy/ fact versions. |
| POST /v1/scripts/{id}:render | Enqueue media render. | Approved hash matches; consent/disclosure/template fields; return job. |
| GET /v1/media/{id} | Return metadata and signed playback URL. | Tenant check; short expiry. |
| GET /healthz /readyz | Deployment health/readiness. | No secret/data disclosure; dependency readiness separated. |

## 9. GEMINI VIDEO ANALYSIS PROMPT AND OUTPUT SCHEMA

### 9.1 System instruction

You are a multimodal sales-content analyst. Analyze only observable evidence in the supplied video/audio and metadata. Return JSON that exactly matches the schema. Every substantive observation must include one or more timestamps. Distinguish spoken claim, on-screen claim, inferred strategy and unknown. Do not infer lead conversion, private intent or creator identity. Flag unsupported numerical, investment-return or guarantee language.

### 9.2 Required JSON shape

```json
{
  "schema_version": "video-analysis-1.0",
  "language": "en",
  "duration_sec": 38.2,
  "summary": "...",
  "transcript_segments": [
    {"start": 0.0, "end": 4.2, "text": "..."}
  ],
  "scenes": [
    {"start": 0.0, "end": 5.0, "visual": "...", "overlay_text": "..."}
  ],
  "content_structure": {
    "hook": {
      "type": "question|problem|claim|story|visual",
      "text": "...",
      "evidence": [{"start": 0.0, "end": 4.2}]
    },
    "audience_problem": {"text": "...", "evidence": []},
    "value_proposition": {"text": "...", "evidence": []},
    "proof_points": [
      {"statement": "...", "kind": "fact|testimonial|demo|social-proof", "evidence": []}
    ],
    "objections": [
      {"objection": "...", "response": "...", "evidence": []}
    ],
    "cta": {"action": "...", "destination": "...", "evidence": []}
  },
  "delivery": {
    "tone": ["consultative"],
    "estimated_wpm": 145,
    "pace": "medium",
    "energy": "medium"
  },
  "claims": [
    {
      "text": "...",
      "claim_type": "numeric|guarantee|comparison|other",
      "evidence": [],
      "risk": "low|medium|high"
    }
  ],
  "reusable_patterns": [
    {
      "name": "problem-first hook",
      "description": "...",
      "evidence": [],
      "confidence": 0.82
    }
  ],
  "limitations": ["No first-party retention data supplied"]
}
```

### 9.3 Validation rules

- Reject invalid JSON or unexpected top-level fields; retry once with validation error, then store failed state.
- duration_sec must be positive; timestamps must be ordered and within duration; confidence is 0-1.
- Hook, value proposition and CTA are required, but may be explicit unknown with reason.
- Every pattern/claim must have timestamp evidence or be labeled derived_from_metadata.
- No output field named conversion_probability is permitted.
- Store raw model response separately from normalized object for debugging; never display hidden/system prompts.

## 10. SCORING ENGINE

### 10.1 Observed Performance Index

Inputs when available: views V, likes L, comments C, age_days A, creator_median_views M, intent_comments I, total_sampled_comments T. Feature values: f1=log(1+V/max(A,1)); f2=(L+4*C)/max(V,1); f3=log(1+V/max(M,1)); f4=I/max(T,1). Within the selected comparison cohort compute robust N(f) using P10/P90; OPI=100*(0.35*N(f1)+0.25*N(f2)+0.25*N(f3)+0.15*N(f4)). Missing feature: remove its weight, renormalize remaining weights, and set confidence = available_weight * sample_quality.

### 10.2 Content Effectiveness Score

| Dimension | Points | MVP rule |
| --- | --- | --- |
| Hook | 15 | Gemini rubric with timestamp; clear in first seconds. |
| Persona/problem relevance | 15 | Explicit problem/audience signal. |
| Value proposition | 10 | Specific and understandable. |
| Evidence/trust | 15 | Proof is present and not obviously unsupported. |
| Pacing/density | 10 | WPM and scene density in acceptable range; reason shown. |
| Objection handling | 10 | Meaningful concern addressed. |
| CTA | 10 | Clear action and destination. |
| Originality/brand fit | 10 | Not too similar; compatible with selected style. |
| Compliance readiness | 5 | No obvious block and mandatory elements considered. |

Campaign Readiness Score (display only after brief) = 0.30*selected-pattern OPI + 0.45*generated-script CES + 0.25*GroundingComplianceScore. GroundingComplianceScore = fact_coverage_percent * compliance_multiplier, where multiplier is 1.0 PASS, 0.75 WARNING, 0.0 BLOCK. Label all scores as prototype decision support, not predicted leads or guaranteed performance.

## 11. PROPERTY FACTS AND GROUNDING

| Required field | Validation |
| --- | --- |
| Property/project name | Required; exact approved spelling. |
| Developer | Required for the demo; source cited. |
| Location | Required; avoid unverified distance/time claims. |
| Property type/bedrooms/area | Structured value and unit; source cited. |
| Price/currency | Optional if unavailable; effective date required when used. |
| Payment plan | Only approved schedule; source and effective date. |
| Completion/handover | Only approved date/status; source cited. |
| Amenities/features | Each claim from brochure/fact form. |
| Expected return/ROI | Do not accept as guaranteed; require approved evidence and disclaimer or omit. |
| Permit number | Required field for demo compliance scenario or explicit missing status. |
| Madmoun QR | Upload asset or explicit missing; DLD states QR verification requirement for real-estate advertisements [S8]. |
| CTA/contact | Demo contact/WhatsApp/URL; no real personal data required. |

### 11.1 Script generation instruction

Use only supplied fact records for factual claims. Each factual sentence must contain fact_ids. You may create persuasive transitions, questions and calls to action, but they cannot introduce new property facts. Generate exactly three 30-45 second variants: Educational, Consultative and Energetic. Return line-level duration estimate, selected pattern_ids, fact_ids, visual suggestion and compliance-sensitive phrases. If a requested claim lacks evidence, omit it and add a missing_fact question.

## 12. COMPLIANCE ENGINE

### 12.1 MVP rules

| Rule ID | Severity | Condition | Remediation |
| --- | --- | --- | --- |
| UAE-FACT-001 | BLOCK | A numerical/property claim has no approved fact_id. | Remove or link to verified source. |
| UAE-CLAIM-002 | BLOCK | Contains guaranteed return, guaranteed appreciation, risk-free or equivalent phrasing. | Rewrite as non-guaranteed positioning and recommend independent evaluation. |
| UAE-PERMIT-003 | WARN/BLOCK | Permit number missing for content marked ready to publish. | Provide valid permit metadata or keep as internal draft. |
| UAE-QR-004 | WARN/BLOCK | Madmoun QR asset missing for a Dubai advertisement output. | Upload QR or block publish-ready export [S8]. |
| UAE-PROJECT-005 | WARN | Developer/project/location fields missing. | Complete approved property brief. |
| UAE-EXPIRY-006 | BLOCK | Price, offer, permit or document is past effective date. | Refresh source and regenerate. |
| RIGHTS-007 | BLOCK | Presenter/voice/source media lacks required rights/consent status. | Use approved synthetic/stock/owned asset. |
| ORIGINALITY-008 | WARN/BLOCK | Generated text similarity exceeds threshold against source transcript. | Regenerate structure/wording; retain only abstract pattern. |
| DISCLOSURE-009 | WARN | AI-generated presenter disclosure absent when template policy requires it. | Insert disclosure overlay/caption. |
| CTA-010 | WARN | CTA lacks destination or contact. | Add approved CTA target. |

### 12.2 Execution order

1. Run deterministic string, field, date and fact-link rules.
2. Use Gemini to classify nuanced risky wording and explain why; it cannot lower deterministic severity.
3. Show the reviewer the exact line, rule, official-policy/source note, suggested rewrite and status.
4. After editing, rerun all rules. Approval is allowed only when no unresolved `BLOCK` remains.

Legal note. The MVP policy pack is a prototype decision aid based on official DLD information and team-defined rules. It is not a substitute for legal advice or live permit verification. Label this clearly in the UI and deck.

## 13. MEDIA GENERATION AND FALLBACK LADDER

| Level | Implementation | Use |
| --- | --- | --- |
| Primary reliable path | Cloud TTS voice -> selected property images/gradient slides -> animated pan/zoom -> captions -> brand title -> permit/QR/disclosure -> FFmpeg 9:16 MP4. | Must work without third-party avatar or Veo access. Cloud TTS supports synthetic speech from text/SSML [S10]. |
| Enhancement | Licensed avatar API behind RENDERER_PROVIDER interface. | Use only when API access, rights and latency are proven; retain primary fallback. |
| Google enhancement | One short Veo-generated B-roll clip inserted into composition. | Optional showpiece; Veo produces short clips and may have quota/region constraints [S11]. |
| Emergency fallback | Pre-rendered template visuals with newly generated script, voice and captions. | Still demonstrates AI analysis, grounding, compliance and execution if media provider fails. |

### 13.1 Render pipeline

```text
approved script JSON -> SSML with pauses/emphasis -> TTS WAV/MP3 -> line timing -> choose 5-7 scenes -> render 1080x1920 images -> overlay captions and factual callouts -> insert QR/disclosure -> FFmpeg compose -> probe duration/codec -> store MP4 -> signed URL.
```

- Do not render every variant. Render only an approved script; use low-resolution draft before final.
- Avoid a real public person face/voice. Use licensed/stock/clearly synthetic presenter or property-visual video.
- Validate QR readability, caption boundaries, duration, audio presence and aspect ratio automatically.
- Store renderer/provider, input script hash, asset list and disclosure in media metadata.

## 14. USER INTERFACE SCREENS

| Screen | Required UI and demo behavior |
| --- | --- |
| 1. Landing/login | One-sentence value, theme, demo login and privacy note. Keep sign-in friction minimal. |
| 2. Campaign setup | Property/persona/language/objective fields; sample campaign button. |
| 3. Source input | YouTube URL/upload, rights checkbox, optional metrics; prepared samples. |
| 4. Analysis progress | Step/status, progress, retry and load-precomputed option. |
| 5. Intelligence comparison | Video cards, timeline evidence, OPI/CES breakdown, limitations and Select Pattern. |
| 6. Property knowledge | Facts with source/status, permit and QR, missing items and brochure/form input. |
| 7. Script studio | Three columns/tabs, line-to-fact/pattern chips, duration, edit/regenerate section and similarity. |
| 8. Compliance desk | Pass/warn/block summary, issue line, explanation, suggested fix, apply and rerun. |
| 9. Approval/render | Reviewer identity, approve button, renderer/template, progress and fallback status. |
| 10. Result/impact | Playable vertical video, download/export, time saved, facts cited, issues caught and future closed-loop diagram. |

UX rule: The judge should always know what the system is doing, why a recommendation exists, what source supports it, whether an action is safe and what to do next.

## 15. REPOSITORY AND ENGINEERING STRUCTURE

```text
pitchops-ai/
├── README.md                 # Setup, architecture, demo, limitations and screenshots
├── LICENSE / NOTICE          # Chosen license and third-party notices
├── docs/                     # Architecture, API, data schema, evaluation, responsible AI
├── web/                      # Next.js/React application
├── api/                      # FastAPI/Node API, auth, campaign and approval endpoints
├── workers/
│   ├── analysis/             # Gemini video analysis and schema validation
│   └── render/               # TTS, captions, FFmpeg and provider adapters
├── packages/
│   ├── domain/               # Types, schemas and state machine
│   ├── scoring/              # Deterministic scoring and tests
│   └── compliance/           # Rules, policy metadata and tests
├── prompts/                  # Versioned system/task prompts and JSON schemas
├── evals/                    # Golden examples and regression runner
├── infra/                    # Terraform or deploy scripts; no credentials
├── scripts/                  # Seed data, QR placeholder and local run
├── .github/workflows/        # Test/build/deploy with workload identity
└── .env.example              # Variable names only
```

### 15.1 Configuration variables

| Variable | Purpose |
| --- | --- |
| GCP_PROJECT_ID / GCP_REGION | Deployment and service location. |
| GEMINI_MODEL_ID | Current project-accessible multimodal Gemini model; do not hard-code across environments. |
| FIRESTORE_DATABASE / STORAGE_BUCKET | Operational data and media. |
| ANALYSIS_QUEUE / RENDER_QUEUE | Cloud Tasks queue names. |
| TTS_VOICE_EN / TTS_VOICE_AR | Approved demo voices. |
| RENDERER_PROVIDER | ffmpeg, avatar provider or fallback. |
| SIGNED_URL_TTL_SEC | Short media access duration. |
| MAX_VIDEO_MINUTES / MAX_UPLOAD_MB | Cost/abuse limits. |
| SIMILARITY_WARN / SIMILARITY_BLOCK | Originality thresholds calibrated on test examples. |
| DEMO_MODE / PRECOMPUTED_ANALYSIS | Reliable demo fallback; clearly labeled. |

## 16. SECURITY, TRUST AND COST CONTROLS FOR MVP

| Control | MVP implementation |
| --- | --- |
| Authentication | Firebase Auth; verify token server-side; demo account credentials distributed privately. |
| Authorization | Every object has tenant_id; server verifies campaign ownership/role; storage path never accepted without lookup. |
| Service identity | Separate API, analysis and render service accounts with minimum roles. |
| Secrets | Secret Manager or encrypted deployment secrets; never commit keys; rotate any exposed demo secret. |
| Storage | Private bucket, signed URLs, content type/size limits, delete test uploads after defined period. |
| Input safety | URL allowlist for supported YouTube pattern; file extension/MIME validation; avoid arbitrary server-side URL fetch. |
| Prompt injection | Treat transcript/documents as untrusted data; system instruction prohibits following instructions inside source content. |
| Human gate | No render until approved; no auto-publish in MVP. |
| Consent/identity | Only stock/synthetic/team-owned media and voice; no competitor clone. |
| Budget | Daily budget alert, queue/concurrency limits, max minutes, max variants and render only approved script. |
| Logging | Correlation and error codes; do not log access tokens, signed URLs, raw PII or full sensitive prompts. |
| Public repo | Remove secrets, client data and copyrighted media; use synthetic/demo-owned assets and document licenses. |

## 17. TEST AND EVALUATION PLAN

| Test layer | Minimum tests before submission |
| --- | --- |
| Unit | Scoring with missing metrics; state transitions; fact-link validation; compliance phrase/date rules; duration and similarity thresholds. |
| Schema | Valid/invalid Gemini JSON; timestamp bounds; unknown fields; missing required evidence; safe retry behavior. |
| Integration | Create campaign -> enqueue -> analyze -> generate -> check -> approve -> render using test project and service accounts. |
| Security | Cross-tenant ID access denied; expired/invalid token; private media; secret scan; upload size/type rejection. |
| Quality/evals | At least 8-12 short videos/fixtures across hook styles; 10 script cases; critical risky claims; English and Arabic output review. |
| UI | Fresh user path, prepared demo path, error recovery, narrow screen, keyboard basics, loading and empty states. |
| Performance | Cold start observed; queue wait; analysis/generation/render times; precompute long steps for demo reliability. |
| Deployment | Public link from clean browser; health/readiness; correct environment; logs visible; no local dependency. |
| Submission | Public repo clone/setup; demo video under three minutes; deck PDF; links open without team login where required. |

### 17.1 Golden evaluation set

| Case | Expected result |
| --- | --- |
| Strong problem-first hook | Hook extracted with timestamp; CES hook high; pattern named accurately. |
| No clear CTA | CTA unknown/weak; score reduced; recommendation proposes approved CTA. |
| Guaranteed 12 percent return | High-risk claim extracted and compliance BLOCK. |
| Missing permit/QR | Publish-readiness warning/block and exact remediation. |
| Conflicting price in brochure/form | Conflict surfaced; generation blocked from choosing silently. |
| Unsupported distance claim | No fact link; script check blocks/removes. |
| Copied source wording | Similarity warning/block and regenerated wording. |
| Arabic variant | Meaning and factual values preserved; review flag if uncertain. |
| Model/API failure | Job retries once; visible error; prepared result can continue demo. |
| Render provider failure | Fallback FFmpeg video path completes. |

## 18. DAY-BY-DAY DELIVERY PLAN: 06-18 OCTOBER 2026

| Date | Primary outcome | Detailed tasks and exit gate |
| --- | --- | --- |
| Tue 06 Oct | Scope/eligibility/architecture freeze | Confirm team and eligibility query; create fresh public/private development repo with initial commit; choose stack; define hero story, P0/P1/P2, data rights, ADRs, schemas and task board. Exit: no unresolved scope ambiguity. |
| Wed 07 Oct | Cloud foundation and UX shell | Create GCP project, budgets, APIs, service accounts, Firestore, bucket, Firebase Hosting/Auth, Cloud Run hello service and CI. Build campaign wizard shell. Exit: deployed authenticated page and API health. |
| Thu 08 Oct | Source ingestion | YouTube URL/upload, rights field, source record, object storage, hash/dedupe, sample media and error states. Exit: source persists and worker can read permitted input. |
| Fri 09 Oct | Gemini analysis | Implement prompt/schema, worker, Cloud Tasks, validator, retry, evidence timeline and prepared output. Exit: two sample videos reliably produce valid analysis. |
| Sat 10 Oct | Scoring and comparison | Metadata entry/API, OPI/CES engine, pattern cards, limitations and tests. Exit: transparent comparison with no conversion language. |
| Sun 11 Oct | Team formation deadline and property knowledge | Finalize team registration; property form/brochure path, fact model, source links, permit/QR. Exit: complete demo property and validated fact set. |
| Mon 12 Oct | Script generation | Three variants, line-level fact/pattern links, word/duration, edit/version and similarity. Exit: grounded output and invalid fact test blocked. |
| Tue 13 Oct | Compliance and approval | Rules, risky claim detection, suggestions, rerun, immutable approval. Exit: guaranteed-return demo visibly blocked and fixed. |
| Wed 14 Oct | Reliable media path | TTS, images/slides, captions, QR/disclosure and FFmpeg job; signed playback. Exit: 9:16 MP4 generated from approved script. |
| Thu 15 Oct | P1 polish | Arabic variant, comment intent or one B-roll/avatar enhancement; impact dashboard; empty/error/ loading states. Exit: P0 remains stable after P1. |
| Fri 16 Oct | Integration, security and evaluation | End-to-end tests, cross-tenant check, secret scan, cost limits, golden eval, bug burn-down, freeze model/prompt/policy versions. Exit: release candidate. |
| Sat 17 Oct | Submission assets | Record multiple demo takes; create final under-three-minute video, deck PDF, README, architecture, responsible-AI notes, licenses, screenshots and public links. Exit: independent reviewer can follow links. |
| Sun 18 Oct | Final verification and submit | Clean-browser run, link/permission checks, GitHub tag, deployed version, backup demo video, submission form and timestamped evidence. Submit with buffer; do not make risky feature changes. |

## 19. TEAM PLAN FOR 2-4 MEMBERS

| Workstream | Primary owner | Secondary/backup | Deliverables |
| --- | --- | --- | --- |
| Product/architecture/pitch | Product lead/architect | UX or AI lead | Problem framing, scope, architecture, compliance story, deck and demo narration. |
| Full-stack/GCP | Cloud/full-stack engineer | AI engineer | Firebase/web, Cloud Run API, Firestore/ storage, tasks, auth, deployment and CI. |
| AI/data/evaluation | GenAI/data engineer | Architect | Prompts/schemas, Gemini integration, scoring, grounding, compliance and evals. |
| UX/media/demo | Frontend/design/media engineer | Full-stack engineer | UI polish, render pipeline, assets, captions, video recording and submission quality. |

Two-person configuration: Person A owns product/architecture/AI/evaluation; Person B owns full-stack/GCP/UX/media. Three-person: split AI/data from product/pitch. Four-person: use the four workstreams above. One person owns final integration and release authority.

## 20. THREE-MINUTE DEMO SCRIPT

| Time | On screen | Narration objective |
| --- | --- | --- |
| 0:00-0:15 | Problem visual and workflow baseline. | Real-estate teams spend time across videos, brochures and compliance checks; content quality is inconsistent and disconnected from evidence. |
| 0:15-0:30 | Landing and new campaign. | PitchOps AI is an enterprise sales-content workspace under Future of Work, not a generic avatar generator. |
| 0:30-0:58 | Prepared video analysis with timeline. | Gemini understands audio and visuals, extracts hook, proof, objection and CTA, and cites exact timestamps. |
| 0:58-1:18 | Comparison/pattern cards. | Scores are explainable. Public engagement is an observed signal, not falsely presented as lead conversion. |
| 1:18-1:38 | Property facts and persona. | The campaign uses verified property facts, target buyer, language and UAE permit/QR requirements. |
| 1:38-2:00 | Three script variants and evidence chips. | Generation combines selected patterns with approved facts; every factual line is traceable. |
| 2:00-2:22 | Compliance block and one-click correction. | The system catches a guaranteed-return claim and missing requirement before publication; a reviewer remains accountable. |
| 2:22-2:42 | Approve, render and play output. | After approval, the workflow creates a vertical, multilingual-ready pitch with captions, disclosure and QR. |
| 2:42-2:55 | Impact dashboard. | Show measured prototype time, facts cited, issues caught and fewer manual steps. |
| 2:55-3:00 | Future closed loop. | Owned campaign and CRM outcomes will continuously improve the organizational playbook across industries and markets. |

Record the final video at 2:45-2:55 to preserve upload/player margin. Never depend on a long live model/render call during the recorded demo; show one short live action and use precomputed, clearly authentic project results for the rest.

## 21. PITCH DECK OUTLINE

| Slide | Content |
| --- | --- |
| 1 | Title, one-line pitch, theme and hero outcome. |
| 2 | Specific UAE brokerage workflow problem and quantified baseline. |
| 3 | Why current point tools fail: fragmented research, ungrounded generation, weak compliance and no outcome loop. |
| 4 | Solution and six-step hero journey. |
| 5 | Live product screenshots/flow. |
| 6 | Meaningful Gemini use: multimodal extraction, grounded reasoning and multilingual generation. |
| 7 | Explainable analytics: OPI/CES and why not conversion probability. |
| 8 | Compliance-by-design and identity-safe synthesis. |
| 9 | Google Cloud architecture and data flow. |
| 10 | Prototype results: time, quality, citations, findings, latency/cost. |
| 11 | Future product: first-party CRM loop, multi-tenant platform, other industries/languages. |
| 12 | Business model, team and ask/closing. |

## 22. SUBMISSION AND RELEASE CHECKLIST

| Area | Checklist |
| --- | --- |
| Eligibility/team | [ ] 2-4 eligible JAPAC working-professional members. [ ] Team finalized by 11 Oct. [ ] Written clarification retained for any DBA/ FPM ambiguity. |
| Fresh project | [ ] Repository history starts in hackathon period. [ ] No reused proprietary client/product code. [ ] Third-party libraries/assets documented. |
| Deployed app | [ ] Public link opens. [ ] Demo credentials work. [ ] Cloud Run/Firebase/GCP visibly used. [ ] Health and core flow pass. |
| Google AI | [ ] Gemini call is real and material. [ ] Model/config documented. [ ] Structured output and evidence visible. |
| Source/data rights | [ ] Public/authorized/synthetic inputs. [ ] No copyrighted download committed. [ ] Avatar/voice/media rights documented. |
| Security | [ ] Secrets removed. [ ] GitHub secret scan. [ ] Bucket private. [ ] Cross-tenant check. [ ] Quotas/budget alert. |
| GitHub | [ ] Public repo. [ ] README quick start, architecture, demo, limitations, responsible AI, license and screenshots. [ ] Release tag/commit recorded. |
| Video | [ ] Under 3 minutes. [ ] Public YouTube/Vimeo/Drive link. [ ] Captions. [ ] Clear problem, product, AI, architecture and impact. |
| Deck | [ ] PDF. [ ] Theme stated. [ ] Feasibility and scalability. [ ] Architecture. [ ] results. [ ] citations/limitations. |
| Final form | [ ] All URLs permission-tested in incognito. [ ] Contact details correct. [ ] Submit before deadline with buffer. [ ] Save confirmation. |

## 23. RISK REGISTER AND FALLBACKS

| Risk | Early signal | Fallback/mitigation |
| --- | --- | --- |
| Gemini video URL/access failure | Source rejected or slow. | Use uploaded owned clip or Cloud Storage object; retain precomputed analysis tied to same input. |
| Model returns malformed JSON | Validation fails. | One repair retry; strict fallback fixture; show job error rather than invent output. |
| Video analysis latency | Demo exceeds flow time. | Analyze before demo; live-show only a short request or cached result with run metadata. |
| Avatar/Veo unavailable | Quota/region/provider error. | Primary TTS + images + captions + FFmpeg output remains the committed P0. |
| Arabic quality weak | Reviewer finds awkward text. | Show English render and Arabic script as P1; label human localization review required. |
| Compliance accuracy disputed | Rule interpretation uncertain. | Use narrowly scoped prototype rules, cite official sources, label legal-review boundary and avoid claiming certification. |
| Public metrics missing | Like/comment counts unavailable. | Allow manual CSV/demo data; renormalize weights; lower confidence. |
| UI unfinished | Core flow hidden behind raw JSON. | Prioritize five polished hero screens and hide/defer admin/P2. |
| Cost/quota exhaustion | Budget alert/429. | Max minutes/variants, cached results, low-cost model, queue limits and disable optional media. |
| Submission link permissions | Incognito access fails. | Final-day independent check; backup video and static screenshots/ README. |
| Eligibility uncertainty | No organizer response. | Do not ignore; keep written query/evidence and align team composition to confirmed rule interpretation. |

## 24. DEFINITION OF DONE

- Functional: one complete campaign can move from source to playable approved output in the deployed application.
- AI depth: Gemini materially analyzes multimodal content and generates grounded variants; the prototype would be meaningfully worse without it.
- Trust: evidence timestamps, fact links, limitations, compliance findings, human approval and identity-safe media are visible.
- Technical: Cloud Run/Firebase/GCP deployment, private storage, async status, retry/error, structured logs and fresh public repository are working.
- Impact: the team reports measured prototype cycle time, facts cited, issues detected and manual steps removed using a reproducible test.
- Demo: final recording is under three minutes, coherent, captioned, and does not depend on an unreliable long-running live request.
- Submission: deployed link, public GitHub, demo video and deck PDF are accessible and permission-tested.
- Honesty: no unsupported conversion claim, no unauthorized scrape/clone, no production-certification claim and no hidden use of client-confidential data.

## 25. OFFICIAL SOURCES

The following official sources support the competition constraints, Google Cloud implementation choices and UAE compliance context. Service availability, quota and terms must be checked in the team project before finalizing the demo.

| Ref. | Official source |
| --- | --- |
| S1 | [AI Builder Cup 2026 - Themes, build requirements and judging criteria](https://aibuildercup.com/themes.html) |
| S2 | [AI Builder Cup 2026 - FAQs, prototype, Google Cloud, fresh-project and submission requirements](https://aibuildercup.com/Faqs.html) |
| S3 | [Google Cloud - Gemini video understanding, including video with audio and supported sources](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/video-understanding) |
| S4 | [Google Cloud - Cloud Tasks with Cloud Run for authenticated asynchronous processing](https://docs.cloud.google.com/run/docs/triggering/using-tasks) |
| S5 | [Google Cloud - Cloud Run Jobs for run-to-completion background tasks](https://docs.cloud.google.com/run/docs/create-jobs) |
| S6 | [Google Developers - YouTube Data API video metadata and public statistics](https://developers.google.com/youtube/v3/docs/videos) |
| S7 | [Google Developers - YouTube Analytics metrics including watch time and audience retention](https://developers.google.com/youtube/analytics/metrics) |
| S8 | [Dubai Land Department - Madmoun QR code for real-estate advertisement verification](https://dubailand.gov.ae/en/news-media/dubai-land-department-provides-madmoun-service-to-verify-validity-of-real-estate-ads-via-qr-codes/) |
| S9 | [Dubai Land Department - Real Estate Ad Permit service](https://dubailand.gov.ae/en/eservices/real-estate-ad-permit/) |
| S10 | [Google Cloud - Cloud Text-to-Speech documentation](https://docs.cloud.google.com/text-to-speech/docs) |
| S11 | [Google Cloud - Veo 3.1 model capabilities and technical specifications](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate) |

## 26. JUDGE Q&A - PREPARED ANSWERS

| Likely question | Concise answer |
| --- | --- |
| Why is this Future of Work rather than only media generation? | The core product reorganizes how sales teams access knowledge, compare evidence, make content decisions, collaborate on approval and execute governed work. Video is the final artifact, not the product boundary. |
| Why is Gemini essential? | Gemini performs multimodal understanding of speech, visuals, overlays and structure, then supports grounded multilingual generation. Deterministic code handles scores, state and policy so the AI is meaningful but controlled. |
| Can public engagement predict leads? | No. We explicitly separate observed performance and content quality from conversion. True propensity is deferred until consented first-party campaign and CRM labels exist. |
| Are you copying competitors or creating deepfakes? | No. We abstract transferable patterns and block excessive textual similarity. The demo uses synthetic, licensed or team-owned identity assets and requires consent/rights metadata. |
| How do you know the compliance result is correct? | The prototype uses narrow versioned rules tied to official DLD context and surfaces evidence, severity and human review. It is decision support, not legal certification or live permit verification. |
| What happens when model or media generation fails? | Every long step is asynchronous and retryable. We keep validated prepared results and a TTS-plus-FFmpeg renderer so the end-to-end product still works without an optional avatar or Veo call. |
| How does this scale beyond UAE real estate? | The workflow, schemas, controls, evaluation and renderer adapters are reusable. Property facts, personas, languages, compliance rules and connectors are controlled domain/market packs. |
| What is the measurable business value? | The prototype measures brief-to-approved-asset time, manual handoffs, facts cited, compliance issues caught, first-pass approval and AI/media cost; future CRM events add qualified-pipeline outcomes. |

## 27. FINAL 30-MINUTE SUBMISSION RUNBOOK

| Time | Action | Stop/go condition |
| --- | --- | --- |
| T-30 | Freeze deployment and GitHub main; tag release; record deployed revision, model, prompt and policy versions. | No new feature merge; critical rollback only. |
| T-20 | Run the prepared campaign in incognito and open app, GitHub, deck and demo video from an independent account. | Core flow works without local credentials; every required link opens. |
| T-10 | Check video length/captions/audio/claims, deck theme/results/limits, secret scan, private storage and asset notices. | Under three minutes; no unsupported claim, secret, client data or unauthorized media. |
| T-05 | Complete form, verify team/theme, paste links from source and capture final screenshots. | All mandatory fields complete and match registration. |
| T-00 | Submit; save confirmation/timestamp; avoid post-submit artifact changes unless permitted. | Confirmation retained by at least two members. |
