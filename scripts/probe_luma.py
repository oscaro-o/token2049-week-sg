# -*- coding: utf-8 -*-
"""Probe a few Luma pages with a real browser and dump interactive elements."""
import sys, json, re
from playwright.sync_api import sync_playwright

URLS = [
    "https://luma.com/m54egbft",
    "https://luma.com/rwasummit",
    "https://luma.com/ydaq5h18",
]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width": 1280, "height": 900},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    pg = ctx.new_page()
    for u in URLS:
        print("=" * 80)
        print(u)
        try:
            pg.goto(u, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3500)
        except Exception as e:
            print(" nav error", e)
            continue
        print(" title:", pg.title())
        # buttons
        btns = pg.query_selector_all("button")
        for b_ in btns[:25]:
            t = (b_.inner_text() or "").strip().replace("\n", " ")
            if t:
                print("  BTN:", t[:80])
        print("  LINKS:")
        for a in pg.query_selector_all("a")[:20]:
            t = (a.inner_text() or "").strip().replace("\n", " ")
            if t:
                print("   A:", t[:60], "|", a.get_attribute("href"))
        body = pg.inner_text("body")[:1200]
        print("  BODY:", body.replace("\n", " | ")[:1000])
    b.close()
