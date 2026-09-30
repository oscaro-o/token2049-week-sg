# -*- coding: utf-8 -*-
"""Render outputs/plan.html — one-page control board for TOKEN2049 Week SG 2026."""
import csv, html, json, os
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return []
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


sched = load("my_schedule.csv")
queue = load("register_queue_enriched.csv") or load("register_queue.csv")
allfree = load("events_free_luma.csv")


def badge(r):
    if r.get("luma_soldout") == "YES":
        return '<i class="bd bad">sold out</i>'
    if r.get("scan") == "OK":
        if r.get("luma_approval") == "YES":
            return '<i class="bd warn">host approval</i>'
        if r.get("luma_free") == "YES":
            return '<i class="bd ok">free · instant</i>'
        return '<i class="bd">paid</i>'
    return '<i class="bd dim">not scanned</i>'


def cards(rows, with_register=True):
    out = []
    for r in rows:
        reg = r.get("register", "")
        cls = "luma" if "luma" in reg else "other"
        out.append(f"""
  <tr data-day="{html.escape(r.get('day',''))}" data-cat="{html.escape(r.get('category',''))}"
      data-name="{html.escape((r.get('name','')).lower())}">
    <td class="when"><b>{html.escape(r.get('day',''))}</b><br>{html.escape(r.get('start',''))}–{html.escape(r.get('end',''))}</td>
    <td>
      <div class="nm">{html.escape(r.get('name',''))}</div>
      <div class="meta">{html.escape(r.get('organiser',''))} · {html.escape(r.get('category',''))} · {html.escape(r.get('type',''))}</div>
      <div class="meta dim">{html.escape((r.get('venue','') or '')[:60])}</div>
      <div class="tags">{''.join(f'<span>{html.escape(t)}</span>' for t in (r.get('themes','') or '').split(',') if t)}{badge(r)}</div>
    </td>
    <td class="score">{r.get('score','')}</td>
    <td class="act"><a class="btn {cls}" href="{html.escape(reg)}" target="_blank" rel="noopener">Register ↗</a></td>
  </tr>""")
    return "\n".join(out)


def table(rows, tid):
    return f"""
<div class="tablewrap">
<table id="{tid}">
  <thead><tr><th class="when">When</th><th>Event</th><th>Fit</th><th></th></tr></thead>
  <tbody>
{cards(rows)}
  </tbody>
</table>
</div>"""


counts = {
    "all": len(load("events_all.csv")),
    "free": sum(1 for r in load("events_all.csv") if r["type"] in ("Free", "Free & Paid")),
    "luma": len(allfree),
    "queue": len(queue),
    "sched": len(sched),
}

HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TOKEN2049 Week Singapore 2026 — Trilumi control board</title>
<style>
:root{{--bg:#f7f8fa;--card:#fff;--line:#e3e6ec;--ink:#12161c;--dim:#6b7280;
--accent:#1f5f8b;--accent2:#0f3d5c;--ok:#0a7d4b;--warn:#b45309;--chip:#eef2f7}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}}
header{{background:linear-gradient(135deg,#0f3d5c,#1f5f8b);color:#fff;padding:26px 30px}}
header h1{{margin:0 0 6px;font-size:22px;letter-spacing:.2px}}
header p{{margin:0;opacity:.85;font-size:14px}}
.wrap{{max-width:1180px;margin:0 auto;padding:22px}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 22px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:120px}}
.stat b{{display:block;font-size:22px;line-height:1.1}}
.stat span{{font-size:12px;color:var(--dim)}}
.alert{{background:#fff6e6;border:1px solid #f0d9a8;border-left:4px solid var(--warn);
border-radius:8px;padding:14px 16px;margin-bottom:18px}}
.alert b{{color:var(--warn)}}
h2{{font-size:17px;margin:26px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}}
.toolbar{{display:flex;gap:10px;align-items:center;margin:12px 0;flex-wrap:wrap}}
input[type=search],select{{padding:8px 10px;border:1px solid var(--line);border-radius:8px;
font:inherit;background:#fff;color:var(--ink)}}
input[type=search]{{min-width:260px}}
.tablewrap{{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:auto;max-height:70vh}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th{{position:sticky;top:0;background:#f0f2f6;text-align:left;padding:10px 12px;
font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim);z-index:2}}
td{{padding:11px 12px;border-top:1px solid var(--line);vertical-align:top}}
td.when{{white-space:nowrap;font-size:13px;width:110px}}
.nm{{font-weight:600}}
.meta{{font-size:12px;color:var(--dim)}}
.dim{{opacity:.75}}
.tags{{margin-top:5px;display:flex;gap:5px;flex-wrap:wrap}}
.tags span{{background:var(--chip);border-radius:20px;padding:2px 8px;font-size:11px;color:var(--accent2)}}
.bd{{font-style:normal;border-radius:20px;padding:2px 8px;font-size:11px;font-weight:700;
background:#e8eef5;color:#33475b}}
.bd.ok{{background:#e3f5ec;color:#0a7d4b}}
.bd.warn{{background:#fdf1de;color:#b45309}}
.bd.bad{{background:#fde8e8;color:#a32121}}
.bd.dim{{background:#f0f1f4;color:#8b93a1}}
td.score{{width:46px;text-align:center;font-weight:700;color:var(--accent2)}}
td.act{{width:110px;white-space:nowrap}}
.btn{{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;
padding:7px 12px;border-radius:7px;font-size:13px;font-weight:600}}
.btn.other{{background:#7a5cc4}}
.btn:hover{{background:var(--accent2)}}
footer{{color:var(--dim);font-size:12px;padding:30px;text-align:center}}
details{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:12px 0}}
details summary{{cursor:pointer;font-weight:600}}
</style></head><body>
<header>
  <h1>TOKEN2049 Week Singapore 2026 — Trilumi control board</h1>
  <p>7–8 Oct main conference (Marina Bay Sands) · side events 5–11 Oct · built {datetime.now():%Y-%m-%d %H:%M}</p>
</header>
<div class="wrap">

<div class="alert">
  <b>Two hard constraints.</b>
  (1) TOKEN2049 Origins hackathon applications closed 18 Sep; participants were announced 28 Sep — you cannot enter it now, only the 2027 waitlist.
  (2) The Singapore F1 Grand Prix runs 9–11 Oct on the same bay. Hotel and venue inventory in Marina Bay is effectively gone — book flights and rooms today, and do not plan an evening event for 9–11 Oct.
</div>

<div class="stats">
  <div class="stat"><b>{counts['all']}</b><span>side events listed</span></div>
  <div class="stat"><b>{counts['free']}</b><span>free</span></div>
  <div class="stat"><b>{counts['luma']}</b><span>free &amp; on Luma</span></div>
  <div class="stat"><b>{counts['queue']}</b><span>worth registering</span></div>
  <div class="stat"><b>{counts['sched']}</b><span>clash-free plan</span></div>
  <div class="stat"><b>0</b><span>green / carbon events</span></div>
</div>

<details>
  <summary>The one strategic finding</summary>
  <p>Out of 380 listed side events, <b>zero</b> mention carbon, REC, green assets, ESG or energy.
  Meanwhile 14 free events already compete on RWA / tokenization. RWA is crowded; green assets onchain
  is an empty room with a real, dated demand driver behind it (EU CBAM entered its definitive regime
  on 1 Jan 2026). That is where your side event should sit.</p>
</details>

<h2>1. Your clash-free schedule ({counts['sched']} slots)</h2>
{table(sched, 't-sched')}

<h2>2. Registration queue ({counts['queue']} — RSVP is free and non-binding)</h2>
<div class="toolbar">
  <input type="search" id="q2" placeholder="filter by name, organiser or keyword…">
  <select id="d2"><option value="">all days</option></select>
</div>
{table(queue, 't-queue')}

<h2>3. Every free Luma event ({counts['luma']})</h2>
<div class="toolbar">
  <input type="search" id="q3" placeholder="filter…">
  <select id="d3"><option value="">all days</option></select>
  <select id="c3"><option value="">all categories</option></select>
</div>
{table(allfree, 't-all')}

<footer>Data: official TOKEN2049 Week API + the official side-events sheet.
Regenerate with <code>scripts/build_lists.py</code> → <code>build_queue.py</code> → <code>build_html.py</code>.</footer>
</div>
<script>
function bind(tid, qid, did, cid){{
  const tb = document.querySelector('#'+tid+' tbody');
  if(!tb) return;
  const rows = [...tb.rows];
  const days = [...new Set(rows.map(r=>r.dataset.day))].filter(Boolean).sort();
  const cats = [...new Set(rows.map(r=>r.dataset.cat))].filter(Boolean).sort();
  if(did){{const d=document.getElementById(did);
    days.forEach(x=>{{const o=document.createElement('option');o.value=x;o.textContent=x;d.appendChild(o);}});}}
  if(cid){{const c=document.getElementById(cid);
    cats.forEach(x=>{{const o=document.createElement('option');o.value=x;o.textContent=x;c.appendChild(o);}});}}
  const q = qid ? document.getElementById(qid) : null;
  const dsel = did ? document.getElementById(did) : null;
  const csel = cid ? document.getElementById(cid) : null;
  function run(){{
    const s = (q?q.value:'').toLowerCase();
    const d = dsel?dsel.value:'';
    const c = csel?csel.value:'';
    rows.forEach(r=>{{
      const ok = (!s || r.dataset.name.includes(s)) && (!d || r.dataset.day===d) && (!c || r.dataset.cat===c);
      r.style.display = ok ? '' : 'none';
    }});
  }}
  [q,dsel,csel].forEach(el=>el && el.addEventListener('input', run));
}}
bind('t-queue','q2','d2',null);
bind('t-all','q3','d3','c3');
</script>
</body></html>"""

p = os.path.join(OUT, "plan.html")
open(p, "w", encoding="utf-8").write(HTML)
print("->", p, f"({len(HTML)} bytes)")
