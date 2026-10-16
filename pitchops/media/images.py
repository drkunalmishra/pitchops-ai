"""P7 property image library helpers (pure): find candidate image URLs in official pages, skip logos/icons, pick a
balanced set of tagged images. Originals live only in the private bucket (never in git)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

TAGS = ["aerial", "exterior_facade", "skyline_view", "interior_living", "interior_bedroom", "kitchen", "bathroom",
        "pool_amenity", "gym_amenity", "lobby", "community", "masterplan", "other"]
SKIP = re.compile(r"logo|icon|favicon|sprite|avatar|badge|flag|qr|whatsapp|facebook|instagram|twitter|linkedin|"
                  r"youtube|tiktok|placeholder|loader|\.svg|\.gif|data:", re.I)
MIN_WIDTH = 1280
MAX_IMAGES = 40
PER_PROPERTY = (8, 15)
WANT = {"aerial": 2, "exterior_facade": 3, "skyline_view": 1, "interior_living": 2, "interior_bedroom": 1, "kitchen": 1,
        "bathroom": 1, "pool_amenity": 2, "gym_amenity": 1, "lobby": 1, "community": 1}


class _Imgs(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[tuple[str, int]] = []  # (url, declared width or 0)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "meta" and a.get("property") in ("og:image", "og:image:url"):
            self.found.append((a.get("content", ""), 0))
        if tag in ("img", "source"):
            for key in ("srcset", "data-srcset"):
                for part in a.get(key, "").split(","):
                    bits = part.strip().split()
                    if bits:
                        w = int(bits[1][:-1]) if len(bits) > 1 and bits[1].endswith("w") and bits[1][:-1].isdigit() else 0
                        self.found.append((bits[0], w))
            for key in ("src", "data-src", "data-lazy-src"):
                if a.get(key):
                    w = int(a["width"]) if a.get("width", "").isdigit() else 0
                    self.found.append((a[key], w))


def candidates(html: str, base: str) -> list[str]:
    """Image URLs on a page, largest srcset variant first, logos/icons dropped, de-duplicated."""
    p = _Imgs()
    p.feed(html)
    best: dict[str, tuple[str, int]] = {}
    for url, w in p.found:
        if not url or SKIP.search(url):
            continue
        full = urljoin(base, url.strip())
        key = re.sub(r"[-_]?\d{2,4}x\d{2,4}|\?.*$", "", full)  # same picture in several sizes
        if key not in best or w > best[key][1]:
            best[key] = (full, w)
    return [u for u, w in sorted(best.values(), key=lambda x: -x[1])][:MAX_IMAGES]


def select(images: list[dict[str, Any]]) -> list[str]:
    """Pick 8-15 images covering aerial/exterior + interiors + amenities, best quality first. images: {id, tag, quality}."""
    good = sorted((i for i in images if i.get("quality", 0) >= 0.5 and i.get("tag") != "other"),
                  key=lambda i: -i.get("quality", 0))
    chosen: list[str] = []
    for tag, n in WANT.items():
        chosen += [i["id"] for i in good if i["tag"] == tag][:n]
    for i in good:  # top up with the best remaining
        if len(chosen) >= PER_PROPERTY[1]:
            break
        if i["id"] not in chosen:
            chosen.append(i["id"])
    return chosen[: PER_PROPERTY[1]]


def tag_schema() -> dict[str, Any]:
    return {"type": "object", "required": ["tag", "quality", "has_text_or_logo", "shows_people"], "properties": {
        "tag": {"type": "string", "enum": TAGS}, "quality": {"type": "number", "minimum": 0, "maximum": 1},
        "has_text_or_logo": {"type": "boolean"}, "shows_people": {"type": "boolean"},
        "caption": {"type": "string", "maxLength": 160}}}
