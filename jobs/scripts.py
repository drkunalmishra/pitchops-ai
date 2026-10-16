"""P6 step 2 — bounded script agent: plan ~100 scripts, generate, check, store (Firestore `scripts`).

Plan (D20): top-20 projects x their top-3 buyer personas (generic 30-45 s) + one script per media property in its
format (16:9 walkthrough <= 120 s | 9:16 Short <= 55 s), de-duplicated on (property, persona, format).
Per script the workflow calls a fixed tool set — get_property_facts, get_persona_insights, get_top_hooks,
get_buyer_questions_and_objections, (generate), check_compliance, estimate_duration, (one repair) — max 8 calls.
Idempotent per (property_id, persona, format, prompt_version): existing script ids are skipped.
Usage:
  uv run python -m jobs.scripts --estimate
  uv run python -m jobs.scripts [--limit N] [--concurrency 2]
  uv run python -m jobs.scripts --seed-demo     # adds the "guaranteed 12% returns" compliance demo draft
"""

from __future__ import annotations

import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from typing import Any

from pitchops.bq import query
from pitchops.config import get_settings
from pitchops.gemini.budget import BudgetExhausted
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.logs import log
from pitchops.workflow import compliance
from pitchops.workflow import scripts as S

JOB = "p6_scripts"
P6_CAP = 5.0
TOP_PROJECTS = 20
EST_IN, EST_OUT = 6000, 1400
MEDIA_FORMAT = {"walkthrough": "walkthrough_16x9", "short": "short_9x16"}


def t(name: str) -> str:
    return get_settings().table(name)


def best_links() -> dict[str, dict[str, Any]]:
    """buyer base code -> best-rated link (seller framework + format) with confidence >= 0.4."""
    rows = query(f"""SELECT l.link_id, l.seller_persona_id, l.buyer_persona_id, l.presenter_persona_id, r.score
        FROM `{t('persona_links')}` l JOIN `{t('persona_ratings')}` r ON r.entity_type = 'link'
          AND r.entity_id = l.link_id AND r.persona_db_version = l.persona_db_version
        WHERE l.persona_db_version = (SELECT MAX(persona_db_version) FROM `{t('personas')}`)
          AND r.confidence >= 0.4 AND r.score IS NOT NULL ORDER BY r.score DESC""")
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        base = r["buyer_persona_id"].split(":", 1)[1].split("|")[0]
        out.setdefault(base, r)
    return out


# 10-persona series: one video per seller persona, each on a property with good official images (owner request)
SERIES = [  # (seller persona, property_id, format, avatar) — avatars proven with Veo first
    ("lifestyle", "prop_greenz", "short_9x16", "avatar_sa"),
    ("education_led", "prop_sobha_central", "walkthrough_16x9", "avatar_eu"),
    ("status_luxury", "prop_bugatti_residences", "walkthrough_16x9", "avatar_ru"),
    ("developer_authority", "prop_sobha_sanctuary", "walkthrough_16x9", "avatar_af"),
    ("financial", "prop_tilal_binghatti", "short_9x16", "avatar_ea"),
    ("authority", "prop_heights_country_club_and_wellness", "walkthrough_16x9", "avatar_me"),
    ("fomo_scarcity", "prop_bayn", "short_9x16", "avatar_na"),
    ("payment_plan_ease", "prop_grand_polo_club_and_resort", "short_9x16", "avatar_sa"),
    ("risk_reduction", "prop_one_za_abeel", "short_9x16", "avatar_ea"),
    ("social_proof", "prop_mercedes_benz_places", "walkthrough_16x9", "avatar_ru"),
]


def plan_series() -> list[dict[str, Any]]:
    props = {p["property_id"]: p for p in query(f"""SELECT property_id, canonical_name, rank, kind, media_candidate,
        top_buyer_personas, example_video_ids FROM `{t('properties_ranked')}`
        WHERE property_id IN UNNEST(@ids)""", {"ids": [x[1] for x in SERIES]})}
    briefs = {r["entity_id"]: r for r in query(f"""SELECT entity_id, name, description FROM `{t('persona_texts')}`
        WHERE entity_type = 'persona' AND STARTS_WITH(entity_id, 'seller:')""")}
    links = best_links()
    items = []
    for seller, pid, fmt, avatar in SERIES:
        p = props[pid]
        buyer = next((b for b in (p["top_buyer_personas"] or []) if b in links and b != "agent_industry"),
                     next(iter(links)))
        b = briefs.get(f"seller:{seller}") or {}
        items.append({"property": p, "buyer": buyer, "format": fmt, "link": links.get(buyer), "avatar": avatar,
                      "seller": f"seller:{seller}", "series": "persona10",
                      "seller_brief": f"{b.get('name', seller)} — {b.get('description', '')} Make this pitch style "
                                      "unmistakable in the hook, the narration and the CTA.",
                      "script_id": S.script_id(pid, f"{buyer}|{seller}", fmt)})
    return items


def plan() -> list[dict[str, Any]]:
    props = query(f"""SELECT property_id, canonical_name, rank, kind, media_candidate, top_buyer_personas,
            example_video_ids FROM `{t('properties_ranked')}`
        WHERE media_candidate IS NOT NULL OR kind = 'project' ORDER BY rank""")
    links = best_links()
    items: dict[tuple[str, str, str], dict[str, Any]] = {}
    projects = [p for p in props if p["kind"] == "project"][:TOP_PROJECTS]
    for p in projects:
        personas = [b for b in (p["top_buyer_personas"] or []) if b in links and b != "agent_industry"][:3]
        for b in personas:
            items[(p["property_id"], b, "generic")] = {"property": p, "buyer": b, "format": "generic"}
    for p in props:
        if p["media_candidate"]:
            b = next((b for b in (p["top_buyer_personas"] or []) if b in links and b != "agent_industry"), None)
            b = b or next(iter(links))
            items[(p["property_id"], b, MEDIA_FORMAT[p["media_candidate"]])] = {
                "property": p, "buyer": b, "format": MEDIA_FORMAT[p["media_candidate"]]}
    for it in items.values():
        it["link"] = links.get(it["buyer"])
        it["script_id"] = S.script_id(it["property"]["property_id"], it["buyer"], it["format"])
    return list(items.values())


# ---- tools (fixed set) -----------------------------------------------------------------------------------------------
def get_property_facts(property_id: str) -> dict[str, dict[str, Any]]:
    return {r["fact_id"]: r for r in query(f"""SELECT fact_id, field, value, source_type, note,
            CAST(expires_at AS STRING) expires_at FROM `{t('property_facts')}` WHERE property_id = @p""",
                                         {"p": property_id})}


def get_persona_insights(link: dict[str, Any], buyer: str, seller: str | None = None) -> list[dict[str, Any]]:
    ids = [seller or link["seller_persona_id"], link["presenter_persona_id"]] if link else ([seller] if seller else [])
    rows = query(f"""SELECT entity_id, name, description, texts FROM `{t('persona_texts')}`
        WHERE entity_type = 'persona' AND (entity_id IN UNNEST(@ids) OR STARTS_WITH(entity_id, @b))""",
                 {"ids": ids, "b": f"buyer:{buyer}|"})
    pats = []
    for r in rows:
        tx = r["texts"] or {}
        pats.append({"pattern_id": r["entity_id"], "name": r["name"], "description": r["description"],
                     "what_works": [w["text"] for w in tx.get("what_works", [])],
                     "avoid": [w["text"] for w in tx.get("what_to_avoid", [])]})
    if link:
        pats.append({"pattern_id": link["link_id"], "name": "best-rated combination", "description":
                     f"{link['seller_persona_id']} x {link['buyer_persona_id']} x {link['presenter_persona_id']}"})
    return pats


def get_top_hooks(property_videos: list[str]) -> list[dict[str, Any]]:
    ids = list(property_videos or [])[:12]
    return query(f"""SELECT a.video_id, a.hook_type, JSON_VALUE(a.overview, '$.hook_text') hook,
            JSON_VALUE(a.overview, '$.cta_text') cta, a.segments, a.claims
        FROM `{t('video_analysis')}` a WHERE a.status = 'succeeded' AND a.video_id IN UNNEST(@ids)""", {"ids": ids})


def get_buyer_questions_and_objections(property_videos: list[str]) -> list[str]:
    rows = query(f"""SELECT question, objection_topic FROM `{t('comment_classifications')}`
        WHERE video_id IN UNNEST(@ids) AND (question IS NOT NULL OR objection_topic IS NOT NULL) LIMIT 40""",
                 {"ids": list(property_videos or [])})
    qs = Counter(r["question"] or f"objection: {r['objection_topic']}" for r in rows)
    return [q for q, _ in qs.most_common(8)]


def snippets(hooks: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for h in hooks:
        out += [h.get("hook") or "", h.get("cta") or ""]
        out += [s.get("on_screen_text") or "" for s in (h.get("segments") or [])]
        out += [s.get("summary") or "" for s in (h.get("segments") or [])]
        out += [c.get("quote") or "" for c in (h.get("claims") or [])]
    return [x for x in out if x]


def avatar_for(buyer: str, insights: list[dict[str, Any]], i: int) -> str:
    return S.ORIGIN_AVATAR.get(buyer) or list(S.AVATARS)[i % len(S.AVATARS)]


def generate(g: Any, it: dict[str, Any], i: int) -> dict[str, Any]:
    s = get_settings()
    p, link, trace = it["property"], it["link"], []
    facts = get_property_facts(p["property_id"])
    trace.append("get_property_facts")
    insights = get_persona_insights(link, it["buyer"], it.get("seller"))
    trace.append("get_persona_insights")
    hooks = get_top_hooks(p["example_video_ids"])
    trace.append("get_top_hooks")
    questions = get_buyer_questions_and_objections(p["example_video_ids"])
    trace.append("get_buyer_questions_and_objections")
    avatar = it.get("avatar") or avatar_for(it["buyer"], insights, i)
    srcs = snippets(hooks)
    ctx = {"format": it["format"], "property_name": p["canonical_name"], "buyer": it["buyer"],
           "seller": it.get("seller_brief") or (link["seller_persona_id"] if link else "education_led"),
           "avatar_label": S.AVATARS[avatar],
           "facts": [{"fact_id": k, "field": v["field"], "value": v["value"], "note": v["note"]} for k, v in facts.items()],
           "patterns": insights, "questions": questions, "snippets": [x[:200] for x in srcs]}
    pids = {x["pattern_id"] for x in insights}
    fixes: list[dict[str, Any]] | None = None
    draft: dict[str, Any] = {}
    check: dict[str, Any] = {}
    for _attempt in (1, 2):  # draft + at most one repair (tool calls stay <= 8)
        res = g.generate_json(s.gemini_model_flash, [S.prompt(ctx, fixes)], S.schema(), prompt_version=S.PROMPT_VERSION,
                              temperature=0.6, system=S.SYSTEM, thinking="low",
                              validator=lambda d: S.validate(d, set(facts), pids))
        trace.append("generate" if not fixes else "repair")
        draft = {**res.data, "permit": S.PERMIT, "ai_disclosure": True,
                 "similarity_to_sources": S.similarity(res.data, srcs)}
        check = compliance.check(draft, facts, today=date.today(), max_similarity=S.SIM_MAX)
        trace.append("check_compliance")
        if check["status"] != "BLOCK":
            break
        fixes = [f for f in check["findings"] if f["severity"] == "BLOCK"]
    draft["duration_est"] = S.duration(draft)
    trace.append("estimate_duration")
    now = datetime.now(UTC).isoformat()
    return {"script_id": it["script_id"], "property_id": p["property_id"], "property_name": p["canonical_name"],
            "buyer_persona": it["buyer"], "persona_link_id": link["link_id"] if link else None,
            "seller_framework": it.get("seller") or ctx["seller"], "format": it["format"], "avatar_id": avatar,
            "series": it.get("series"),
            "status": "draft", "compliance_status": check["status"], "version": 1, "prompt_version": S.PROMPT_VERSION,
            "model_id": s.gemini_model_flash, "tool_trace": trace, "created_at": now, "updated_at": now,
            "current": {**draft, "compliance": check, "content_hash": S.content_hash(draft)}}


def store(rows: list[dict[str, Any]]) -> None:
    from pitchops.fs import client as fs

    db = fs()
    for r in rows:
        ref = db.collection("scripts").document(r["script_id"])
        ref.set(r)
        ref.collection("versions").document("1").set({**r["current"], "version": 1, "by": "agent", "at": r["created_at"]})


DEMO = {"title": "Guaranteed returns? (compliance demo)", "angle": "Intentional bad draft for the compliance demo",
        "hook": "Want guaranteed 12% returns in Dubai?", "avatar_intro_line": "Hi, I'm your PitchOps Demo Realty advisor.",
        "narration": [{"text": "This project gives guaranteed 12% returns every year, completely risk-free.",
                       "fact_ids": [], "pattern_ids": [], "visual_suggestion": "Skyline at sunset"}],
        "avatar_outro_line": "Message PitchOps Demo Realty today.", "cta": "WhatsApp PitchOps Demo Realty.",
        "on_screen_facts": [], "missing_facts": [], "permit": S.PERMIT, "ai_disclosure": True,
        "similarity_to_sources": 0.0}


def seed_demo(it: dict[str, Any]) -> dict[str, Any]:
    facts = get_property_facts(it["property"]["property_id"])
    check = compliance.check(DEMO, facts)
    now = datetime.now(UTC).isoformat()
    sid = "s_demo_guaranteed_returns"
    prop = it["property"]
    return {"script_id": sid, "property_id": prop["property_id"], "property_name": prop["canonical_name"],
            "buyer_persona": it["buyer"], "persona_link_id": None, "seller_framework": "fomo_scarcity",
            "format": "generic", "avatar_id": "avatar_na", "status": "draft", "compliance_status": check["status"],
            "version": 1, "prompt_version": "demo", "model_id": "manual", "tool_trace": ["seed_demo"],
            "created_at": now, "updated_at": now, "demo_case": True,
            "current": {**DEMO, "duration_est": S.duration(DEMO), "compliance": check, "content_hash": S.content_hash(DEMO)}}


def recheck() -> dict[str, Any]:
    """Re-apply the current deterministic rules to every script's current version (keeps Gemini explanations out)."""
    from pitchops.fs import client as fs

    out: Counter[str] = Counter()
    facts_cache: dict[str, dict[str, Any]] = {}
    for d in fs().collection("scripts").stream():
        doc = d.to_dict()
        pid = doc["property_id"]
        facts = facts_cache.setdefault(pid, get_property_facts(pid))
        cur = doc["current"]
        res = compliance.check(cur, facts, today=date.today(), max_similarity=S.SIM_MAX)
        out[res["status"]] += 1
        if res["status"] != cur.get("compliance", {}).get("status") or res["findings"] != cur["compliance"]["findings"]:
            cur["compliance"] = res
            upd = {"current": cur, "compliance_status": res["status"]}
            if doc.get("status") == "approved" and res["status"] == "BLOCK":
                upd["status"] = "draft"  # an approval never survives a new BLOCK
            d.reference.update(upd)
            out["changed"] += 1
    return dict(out)


def main(argv: list[str] | None = None) -> int:
    p = base_parser("scripts")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--seed-demo", action="store_true")
    p.add_argument("--recheck", action="store_true", help="re-run deterministic compliance on all scripts (no LLM)")
    p.add_argument("--series", action="store_true", help="the 10-persona series (one script per seller persona)")
    a = p.parse_args(argv)
    if a.recheck:
        print(recheck())
        return 0
    s = get_settings()
    items = plan_series() if a.series else plan()
    from pitchops.fs import client as fs

    existing = {d.id for d in fs().collection("scripts").select([]).stream()}
    todo = [it for it in items if it["script_id"] not in existing]
    todo = todo[: a.limit] if a.limit else todo
    if a.seed_demo:
        store([seed_demo(items[0])])
        print({"seeded": "s_demo_guaranteed_returns"})
        return 0
    if a.estimate or a.dry_run:
        pin, pout = s.price_for(s.gemini_model_flash)
        n_props = len({i["property"]["property_id"] for i in items})
        print({"planned": len(items), "to_generate": len(todo), "properties": n_props,
               "buyer_personas": len({i["buyer"] for i in items}), "formats": dict(Counter(i["format"] for i in items)),
               "est_usd_with_30pct_repairs": round(len(todo) * (EST_IN * pin + EST_OUT * pout) / 1e6 * 1.3, 2)})
        return 0
    from pitchops.gemini.client import GeminiClient

    run_id = a.run_id or new_run_id("scripts")
    g = GeminiClient(JOB, run_id, phase_prefix="p6_", phase_cap=P6_CAP)
    out: list[dict[str, Any]] = []
    with job_run("scripts", run_id) as c:
        failed = 0
        with ThreadPoolExecutor(a.concurrency) as pool:
            futs = {pool.submit(generate, g, it, i): it["script_id"] for i, it in enumerate(todo)}
            for f in as_completed(futs):
                try:
                    out.append(f.result())
                    if len(out) % 10 == 0:
                        store(out[-10:])
                except BudgetExhausted as e:
                    c["_status"] = "BUDGET_EXHAUSTED"
                    log("BUDGET_EXHAUSTED", severity="WARNING", detail=str(e))
                    break
                except Exception as e:  # noqa: BLE001 — one failure must not stop the batch
                    failed += 1
                    log("script_failed", severity="WARNING", script_id=futs[f], error=f"{type(e).__name__}: {e}"[:300])
        store(out[len(out) - len(out) % 10:])
        c.update(planned=len(items), generated=len(out), failed=failed,
                 compliance=dict(Counter(r["compliance_status"] for r in out)))
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
