"""P4 Part B5 — official website per media-candidate property, verified by HTTP fetch (no LLM).

Candidates: URLs found in the descriptions of videos that mention the property (corpus) whose domain is the
developer's official domain or whose path / domain contains the project name; plus the developer homepage as a
fallback. Every URL is fetched (robots.txt respected, PitchOpsResearchBot UA); only HTTP < 400 counts as verified.
Unverified properties are listed for the owner to fill manually (config/property_sources_manual.csv).
Usage: uv run python -m jobs.property_sources
"""

from __future__ import annotations

import asyncio
import re
import sys
import urllib.robotparser
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from jobs.properties import read_csv
from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.discovery.website_links import user_agent
from pitchops.jobrun import base_parser, job_run, new_run_id
from pitchops.properties.normalize import canonical_key, developer_key

# developer key -> official domain(s) (public, well-known; each is still verified by fetch)
DEV_DOMAINS = {
    "emaar": ["emaar.com"], "damac": ["damacproperties.com"], "sobha": ["sobharealty.com"],
    "nakheel": ["nakheel.com"], "meraas": ["meraas.com"], "azizi": ["azizidevelopments.com"],
    "binghatti": ["binghatti.com"], "danube": ["danubeproperties.com"], "arada": ["arada.com"],
    "majid al": ["majidalfuttaim.com"], "imtiaz": ["imtiaz.ae"], "ora": ["oradevelopers.com"],
    "meydan": ["meydan.ae"], "kerzner international": ["atlantis.com"], "nshama": ["nshama.ae"],
    "ellington": ["ellingtonproperties.ae"], "omniyat": ["omniyat.com"], "select": ["select-group.ae"],
    "aldar": ["aldar.com"], "samana": ["samanadevelopers.com"], "deca": ["decadevelopments.com"],
    "mr eight": ["mreight.ae"], "investment corporation": ["onezaabeel.com"], "r revolution": ["r-evolution.ae"],
    "hre": ["hre.ae"], "dubai holding": ["dubaiholding.com"], "wasl": ["wasl.ae"],
}
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
SKIP_HOSTS = re.compile(r"(youtube|youtu\.be|instagram|facebook|tiktok|twitter|x\.com|linkedin|wa\.me|whatsapp|"
                        r"bit\.ly|linktr|t\.me|google|goo\.gl|bayut|propertyfinder|dubizzle)", re.I)


def t(name: str) -> str:
    return get_settings().table(name)


def domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def candidates(prop: dict[str, Any], descriptions: list[str]) -> list[tuple[str, str]]:
    """(url, kind) ordered best first. Pure."""
    dkey = developer_key(prop.get("developer")) or ""
    dev_domains = next((v for k, v in DEV_DOMAINS.items() if dkey.startswith(k)), [])
    name_toks = [w for w in (canonical_key(prop["canonical_name"]) or "").split() if len(w) > 2]
    found: Counter[str] = Counter()
    for d in descriptions:
        for u in URL_RE.findall(d or ""):
            u = u.rstrip(".,;")
            if not SKIP_HOSTS.search(domain(u)):
                found[u] += 1
    out: list[tuple[str, str]] = []
    for u, _ in found.most_common():
        dom, low = domain(u), u.lower()
        on_dev = any(dom == x or dom.endswith("." + x) for x in dev_domains)
        named = bool(name_toks) and all(tok in low.replace("-", "").replace("_", "") or tok in low for tok in name_toks)
        if on_dev and named:
            out.append((u, "project_page"))
        elif named and len(name_toks) >= 1 and name_toks[0] in dom:
            out.append((u, "project_microsite"))
    for x in dev_domains:
        out.append((f"https://www.{x}/", "developer_site"))
    seen, uniq = set(), []
    for u, k in out:
        if u not in seen:
            seen.add(u)
            uniq.append((u, k))
    return uniq[:6]


async def verify(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    rp = urllib.robotparser.RobotFileParser()
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    try:
        rob = await client.get(base + "/robots.txt", follow_redirects=True)
        if rob.status_code == 200:
            rp.parse(rob.text.splitlines())
        else:
            rp.allow_all = True  # type: ignore[attr-defined]
    except httpx.HTTPError:
        rp.allow_all = True  # type: ignore[attr-defined]
    if not rp.can_fetch(user_agent(), url):
        return {"http_status": None, "robots_allowed": False, "verified": False, "final_url": url}
    try:
        r = await client.get(url, follow_redirects=True)
        return {"http_status": r.status_code, "robots_allowed": True, "verified": r.status_code < 400,
                "final_url": str(r.url)}
    except httpx.HTTPError as e:
        return {"http_status": None, "robots_allowed": True, "verified": False, "final_url": url,
                "error": type(e).__name__}


async def verify_all(items: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": user_agent()}) as client:
        async def one(pid: str, url: str, kind: str) -> dict[str, Any]:
            async with sem:
                res = await verify(client, url)
                await asyncio.sleep(1)
                return {"property_id": pid, "url": url, "url_kind": kind, **res}
        return await asyncio.gather(*(one(*i) for i in items))


def main(argv: list[str] | None = None) -> int:
    a = base_parser("property_sources").parse_args(argv)
    run_id = a.run_id or new_run_id("property_sources")
    with job_run("property_sources", run_id, dry_run=a.dry_run) as c:
        props = query(f"""SELECT property_id, rank, canonical_name, developer, aliases, media_candidate
                          FROM `{t('properties_ranked')}` WHERE media_candidate IS NOT NULL ORDER BY rank""")
        texts = query(f"""SELECT m.project_name, v.description FROM `{t('property_mentions')}` m
                          JOIN `{t('v_videos_relevant')}` v USING (video_id) WHERE v.description LIKE '%http%'""")
        by_key: dict[str, list[str]] = {}
        for r in texts:
            k = canonical_key(r["project_name"])
            if k:
                by_key.setdefault(k, []).append(r["description"])
        manual = {r["property_id"]: r["url"] for r in read_csv("property_sources_manual.csv")}
        items = []
        for p in props:
            descs = [d for al in p["aliases"] for d in by_key.get(al, [])]
            cands = ([(manual[p["property_id"]], "manual")] if p["property_id"] in manual else []) + candidates(p, descs)
            items += [(p["property_id"], u, k) for u, k in cands]
        results = asyncio.run(verify_all(items))
        now = datetime.now(UTC).isoformat()
        best: dict[str, dict[str, Any]] = {}
        order = {"manual": 0, "project_page": 1, "project_microsite": 2, "developer_site": 3}
        for r in results:
            cur = best.get(r["property_id"])
            if r["verified"] and (cur is None or order[r["url_kind"]] < order[cur["url_kind"]]):
                best[r["property_id"]] = r
        rows = [{"property_id": p["property_id"], "canonical_name": p["canonical_name"],
                 "media_candidate": p["media_candidate"], **(best.get(p["property_id"]) or
                 {"url": None, "url_kind": None, "http_status": None, "robots_allowed": None, "verified": False,
                  "final_url": None}), "checked_at": now, "run_id": run_id, "ingested_at": now} for p in props]
        if not a.dry_run:
            merge_rows("property_sources", rows, ["property_id"])
        c.update(properties=len(props), urls_checked=len(results),
                 verified=sum(1 for r in rows if r["verified"]),
                 project_level=sum(1 for r in rows if r["url_kind"] in ("project_page", "project_microsite", "manual")))
        for r in rows:
            mark = "✓" if r["verified"] else "✗"
            print(f"{mark} {r['media_candidate']:<11} {r['canonical_name'][:34]:<34} {r['url_kind'] or '-':<17} "
                  f"{r['final_url'] or ''}")
    print({"run_id": run_id, **c})
    return 0


if __name__ == "__main__":
    sys.exit(main())
