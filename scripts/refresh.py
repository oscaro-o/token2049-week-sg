# -*- coding: utf-8 -*-
"""
refresh.py — pull the latest official side-event list and rebuild everything.

The TOKEN2049 Week directory is still being edited (new events appear daily right
up to the conference), so re-run this every morning until 9 Oct.

    python refresh.py
"""
import json, os, subprocess, sys, urllib.request
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://week.token2049.com/api/events"
DEST = os.path.join(BASE, "scripts", "api_events.json")
PY = sys.executable

req = urllib.request.Request(API_URL, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json"})
raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
data = json.loads(raw)

old = json.load(open(DEST, encoding="utf-8")) if os.path.exists(DEST) else {"events": []}
old_ids = {e.get("_id") for e in old.get("events", [])}
new = [e for e in data.get("events", []) if e.get("_id") not in old_ids]

json.dump(data, open(DEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"[{datetime.now():%Y-%m-%d %H:%M}] {len(data.get('events', []))} events "
      f"({len(new)} new since last pull)")

for e in new[:40]:
    print(f"   + {e.get('event_date','')[:10]} {(e.get('event_name') or '')[:60]} "
          f"| {e.get('event_type')} | {e.get('registration_link')}")

for s in ("build_lists.py", "build_queue.py", "build_html.py"):
    subprocess.run([PY, os.path.join(BASE, "scripts", s)], cwd=os.path.join(BASE, "scripts"))
print("done -> outputs/plan.html")
