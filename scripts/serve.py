# -*- coding: utf-8 -*-
"""
serve.py — local companion that turns the board into a one-button machine.

    python serve.py            # opens http://127.0.0.1:8765/

What it adds on top of the static board:
    GET  /            the board itself (always read fresh from site/index.html)
    GET  /api/status  live progress of the current / last run
    POST /api/start   {"scope":"all"|"instant"|"day","day":"Tue 6 Oct","limit":0,"dry":false}
    POST /api/stop    stop the run (progress is kept — restart resumes)
    GET  /api/log     registration_log.csv
    GET  /api/out     raw stdout of the engine

It also answers cross-origin (Access-Control-Allow-Origin: *), so the copy
hosted on GitHub Pages / trilumi.xyz can drive it too: open that link in Chrome
on THIS machine and the "Register all" button lights up by itself.

Why a local helper and not a plain web button: a page on github.io cannot click
into luma.com — that is a hard browser boundary (different origin, and it has no
access to your Luma session). The button talks to this helper, which drives your
own logged-in Chrome. Nothing leaves your machine.
"""
import csv, json, os, subprocess, sys, threading, time, webbrowser
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site", "index.html")
OUT = os.path.join(BASE, "outputs")
LOG = os.path.join(OUT, "registration_log.csv")
AGENT_OUT = os.path.join(OUT, ".agent_out.txt")
PY = sys.executable
PORT = int(os.environ.get("AGENT_PORT", "8765"))
ENGINE = os.environ.get("AGENT_ENGINE") or os.path.join(BASE, "scripts", "one_click.py")

STATE = {
    "proc": None,
    "scope": "all",
    "day": "",
    "total": 0,
    "started": None,
    "last": None,
}

DONE = {"REGISTERED", "REQUESTED", "WAITLISTED", "ALREADY", "SOLD_OUT",
        "WOULD_REGISTER"}


def queue_size(scope, day):
    try:
        if scope == "instant":
            p = os.path.join(OUT, "free_luma_instant_all.csv")
        elif scope == "day":
            p = os.path.join(OUT, "register_all_free.csv")
        else:
            p = os.path.join(OUT, "register_all_free.csv")
        rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
        if scope == "day":
            rows = [r for r in rows if (r.get("day") or "") == day]
        return len(rows)
    except Exception:
        return 0


def read_log():
    if not os.path.exists(LOG):
        return [], Counter()
    rows = list(csv.DictReader(open(LOG, encoding="utf-8-sig")))
    return rows, Counter(r.get("result", "") for r in rows)


def tail(n=25):
    if not os.path.exists(AGENT_OUT):
        return []
    try:
        with open(AGENT_OUT, "r", encoding="utf-8", errors="replace") as f:
            return [l.rstrip() for l in f.readlines()[-n:] if l.strip()]
    except Exception:
        return []


def status():
    rows, cnt = read_log()
    proc = STATE["proc"]
    running = bool(proc and proc.poll() is None)
    lines = tail()
    phase = "idle"
    if running:
        phase = "login" if any("opening Chrome" in l for l in lines) else "running"
    elif STATE["last"]:
        phase = "done" if not any("login never" in l or "[x]" in l for l in lines) else "failed"
    finished = sum(v for k, v in cnt.items() if k in DONE)
    return {
        "running": running,
        "phase": phase,
        "scope": STATE["scope"],
        "day": STATE["day"],
        "total": STATE["total"] or queue_size(STATE["scope"], STATE["day"]),
        "attempted": len(rows),
        "finished": finished,
        "left": max(0, (STATE["total"] or queue_size(STATE["scope"], STATE["day"])) - finished),
        "counts": dict(cnt.most_common()),
        "started": STATE["started"],
        "recent": [{"n": r.get("event", ""), "r": r.get("result", ""),
                    "u": r.get("url", "")} for r in rows[-30:][::-1]],
        "tail": lines[-12:],
        "log": os.path.exists(LOG),
    }


def start(scope="all", day="", limit=0, dry=False):
    if STATE["proc"] and STATE["proc"].poll() is None:
        return {"ok": False, "msg": "already running"}
    STATE.update(scope=scope, day=day,
                 total=queue_size(scope, day),
                 started=datetime.now().strftime("%H:%M:%S"))
    cmd = [PY, "-u", ENGINE, "--scope", scope]
    if scope == "day":
        cmd += ["--day", day]
    if limit:
        cmd += ["--limit", str(int(limit))]
    if dry:
        cmd += ["--dry"]
    f = open(AGENT_OUT, "w", encoding="utf-8")
    STATE["proc"] = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT,
                                     cwd=BASE, bufsize=1)
    return {"ok": True, "msg": f"started: {scope} {day}".strip()}


def stop():
    p = STATE["proc"]
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=10)
        except Exception:
            p.kill()
        return {"ok": True, "msg": "stopped — progress saved, restart resumes"}
    return {"ok": False, "msg": "not running"}


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self._cors()
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/status":
            return self._json(status())
        if p == "/api/out":
            return self._json({"lines": tail(80)})
        if p == "/api/log":
            if not os.path.exists(LOG):
                return self._json({"error": "no log yet"}, 404)
            b = open(LOG, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self._cors()
            self.end_headers()
            self.wfile.write(b)
            return
        if p in ("/", "/index.html"):
            b = open(SITE, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(b)
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        p = self.path.split("?")[0]
        if p == "/api/start":
            return self._json(start(body.get("scope", "all"), body.get("day", ""),
                                    body.get("limit", 0), bool(body.get("dry"))))
        if p == "/api/stop":
            return self._json(stop())
        self._json({"error": "not found"}, 404)


def main():
    for attempt in range(6):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", PORT + attempt), H)
            port = PORT + attempt
            break
        except OSError:
            continue
    else:
        print("no free port"); sys.exit(1)

    url = f"http://127.0.0.1:{port}/"
    print("=" * 62)
    print("  TOKEN2049 board + registration agent")
    print("  " + url)
    print("  Keep this window open. Ctrl+C to quit.")
    print("=" * 62)
    if "--no-open" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        stop()


if __name__ == "__main__":
    main()
