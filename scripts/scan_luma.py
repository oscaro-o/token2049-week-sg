# -*- coding: utf-8 -*-
"""
Pre-flight scan of every Luma registration link found in the official
TOKEN2049 Week Singapore 2026 side-event API.

For each link it pulls (no login required):
  - real event name / start / end / timezone / venue
  - is_free, is_sold_out, spots_remaining, require_approval
  - custom registration questions (so we can pre-fill answers)
  - whether this browser session is already registered

Output: outputs/luma_scan.csv
"""
import csv, json, os, re, sys, time
import concurrent.futures as cf
import urllib.request, urllib.error

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
os.makedirs(OUT, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


THROTTLE = float(os.environ.get("LUMA_DELAY", "4.5"))
_last = [0.0]
_lock = __import__("threading").Lock()


def fetch(url, tries=5):
    for i in range(tries):
        with _lock:
            gap = time.time() - _last[0]
            if gap < THROTTLE:
                time.sleep(THROTTLE - gap)
            _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(60 * (i + 1))     # hard back-off on rate limit
                continue
            if i == tries - 1:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(2 * (i + 1))
    return None


NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def parse(url):
    row = {"url": url, "status": "", "luma_name": "", "start": "", "end": "",
           "tz": "", "venue": "", "is_free": "", "sold_out": "", "spots_left": "",
           "require_approval": "", "questions": "", "registered": "", "api_id": ""}
    html = fetch(url)
    if not html:
        row["status"] = "FETCH_FAILED"
        return row
    m = NEXT.search(html)
    if not m:
        row["status"] = "NO_DATA"
        return row
    try:
        d = json.loads(m.group(1))
        data = d["props"]["pageProps"]["initialData"]["data"]
    except Exception:
        row["status"] = "PARSE_FAILED"
        return row
    ev = data.get("event") or {}
    ti = data.get("ticket_info") or {}
    gd = data.get("guest_data") or {}
    row["status"] = "OK"
    row["api_id"] = ev.get("api_id", "")
    row["luma_name"] = (ev.get("name") or "").strip()
    row["start"] = ev.get("start_at", "")
    row["end"] = ev.get("end_at", "")
    row["tz"] = ev.get("timezone", "")
    ga = ev.get("geo_address_info") or {}
    row["venue"] = " ".join(x for x in [ga.get("city_state"), ga.get("sublocality"),
                                        ga.get("country")] if x)
    row["is_free"] = "YES" if ti.get("is_free") else ("NO" if ti else "")
    row["sold_out"] = "YES" if ti.get("is_sold_out") else ""
    row["spots_left"] = ti.get("spots_remaining", "")
    row["require_approval"] = "YES" if ti.get("require_approval") else ""
    qs = data.get("registration_questions") or []
    row["questions"] = " | ".join(
        f"{q.get('label','')}{'(*)' if q.get('required') else ''}" for q in qs)
    row["registered"] = "YES" if (gd.get("ticket_key") or gd.get("email")) else ""
    row["url_resolved"] = "https://lu.ma/" + (ev.get("url") or "")
    row["waitlist"] = "YES" if data.get("waitlist_active") else ""
    return row


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--retry", action="store_true",
                    help="only re-fetch rows that failed last time")
    a = ap.parse_args()

    src = os.path.join(OUT, "events_free_luma.csv")
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    urls = []
    seen = set()
    previous = {}
    if a.retry and os.path.exists(os.path.join(OUT, "luma_scan.csv")):
        for r in csv.DictReader(open(os.path.join(OUT, "luma_scan.csv"),
                                     encoding="utf-8-sig")):
            previous[r["url"]] = r
    for r in rows:
        u = (r.get("register") or "").strip()
        if not u or "luma.com" not in u and "lu.ma" not in u:
            continue
        key = u.split("?")[0]
        if key in seen:
            continue
        if a.retry and previous.get(u, {}).get("status") == "OK":
            continue
        seen.add(key)
        urls.append((u, r))
    print(f"scanning {len(urls)} Luma links (retry={a.retry}) ...")

    results = []
    for _u, _r in previous.items():
        if _r.get("status") == "OK":
            results.append(_r)          # keep prior successes in retry mode
    print(f"  carrying forward {len(results)} already-scanned rows")
    workers = int(os.environ.get("LUMA_WORKERS", "1"))
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(parse, u): (u, r) for u, r in urls}
        done = 0
        for f in cf.as_completed(futs):
            u, meta = futs[f]
            try:
                row = f.result()
            except Exception as e:
                row = {"url": u, "status": "ERROR:" + str(e)[:60]}
            row.update({"t2049_name": meta.get("name", ""),
                        "t2049_day": meta.get("day", ""),
                        "t2049_start": meta.get("start", ""),
                        "t2049_cat": meta.get("category", ""),
                        "t2049_price": meta.get("price", ""),
                        "score": meta.get("score", "")})
            results.append(row)
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(urls)}")

    fields = ["status", "t2049_day", "t2049_start", "t2049_name", "luma_name",
              "start", "end", "tz", "venue", "is_free", "sold_out", "spots_left",
              "require_approval", "waitlist", "registered", "questions",
              "url", "url_resolved", "api_id", "score", "t2049_cat", "t2049_price"]
    results.sort(key=lambda r: (-int(r.get("score") or 0), r.get("t2049_day", "")))
    p = os.path.join(OUT, "luma_scan.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    print(f"-> {p}")

    ok = [r for r in results if r["status"] == "OK"]
    print(f"\nOK: {len(ok)} / {len(results)}")
    print("truly free (Luma):", sum(1 for r in ok if r["is_free"] == "YES"))
    print("sold out:", sum(1 for r in ok if r["sold_out"] == "YES"))
    print("approval required:", sum(1 for r in ok if r["require_approval"] == "YES"))
    print("no approval + free + not sold out (FULL AUTO CANDIDATES):",
          sum(1 for r in ok if r["is_free"] == "YES" and not r["sold_out"]
              and r["require_approval"] != "YES"))


if __name__ == "__main__":
    main()
