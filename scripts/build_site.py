# -*- coding: utf-8 -*-
"""
build_site.py — emit site/index.html, a fully self-contained (offline-capable)
catalogue of every FREE TOKEN2049 Week Singapore 2026 side event.

Everything is inlined into one HTML file so it can be dropped on any static host
( trilumi.xyz, GitHub Pages, S3, or just opened from disk ).

    python build_site.py

Canonial / OG URL is set by env so the same file can be published at several
addresses without editing the template:

    SITE_URL=https://trilumi.xyz/token2049/ python build_site.py
"""
import csv, html, json, os, re, sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)

SITE_URL = os.environ.get(
    "SITE_URL", "https://oscaro-o.github.io/token2049-week-sg/").strip()


def load(name):
    p = os.path.join(OUT, name)
    return list(csv.DictReader(open(p, encoding="utf-8-sig"))) if os.path.exists(p) else []


def key(u):
    return re.sub(r"https?://(www\.)?", "", (u or "")).strip("/").lower()


scan = {}
for r in load("luma_scan.csv"):
    if r.get("status") == "OK":
        scan[key(r.get("url"))] = r

rows = load("events_all.csv")
free = [r for r in rows if r["type"] in ("Free", "Free & Paid")]

items = []
for r in free:
    reg = (r.get("register") or "").strip()
    s = scan.get(key(reg), {})
    is_luma = "luma.com" in reg or "lu.ma" in reg
    if s:
        if s.get("sold_out") == "YES":
            st = "soldout"
        elif s.get("require_approval") == "YES":
            st = "approval"
        elif s.get("is_free") == "YES":
            st = "instant"
        else:
            st = "paid"
    else:
        st = "unknown"
    items.append({
        "k": r.get("date", ""),          # ISO date — used for every sort, never the label
        "d": r.get("day", ""),           # display label, e.g. "Tue 6 Oct"
        "s": r.get("start", ""),
        "e": r.get("end", ""),
        "n": r.get("name", ""),
        "o": r.get("organiser", ""),
        "c": r.get("category", ""),
        "v": (r.get("venue", "") or "")[:70],
        "u": reg,
        "p": "luma" if is_luma else "other",
        "st": st,
        "f": int(r.get("score") or 0),
        "th": [t for t in (r.get("themes") or "").split(",") if t],
    })

# "Mon 5 Oct" sorts alphabetically (Fri, Mon, Sat, Sun, Thu, Tue, Wed) — always
# sort on the ISO date in "k", never on the display label in "d".
items.sort(key=lambda x: (-x["f"], x["k"], x["s"]))

DATA = json.dumps(items, ensure_ascii=False)
STATS = {
    "free": len(free),
    "luma": sum(1 for i in items if i["p"] == "luma"),
    "instant": sum(1 for i in items if i["st"] == "instant"),
    "approval": sum(1 for i in items if i["st"] == "approval"),
    "soldout": sum(1 for i in items if i["st"] == "soldout"),
    "unknown": sum(1 for i in items if i["st"] == "unknown"),
    "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
}

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TOKEN2049 Week Singapore 2026 — free side events</title>
<link rel="canonical" href="__SITE_URL__">
<meta name="description" content="__N_FREE__ free side events during TOKEN2049 Week Singapore 2026, verified one by one. __N_INSTANT__ join instantly, __N_APPROVAL__ need host approval. Filter by day, open in batches, split the work across your team.">
<meta name="robots" content="index, follow">
<meta property="og:type" content="website">
<meta property="og:title" content="TOKEN2049 Week Singapore 2026 — free side events">
<meta property="og:description" content="__N_FREE__ free side events, verified. __N_INSTANT__ one-click, __N_APPROVAL__ need host approval.">
<meta property="og:url" content="__SITE_URL__">
<meta property="og:site_name" content="Trilumi">
<meta property="og:locale" content="en_HK">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="TOKEN2049 Week Singapore 2026 — free side events">
<meta name="twitter:description" content="__N_FREE__ free side events, verified. __N_INSTANT__ one-click, __N_APPROVAL__ need host approval.">
<style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e4e7ec;--ink:#111620;--dim:#6b7280;
--a:#1f5f8b;--a2:#0f3d5c;--ok:#0a7d4b;--warn:#b45309;--bad:#a32121;--chip:#eef2f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
header{background:linear-gradient(135deg,#0f3d5c,#1f5f8b);color:#fff;padding:24px 24px 20px}
header h1{margin:0 0 4px;font-size:21px}
header p{margin:0;opacity:.85;font-size:13px}
.bar{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);
padding:10px 20px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.bar input,.bar select{padding:7px 10px;border:1px solid var(--line);border-radius:8px;
font:inherit;background:#fff;color:var(--ink)}
.bar input{min-width:220px;flex:1 1 220px}
.btn{background:var(--a);color:#fff;border:0;border-radius:8px;padding:8px 13px;
font:inherit;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{background:var(--a2)}
.btn.ghost{background:#fff;color:var(--a);border:1px solid var(--line)}
.count{margin-left:auto;font-size:13px;color:var(--dim);white-space:nowrap}
.wrap{max-width:1200px;margin:0 auto;padding:16px 20px 60px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:9px 14px}
.stat b{font-size:19px;display:block;line-height:1.1}
.stat span{font-size:11px;color:var(--dim)}
.note{background:#fff8e8;border:1px solid #f0d9a8;border-left:4px solid var(--warn);
border-radius:8px;padding:12px 14px;margin-bottom:16px;font-size:14px}
.start{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-bottom:16px}
.s1{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px}
.s1 b{display:block;margin-bottom:5px}
.s1 p{margin:0 0 9px;font-size:13px;color:var(--dim)}
.chips{padding:0 20px 6px;display:flex;gap:6px;flex-wrap:wrap}
.chips button{background:#fff;border:1px solid var(--line);border-radius:20px;padding:5px 12px;
font:inherit;font-size:13px;cursor:pointer;color:var(--a2)}
.chips button.on{background:var(--a);border-color:var(--a);color:#fff}
.agfab{position:fixed;right:16px;bottom:16px;z-index:99;background:var(--a);color:#fff;
border:0;border-radius:24px;padding:11px 16px;font:inherit;font-weight:700;cursor:pointer;
box-shadow:0 6px 18px rgba(31,95,139,.35)}
.agfab:hover{background:var(--a2)}
.ag{position:fixed;right:16px;bottom:66px;z-index:99;width:340px;max-height:76vh;overflow:auto;
background:#fff;border:1px solid var(--line);border-radius:12px;font-size:13px;
box-shadow:0 10px 34px rgba(0,0,0,.2)}
.ag-h{display:flex;align-items:center;gap:8px;padding:10px 13px;border-bottom:1px solid var(--line);
background:#f2f7fb;border-radius:12px 12px 0 0;position:sticky;top:0}
.ag-h b{flex:1}
.ag-h span{cursor:pointer;color:var(--dim);font-size:15px}
.ag-b{padding:12px 13px 14px}
.agbtn{background:var(--a);color:#fff;border:0;border-radius:9px;padding:10px;
font:inherit;font-weight:700;cursor:pointer;white-space:nowrap}
.agbtn[disabled]{opacity:.45;cursor:default}
.agbtn.g{background:#fff;color:var(--a);border:1px solid var(--line);padding:7px 13px;font-weight:600}
.agrow{display:flex;gap:8px;align-items:center;margin-bottom:9px}
.agrow select{flex:1;min-width:0;padding:7px;border:1px solid var(--line);border-radius:8px;
font:inherit;background:#fff;color:var(--ink)}
.agbar{height:7px;background:var(--chip);border-radius:9px;overflow:hidden;margin:2px 0 9px}
.agbar i{display:block;height:100%;width:0;background:var(--ok);transition:width .4s}
.agcnt{font-size:12px;color:var(--dim);line-height:1.6}
.agcnt b{color:var(--ink)}
pre.agt{background:#0f1720;color:#cfe3f2;padding:9px;border-radius:8px;font-size:11px;
max-height:140px;overflow:auto;white-space:pre-wrap;margin:6px 0 0}
.agoff{font-size:12px;color:var(--dim);line-height:1.65}
.agoff b{color:var(--ink)}
.agoff code{background:var(--chip);padding:1px 5px;border-radius:4px;font-size:11px}
@media(max-width:640px){.ag{width:calc(100vw - 32px)}}

table{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{position:sticky;top:52px;background:#f1f3f7;text-align:left;padding:9px 10px;
font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--dim);z-index:5}
td{padding:10px;border-top:1px solid var(--line);vertical-align:top;font-size:14px}
td.w{white-space:nowrap;width:104px;font-size:13px}
.nm{font-weight:600}
.mt{font-size:12px;color:var(--dim)}
.tags{margin-top:4px;display:flex;gap:4px;flex-wrap:wrap}
.tags i{font-style:normal;background:var(--chip);border-radius:20px;padding:1px 7px;
font-size:11px;color:var(--a2)}
.bd{font-style:normal;border-radius:20px;padding:1px 8px;font-size:11px;font-weight:700}
.bd.instant{background:#e3f5ec;color:var(--ok)}
.bd.approval{background:#fdf1de;color:var(--warn)}
.bd.soldout{background:#fde8e8;color:var(--bad)}
.bd.unknown{background:#f0f1f4;color:#8b93a1}
td.f{width:44px;text-align:center;font-weight:700;color:var(--a2)}
td.act{width:150px;white-space:nowrap}
.mini{font-size:12px;padding:5px 9px;border-radius:7px;border:1px solid var(--line);
background:#fff;color:var(--dim);cursor:pointer}
.mini.on{background:#e3f5ec;border-color:#9fd8bb;color:var(--ok);font-weight:700}
a.go{display:inline-block;background:var(--a);color:#fff;text-decoration:none;
padding:6px 11px;border-radius:7px;font-size:13px;font-weight:600}
a.go.other{background:#7a5cc4}
tr.done{opacity:.45}
tr.done .nm{text-decoration:line-through}
footer{color:var(--dim);font-size:12px;text-align:center;padding:24px}
@media(max-width:720px){td.act{width:auto}th,td{font-size:13px}}
</style></head><body>
<header>
  <h1>TOKEN2049 Week Singapore 2026 — every free side event</h1>
  <p>5–11 October · main conference 7–8 Oct at Marina Bay Sands · __BUILT__</p>
</header>

<div class="bar">
  <input id="q" type="search" placeholder="search name, organiser, venue, theme…">
  <select id="fd"><option value="">all days</option></select>
  <select id="fc"><option value="">all categories</option></select>
  <select id="fs">
    <option value="">all access</option>
    <option value="instant">one-click free</option>
    <option value="approval">host approval</option>
    <option value="soldout">sold out</option>
    <option value="unknown">not scanned</option>
  </select>
  <select id="fp"><option value="">all platforms</option><option value="luma">Luma only</option>
    <option value="other">non-Luma</option></select>
  <select id="fo"><option value="fit">sort: fit</option><option value="time">sort: time</option></select>
  <button class="btn" id="open">Open visible ↗</button>
  <button class="btn ghost" id="copy">Copy links</button>
  <button class="btn ghost" id="csv">Export CSV</button>
  <span class="count" id="cnt"></span>
</div>
<div class="chips" id="chips"></div>

<div class="wrap">
  <div class="stats">
    <div class="stat"><b>__N_FREE__</b><span>free events</span></div>
    <div class="stat"><b>__N_LUMA__</b><span>on Luma</span></div>
    <div class="stat"><b>__N_INSTANT__</b><span>one-click in</span></div>
    <div class="stat"><b>__N_APPROVAL__</b><span>host approval</span></div>
    <div class="stat"><b><span id="done">0</span></b><span>marked done</span></div>
  </div>

  <div class="start">
    <div class="s1"><b>1. Log in to Luma once</b>
      <p>Open Luma in a new tab and sign in. After that every button below
      already knows who you are.</p>
      <a class="btn" href="https://luma.com/signin" target="_blank" rel="noopener">Log in to Luma ↗</a></div>
    <div class="s1"><b>2. Filter</b>
      <p>Pick a day, or pick <i>one-click free</i> to only see events that let
      you straight in. Sorted by fit — the top is the good stuff.</p></div>
    <div class="s1"><b>3. Register</b>
      <p>Hit <b>Register ↗</b> on each row, or <b>Open visible</b> to fire a batch
      of tabs. Tick <b>Done</b> as you go — ticks are saved in this browser.</p></div>
  </div>

  <div class="note">
    <b>Read this before you start.</b> <b>__N_APPROVAL__ of __N_FREE__ events need host approval</b>
    — you submit, a human decides. For those, the one line you write about yourself is the whole game:
    hosts read hundreds of identical requests a day and bin them on sight. Write yours yourself,
    once, and reuse it. <b>__N_INSTANT__ events are one-click</b> — grab those first, they're free money.
  </div>

  <table><thead><tr>
    <th class="w">When</th><th>Event</th><th>Fit</th><th>Action</th>
  </tr></thead><tbody id="tb"></tbody></table>
</div>

<footer>
  Data: official TOKEN2049 Week side-event API + a per-page scan of every Luma listing.
  “free” = listed free by the organiser; the one-click / approval / sold-out badge is read from the live Luma page.
  <br>Done-ticks live in your own browser only — share the link freely, each teammate keeps their own progress.
  <br><br>Built by <a href="https://trilumi.xyz/" target="_blank" rel="noopener">Trilumi Limited</a> · Hong Kong
</footer>

<script>
const DATA = __DATA__;
const tb = document.getElementById('tb');
const done = new Set(JSON.parse(localStorage.getItem('tk2049done') || '[]'));
const save = () => localStorage.setItem('tk2049done', JSON.stringify([...done]));

// days ordered by ISO date (d.k), not by the "Tue 6 Oct" label
const days = [...new Map(DATA.filter(d=>d.k).sort((a,b)=>a.k.localeCompare(b.k)||a.s.localeCompare(b.s))
  .map(d=>[d.d,d.k])).keys()];
const cats = [...new Set(DATA.map(d=>d.c))].sort();
const fill = (id, arr) => { const s=document.getElementById(id);
  arr.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;s.appendChild(o);}); };
fill('fd', days); fill('fc', cats);

const badge = st => `<i class="bd ${st}">${st==='instant'?'one-click':st==='approval'?
  'host approval':st==='soldout'?'sold out':'not scanned'}</i>`;

let view = [];
function render(){
  const q = document.getElementById('q').value.toLowerCase();
  const fd = document.getElementById('fd').value;
  const fc = document.getElementById('fc').value;
  const fs = document.getElementById('fs').value;
  const fp = document.getElementById('fp').value;
  const fo = document.getElementById('fo').value;
  view = DATA.filter(d =>
    (!q || (d.n+' '+d.o+' '+d.v+' '+d.th.join(' ')).toLowerCase().includes(q)) &&
    (!fd || d.d===fd) && (!fc || d.c===fc) && (!fs || d.st===fs) && (!fp || d.p===fp));
  const clock = (a,b)=> (a.k||'9').localeCompare(b.k||'9') || (a.s||'').localeCompare(b.s||'');
  view.sort(fo==='time' ? clock : (a,b)=> b.f-a.f || clock(a,b));
  tb.innerHTML = view.map(d => `<tr class="${done.has(d.u)?'done':''}" data-u="${d.u}">
    <td class="w"><b>${esc(d.d)}</b><br>${esc(d.s)}–${esc(d.e)}</td>
    <td><div class="nm">${esc(d.n)}</div>
        <div class="mt">${esc(d.o)} · ${esc(d.c)}</div>
        <div class="mt">${esc(d.v)}</div>
        <div class="tags">${d.th.map(t=>`<i>${esc(t)}</i>`).join('')}${badge(d.st)}</div></td>
    <td class="f">${d.f}</td>
    <td class="act">
      <a class="go ${d.p==='luma'?'':'other'}" href="${d.u}" target="_blank" rel="noopener">Register ↗</a>
      <button class="mini ${done.has(d.u)?'on':''}" data-t="${d.u}">${done.has(d.u)?'✓ Done':'Done'}</button>
    </td></tr>`).join('');
  document.getElementById('cnt').textContent = `${view.length} shown · ${done.size} done`;
  document.getElementById('done').textContent = done.size;
}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

['q','fd','fc','fs','fp','fo'].forEach(id =>
  document.getElementById(id).addEventListener('input', ()=>{syncChips();render();}));

// day chips
const chips = document.getElementById('chips');
chips.innerHTML = ['<button data-d="" class="on">all days</button>',
  ...days.map(d=>`<button data-d="${d}">${d}</button>`),
  '<button data-d="__instant">one-click only</button>'].join('');
chips.onclick = e => {
  const b = e.target.closest('button'); if(!b) return;
  const d = b.dataset.d;
  if(d === '__instant'){
    document.getElementById('fd').value=''; document.getElementById('fs').value='instant';
  } else {
    document.getElementById('fd').value=d; document.getElementById('fs').value='';
  }
  syncChips(); render();
};
function syncChips(){
  const fd = document.getElementById('fd').value, fs = document.getElementById('fs').value;
  [...chips.children].forEach(b=>{
    const d = b.dataset.d;
    b.classList.toggle('on', d==='__instant' ? (!fd && fs==='instant') : (d===fd && !fs));
  });
}

tb.addEventListener('click', e => {
  const b = e.target.closest('button.mini'); if(!b) return;
  const u = b.dataset.t;
  done.has(u) ? done.delete(u) : done.add(u);
  save(); render();
});

document.getElementById('open').onclick = () => {
  const n = view.filter(d=>!done.has(d.u)).length;
  if(!confirm(`Open ${n} un-done events in new tabs?\\n\\nBrowsers may block a large burst — if nothing opens, allow pop-ups for this site and try again with a filter applied.`)) return;
  view.filter(d=>!done.has(d.u)).slice(0,40).forEach((d,i)=>
    setTimeout(()=>window.open(d.u,'_blank'), i*350));
};

document.getElementById('copy').onclick = async () => {
  const links = view.map(d=>d.u).join('\\n');
  try { await navigator.clipboard.writeText(links);
    alert(view.length + ' links copied.\\n\\nPaste into a note, or into your browser address bar one by one.');
  } catch(e){ prompt('Copy these links:', links); }
};

document.getElementById('csv').onclick = () => {
  const head = ['day','start','end','name','organiser','category','venue','access','register'];
  const body = view.map(d=>[d.d,d.s,d.e,d.n,d.o,d.c,d.v,d.st,d.u]
    .map(v=>`"${String(v).replace(/"/g,'""')}"`).join(','));
  const blob = new Blob([[head.join(','),...body].join('\\n')],{type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'token2049-free-events.csv'; a.click();
};

render();
</script>

<!-- ------------------------------------------------------------------ -->
<!-- registration agent bridge                                          -->
<!-- The page itself can never click into luma.com (different origin, and -->
<!-- it has no access to your Luma session). It talks to a small helper   -->
<!-- running on your own machine:  python scripts/serve.py                -->
<!-- Offline, the button stays grey and tells you how to start it.        -->
<!-- ------------------------------------------------------------------ -->
<button class="agfab" id="agfab" title="Registration agent">&#9889; Register</button>
<div class="ag" id="ag" hidden>
  <div class="ag-h"><b>Registration agent</b><span id="agx">&#10005;</span></div>
  <div class="ag-b">
    <div id="agstat" class="agcnt">connecting&hellip;</div>
    <div class="agrow">
      <select id="agscope">
        <option value="all">all free events</option>
        <option value="instant">one-click only</option>
        <optgroup label="single day" id="agdays"></optgroup>
      </select>
      <button class="agbtn" id="aggo">Register all</button>
    </div>
    <div class="agbar"><i id="agfill"></i></div>
    <div id="agcnt" class="agcnt"></div>
    <div class="agrow">
      <button class="agbtn g" id="agstop">Stop</button>
      <a class="agbtn g" id="aglog" href="#" target="_blank"
         style="text-decoration:none;display:inline-block">log &#8599;</a>
    </div>
    <pre class="agt" id="agtail"></pre>
    <div id="agoff" class="agoff">
      <b>One-click registration only works on your own machine.</b><br>
      Chrome blocks any website from reaching your computer (loopback), and a
      hosted page has no access to your Luma login anyway. Both are hard
      boundaries, not bugs.<br><br>
      On this PC run:<br>
      <code>python scripts/serve.py</code><br>
      or double-click <code>0-一键注册全部.bat</code>.<br>
      It opens its own copy of this board at
      <b>http://127.0.0.1:8765</b> &mdash; the button is live there.<br><br>
      This hosted page is still the one to share: filter, search, open batch
      tabs, tick off events.
    </div>
  </div>
</div>

<script>
(function(){
  const AGENT = 'http://127.0.0.1:8765';
  const el = id => document.getElementById(id);
  const box = el('ag'), fab = el('agfab');
  let online = false, timer = null, open = false;

  const daysSel = el('agdays');
  days.forEach(d => { const o = document.createElement('option');
    o.value = 'day|' + d; o.textContent = d; daysSel.appendChild(o); });

  fab.onclick = () => { open = !open; box.hidden = !open; if (open) poll(); };
  el('agx').onclick = () => { open = false; box.hidden = true; };

  async function jfetch(url, opt){
    const c = new AbortController();
    const t = setTimeout(() => c.abort(), 2000);
    try { const r = await fetch(url, Object.assign({signal:c.signal}, opt||{}));
          clearTimeout(t); return await r.json(); }
    catch(e){ clearTimeout(t); return null; }
  }

  function paint(s){
    el('agoff').hidden = !!s;
    el('agstat').hidden = !s;
    el('agtail').hidden = !s;
    if (!s){
      online = false;
      fab.textContent = '\u2699 agent';
      el('aggo').disabled = true;
      el('aggo').textContent = 'Register all';
      el('agcnt').textContent = '';
      el('agfill').style.width = '0';
      return;
    }
    online = true;
    const run = s.running;
    fab.textContent = run ? '\u26a1 ' + (s.finished||0) + '/' + (s.total||0) : '\u26a1 Register';
    el('aggo').disabled = run;
    el('aggo').textContent = run ? 'running\u2026' : 'Register all ' + (s.total||0);
    if (s.phase === 'login')
      el('agstat').innerHTML = '<b>Sign in to Luma</b> \u2014 Chrome is open. '
        + 'The run starts by itself the moment you are in.';
    else if (run)
      el('agstat').innerHTML = '<b>' + (s.finished||0) + '</b> of <b>' + (s.total||0)
        + '</b> done \u00b7 ' + (s.left||0) + ' left \u00b7 started ' + (s.started||'');
    else
      el('agstat').innerHTML = (s.attempted ? '<b>' + (s.finished||0)
        + '</b> registered of <b>' + (s.total||0) + '</b> \u00b7 last run ' + (s.started||'')
        : 'Ready \u2014 <b>' + (s.total||0) + '</b> events queued.');

    const tot = Math.max(1, s.total||1);
    el('agfill').style.width = Math.min(100, (s.finished||0) / tot * 100) + '%';

    const c = s.counts || {};
    const nice = {REGISTERED:'registered', REQUESTED:'pending host', WAITLISTED:'waitlisted',
                  ALREADY:'already in', SOLD_OUT:'sold out', NEEDS_REVIEW:'needs review',
                  NO_BUTTON:'no button', RATELIMIT:'rate limited', NAV_ERROR:'nav error',
                  WOULD_REGISTER:'dry run'};
    el('agcnt').innerHTML = Object.keys(c).sort((a,b)=>c[b]-c[a])
      .map(k => (nice[k]||k.toLowerCase()) + ' <b>' + c[k] + '</b>').join(' \u00b7 ');

    el('agtail').textContent = (s.tail||[]).slice(-9).join(String.fromCharCode(10));
    el('aglog').href = AGENT + '/api/log';

    // tick off everything the agent already finished
    (s.recent||[]).forEach(r => { if (r.u) done.add(r.u); });
    if (run) render();
  }

  async function poll(){
    if (timer) clearTimeout(timer);
    const s = await jfetch(AGENT + '/api/status');
    paint(s);
    timer = setTimeout(poll, online ? 2500 : 10000);
  }

  el('aggo').onclick = async () => {
    const v = el('agscope').value;
    const body = v.startsWith('day|') ? {scope:'day', day:v.slice(4)} : {scope:v};
    await jfetch(AGENT + '/api/start', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    open = true; box.hidden = false; poll();
  };
  el('agstop').onclick = async () => {
    await jfetch(AGENT + '/api/stop', {method:'POST'}); poll();
  };
  el('aglog').href = AGENT + '/api/log';

  poll();
})();
</script>
</body></html>"""

HTML = (HTML.replace("__DATA__", DATA)
            .replace("__BUILT__", STATS["built"])
            .replace("__N_FREE__", str(STATS["free"]))
            .replace("__N_LUMA__", str(STATS["luma"]))
            .replace("__N_INSTANT__", str(STATS["instant"]))
            .replace("__N_APPROVAL__", str(STATS["approval"]))
            .replace("__SITE_URL__", SITE_URL))

_leftover = sorted(set(re.findall(r"__[A-Z][A-Z_]*__", HTML)))
assert not _leftover, _leftover

# --- syntax-check every inline script -------------------------------------
# A stray \n inside a Python triple-quoted string silently becomes a real
# newline inside a JS string literal and kills the whole block at runtime.
# Node catches it at build time instead.
import shutil, subprocess, tempfile
_node = shutil.which("node")
if _node:
    for i, blk in enumerate(re.findall(r"<script>(.*?)</script>", HTML, re.S)):
        tmp = os.path.join(tempfile.gettempdir(), f"_tk2049_{i}.js")
        open(tmp, "w", encoding="utf-8").write(blk)
        r = subprocess.run([_node, "--check", tmp], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"!! JS syntax error in script block {i}:\n{r.stderr[:800]}")

p = os.path.join(SITE, "index.html")
open(p, "w", encoding="utf-8").write(HTML)
print("->", p, f"({len(HTML)/1024:.0f} KB)")
print("   free", STATS["free"], "| luma", STATS["luma"], "| instant", STATS["instant"],
      "| approval", STATS["approval"], "| soldout", STATS["soldout"],
      "| unscanned", STATS["unknown"])
