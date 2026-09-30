# -*- coding: utf-8 -*-
"""
luma_bot.py — semi-automatic registration for TOKEN2049 Week Singapore 2026
side events hosted on Luma.

WHY SEMI-AUTOMATIC
  Luma rate-limits aggressively (HTTP 429) and requires a login. We therefore:
    1. use ONE persistent Chrome profile  -> you sign in to Luma exactly once
    2. throttle every request (default 9s) and back off hard on 429
    3. never guess a submit; every click is logged and screenshotted

USAGE
  python luma_bot.py login                 # step 1: sign in to Luma, then close
  python luma_bot.py run                   # step 2: walk the queue and register
  python luma_bot.py run --limit 10        # try on 10 events first
  python luma_bot.py run --dry             # scan only, do not click Register
  python luma_bot.py run --input outputs/register_queue.csv

STATE FILES
  outputs/.luma-profile/     persistent browser profile (your login lives here)
  outputs/registration_log.csv    one row per attempt, appended live
  outputs/shots/                  screenshots of anything that needs your eyes
"""
import argparse, csv, json, os, random, re, sys, time
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
PROFILE = os.path.join(OUT, ".luma-profile")
SHOTS = os.path.join(OUT, "shots")
LOG = os.path.join(OUT, "registration_log.csv")
PROFILE_JSON = os.path.join(OUT, "profile.json")
DEFAULT_QUEUE = os.path.join(OUT, "register_queue.csv")

for d in (OUT, SHOTS, PROFILE):
    os.makedirs(d, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# ----------------------------------------------------------------- profile.json
DEFAULT_ME = {
    "name": "Oscar",
    "email": "you@example.com",
    "company": "Trilumi Limited",
    "title": "Founder",
    "linkedin": "https://www.linkedin.com/in/your-handle",
    "telegram": "@yourhandle",
    "answers": {}          # extra free-text question label -> answer
}


def load_me():
    if not os.path.exists(PROFILE_JSON):
        json.dump(DEFAULT_ME, open(PROFILE_JSON, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"[!] created {PROFILE_JSON} — EDIT IT before running (name/email/company).")
    return json.load(open(PROFILE_JSON, encoding="utf-8"))


# ----------------------------------------------------------------- log helpers
FIELDS = ["ts", "url", "event", "day", "start", "result", "detail", "shot"]


def log_open():
    new = not os.path.exists(LOG)
    f = open(LOG, "a", newline="", encoding="utf-8-sig")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new:
        w.writeheader()
    return f, w


# ----------------------------------------------------------------- selectors
REGISTER_WORDS = ["register", "rsvp", "get ticket", "get tickets", "join",
                  "request to join", "request invite", "apply", "add to waitlist",
                  "join waitlist", "i'm going", "get access", "claim", "sign up",
                  "join the waitlist", "request to attend"]
DONE_WORDS = ["you're in", "you are in", "you're going", "youre going",
              "view ticket", "see you there", "you're registered",
              "you are registered", "registered", "you're on the list",
              "you have a ticket", "manage your ticket", "cancel registration"]
SOLD_WORDS = ["sold out", "no spots left", "registration closed", "waitlist closed"]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def find_register_button(pg):
    """Return (element, label) for the most likely registration CTA."""
    best = None
    for sel in ["button", "a[role='button']", "div[role='button']"]:
        for el in pg.query_selector_all(sel):
            try:
                if not el.is_visible():
                    continue
                t = norm(el.inner_text())
            except Exception:
                continue
            if not t or len(t) > 60:
                continue
            for w in REGISTER_WORDS:
                if t == w or t.startswith(w):
                    # prefer the biggest / most specific one
                    score = len(w)
                    if best is None or score > best[0]:
                        best = (score, el, el.inner_text().strip())
    return (best[1], best[2]) if best else (None, None)


def body_text(pg):
    try:
        return norm(pg.inner_text("body"))
    except Exception:
        return ""


def classify(pg):
    """Return (state, detail)."""
    txt = body_text(pg)
    if "rate limit hit" in txt or re.search(r"\b429\b", txt):
        return "RATELIMIT", ""
    for w in DONE_WORDS:
        if w in txt:
            return "ALREADY", w
    for w in SOLD_WORDS:
        if w in txt:
            return "SOLD_OUT", w
    return "OPEN", ""


def fill_form(pg, me):
    """Fill visible inputs inside the registration modal."""
    filled = []
    # text inputs / textareas
    for el in pg.query_selector_all("input[type='text'], input[type='email'], "
                                    "input:not([type]), textarea"):
        try:
            if not el.is_visible():
                continue
        except Exception:
            continue
        ph = norm(el.get_attribute("placeholder"))
        name = norm(el.get_attribute("name"))
        aria = norm(el.get_attribute("aria-label"))
        label = " ".join(x for x in (ph, name, aria) if x)
        val = el.input_value()
        if val:
            filled.append(f"(prefilled){label}")
            continue
        answer = None
        low = label
        if "email" in low:
            answer = me["email"]
        elif "name" in low and "company" not in low and "user" not in low:
            answer = me["name"]
        elif "company" in low or "organisation" in low or "organization" in low:
            answer = me["company"]
        elif "title" in low or "role" in low or "position" in low:
            answer = me["title"]
        elif "linkedin" in low:
            answer = me["linkedin"]
        elif "telegram" in low or "whatsapp" in low or "phone" in low:
            answer = me["telegram"]
        if answer is None:
            for k, v in me.get("answers", {}).items():
                if norm(k) in low:
                    answer = v
                    break
        if answer:
            try:
                el.click()
                el.fill(answer)
                filled.append(f"{label}={answer}")
            except Exception:
                pass
    # required dropdowns
    for sel in pg.query_selector_all("select"):
        try:
            if sel.is_visible() and not sel.input_value():
                opts = sel.query_selector_all("option")
                if len(opts) > 1:
                    sel.select_option(index=1)
                    filled.append("select->opt1")
        except Exception:
            pass
    # required checkboxes (e.g. agree to terms)
    for cb in pg.query_selector_all("input[type='checkbox']"):
        try:
            if cb.is_visible() and not cb.is_checked():
                cb.check()
                filled.append("checkbox")
        except Exception:
            pass
    return filled


def click_submit(pg):
    """Click the final confirm inside the modal."""
    for w in ["register", "rsvp", "confirm", "submit", "continue", "join",
              "request", "get ticket", "complete registration", "send request",
              "apply", "finish", "done"]:
        for el in pg.query_selector_all("button"):
            try:
                if not el.is_visible():
                    continue
                if norm(el.inner_text()) == w or norm(el.inner_text()).startswith(w):
                    el.click()
                    return el.inner_text().strip()
            except Exception:
                continue
    return None


# ----------------------------------------------------------------- main flows
def check_login(timeout=25000):
    """Headless probe: is the saved profile actually signed in to Luma?

    Returns True / False. Launches Chromium for a few seconds, so call it
    sparingly (once per run, not per event).
    """
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                PROFILE, headless=True, viewport={"width": 900, "height": 700},
                user_agent=UA, args=["--disable-blink-features=AutomationControlled"])
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto("https://luma.com/dashboard", wait_until="domcontentloaded",
                    timeout=timeout)
            pg.wait_for_timeout(1500)
            ok = "signin" not in (pg.url or "").lower()
            ctx.close()
            return ok
    except Exception as e:
        print("[!] login check failed:", str(e)[:120])
        return False


def do_login(wait_minutes=15):
    """Open Chrome on the Luma sign-in page and detect the login automatically.

    A second background tab keeps reloading /dashboard; the moment it stops
    bouncing to /signin we know the session is live, so the window closes itself.
    No need to sit and press ENTER.
    """
    me = load_me()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, viewport={"width": 1280, "height": 900},
            user_agent=UA, args=["--disable-blink-features=AutomationControlled"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://luma.com/signin", wait_until="domcontentloaded")
        probe = ctx.new_page()
        print("\n>>> Chrome opened on the Luma sign-in page.")
        print(">>> Sign in (Google / Apple / email magic link). "
              "The window closes by itself once it detects you are in.\n")

        import time as _t
        deadline = _t.time() + wait_minutes * 60
        ok = False
        while _t.time() < deadline:
            _t.sleep(5)
            try:
                probe.goto("https://luma.com/dashboard", wait_until="domcontentloaded",
                           timeout=20000)
                _t.sleep(1.5)
                if "signin" not in (probe.url or "").lower():
                    ok = True
                    break
            except Exception:
                pass
        ctx.close()
    if ok:
        print("[ok] logged in — session saved in", PROFILE)
    else:
        print(f"[!] no login detected within {wait_minutes} min. "
              f"Run this again and sign in (or press ENTER next time).")
    return ok


DONE_STATES = {"REGISTERED", "REQUESTED", "WAITLISTED", "ALREADY", "SOLD_OUT",
               "WOULD_REGISTER"}


def load_queue(path, limit, only=None, resume=True):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if only:
        rows = [r for r in rows if only.lower() in (r.get("day", "") or "").lower()]
    skipped = 0
    if resume and os.path.exists(LOG):
        done = set()
        for r in csv.DictReader(open(LOG, encoding="utf-8-sig")):
            if r.get("result") in DONE_STATES:
                done.add((r.get("url") or "").split("?")[0])
        before = len(rows)
        rows = [r for r in rows
                if (r.get("register") or "").split("?")[0] not in done]
        skipped = before - len(rows)
    if skipped:
        print(f"[i] resume: {skipped} already finished, skipping")
    if limit:
        rows = rows[:limit]
    return rows


def do_run(args):
    me = load_me()
    queue = load_queue(args.input, args.limit, args.day, resume=not args.fresh)
    print(f"[i] queue: {len(queue)} events from {args.input}")
    print(f"[i] throttle: {args.delay}s between events, dry-run={args.dry}")

    f, w = log_open()
    results = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=args.headless,
            viewport={"width": 1280, "height": 900}, user_agent=UA,
            args=["--disable-blink-features=AutomationControlled"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()

        for i, row in enumerate(queue, 1):
            url = (row.get("register") or "").strip()
            name = row.get("name") or row.get("t2049_name") or ""
            if not url:
                continue
            print(f"\n[{i}/{len(queue)}] {name[:60]}  {url}")
            result, detail, shot = attempt(pg, url, name, me, args)
            rec = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "url": url,
                   "event": name, "day": row.get("day", ""), "start": row.get("start", ""),
                   "result": result, "detail": detail, "shot": shot}
            w.writerow(rec)
            f.flush()
            results.append(rec)
            print(f"    -> {result} {detail}")
            if result == "RATELIMIT":
                print("    ... rate limited, cooling off 90s")
                time.sleep(90)
            time.sleep(args.delay + random.uniform(0, 2.5))
        ctx.close()
    f.close()

    from collections import Counter
    print("\n=== SUMMARY ===")
    for k, v in Counter(r["result"] for r in results).most_common():
        print(f"  {k:<14} {v}")
    print(f"\nfull log: {LOG}")


def attempt(pg, url, name, me, args):
    shot = ""
    for tries in range(2):
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(2500)
        except Exception as e:
            return "NAV_ERROR", str(e)[:80], ""

        state, detail = classify(pg)
        if state == "RATELIMIT":
            if tries == 0:
                time.sleep(45)
                continue
            return "RATELIMIT", "", ""
        if state == "ALREADY":
            return "ALREADY", detail, ""
        if state == "SOLD_OUT":
            # try waitlist
            btn, label = find_register_button(pg)
            if btn and "waitlist" in norm(label):
                if args.dry:
                    return "WAITLIST_AVAILABLE", label, ""
                btn.click()
                pg.wait_for_timeout(2000)
                fill_form(pg, me)
                click_submit(pg)
                pg.wait_for_timeout(2500)
                return "WAITLISTED", label, ""
            return "SOLD_OUT", detail, ""

        if state != "OPEN":
            return state, detail, ""

        btn, label = find_register_button(pg)
        if not btn:
            shot = os.path.join(SHOTS, re.sub(r"[^A-Za-z0-9]", "_", url)[-40:] + ".png")
            try:
                pg.screenshot(path=shot, full_page=False)
            except Exception:
                shot = ""
            return "NO_BUTTON", "", shot

        if args.dry:
            return "WOULD_REGISTER", label, ""

        try:
            btn.click()
        except Exception as e:
            return "CLICK_FAILED", str(e)[:60], ""
        pg.wait_for_timeout(2200)

        filled = fill_form(pg, me)
        sub = click_submit(pg)
        pg.wait_for_timeout(3500)

        txt = body_text(pg)
        if re.search(r"rate limit", txt):
            return "RATELIMIT", "", ""
        for wd in ["you're in", "you are in", "you're going", "see you there",
                   "you're registered", "you are registered", "view ticket",
                   "you're on the list", "confirmed", "success"]:
            if wd in txt:
                return "REGISTERED", (sub or label) + " | " + ";".join(filled[:4]), ""
        for wd in ["request", "approval", "pending", "waiting for host",
                   "we'll let you know", "host will review"]:
            if wd in txt:
                return "REQUESTED", (sub or label) + " | " + ";".join(filled[:4]), ""
        for wd in ["waitlist", "waiting list"]:
            if wd in txt:
                return "WAITLISTED", (sub or label), ""
        shot = os.path.join(SHOTS, re.sub(r"[^A-Za-z0-9]", "_", url)[-40:] + ".png")
        try:
            pg.screenshot(path=shot, full_page=False)
        except Exception:
            shot = ""
        return "NEEDS_REVIEW", (sub or label) + " | " + txt[:120], shot
    return "UNKNOWN", "", ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["login", "run"])
    ap.add_argument("--input", default=DEFAULT_QUEUE)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=9.0)
    ap.add_argument("--day", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore registration_log.csv and redo everything")
    a = ap.parse_args()
    if a.mode == "login":
        do_login()
    else:
        do_run(a)
