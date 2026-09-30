# -*- coding: utf-8 -*-
"""
build_site.py — emit site/index.html, a fully self-contained (offline-capable)
catalogue of every FREE TOKEN2049 Week Singapore 2026 side event.

Everything is inlined into one HTML file so it can be dropped on any static host
( trilumi.xyz, GitHub Pages, S3, or just opened from disk ).

    python build_site.py
"""
import csv, html, json, os, re
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)


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
        "d": r.get("day", ""),
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

items.sort(key=lambda x: (-x["f"], x["d"], x["s"]))

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
</footer>

<script>
const DATA = __DATA__;
const tb = document.getElementById('tb');
const done = new Set(JSON.parse(localStorage.getItem('tk2049done') || '[]'));
const save = () => localStorage.setItem('tk2049done', JSON.stringify([...done]));

const days = [...new Set(DATA.map(d=>d.d))].sort();
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
  view.sort(fo==='time' ? (a,b)=> (a.d+a.s).localeCompare(b.d+b.s)
                        : (a,b)=> b.f-a.f || (a.d+a.s).localeCompare(b.d+b.s));
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
</body></html>"""

HTML = (HTML.replace("__DATA__", DATA)
            .replace("__BUILT__", STATS["built"])
            .replace("__N_FREE__", str(STATS["free"]))
            .replace("__N_LUMA__", str(STATS["luma"]))
            .replace("__N_INSTANT__", str(STATS["instant"]))
            .replace("__N_APPROVAL__", str(STATS["approval"])))

p = os.path.join(SITE, "index.html")
open(p, "w", encoding="utf-8").write(HTML)
print("->", p, f"({len(HTML)/1024:.0f} KB)")
print("   free", STATS["free"], "| luma", STATS["luma"], "| instant", STATS["instant"],
      "| approval", STATS["approval"], "| soldout", STATS["soldout"],
      "| unscanned", STATS["unknown"])
