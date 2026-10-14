"""Channel -> registry entity matcher (pure; no I/O). Every signal is stored for explainability.

Score: website_route | domain_match | brn_match -> 0.95, else 0.55*name + 0.25*dubai + 0.20*real_estate.
Decision: >= 0.80 auto_accept, 0.60-0.80 review, < 0.60 reject.
Precision guards (P2 addition): a name-only auto_accept also needs name_similarity >= 0.85; broker matches need
full-name similarity >= 0.90 on a name that is unique in the registry, or a BRN match; portals / aggregators /
news / developers are rejected unless a strong signal or a near-exact registry company name matches.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz, process

from pitchops.discovery.names import clean, company_names, title_segments

AUTO, REVIEW = 0.80, 0.60
NAME_ONLY_AUTO_MIN = 0.85
NAME_MIN = 0.70          # company-name matches below this are rejected outright
WEBSITE_WEAK_SCORE = 0.70  # website link without real-estate context or name evidence -> review
BROKER_MIN = 0.90

DOMAIN_RE = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9\-]{1,62}(?:\.[a-z0-9\-]{2,63})*\.(?:ae|com|net|org|co|"
                       r"io|uk|in|ru|me|realestate|properties|property|homes|estate|dubai))\b", re.I)
BRN_RE = re.compile(r"\b(?:BRN|Broker\s*(?:Registration)?\s*(?:No|Number)?)\s*[.:#\-]*\s*(?:No\.?\s*)?(\d{3,7})\b", re.I)
DUBAI_RE = re.compile(r"dubai|\buae\b|emirates|abu dhabi|دبي|الإمارات", re.I)
RE_RE = re.compile(r"real\s*estate|propert|apartment|villa|off[\s-]?plan|broker|realty|homes?\b|penthouse|townhouse|"
                   r"invest|rent|عقار|недвижимост", re.I)
BLOCK_RE = re.compile(r"\b(bayut|property\s*finder|propertyfinder|dubizzle|houza|property\s*monitor|gulf\s*news|"
                      r"khaleej\s*times|the\s*national|arabian\s*business|zawya|gulf\s*business|dubai\s*eye|"
                      r"emaar|damac|sobha|nakheel|meraas|aldar|azizi|danube|binghatti|ellington|omniyat|deyaar|"
                      r"news|tv\b|channel\s*\d|bloomberg|cnbc|bbc|reuters)\b", re.I)
FREEMAIL_RE = re.compile(r"^(gmail|yahoo|hotmail|outlook|live|icloud|aol|msn|youtube|google|instagram|facebook|"
                         r"linkedin|tiktok|twitter|x|wa|whatsapp|bit|linktr|t)\.", re.I)


@dataclass
class Registry:
    """In-memory registry index built once per run."""

    company_names: dict[str, list[str]]                 # company_id -> cleaned names
    domain_to_company: dict[str, str]                   # domain -> company_id
    broker_names: dict[str, str]                        # broker_number -> raw name_en
    broker_company: dict[str, str | None] = field(default_factory=dict)
    company_cores: dict[str, list[str]] = field(default_factory=dict)  # names minus legal suffixes only
    _choices: list[str] = field(default_factory=list, init=False)
    _owners: list[str] = field(default_factory=list, init=False)
    _bnames: list[str] = field(default_factory=list, init=False)
    _bnums: list[str] = field(default_factory=list, init=False)
    _bcount: Counter[str] = field(default_factory=Counter, init=False)

    def __post_init__(self) -> None:
        for cid, names in self.company_names.items():
            for n in names:
                self._choices.append(n)
                self._owners.append(cid)
        for num, name in self.broker_names.items():
            n = norm_person(name)
            if len(n.split()) >= 2:
                self._bnames.append(n)
                self._bnums.append(num)
                self._bcount[n] += 1

    @classmethod
    def from_rows(cls, companies: list[dict[str, Any]], brokers: list[dict[str, Any]]) -> Registry:
        dom: dict[str, str] = {}
        for c in sorted(companies, key=lambda r: -(r.get("broker_count") or 0)):
            for d in [c.get("primary_domain"), *(c.get("corporate_domains") or [])]:
                if d and not FREEMAIL_RE.match(d):
                    dom.setdefault(d.lower(), c["company_id"])
        return cls(company_names={c["company_id"]: company_names(c.get("office_names_en")) for c in companies},
                   domain_to_company=dom,
                   broker_names={b["broker_number"]: b.get("name_en") or "" for b in brokers},
                   broker_company={b["broker_number"]: b.get("company_id") for b in brokers},
                   company_cores={c["company_id"]: core_names(c.get("office_names_en")) for c in companies})

    def best_company(self, text: str) -> tuple[str | None, float]:
        q = clean(text)
        if not q or not self._choices:
            return None, 0.0
        hit = process.extractOne(q, self._choices, scorer=fuzz.token_sort_ratio)
        if not hit:
            return None, 0.0
        name, score, idx = hit
        return self._owners[idx], name_score(q, name, score)

    def distinctive(self, company_id: str | None, title: str) -> bool:
        """Multi-word / long cleaned names are distinctive. One-word names ("classic", "driven") only count when
        the title contains the company's trading name ("Driven Properties"), not just the bare word."""
        cid = company_id or ""
        if any(len(n.split()) >= 2 or len(n) >= 8 for n in self.company_names.get(cid, [])):
            return True
        t = re.sub(r"[^\w\s&]", " ", title.lower())
        return any(fuzz.token_set_ratio(core, t) >= 90 for core in self.company_cores.get(cid, []))

    def company_similarity(self, company_id: str, text: str) -> float:
        q = clean(text)
        return max((name_score(q, n, fuzz.token_sort_ratio(q, n)) for n in self.company_names.get(company_id, [])),
                   default=0.0)

    def best_broker(self, text: str) -> tuple[str | None, float]:
        q = norm_person(text)
        if len(q.split()) < 2 or not self._bnames:
            return None, 0.0
        hit = process.extractOne(q, self._bnames, scorer=fuzz.token_sort_ratio, score_cutoff=BROKER_MIN * 100)
        if not hit or self._bcount[hit[0]] > 1:  # ambiguous common name -> no broker match
            return None, 0.0
        return self._bnums[hit[2]], hit[1] / 100


CORE_DROP = re.compile(r"\(.*?\)|\bl\.?\s?l\.?\s?c\.?|\bfz[a-z-]*\b|\bbranch\b|\bbrokers?\b|\bbrokerage\b|\breal estate\b",
                       re.I)


def core_names(office_names_en: str | None) -> list[str]:
    """'CLASSIC PROPERTIES REAL ESTATE L.L.C' -> 'classic properties'."""
    out = []
    for part in (office_names_en or "").split("|"):
        c = " ".join(re.sub(r"[^\w\s&]", " ", CORE_DROP.sub(" ", part.lower())).split())
        if c:
            out.append(c)
    return list(dict.fromkeys(out))


def norm_person(name: str | None) -> str:
    s = re.sub(r"[^a-z\s]", " ", (name or "").lower())
    return " ".join(t for t in s.split() if t not in {"mr", "mrs", "ms", "dr", "realtor", "agent", "broker",
                                                      "dubai", "real", "estate", "properties", "uae"})


def name_score(q: str, name: str, raw: float) -> float:
    """Names shorter than 4 characters are too generic to match on; otherwise token_sort_ratio / 100."""
    if min(len(q.replace(" ", "")), len(name.replace(" ", ""))) < 4:
        return 0.0
    return raw / 100


def domains_in(text: str) -> set[str]:
    return {d.lower() for d in DOMAIN_RE.findall(text or "") if not FREEMAIL_RE.match(d.lower())}


def match_channel(ch: dict[str, Any], candidates: list[dict[str, Any]], reg: Registry) -> dict[str, Any]:
    """ch: {channel_id, title, handle, description, country}. candidates: channel_candidates rows for it."""
    title, desc = ch.get("title") or "", ch.get("description") or ""
    handle = (ch.get("handle") or "").lstrip("@")
    text = f"{title}\n{desc}"
    sig: dict[str, Any] = {"website_route": 0.0, "domain_match": 0.0, "brn_match": 0.0, "name_similarity": 0.0,
                           "dubai_context": 1.0 if (DUBAI_RE.search(text) or ch.get("country") == "AE") else 0.0,
                           "real_estate_context": 1.0 if RE_RE.search(text) else 0.0}
    routes = sorted({c["source_route"] for c in candidates})
    company_id: str | None = None
    broker_number: str | None = None
    match_type = "none"

    web = [c for c in candidates if c["source_route"] == "website" and c.get("company_id_guess")]
    if web:
        sig["website_route"], company_id, match_type = 1.0, web[0]["company_id_guess"], "company_website"

    for num in BRN_RE.findall(desc):
        if num in reg.broker_names:
            sig["brn_match"], broker_number = 1.0, num
            match_type = match_type if company_id else "broker_brn"
            break

    if not company_id:
        for d in sorted(domains_in(desc)):
            for cand in (d, d.split(".", 1)[-1]):
                if cand in reg.domain_to_company:
                    sig["domain_match"], company_id, match_type = 1.0, reg.domain_to_company[cand], "company_domain"
                    sig["matched_domain"] = cand
                    break
            if company_id:
                break

    # name similarity: best registry company over title segments + handle, and against any search guess
    segs = title_segments(title) + ([handle] if handle else [])
    best_cid, best = None, 0.0
    for seg in segs:
        cid, sc = reg.best_company(seg)
        if sc > best:
            best_cid, best = cid, sc
    for c in candidates:
        g = c.get("company_id_guess")
        if g:
            sc = max(reg.company_similarity(g, s) for s in segs)
            if sc >= best:
                best_cid, best = g, sc
    sig["name_similarity"] = round(best, 3)
    if best_cid:
        sig["name_company_id"] = best_cid

    # the website of company A can link to the channel of a *different* registry company B: trust the name instead
    if match_type == "company_website" and best_cid and best_cid != company_id and best >= 0.90 \
            and max(reg.company_similarity(company_id or "", s) for s in segs) < 0.5:
        sig["website_route"], sig["website_other_company"] = 0.0, company_id
        company_id, match_type = None, "none"

    # broker (person) name — only when there is no company evidence
    if not company_id and not broker_number:
        for seg in segs:
            num, sc = reg.best_broker(seg)
            if num:
                broker_number, sig["broker_name_similarity"] = num, round(sc, 3)
                break

    # a company website can link to unrelated channels (agencies, partners, embeds): only trust the link when the
    # channel itself looks like real estate or resembles the company name
    website_weak = sig["website_route"] > 0 and not sig["real_estate_context"] and \
        (reg.company_similarity(company_id, title) if company_id else 0.0) < 0.6
    sig["website_weak"] = website_weak
    strong = max(sig["domain_match"], sig["brn_match"]) > 0 or (sig["website_route"] > 0 and not website_weak)
    if strong:
        score = 0.95
    elif website_weak:
        score = WEBSITE_WEAK_SCORE
    else:
        score = 0.55 * sig["name_similarity"] + 0.25 * sig["dubai_context"] + 0.20 * sig["real_estate_context"]
        if broker_number and sig.get("broker_name_similarity", 0) >= BROKER_MIN:
            b_score = 0.55 * sig["broker_name_similarity"] + 0.25 * sig["dubai_context"] + \
                0.20 * sig["real_estate_context"]
            if b_score > score or not best_cid or sig["name_similarity"] < NAME_ONLY_AUTO_MIN:
                score, match_type, company_id = b_score, "broker_name", None
        if match_type == "none" and best_cid:
            company_id, match_type, broker_number = best_cid, "company_name", None

    decision = "auto_accept" if score >= AUTO else "review" if score >= REVIEW else "reject"
    if decision == "auto_accept" and not strong and match_type == "company_name" and (
            sig["name_similarity"] < NAME_ONLY_AUTO_MIN or not reg.distinctive(company_id, title)):
        decision = "review"  # generic one-word names ("classic", "aqua") need a human
    blocked = bool(BLOCK_RE.search(title)) or bool(BLOCK_RE.search(handle))
    sig["blocklisted"] = blocked
    if blocked and not strong and sig["name_similarity"] < 0.95:
        decision = "reject"
    if website_weak and not sig["dubai_context"]:
        decision = "reject"
    if match_type == "company_name" and sig["name_similarity"] < NAME_MIN:
        decision = "reject"
    if not company_id and not broker_number:
        decision = "reject"

    top = sorted(((k, v) for k, v in sig.items() if isinstance(v, float) and v > 0), key=lambda kv: -kv[1])
    sig["routes"] = routes
    sig["top_signal"] = top[0][0] if top else None
    return {"channel_id": ch["channel_id"], "company_id": company_id, "broker_number": broker_number,
            "match_type": match_type, "match_score": round(score, 4), "signals": sig, "decision": decision}
