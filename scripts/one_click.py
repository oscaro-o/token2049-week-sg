# -*- coding: utf-8 -*-
"""
one_click.py — the engine behind the "Register all" button.

It is the whole flow in one command, with no prompting:

    1. is the saved Chrome profile signed in to Luma?   (headless, a few seconds)
    2. if not -> open Chrome on the sign-in page, wait, and auto-detect the login
    3. walk the whole queue and register

You normally never run this by hand — serve.py spawns it. But you can:

    python one_click.py --scope all
    python one_click.py --scope instant          # only the 38 one-click events
    python one_click.py --scope day --day "Tue 6 Oct"
    python one_click.py --scope all --limit 10 --dry
"""
import argparse, csv, os, sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import luma_bot as B

ALL = os.path.join(B.OUT, "register_all_free.csv")
INSTANT = os.path.join(B.OUT, "free_luma_instant_all.csv")
DAY_TMP = os.path.join(B.OUT, "_queue_day.csv")


def _k(u):
    import re
    return re.sub(r"https?://(www\.)?", "", (u or "")).strip("/").lower()


def drop_soldout(path):
    """Skip events the scan already knows are sold out.

    A sold-out page costs a full page load and can never succeed. At ~25-50s
    each that is pure waste.
    """
    try:
        scan = list(csv.DictReader(open(os.path.join(B.OUT, "luma_scan.csv"),
                                        encoding="utf-8-sig")))
        out = {_k(r.get("url")) for r in scan if r.get("sold_out") == "YES"}
    except Exception:
        return path
    if not out:
        return path
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    keep = [r for r in rows if _k(r.get("register")) not in out]
    if len(keep) == len(rows):
        return path
    tmp = os.path.join(B.OUT, "_queue_run.csv")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(keep)
    print(f"[i] skipping {len(rows)-len(keep)} events already sold out")
    return tmp


def pick_queue(scope, day):
    """Return (path, human label)."""
    if scope == "instant":
        return INSTANT, "one-click events"
    if scope == "day":
        if not day:
            raise SystemExit("--scope day needs --day")
        rows = [r for r in csv.DictReader(open(ALL, encoding="utf-8-sig"))
                if (r.get("day") or "") == day]
        with open(DAY_TMP, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows
                               else ["register"])
            w.writeheader()
            w.writerows(rows)
        return DAY_TMP, day
    return ALL, "all free events"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="all", choices=["all", "instant", "day"])
    ap.add_argument("--day", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=5.0)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--headless", action="store_true", default=True)
    ap.add_argument("--show", dest="headless", action="store_false",
                    help="show the browser window while it works")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--skip-login", action="store_true",
                    help="do not probe or prompt for the Luma login (testing)")
    a = ap.parse_args()

    path, label = pick_queue(a.scope, a.day)
    path = drop_soldout(path)
    total = sum(1 for _ in csv.DictReader(open(path, encoding="utf-8-sig")))
    print(f"[i] scope: {label}  ({total} events)")
    sys.stdout.flush()

    me = B.load_me()
    if "example.com" in (me.get("email") or ""):
        print("[!] profile.json still has the placeholder email — "
              "registrations will be sent to you@example.com. Edit it first.")
        sys.stdout.flush()

    if a.skip_login:
        print("[i] --skip-login: not checking the Luma session")
    elif not B.check_login():
        print("[i] not signed in -> opening Chrome. Sign in; it starts by itself.")
        sys.stdout.flush()
        if not B.do_login(wait_minutes=20):
            print("[x] login never completed")
            sys.exit(2)
    else:
        print("[ok] already signed in")

    B.do_run(SimpleNamespace(input=path, limit=a.limit, day="", dry=a.dry,
                             headless=a.headless, fresh=a.fresh, delay=a.delay))


if __name__ == "__main__":
    main()
