"""Print N random auto_accept matches (title, link, matched entity, score, top signal) for a manual spot check."""

from __future__ import annotations

import sys

from pitchops.bq import query
from pitchops.config import get_settings


def main(n: int = 20, seed: str = "p2") -> int:
    t = get_settings().table
    rows = query(f"""
        SELECT m.channel_id, JSON_VALUE(m.signals, '$.title') AS title, m.match_type, m.match_score,
               JSON_VALUE(m.signals, '$.top_signal') AS top, c.office_names_en AS company, m.broker_number
        FROM `{t('channel_matches')}` m LEFT JOIN `{t('companies')}` c USING (company_id)
        WHERE m.decision = 'auto_accept'
        ORDER BY FARM_FINGERPRINT(CONCAT(m.channel_id, @seed)) LIMIT @n""", {"seed": seed, "n": n})
    for i, r in enumerate(rows, 1):
        ent = (r["company"] or "").split("|")[0].strip()[:44]
        if r["broker_number"]:
            ent = f"broker #{r['broker_number']} @ {ent}"
        print(f"{i:2} | {r['match_score']:.2f} | {r['top'] or '':<15} | {(r['title'] or '')[:40]:<40} | "
              f"https://youtube.com/channel/{r['channel_id']} | {ent}")
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 20, sys.argv[2] if len(sys.argv) > 2 else "p2"))
