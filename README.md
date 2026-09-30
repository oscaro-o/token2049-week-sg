# TOKEN2049 Week Singapore 2026 — Free Side-Event Board

A single-file, zero-backend web app that lists **every free side event** during TOKEN2049 Week Singapore (Oct 2026), so a small team can fan out and register in bulk — then decide on site which ones to actually attend.

Live: **https://oscaro-o.github.io/token2049-week-sg/**

---

## Why this exists

TOKEN2049 Week has **380 side events**. The official sheet is a spreadsheet; the official site paginates. Neither answers the two questions that actually matter:

1. Which of these are **free**?
2. Which can I **get into**, and is it one click or does a host have to approve me?

So we pulled the data, verified each Luma page, and put it in one page you can send to your team.

### What the data says

| | |
|---|---|
| Total official side events | 380 |
| Free events (verified) | 357 |
| Hosted on Luma | 306 |
| **One-click instant join** | **38** |
| **Require host approval** | **247** |
| Already sold out | 24 |

**89% of free events require host approval.** That is the real bottleneck — registering 300 events does not get you into 300 rooms. Your approval rate is decided by one thing: the free-text intro you write on each form. See `data/register_all_free.csv` and the `profile.json` template in the source workspace.

---

## Using the board

1. **Log in to Luma once.** Click *Log in to Luma* in the top card. One session covers every `lu.ma` link you open afterwards.
2. **Filter.** Pick a day, or switch to `one-click only` if you want the 38 that confirm instantly.
3. **Register.** Hit *Open visible ↗* to open 40 tabs at a time (350 ms apart), or *Copy links* to paste into a group chat and split the work.

## One-button registration

```bash
python scripts/serve.py           # opens http://127.0.0.1:8765/
```

Click the **⚡ Register** button bottom-right, pick a scope, hit *Register all*. It then:

1. checks whether your saved Chrome profile is signed in to Luma
2. if not, opens Chrome on the sign-in page — **the run starts by itself the moment you are in**, no second click
3. walks the queue, filling and submitting each form, with live progress in the panel

Stop any time; progress is kept and the next start resumes. Scopes: all 320 / the 38 one-click / a single day.

**Why a local helper instead of a plain web button?** Two hard browser boundaries, neither of which is a bug:

1. a page on another origin cannot click into `luma.com`, and it has no access to your Luma session;
2. Chrome's Local Network Access blocks any *website* from reaching `127.0.0.1` — so the hosted copy can never drive the helper either.

So the agent serves its own copy of the board at `http://127.0.0.1:8765`, and that is where the button is live. The hosted copy stays read-only — that is the one you share with the team. Nothing is uploaded anywhere.

Done-ticks are stored in **your own browser** (`localStorage`), so everyone keeps their own progress. Share the link freely.

- Badge **instant** = joins immediately
- Badge **approval** = host must approve; write a real intro
- Badge **soldout** = skip
- Badge **unknown** = not yet scanned / not on Luma

---

## Files

```
index.html                      the whole app, self-contained (108 KB, no build step)
data/
  events_all.csv                all 380 official events, scored
  events_free_luma.csv          free + Luma subset
  register_all_free.csv         the 320-row registration queue (Luma first, then by relevance)
  free_luma_instant_all.csv     the 38 one-click events
  luma_scan.csv                 per-URL Luma verification (free / sold out / approval / spots left)
  my_schedule.csv               17 clash-free picks
  token2049_shortlist.ics       import into your calendar
  api_events.json               raw dump from the official API
scripts/
  build_lists.py                fetch official API -> score -> CSV
  scan_luma.py                  verify each Luma page (throttled; Luma rate-limits hard)
  build_all_queue.py            merge -> registration queue
  enrich.py                     join queue with scan results
  build_site.py                 emit index.html
  luma_bot.py                   registration engine (Playwright, persistent profile)
  one_click.py                  ensure-login-then-register in one command
  serve.py                      local agent: serves the board + /api/start|stop|status
  submit_side_event.py          pre-fill the official "host your own side event" forms
  upload_ftp.py                 push the board to Hostinger/trilumi.xyz over FTP TLS
  refresh.py                    re-pull API, diff, rebuild
```

## Data source

Official endpoint, no auth required:

```
https://week.token2049.com/api/events
```

Luma pages embed their full event payload in `__NEXT_DATA__`, including `ticket_info` (`is_free`, `is_sold_out`, `spots_remaining`, `require_approval`) — readable without logging in.

⚠️ **Luma rate-limits aggressively.** Concurrent fetching gets HTTP 429 after roughly 65 pages. Serialize requests with a 4.5–6 s delay and back off 60 s × n on 429.

---

## Rebuilding

```bash
pip install openpyxl
python scripts/build_lists.py      # -> data/events_all.csv
LUMA_DELAY=5 python scripts/scan_luma.py
python scripts/build_all_queue.py
python scripts/enrich.py
python scripts/build_site.py       # -> index.html
```

Deploy is just: copy `index.html` anywhere. It has no dependencies.

---

Built by Trilumi Limited (Hong Kong) · trilumi.xyz
