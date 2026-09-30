# -*- coding: utf-8 -*-
"""
TOKEN2049 Week Singapore 2026 - side event triage.
Source: https://week.token2049.com/api/events  (official API, 380 events)
Cross-check: TOKEN2049 Week Singapore_ Official Side Events Sheet.xlsx

Outputs:
  outputs/events_all.csv          - every event, enriched
  outputs/events_free_luma.csv    - FREE + Luma-hosted (auto-registrable)
  outputs/events_shortlist.csv    - relevance-ranked shortlist for Trilumi
  outputs/token2049_shortlist.ics - calendar for the shortlist
"""
import csv, json, os, re, html
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
os.makedirs(OUT, exist_ok=True)

API = json.load(open(os.path.join(BASE, "scripts", "api_events.json"), encoding="utf-8"))
EVENTS = API["events"]

# ---------------------------------------------------------------- themes
# Trilumi / O's thesis: RWA + green assets (REC/carbon) + regulated issuance
# + enterprise/permissioned chain + APAC (TH/VN/ID/HK) + institutional money.
THEMES = {
    "RWA_Tokenization": 6,
    "Green_Energy_Carbon": 9,
    "Regulation_Compliance": 5,
    "Enterprise_Chain": 7,
    "Stablecoin_Payments": 4,
    "Institutional_DAT": 4,
    "APAC_Market": 5,
    "Investor_Fundraise": 4,
    "AI": 2,
    "Infra_Interop": 3,
}

KEYWORDS = {
    "RWA_Tokenization": ["rwa", "real world asset", "real-world", "tokeniz", "tokenis",
                         "tokenized", "tokenisation", "asset-backed", "onchain asset",
                         "private credit", "treasury", "fund token", "equity token"],
    "Green_Energy_Carbon": ["carbon", "rec]", " rec ", "renewable", "green", "esg",
                            "sustainab", "climate", "energy", "clean energy", "net zero",
                            "netzero", "decarbon", "grid", "solar", "hydro", "carbon credit"],
    "Regulation_Compliance": ["regulat", "compliance", "policy", "licen", "legal",
                              "mica", "sec ", "mas ", "hkma", "custody", "aml", "kyc",
                              "audit", "institutional grade", "framework"],
    "Enterprise_Chain": ["enterprise", "hyperledger", "besu", "fabric", "permissioned",
                         "consortium", "bank", "tradfi", "trad-fi", "infrastructure",
                         "interop", "settlement", "proof of concept", "poc"],
    "Stablecoin_Payments": ["stablecoin", "payment", "remittance", "fx", "cross-border",
                            "payfi", "usdc", "usdt", "yield", "money"],
    "Institutional_DAT": ["institutional", "dat ", "digital asset treasury", "fund",
                          "vc ", "venture", "investor", "lp ", "allocator", "family office",
                          "asset manager", "etf"],
    "APAC_Market": ["asia", "apac", "singapore", "hong kong", "thailand", "vietnam",
                    "indonesia", "malaysia", "japan", "korea", "sea ", "emerging market"],
    "Investor_Fundraise": ["pitch", "demo day", "investor", "fundraise", "raise",
                           "speed dating", "roundtable", "capital", "back", "accelerator",
                           "grant", "prize", "competition"],
    "AI": [" ai", "ai ", "a.i.", "agent", "llm", "machine learning", "ai4", "artificial"],
    "Infra_Interop": ["infra", "interop", "bridge", "l2", "rollup", "modular", "chain",
                      "developer", "dev", "sdk", "node"],
}

# Penalise pure party / sport noise (still useful, but low signal-per-hour)
NOISE_CAT = {"Party/Dinner": -3, "Sport": -2, "Other": -1}
BONUS_CAT = {"Conference/Summit": 3, "Hackathon": 4, "Workshop/Hackathon": 3,
             "Startup Competition": 4, "Networking": 1}

DATE_MAP = {"2026-10-05": "Mon 5 Oct", "2026-10-06": "Tue 6 Oct", "2026-10-07": "Wed 7 Oct",
            "2026-10-08": "Thu 8 Oct", "2026-10-09": "Fri 9 Oct", "2026-10-10": "Sat 10 Oct",
            "2026-10-11": "Sun 11 Oct"}


def host(u):
    m = re.match(r"https?://([^/]+)", u or "")
    return m.group(1).lower() if m else ""


def is_luma(u):
    return "luma.com" in host(u) or "lu.ma" in host(u)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def score(e):
    v = e.get("venue")
    vname = (v.get("name") if isinstance(v, dict) else None) or ""
    text = " ".join([e.get("event_name") or "", e.get("organiser_name") or "",
                     vname, e.get("listing_note") or ""]).lower()
    s, hits = 0, []
    for theme, kwlist in KEYWORDS.items():
        n = sum(1 for k in kwlist if k in text)
        if n:
            s += THEMES[theme] * min(n, 3)
            hits.append(f"{theme}x{n}")
    s += BONUS_CAT.get(e.get("event_category", ""), 0)
    s += NOISE_CAT.get(e.get("event_category", ""), 0)
    if e.get("featured_event"):
        s += 3
    if e.get("verified"):
        s += 1
    return s, hits


rows = []
for e in EVENTS:
    link = e.get("registration_link") or ""
    et = e.get("event_type", "")
    free = et in ("Free", "Free & Paid")
    d = (e.get("event_date") or "")[:10]
    venue = e.get("venue") or {}
    s, hits = score(e)
    rows.append({
        "date": d,
        "day": DATE_MAP.get(d, d),
        "start": e.get("start_time", ""),
        "end": e.get("end_time", ""),
        "name": clean(e.get("event_name", "")),
        "organiser": clean(e.get("organiser_name", "")),
        "category": e.get("event_category", ""),
        "type": et,
        "price": e.get("price", "0"),
        "venue": clean(venue.get("name", "")) if isinstance(venue, dict) else "",
        "featured": "YES" if e.get("featured_event") else "",
        "soldout": "YES" if e.get("soldOut") else "",
        "platform": host(link),
        "luma": "YES" if is_luma(link) else "",
        "register": link,
        "score": s,
        "themes": ",".join(hits),
        "note": clean(e.get("listing_note", "")),
    })

rows.sort(key=lambda r: (r["date"], r["start"], r["name"]))

FIELDS = ["date", "day", "start", "end", "name", "organiser", "category", "type",
          "price", "venue", "featured", "soldout", "platform", "luma",
          "register", "score", "themes", "note"]


def dump(path, data):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(data)
    print(f"  -> {path}  ({len(data)} rows)")


print("=== TOKEN2049 Week Singapore 2026 triage ===")
dump(os.path.join(OUT, "events_all.csv"), rows)

free_rows = [r for r in rows if r["type"] in ("Free", "Free & Paid")]
print(f"Free events: {len(free_rows)} / {len(rows)}")

free_luma = [r for r in free_rows if r["luma"] == "YES"]
free_luma.sort(key=lambda r: -r["score"])
dump(os.path.join(OUT, "events_free_luma.csv"), free_luma)
print(f"Free + Luma (auto-registrable): {len(free_luma)}")

short = [r for r in free_rows if r["score"] >= 12]
short.sort(key=lambda r: (-r["score"], r["date"], r["start"]))
dump(os.path.join(OUT, "events_shortlist.csv"), short)
print(f"Shortlist (score>=12): {len(short)}")

# ---------------------------------------------------------------- ICS
def ics_dt(d, t):
    try:
        hh, mm = t.split(":")
        dt = datetime.strptime(d, "%Y-%m-%d") + timedelta(hours=int(hh), minutes=int(mm))
        # Singapore is UTC+8 -> store as floating local time (no TZID, naive = local)
        return dt.strftime("%Y%m%dT%H%M%S")
    except Exception:
        return None


def esc(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//wb//TOKEN2049 Week SG 2026//EN",
         "CALSCALE:GREGORIAN", "X-WR-TIMEZONE:Asia/Singapore"]
n = 0
for r in short:
    a = ics_dt(r["date"], r["start"])
    b = ics_dt(r["date"], r["end"] or r["start"])
    if not a:
        continue
    if b and b < a:  # crosses midnight
        end = (datetime.strptime(r["date"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d") + b[8:]
        b = end
    lines += ["BEGIN:VEVENT",
              f"UID:tk2049-{abs(hash(r['register'] + r['name']))}@week.token2049.com",
              f"DTSTART:{a}", f"DTEND:{b or a}",
              f"SUMMARY:{esc('[T2049] ' + r['name'])}",
              f"LOCATION:{esc(r['venue'])}",
              f"DESCRIPTION:{esc('Organiser: ' + r['organiser'] + ' | ' + r['category'] +
                                 ' | ' + r['type'] + chr(10) + 'Register: ' + r['register'])}",
              "END:VEVENT"]
    n += 1
lines.append("END:VCALENDAR")
p = os.path.join(OUT, "token2049_shortlist.ics")
open(p, "w", encoding="utf-8").write("\r\n".join(lines))
print(f"  -> {p}  ({n} events)")

# ---------------------------------------------------------------- console summary
print("\n=== TOP 30 by relevance ===")
for r in short[:30]:
    print(f"{r['day']} {r['start']}-{r['end']} [{r['score']:>3}] {r['name'][:62]:<62} {r['register'][:48]}")

print("\n=== day counts (free) ===")
import collections
print(collections.Counter(r["day"] for r in free_rows))
print("\n=== category counts (free) ===")
print(collections.Counter(r["category"] for r in free_rows))
