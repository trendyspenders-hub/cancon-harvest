#!/usr/bin/env python3
"""CanCon Topic-harvest relay — deploy on any host that can reach YouTube.

What it does:
  - background thread walks artists.txt, finds each artist's "… - Topic"
    channel uploads via yt-dlp, appends to tracks_local.jsonl (resumable)
  - HTTP endpoints for the CanCon sandbox to pull results:
      GET /status               -> {"done": n, "total": n, "tracks": n, "running": bool}
      GET /tracks_local.jsonl   -> the accumulated results file
      POST /start               -> (re)start the harvest loop  {"max_per_artist": 10}
      GET  /health              -> "ok"

Run:     pip install -r requirements.txt && python3 server.py
         (listens on 0.0.0.0:8080; put it behind HTTPS via your host or Caddy)
Docker:  docker build -t topic-relay . && docker run -p 8080:8080 topic-relay

Optional shared secret: set RELAY_TOKEN env, then requests need
?token=... or header X-Relay-Token.
"""
import json, os, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
ARTISTS = os.environ.get("ARTISTS_FILE", os.path.join(BASE, "artists.txt"))
OUT = os.path.join(BASE, "tracks_local.jsonl")
TOKEN = os.environ.get("RELAY_TOKEN")
PORT = int(os.environ.get("PORT", "8080"))
state = {"running": False, "done": 0, "total": 0, "current": None}
lock = threading.Lock()

def harvested_artists():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(line)["artist"].lower())
            except Exception: pass
    return done

def harvest_loop(max_per):
    names = [n.strip() for n in open(ARTISTS, encoding="utf-8") if n.strip()]
    done = harvested_artists()
    todo = [n for n in names if n.lower() not in done]
    with lock:
        state.update(running=True, total=len(names), done=len(done))
    with open(OUT, "a", encoding="utf-8") as out:
        for name in todo:
            if not state["running"]:
                break
            with lock: state["current"] = name
            try:
                # one yt-dlp search per artist; keep only their own Topic channel
                cmd = ["yt-dlp", "--flat-playlist", "--skip-download", "--print",
                       "%(id)s\t%(title)s\t%(channel)s", f"ytsearch{max_per * 3}:{name} - Topic"]
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                kept = 0
                for line in p.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) < 3 or kept >= max_per: continue
                    vid, title, ch = parts[0], parts[1], parts[2].lower()
                    if ch.startswith(name.lower()) and "topic" in ch and len(vid) == 11:
                        out.write(json.dumps({"yt": vid, "title": title, "artist": name,
                                              "album": "", "year": None, "dgenres": [],
                                              "location": "", "genre_tags": "", "act_type": ""}) + "\n")
                        kept += 1
                out.flush()
            except Exception:
                pass
            with lock: state["done"] += 1
            time.sleep(1)
    with lock:
        state.update(running=False, current=None)

def count_tracks():
    return sum(1 for _ in open(OUT, encoding="utf-8")) if os.path.exists(OUT) else 0

class H(BaseHTTPRequestHandler):
    def _auth(self):
        if not TOKEN: return True
        q = parse_qs(urlparse(self.path).query)
        return self.headers.get("X-Relay-Token") == TOKEN or q.get("token", [None])[0] == TOKEN
    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def log_message(self, *a): pass
    def do_GET(self):
        if not self._auth(): return self._send(401, '{"error":"unauthorized"}')
        path = urlparse(self.path).path
        if path == "/health": return self._send(200, "ok", "text/plain")
        if path == "/status":
            with lock: s = dict(state)
            s["tracks"] = count_tracks()
            return self._send(200, json.dumps(s))
        if path == "/tracks_local.jsonl":
            if not os.path.exists(OUT): return self._send(404, '{"error":"no results yet"}')
            return self._send(200, open(OUT, "rb").read(), "application/x-ndjson")
        return self._send(404, '{"error":"unknown endpoint"}')
    def do_POST(self):
        if not self._auth(): return self._send(401, '{"error":"unauthorized"}')
        if urlparse(self.path).path != "/start": return self._send(404, '{}')
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if state["running"]: return self._send(409, '{"error":"already running"}')
        threading.Thread(target=harvest_loop, args=(int(body.get("max_per_artist", 10)),), daemon=True).start()
        return self._send(202, '{"started":true}')

if __name__ == "__main__":
    print(f"relay on :{PORT} — POST /start to begin, GET /tracks_local.jsonl to collect")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
