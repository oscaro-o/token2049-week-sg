# -*- coding: utf-8 -*-
"""
Build outputs/register_queue.csv — the prioritised list luma_bot.py will walk.

Rules:
  * keep FREE events only
  * prefer Luma-hosted (automatable); keep non-Luma as manual tasks
  * relevance score >= MIN_SCORE, OR force-include build/pitch/hackathon content
  * de-duplicate multi-day repeats of the same registration link
  * never schedule two things at once -> flag clashes, keep the higher score
"""
import csv, os, re
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")

MIN_SCORE = int(os.environ.get("MIN_SCORE", "10"))
FORCE = re.compile(r"hack|pitch|demo day|competition|bounty|workshop|hacker house", re.I)

rows = list(csv.DictReader(open(os.path.join(OUT, "events_all.csv"), encoding="utf-8-sig")))
free = [r for r in rows if r["type"] in ("Free", "Free & Paid")]

picked = []
for r in free:
    s = int(r["score"])
    if s >= MIN_SCORE or FORCE.search(r["name"]):
        picked.append(r)

# de-dup by registration link (multi-day events share one link)
seen, uniq = set(), []
for r in picked:
    k = (r["register"] or r["name"]).split("?")[0]
    if k in seen:
        continue
    seen.add(k)
    uniq.append(r)


BAD = re.compile(r"luma\.com/event/manage|/manage/", re.I)
uniq = [r for r in uniq if not BAD.search(r["register"] or "")]


def span(r):
    """(start, end) as datetime; end rolls to next day if it looks earlier."""
    try:
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        hh, mm = (r["start"] or "00:00").split(":")
        a = d + timedelta(hours=int(hh), minutes=int(mm))
        hh, mm = (r["end"] or r["start"] or "00:00").split(":")
        b = d + timedelta(hours=int(hh), minutes=int(mm))
        if b <= a:
            b += timedelta(days=1)
        return a, b
    except Exception:
        return datetime.max, datetime.max


def mins(r):
    return span(r)[0]


uniq.sort(key=lambda r: (-int(r["score"]), mins(r)))

# clash resolution: only drop when intervals genuinely overlap
kept, clashes = [], []
for r in uniq:
    a, b = span(r)
    conflict = None
    for k in kept:
        ka, kb = span(k)
        if a < kb and ka < b:
            conflict = k
            break
    if conflict:
        clashes.append((r, conflict))
        continue
    kept.append(r)

kept.sort(key=lambda r: (mins(r), -int(r["score"])))

FIELDS = ["date", "day", "start", "end", "name", "organiser", "category",
          "venue", "platform", "luma", "register", "score", "themes"]
# what the bot walks: every relevant free Luma event (RSVP is free & non-binding)
with open(os.path.join(OUT, "register_queue.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(uniq, key=lambda r: -int(r["score"])))
print(f"-> register_queue.csv ({len(uniq)} rows)  <-- bot input")

# what you actually attend: clash-free schedule
with open(os.path.join(OUT, "my_schedule.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(kept)
print(f"-> my_schedule.csv ({len(kept)} rows)  <-- clash-free plan")

manual = [r for r in kept if r["luma"] != "YES"]
with open(os.path.join(OUT, "register_manual.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(manual)
print(f"-> register_manual.csv ({len(manual)} non-Luma, must be done by hand)")

print("\n=== QUEUE ===")
for r in kept:
    print(f"{r['day']} {r['start']}-{r['end']} [{r['score']:>3}] "
          f"{r['name'][:56]:<56} {r['register'][:46]}")
print(f"\ntotal {len(kept)} | dropped as clash {len(clashes)} | non-Luma {len(manual)}")
