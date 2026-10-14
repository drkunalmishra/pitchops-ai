"""Route A — find YouTube links on registry company websites (no YouTube quota for the fetch).

Respects robots.txt, identifies itself, fetches at most 2 pages per domain (home + one contact/about page),
never stores HTML. Extracted channel links are resolved with channels.list (1 unit each / per 50 ids).
"""

from __future__ import annotations

import asyncio
import re
import urllib.robotparser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from pitchops.bq import merge_rows, query
from pitchops.config import get_settings
from pitchops.discovery.common import candidate_row, now_iso, save_candidates
from pitchops.logs import log
from pitchops.youtube.client import YouTubeClient

CONCURRENCY = 20
TIMEOUT = 10.0
HOST_DELAY_S = 1.0
MAX_BYTES = 2_000_000

YT_HANDLE = re.compile(r"youtube\.com/@([A-Za-z0-9._\-]{3,})", re.I)
YT_CHANNEL = re.compile(r"youtube\.com/channel/(UC[\w\-]{22})", re.I)
YT_C = re.compile(r"youtube\.com/c/([A-Za-z0-9._\-%]{2,})", re.I)
YT_USER = re.compile(r"youtube\.com/user/([A-Za-z0-9._\-]{2,})", re.I)
YT_VIDEO = re.compile(r"(?:youtube\.com/(?:watch\?(?:[^\"'\s<>]*&)?v=|embed/|shorts/|live/)|youtu\.be/)([\w\-]{11})", re.I)
SOCIAL = re.compile(r"https?://(?:www\.)?(?:instagram\.com|linkedin\.com/company|tiktok\.com/@)[^\s\"'<>)]*", re.I)
HREF = re.compile(r"""href=["']([^"'#]+)["']""", re.I)
FREEMAIL = re.compile(r"^(gmail|googlemail|yahoo|ymail|rocketmail|hotmail|outlook|live|windowslive|msn|icloud|me|mac|aol|"
                      r"protonmail|proton|gmx|mail|yandex|rediffmail|zoho|qq|163|126|emirates|eim|du|etisalat|"
                      r"inbox|web|t-online|orange|free|libero|seznam|wp|o2|btinternet|sky|comcast|verizon)\.", re.I)
SKIP_HANDLES = {"youtube", "googlecreators", "user", "channel"}


def user_agent() -> str:
    return f"PitchOpsResearchBot/0.1 (+mailto:{get_settings().contact_email or 'research@pitchops.test'})"


def extract(html: str) -> dict[str, list[str]]:
    """Pure: pull YouTube channel refs, video ids and social links out of page text."""
    handles = sorted({h.rstrip(".") for h in YT_HANDLE.findall(html) if h.lower() not in SKIP_HANDLES})
    return {
        "handles": handles,
        "channel_ids": sorted(set(YT_CHANNEL.findall(html))),
        "custom": sorted(set(YT_C.findall(html))),
        "users": sorted(set(YT_USER.findall(html))),
        "video_ids": sorted(set(YT_VIDEO.findall(html))),
        "social": sorted({s.rstrip("/.,") for s in SOCIAL.findall(html)})[:20],
    }


def youtube_links(found: dict[str, list[str]]) -> list[str]:
    return ([f"https://www.youtube.com/@{h}" for h in found["handles"]]
            + [f"https://www.youtube.com/channel/{c}" for c in found["channel_ids"]]
            + [f"https://www.youtube.com/c/{c}" for c in found["custom"]]
            + [f"https://www.youtube.com/user/{u}" for u in found["users"]])


def contact_link(html: str, base: str) -> str | None:
    host = urlparse(base).netloc
    for href in HREF.findall(html):
        if re.search(r"contact|about", href, re.I):
            u = urljoin(base, href)
            if urlparse(u).netloc == host and u.startswith("http"):
                return u
    return None


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        r = await client.get(url, follow_redirects=True)
        return r
    except (httpx.HTTPError, ValueError):
        return None


async def probe_domain(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    ua = user_agent()
    rec: dict[str, Any] = {"domain": domain, "url_fetched": None, "http_status": None, "robots_allowed": None,
                           "youtube_links": [], "social_links": [], "fetched_at": now_iso(), "error": None,
                           "_found": {}}
    for base in (f"https://{domain}/", f"https://www.{domain}/"):
        rp = urllib.robotparser.RobotFileParser()
        rob = await _get(client, urljoin(base, "/robots.txt"))
        if rob is not None and rob.status_code in (401, 403):
            rp.disallow_all = True  # type: ignore[attr-defined]
        elif rob is not None and rob.status_code == 200:
            rp.parse(rob.text.splitlines())
        else:
            rp.allow_all = True  # type: ignore[attr-defined]
        await asyncio.sleep(HOST_DELAY_S)
        if not rp.can_fetch(ua, base):
            rec.update(robots_allowed=False, url_fetched=base)
            return rec
        rec["robots_allowed"] = True
        home = await _get(client, base)
        if home is None:
            rec["error"] = "fetch_failed"
            continue
        rec.update(url_fetched=str(home.url), http_status=home.status_code, error=None)
        if home.status_code >= 400:
            continue
        html = home.text[:MAX_BYTES]
        found = extract(html)
        if not (found["handles"] or found["channel_ids"] or found["custom"] or found["users"]):
            nxt = contact_link(html, str(home.url))
            if nxt and rp.can_fetch(ua, nxt):
                await asyncio.sleep(HOST_DELAY_S)
                page2 = await _get(client, nxt)
                if page2 is not None and page2.status_code < 400:
                    f2 = extract(page2.text[:MAX_BYTES])
                    found = {k: sorted(set(found[k]) | set(f2[k])) for k in found}
        rec["_found"] = found
        rec["youtube_links"] = youtube_links(found)
        rec["social_links"] = found["social"]
        return rec
    return rec


async def probe_all(domains: list[str]) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(CONCURRENCY)
    out: list[dict[str, Any]] = []
    limits = httpx.Limits(max_connections=CONCURRENCY * 2)
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": user_agent()}, limits=limits) as client:

        async def one(d: str) -> None:
            async with sem:
                try:
                    out.append(await asyncio.wait_for(probe_domain(client, d), timeout=60))
                except Exception as e:  # never let one domain kill the sweep
                    out.append({"domain": d, "fetched_at": now_iso(), "error": f"{type(e).__name__}"[:200],
                                "youtube_links": [], "social_links": [], "_found": {}})
                if len(out) % 250 == 0:
                    log("website_progress", done=len(out), total=len(domains))

        await asyncio.gather(*(one(d) for d in domains))
    return out


def pending_domains(limit: int | None) -> list[tuple[str, str]]:
    """(domain, company_id) by broker_count desc; primary domain first; skip already-probed domains."""
    t = get_settings().table
    rows = query(f"""
        WITH d AS (
          SELECT company_id, broker_count, primary_domain AS domain, 0 AS pri FROM `{t('companies')}`
          WHERE primary_domain IS NOT NULL
          UNION ALL
          SELECT company_id, broker_count, dom, 1 FROM `{t('companies')}`, UNNEST(corporate_domains) dom
          WHERE dom != IFNULL(primary_domain, ''))
        SELECT domain, ANY_VALUE(company_id HAVING MAX broker_count) AS company_id, MAX(broker_count) AS bc,
               MIN(pri) AS pri
        FROM d WHERE domain NOT IN (SELECT domain FROM `{t('website_probes')}`)
        GROUP BY domain ORDER BY pri, bc DESC""")
    pairs = [(r["domain"], r["company_id"]) for r in rows if not FREEMAIL.match(r["domain"])]
    return pairs[:limit] if limit else pairs


def resolve_found(yt: YouTubeClient, found_by_company: dict[str, dict[str, list[str]]], run_id: str) -> int:
    """channels.list for every extracted reference -> channel_candidates (source_route='website')."""
    rows: list[dict[str, Any]] = []
    ids_to_company: dict[str, set[str]] = {}
    video_to_company: dict[str, set[str]] = {}
    for comp, f in found_by_company.items():
        for cid in f.get("channel_ids", []):
            ids_to_company.setdefault(cid, set()).add(comp)
        for h in f.get("handles", []) + f.get("custom", []):
            ch = yt.channel_by_handle(h)
            if ch:
                ids_to_company.setdefault(ch["id"], set()).add(comp)
        for u in f.get("users", []):
            ch = yt.channel_by_username(u) or yt.channel_by_handle(u)
            if ch:
                ids_to_company.setdefault(ch["id"], set()).add(comp)
        if not any(f.get(k) for k in ("channel_ids", "handles", "custom", "users")):
            for v in f.get("video_ids", [])[:3]:
                video_to_company.setdefault(v, set()).add(comp)
    if video_to_company:
        for vid in yt.videos_by_ids(list(video_to_company)):
            for comp in video_to_company[vid["id"]]:
                ids_to_company.setdefault(vid["snippet"]["channelId"], set()).add(comp)
    for ch in yt.channels_by_ids(list(ids_to_company)):
        sn = ch.get("snippet", {})
        for comp in ids_to_company.get(ch["id"], ()):
            rows.append(candidate_row(ch["id"], "website", f"website:{comp}", run_id, title=sn.get("title"),
                                      description=sn.get("description"), handle=sn.get("customUrl"),
                                      country=sn.get("country"), company_id_guess=comp))
    return save_candidates(rows)


CHUNK = 300


def run(yt: YouTubeClient, run_id: str, limit: int | None = None, dry_run: bool = False) -> dict[str, int]:
    pairs = pending_domains(limit)
    log("website_start", domains=len(pairs))
    c = {"domains": 0, "robots_blocked": 0, "fetch_ok": 0, "with_youtube": 0, "candidates": 0}
    if dry_run:
        return {**c, "domains": len(pairs)}
    for i in range(0, len(pairs), CHUNK):  # checkpoint per chunk: probes persisted, re-runs skip them
        chunk = pairs[i : i + CHUNK]
        probes = asyncio.run(probe_all([d for d, _ in chunk]))
        comp_of = dict(chunk)
        found_by_company: dict[str, dict[str, list[str]]] = {}
        for p in probes:
            f = p.pop("_found", {}) or {}
            if any(f.get(k) for k in ("handles", "channel_ids", "custom", "users", "video_ids")):
                agg = found_by_company.setdefault(comp_of[p["domain"]], {})
                for k, v in f.items():
                    agg[k] = sorted(set(agg.get(k, [])) | set(v))
            p.update(run_id=run_id, ingested_at=now_iso())
        c["candidates"] += resolve_found(yt, found_by_company, run_id)
        merge_rows("website_probes", probes, ["domain"])
        c["domains"] += len(probes)
        c["robots_blocked"] += sum(1 for p in probes if p.get("robots_allowed") is False)
        c["fetch_ok"] += sum(1 for p in probes if (p.get("http_status") or 999) < 400)
        c["with_youtube"] += len(found_by_company)
        log("website_chunk", **c)
    return c
