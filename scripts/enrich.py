# -*- coding: utf-8 -*-
"""
enrich.py — join register_queue.csv with the Luma pre-scan so you can see,
before you spend a click, whether an event is REALLY free, sold out, or
gated behind host approval.

    python enrich.py     ->  outputs/register_queue_enriched.csv
"""
import csv, os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")


def key(u):
    return re.sub(r"https?://(www\.)?", "", (u or "")).strip("/").lower()


scan = {}
p = os.path.join(OUT, "luma_scan.csv")
if os.path.exists(p):
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        if r.get("status") == "OK":
            scan[key(r.get("url"))] = r

q = list(csv.DictReader(open(os.path.join(OUT, "register_queue.csv"), encoding="utf-8-sig")))

FIELDS = list(q[0].keys()) + ["luma_free", "luma_soldout", "luma_approval",
                              "luma_spots", "luma_questions", "scan"]
out = []
stats = {"real_free": 0, "sold_out": 0, "approval": 0, "unknown": 0}
for r in q:
    s = scan.get(key(r.get("register")), {})
    r["luma_free"] = s.get("is_free", "")
    r["luma_soldout"] = s.get("sold_out", "")
    r["luma_approval"] = s.get("require_approval", "")
    r["luma_spots"] = s.get("spots_left", "")
    r["luma_questions"] = (s.get("questions") or "")[:200]
    r["scan"] = "OK" if s else "PENDING"
    if not s:
        stats["unknown"] += 1
    else:
        if r["luma_free"] == "YES":
            stats["real_free"] += 1
        if r["luma_soldout"] == "YES":
            stats["sold_out"] += 1
        if r["luma_approval"] == "YES":
            stats["approval"] += 1
    out.append(r)

# sort: real-free & no approval first, then unknown, then blocked
def rank(r):
    return (0 if (r["luma_free"] == "YES" and r["luma_approval"] != "YES"
                  and r["luma_soldout"] != "YES") else
            1 if r["scan"] == "PENDING" else 2, -int(r["score"]))


out.sort(key=rank)
with open(os.path.join(OUT, "register_queue_enriched.csv"), "w",
          newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(out)

# the 26-ish you can actually get into with one click — run the bot on these first
instant = [r for r in out if r["luma_free"] == "YES" and r["luma_approval"] != "YES"
           and r["luma_soldout"] != "YES"]
with open(os.path.join(OUT, "register_queue_instant.csv"), "w",
          newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(instant)
print(f"-> register_queue_instant.csv ({len(instant)} rows)  <-- one-click, do these first")

# and every one-click free event across the whole directory, not just the queue
allrows = list(csv.DictReader(open(os.path.join(OUT, "events_free_luma.csv"),
                                   encoding="utf-8-sig")))
broadcast = []
for r in allrows:
    s = scan.get(key(r.get("register")), {})
    if not s:
        continue
    if s.get("is_free") == "YES" and s.get("sold_out") != "YES" \
            and s.get("require_approval") != "YES":
        r["luma_free"] = "YES"
        r["luma_soldout"] = ""
        r["luma_approval"] = ""
        r["luma_spots"] = s.get("spots_left", "")
        r["luma_questions"] = (s.get("questions") or "")[:200]
        r["scan"] = "OK"
        broadcast.append(r)
broadcast.sort(key=lambda r: (-int(r["score"]), r["day"], r["start"]))
with open(os.path.join(OUT, "free_luma_instant_all.csv"), "w",
          newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(broadcast)
print(f"-> free_luma_instant_all.csv ({len(broadcast)} rows)  "
      f"<-- every one-click free event in the directory")

print(f"-> register_queue_enriched.csv ({len(out)} rows)")
print("   really free & one-click :", stats["real_free"])
print("   sold out                :", stats["sold_out"])
print("   host approval required  :", stats["approval"])
print("   not yet scanned         :", stats["unknown"])
