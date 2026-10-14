"""Preview matcher decisions without writing (channels.list costs ~1 unit per 50 channels)."""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict

from pitchops.bq import query
from pitchops.config import get_settings
from pitchops.discovery.common import yt_client
from pitchops.discovery.matcher import match_channel
from pitchops.discovery.resolve import load_registry


def main() -> int:
    t = get_settings().table
    cands = query(f"SELECT * FROM `{t('channel_candidates')}`")
    by: dict[str, list] = defaultdict(list)
    for c in cands:
        by[c["channel_id"]].append(c)
    yt = yt_client("match_preview", "preview")
    details = {c["id"]: c for c in yt.channels_by_ids(list(by))}
    yt.close()
    reg = load_registry()
    rows_c = query(f"SELECT company_id, office_names_en FROM `{t('companies')}`")
    names = {r["company_id"]: r["office_names_en"] for r in rows_c}
    out = []
    for cid, rows in by.items():
        ch = details.get(cid)
        if not ch:
            continue
        sn = ch["snippet"]
        m = match_channel({"channel_id": cid, "title": sn.get("title"), "handle": sn.get("customUrl"),
                           "description": sn.get("description"), "country": sn.get("country")}, rows, reg)
        m["title"] = sn.get("title")
        m["entity"] = (names.get(m["company_id"]) or "")[:60] if m["company_id"] else f"broker {m['broker_number']}"
        out.append(m)
    print(Counter(m["decision"] for m in out))
    print(Counter((m["decision"], m["match_type"]) for m in out if m["decision"] != "reject"))
    random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    for label in ("auto_accept", "review"):
        pool = [m for m in out if m["decision"] == label]
        print(f"\n--- {label} sample ({len(pool)})")
        for m in random.sample(pool, min(25, len(pool))):
            print(f"{m['match_score']:.2f} {m['match_type']:<16} {m['signals']['top_signal'] or '':<16} "
                  f"{(m['title'] or '')[:38]:<38} -> {m['entity']}")
    json.dump(out, open("/tmp/pitchops_match_preview.json", "w"), default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
