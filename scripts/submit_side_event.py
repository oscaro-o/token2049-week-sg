# -*- coding: utf-8 -*-
"""
submit_side_event.py — pre-fills the two official TOKEN2049 "host a side event"
forms and leaves them open on screen for you to review and press SUBMIT.

  1) Venue / space request (public Typeform)
     https://forms.token2049.com/r/A7G9vW
     -> asks TOKEN2049 to find you a space inside MBS or a curated venue nearby

  2) Directory listing (needs sign-in)
     https://week.token2049.com/dashboard/event/create
     -> puts your event into the official side-event directory (free)

It never presses the final submit for you. You read it, you own it.

Usage:
    python submit_side_event.py            # both forms
    python submit_side_event.py venue      # only the venue form
    python submit_side_event.py listing    # only the directory listing
"""
import json, os, sys
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
CFG = os.path.join(OUT, "side_event.json")
PROFILE = os.path.join(OUT, ".luma-profile")

DEFAULT = {
    "first_name": "Oscar",
    "last_name": "",
    "email": "you@example.com",
    "telegram_or_whatsapp": "+852 0000 0000",
    "company": "Trilumi Limited",
    "event_date": "7 October",
    "start_time": "07:45",
    "end_time": "09:15",
    "pax": "25",
    "event_type": "Networking",
    "budget_usd": "4000",
    "extra": ("Closed working breakfast, 25 named guests. Theme: APAC green assets "
              "(REC / carbon) onchain — CBAM-driven demand from SEA exporters. "
              "Needs: private room, breakfast for 25, 1 screen + HDMI, no stage, "
              "no AV crew. Walking distance from Marina Bay Sands / Raffles Place MRT."),
    "event_name": "Carbon Is Now a Customs Duty — APAC Green Assets Onchain",
    "venue_name": "TBC (requesting TOKEN2049 curated space)",
    "description": ("Invite-only working breakfast for 25 named guests. CBAM entered "
                    "its definitive regime on 1 Jan 2026: SEA exporters to the EU now "
                    "need verified carbon data, and that demand is a tax, not a virtue "
                    "signal. 90 minutes, no panels. Framing, a live walkthrough of a "
                    "permissioned-chain REC issuance stack, structured roundtable, and "
                    "a pilot term sheet signed before anyone leaves."),
    "registration_link": "https://lu.ma/",
    "category": "Networking",
    "ticket_type": "Free"
}

if not os.path.exists(CFG):
    json.dump(DEFAULT, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[!] created {CFG} — EDIT IT, then run again.")
    sys.exit(0)

cfg = json.load(open(CFG, encoding="utf-8"))


def fill(page, texts, value):
    """Type into the first visible input whose placeholder/label matches."""
    if value in (None, ""):
        return False
    for t in texts:
        for el in page.query_selector_all("input, textarea"):
            try:
                if not el.is_visible():
                    continue
            except Exception:
                continue
            ph = " ".join([el.get_attribute("placeholder") or "",
                           el.get_attribute("name") or "",
                           el.get_attribute("aria-label") or ""]).lower()
            if t.lower() in ph:
                try:
                    el.click()
                    el.fill(str(value))
                    el.press("Tab")
                    return True
                except Exception:
                    pass
    return False


def click_text(page, words):
    for w in words:
        for el in page.query_selector_all("button, div[role='button'], label, span"):
            try:
                if not el.is_visible():
                    continue
                if (el.inner_text() or "").strip().lower() == w.lower():
                    el.click()
                    return True
            except Exception:
                continue
    return False


def venue_form(p):
    print("\n>>> opening venue request form ...")
    pg = p.new_page()
    pg.goto("https://forms.token2049.com/r/A7G9vW", wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    click_text(pg, ["Start", "Get started", "Begin", "Next"])
    pg.wait_for_timeout(1500)
    for _ in range(6):
        fill(pg, ["first name"], cfg["first_name"])
        fill(pg, ["last name"], cfg["last_name"])
        fill(pg, ["email"], cfg["email"])
        fill(pg, ["telegram", "whatsapp"], cfg["telegram_or_whatsapp"])
        fill(pg, ["company", "project"], cfg["company"])
        fill(pg, ["date"], cfg["event_date"])
        fill(pg, ["start"], cfg["start_time"])
        fill(pg, ["end"], cfg["end_time"])
        fill(pg, ["size", "pax"], cfg["pax"])
        fill(pg, ["type"], cfg["event_type"])
        fill(pg, ["budget"], cfg["budget_usd"])
        fill(pg, ["additional", "details", "should know"], cfg["extra"])
        click_text(pg, ["Next", "Continue", "OK"])
        pg.wait_for_timeout(1200)
    print("    filled. REVIEW IT AND PRESS SUBMIT YOURSELF.")
    return pg


def listing_form(p):
    print("\n>>> opening directory listing form (sign in if asked) ...")
    pg = p.new_page()
    pg.goto("https://week.token2049.com/dashboard/event/create",
            wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    print("    if you land on a sign-in page, sign in, then press ENTER here.")
    input("    ENTER to continue ...")
    for _ in range(3):
        fill(pg, ["event name", "name"], cfg["event_name"])
        fill(pg, ["venue", "location", "address"], cfg["venue_name"])
        fill(pg, ["description", "about"], cfg["description"])
        fill(pg, ["registration", "link", "url"], cfg["registration_link"])
        fill(pg, ["date"], cfg["event_date"])
        fill(pg, ["start"], cfg["start_time"])
        fill(pg, ["end"], cfg["end_time"])
        pg.wait_for_timeout(800)
    print("    filled as far as the form allows. REVIEW AND SUBMIT YOURSELF.")
    return pg


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False,
                              args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(viewport={"width": 1400, "height": 950})
        pages = []
        if which in ("both", "venue"):
            pages.append(venue_form(ctx))
        if which in ("both", "listing"):
            pages.append(listing_form(ctx))
        print("\n>>> browser stays open. Finish both forms, then close the window.")
        input("    press ENTER here when you are done ...")
        b.close()


if __name__ == "__main__":
    main()
