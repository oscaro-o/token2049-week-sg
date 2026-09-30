# -*- coding: utf-8 -*-
"""
build_all_queue.py — the "just register everything free" queue.

Order matters: if we hit a rate limit or run out of time, the good stuff must
already be done. So: Luma first, then by relevance, then by day.

    -> outputs/register_all_free.csv
"""
import csv, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")

rows = list(csv.DictReader(open(os.path.join(OUT, "events_all.csv"), encoding="utf-8-sig")))
free = [r for r in rows if r["type"] in ("Free", "Free & Paid")]

BAD = re.compile(r"luma\.com/event/manage|/manage/|^$", re.I)
free = [r for r in free if not BAD.search(r.get("register") or "")]

# de-dup identical registration links (multi-day events share one)
seen, uniq = set(), []
for r in free:
    k = (r["register"] or r["name"]).split("?")[0]
    if k in seen:
        continue
    seen.add(k)
    uniq.append(r)

DAY_ORDER = {"2026-10-05": 0, "2026-10-06": 1, "2026-10-07": 2, "2026-10-08": 3,
             "2026-10-09": 4, "2026-10-10": 5, "2026-10-11": 6}
uniq.sort(key=lambda r: (0 if r["luma"] == "YES" else 1,
                         -int(r["score"]),
                         DAY_ORDER.get(r["date"], 9),
                         r["start"]))

FIELDS = ["date", "day", "start", "end", "name", "organiser", "category",
          "venue", "platform", "luma", "register", "score", "themes"]
with open(os.path.join(OUT, "register_all_free.csv"), "w", newline="",
          encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(uniq)

n_luma = sum(1 for r in uniq if r["luma"] == "YES")
print(f"-> register_all_free.csv  ({len(uniq)} rows: {n_luma} Luma + "
      f"{len(uniq)-n_luma} other)")
print("\nfirst 15 (these get done first if anything breaks):")
for r in uniq[:15]:
    print(f"  {r['day']} {r['start']} [{r['score']:>3}] {r['name'][:52]}  {r['register'][:40]}")
