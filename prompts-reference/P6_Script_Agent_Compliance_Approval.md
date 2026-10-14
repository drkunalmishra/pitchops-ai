# P6 — Script Agent → UAE Compliance → Human Approval

**When:** Fri 16 Oct · **Depends on:** P4 (personas + properties_ranked + property_sources) and P5 (app shell) · **Budget cap:** Gemini ≤ **$5**

**What this phase produces:**
- about 100 English scripts: top ~25 properties × 3–4 buyer-persona angles, plus one per media property, de-duplicated (D20)
- a compliance check on every script
- an approval desk in the web app

---

````text
You are building Phase P6 of PitchOps AI. Read CLAUDE.md (§11 D1–D21) and docs/02_PitchOps_AI_Build_Now_Hackathon_Playbook.md §§9–12 (grounding, scripts, compliance engine, approval). FinOps (D14) applies.

1. Property fact sheets (grounding)
   - For each selected property (top 25 by rank + the 40 media properties): build property_facts from (a) the official website pages in property_sources (fetch text only, robots.txt respected, ≤ 5 pages per site, store extracted facts not HTML) and (b) consistent claims across our deep analyses (only when ≥ 2 independent channels state the same fact).
   - Each fact: fact_id, field (developer, project, location, type, bedrooms, size, starting price, payment plan, handover, amenities, golden-visa eligibility), value, source_url or video_ids, source_type (official|corpus), effective_date, confidence.
   - Missing fields stay explicitly "unknown". Corpus-only prices are marked "as reported by brokers, unverified".

2. Script Agent (bounded agent — workflow-controlled, not autonomous)
   - Implement as a Python service with a fixed tool set and a max of 8 tool calls per script:
       get_property_facts(property_id), get_persona_insights(persona_link_id), get_top_hooks(persona_link_id), get_buyer_questions_and_objections(property_id|persona), check_compliance(script_draft), estimate_duration(script_draft)
   - Inputs: property_id, target buyer persona (+ motive/trigger), seller framework chosen from the Persona DB's best-rated links for that buyer persona, format (16:9 ≤ 120 s | 9:16 ≤ 55 s | generic 30–45 s), presenter avatar_id.
   - Output schema (versioned): title, angle, persona_link_id, hook (≤ 3 s), avatar_intro_line (≤ 18 words, spoken by avatar on camera), narration lines [{text, fact_ids[], pattern_ids[], visual_suggestion, est_sec}], avatar_outro_line + CTA (≤ 18 words), on_screen_facts[], duration_est, similarity_to_sources (must be < threshold), compliance status.
   - Rules: every factual sentence must reference fact_ids; persuasive lines may reference persona patterns (pattern_ids) but cannot introduce facts; never copy creator wording (similarity check vs transcripts of evidence videos); English only; brand "PitchOps Demo Realty"; permit text "DEMO-PERMIT".
   - Batch job generates the planned set (≈ 100), idempotent per (property_id, persona, format, prompt_version).

3. Compliance engine (playbook §12): deterministic rules UAE-FACT-001, UAE-CLAIM-002 (guaranteed return/appreciation/risk-free), UAE-PERMIT-003 (DEMO-PERMIT accepted in demo mode), UAE-PROJECT-005, UAE-EXPIRY-006, ORIGINALITY-008, CTA-010; Gemini explains and suggests rewrites but cannot lower severity. Pass/Warn/Block stored per script version.

4. Approval desk (web app)
   - Script Studio: list/filter scripts by property, persona, format, status; script view with line-level fact/pattern chips (click → source), duration, similarity, compliance findings; inline edit creates a new version; "Regenerate line"; "Run compliance"; Approve (blocked if any unresolved BLOCK) / Reject with note.
   - Approval freezes: script hash, fact set version, persona_db_version, policy version, reviewer uid, timestamp (Firestore approvals + audit).
   - Seed one intentional demo case: a draft containing "guaranteed 12% returns" that the engine blocks and the suggested fix resolves.

FinOps: estimate before batch generation (≈ 100 scripts × tokens), confirm, ledger, P6 cap $5.

ACCEPTANCE
- ≥ 90 scripts generated across ≥ 25 properties and ≥ 4 buyer personas; 40 media properties each have ≥ 1 script in the right format.
- 100% of factual lines carry fact_ids; 0 scripts above the similarity threshold.
- Guaranteed-return demo case blocked → fixed → approved, with audit trail.
- I can approve/reject from the website; approval record visible.
````
