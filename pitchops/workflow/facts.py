"""P6 property fact sheets (pure helpers).

Corpus facts: a value counts only when >= 2 independent channels state it (prices are labelled "as reported by
brokers, unverified"). Official facts: Gemini extracts field + exact quote from official page text; a fact is kept only
if its quote really appears in that text (grounding check)."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from html.parser import HTMLParser
from typing import Any

FIELDS = ["developer", "project", "location", "type", "bedrooms", "size", "starting price", "payment plan",
          "handover", "amenities", "golden-visa eligibility"]
PRICE = re.compile(r"(?:aed|dhs?|\$|usd|€|eur|£)\s?[\d.,]+\s?(?:k|m|mn|million|bn)?"
                   r"|[\d.,]+\s?(?:k|m|mn|million)\s?(?:aed|dhs)", re.I)
PLAN = re.compile(r"\b\d{1,2}\s?/\s?\d{1,2}\b|\b\d(?:\.\d+)?\s?%\s?(?:monthly|per month|a month)|post[- ]handover",
                  re.I)
SINGLE = ("developer", "location", "starting price")


def fact_id(property_id: str, field: str, value: str) -> str:
    return "f_" + hashlib.sha1(f"{property_id}|{field}|{value.lower()}".encode()).hexdigest()[:12]


def norm_price(text: str) -> str | None:
    m = PRICE.search(text or "")
    if not m:
        return None
    s = m.group(0).upper().replace("DHS", "AED").replace("DH", "AED").replace(" ", "")
    s = re.sub(r"MILLION|MN", "M", s)
    m2 = re.fullmatch(r"([\d.,]+[KMB]?)(AED)", s)
    return f"AED{m2.group(1)}" if m2 else s


def norm_plan(text: str) -> str | None:
    m = PLAN.search(text or "")
    return re.sub(r"\s+", "", m.group(0).lower()) if m else None


def corpus_facts(property_id: str, mentions: list[dict[str, Any]], claims: list[dict[str, Any]],
                 effective: str) -> list[dict[str, Any]]:
    """mentions: {video_id, channel_id, developer, area, emirate, property_type, price_text};
    claims: {video_id, channel_id, claim_type, quote} from deep analyses of videos mentioning only this property."""
    votes: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: {"ch": set(), "v": set()})

    def vote(field: str, value: str | None, m: dict[str, Any]) -> None:
        if value and str(value).strip() and str(value).lower() not in ("unknown", "none", "null"):
            k = (field, str(value).strip())
            votes[k]["ch"].add(m["channel_id"])
            votes[k]["v"].add(m["video_id"])

    for m in mentions:
        vote("developer", m.get("developer"), m)
        loc = ", ".join(x for x in (m.get("area"), m.get("emirate")) if x)
        vote("location", loc or None, m)
        vote("type", m.get("property_type") if m.get("property_type") not in ("mixed", "unknown") else None, m)
        vote("starting price", norm_price(m.get("price_text") or ""), m)
    for c in claims:
        if c.get("claim_type") == "payment_plan":
            vote("payment plan", norm_plan(c.get("quote") or ""), c)
        if c.get("claim_type") == "price":
            vote("starting price", norm_price(c.get("quote") or ""), c)
    out: list[dict[str, Any]] = []
    best: dict[str, tuple[int, str]] = {}
    for (field, value), s in votes.items():
        n = len(s["ch"])
        if n < 2:
            continue
        if field in SINGLE and best.get(field, (0, ""))[0] >= n:
            continue  # one value per identity / price field: the most-corroborated
        if field in SINGLE:
            out = [f for f in out if f["field"] != field]
            best[field] = (n, value)
        out.append({"fact_id": fact_id(property_id, field, value), "property_id": property_id, "field": field,
                    "value": value, "quote": None, "source_type": "corpus", "source_url": None,
                    "video_ids": sorted(s["v"])[:8], "channel_count": n, "effective_date": effective,
                    "expires_at": None, "confidence": round(min(1.0, 0.4 + 0.15 * n), 2),
                    "note": "as reported by brokers, unverified" if field in ("starting price", "payment plan") else
                    f"stated by {n} channels"})
    return out


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript", "svg") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def html_text(html: str) -> tuple[str, list[str]]:
    p = _Text()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.parts))[:20000], p.links


def _squash(s: str) -> str:
    return re.sub(r"[^a-z0-9%/]+", "", s.lower())


def grounded(quote: str, text: str) -> bool:
    q = _squash(quote)
    return len(q) >= 4 and q in _squash(text)


def extraction_schema() -> dict[str, Any]:
    return {"type": "object", "required": ["facts"], "properties": {"facts": {"type": "array", "maxItems": 15, "items": {
        "type": "object", "required": ["field", "value", "quote"], "properties": {
            "field": {"type": "string", "enum": FIELDS}, "value": {"type": "string", "maxLength": 160},
            "quote": {"type": "string", "maxLength": 240}}}}}}
