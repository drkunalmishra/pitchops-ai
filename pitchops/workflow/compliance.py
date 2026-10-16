"""P6 compliance engine — deterministic UAE rules (playbook §12). Pure functions; Gemini may only explain findings and
suggest rewrites, never lower a severity. Prototype decision aid, not legal advice.

Script shape (subset used here): {hook, avatar_intro_line, narration: [{text, fact_ids, pattern_ids}],
avatar_outro_line, cta, on_screen_facts: [{text, fact_ids}]} + facts {fact_id: {field, value, effective_date,
expires_at, source_type}}.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

POLICY_VERSION = "uae-demo-2026-10"
DEMO_PERMIT = "DEMO-PERMIT"

GUARANTEE = re.compile(
    r"\b(guarantee[ds]?|guaranteed|assured|risk[- ]?free|no[- ]risk|zero[- ]risk|can'?t lose|cannot lose|"
    r"certain(?:ly)? (?:returns?|profit|appreciation)|fixed returns?|promised returns?|100% safe|sure[- ]shot)\b", re.I)
NUMBER = re.compile(r"(?:aed|usd|eur|€|\$|£)\s?\d|\d[\d,.]*\s?(?:%|percent|aed|sq\.? ?ft|sqft|m²|bed(?:room)?s?|"
                    r"million|mn|k\b|years?|months?)|\b20\d\d\b|\bq[1-4]\b", re.I)
NUMBER_WORDS = re.compile(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|"
                          r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|half)[- ]?"
                          r"(?:\w+[- ])?(?:percent|per cent|dirhams?|aed|million|billion|thousand|bedrooms?|years?|"
                          r"months?|square)\b", re.I)
CONTACT = re.compile(r"whatsapp|call|book|visit|contact|register|dm\b|message|link|pitchops demo realty", re.I)


def _lines(script: dict[str, Any]) -> list[tuple[str, str, list[str]]]:
    """(line_ref, text, fact_ids) for every spoken / on-screen line."""
    out: list[tuple[str, str, list[str]]] = []
    for k in ("hook", "avatar_intro_line", "avatar_outro_line", "cta"):
        if script.get(k):
            v = script[k]
            text, fids = (v.get("text", ""), v.get("fact_ids") or []) if isinstance(v, dict) else (str(v), [])
            out.append((k, text, fids))
    for i, n in enumerate(script.get("narration") or []):
        out.append((f"narration[{i}]", n.get("text", ""), n.get("fact_ids") or []))
    for i, f in enumerate(script.get("on_screen_facts") or []):
        out.append((f"on_screen_facts[{i}]", f.get("text", ""), f.get("fact_ids") or []))
    return out


def finding(rule: str, severity: str, line: str, text: str, why: str, fix: str) -> dict[str, Any]:
    return {"rule_id": rule, "severity": severity, "line": line, "text": text[:240], "why": why, "remediation": fix}


def check(script: dict[str, Any], facts: dict[str, dict[str, Any]], today: date | None = None,
          max_similarity: float = 0.35, publish_ready: bool = False) -> dict[str, Any]:
    today = today or date.today()
    fs: list[dict[str, Any]] = []
    for ref, text, fids in _lines(script):
        if GUARANTEE.search(text):
            fs.append(finding("UAE-CLAIM-002", "BLOCK", ref, text, "Guaranteed / risk-free return or appreciation wording.",
                              "Rewrite as non-guaranteed positioning and recommend independent evaluation."))
        unknown = [f for f in fids if f not in facts]
        if unknown:
            fs.append(finding("UAE-FACT-001", "BLOCK", ref, text, f"References unknown fact_ids {unknown[:3]}.",
                              "Link to an approved fact record or remove the claim."))
        elif (NUMBER.search(text) or NUMBER_WORDS.search(text)) and not fids:
            fs.append(finding("UAE-FACT-001", "BLOCK", ref, text, "Numerical / property claim without an approved fact_id.",
                              "Remove the number or link it to a verified fact."))
        for f in fids:
            fact = facts.get(f) or {}
            exp = fact.get("expires_at")
            if exp and str(exp) < today.isoformat():
                fs.append(finding("UAE-EXPIRY-006", "BLOCK", ref, text, f"Fact {f} expired on {exp}.",
                                  "Refresh the source and regenerate."))
    permit = (script.get("permit") or "").strip()
    if not permit:
        fs.append(finding("UAE-PERMIT-003", "BLOCK" if publish_ready else "WARN", "permit", "",
                          "No advertising permit number.", "Provide permit metadata or keep as internal draft."))
    elif permit == DEMO_PERMIT:
        fs.append(finding("UAE-PERMIT-003", "INFO", "permit", permit, "Demo permit placeholder accepted in demo mode.",
                          "Replace with a real DLD permit before any publication."))
    fields = {(facts.get(f) or {}).get("field") for _, _, fids in _lines(script) for f in fids}
    missing = [k for k in ("developer", "project", "location") if k not in fields]
    if missing:
        fs.append(finding("UAE-PROJECT-005", "WARN", "facts", "", f"Script cites no {', '.join(missing)} fact.",
                          "Complete the approved property brief."))
    sim = float(script.get("similarity_to_sources") or 0.0)
    if sim > max_similarity:
        fs.append(finding("ORIGINALITY-008", "BLOCK" if sim > 1.5 * max_similarity else "WARN", "script", "",
                          f"Similarity {sim:.2f} to source transcripts exceeds {max_similarity}.",
                          "Regenerate structure and wording; keep only the abstract pattern."))
    cta = script.get("cta")
    cta_text = cta.get("text", "") if isinstance(cta, dict) else str(cta or "")
    if not CONTACT.search(cta_text + " " + str(script.get("avatar_outro_line") or "")):
        fs.append(finding("CTA-010", "WARN", "cta", cta_text, "CTA has no destination or contact.",
                          "Add the approved CTA target (PitchOps Demo Realty contact)."))
    if not script.get("ai_disclosure", True):
        fs.append(finding("DISCLOSURE-009", "WARN", "script", "", "AI-generated presenter disclosure is off.",
                          "Insert the AI-presenter disclosure caption."))
    sev = {f["severity"] for f in fs}
    status = "BLOCK" if "BLOCK" in sev else "WARN" if "WARN" in sev else "PASS"
    return {"status": status, "policy_version": POLICY_VERSION, "findings": fs}
