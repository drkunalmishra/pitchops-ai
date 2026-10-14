"""Name normalization for matching (pure)."""

from __future__ import annotations

import re

STOP = {"llc", "l.l.c", "l.l.c.", "fz", "fze", "fzco", "fz-llc", "real", "estate", "realestate", "properties",
        "property", "broker", "brokers", "brokerage", "dubai", "uae", "branch", "co", "company", "ltd", "limited",
        "the", "and", "&", "group", "realty", "llc.", "est", "est.", "services", "management", "investment",
        "investments", "development", "developments", "international", "agency", "agent", "agents", "homes"}
SEP = re.compile(r"\s*[|•·–—\-:/]\s+|\s+[|•·–—\-:/]\s*")


LEGAL = {"llc", "l.l.c", "fz", "fze", "fzco", "branch", "broker", "brokers", "brokerage", "ltd", "limited", "co",
         "real", "estate", "properties", "property", "dubai", "uae"}


def search_name(name: str | None) -> str:
    """Light clean for search queries: drop legal/sector words, keep 'and'/'&'."""
    return clean(name, stop=LEGAL)


def clean(name: str | None, stop: set[str] | None = None) -> str:
    stop = STOP if stop is None else stop
    s = (name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.replace("l.l.c", " ").replace("f.z.e", " ").replace("f.z", " ")
    s = re.sub(r"[^\w&\s]", " ", s)
    toks = [t for t in s.split() if t not in stop]
    # collapse spaced initials: "f a m" -> "fam"
    out: list[str] = []
    buf = ""
    for t in toks:
        if len(t) == 1 and t.isalpha():
            buf += t
            continue
        if buf:
            out.append(buf)
            buf = ""
        out.append(t)
    if buf:
        out.append(buf)
    return " ".join(out).strip()


def company_names(office_names_en: str | None) -> list[str]:
    """Distinct cleaned names from 'A | B | C'."""
    seen: dict[str, None] = {}
    for part in (office_names_en or "").split("|"):
        c = clean(part)
        if c:
            seen[c] = None
    return list(seen)


def title_segments(title: str | None) -> list[str]:
    """'Driven Properties | Dubai Real Estate' -> ['driven properties | ...', 'driven properties', 'dubai real estate']"""
    t = title or ""
    parts = [p for p in SEP.split(t) if p.strip()]
    return list(dict.fromkeys([t, *parts]))
