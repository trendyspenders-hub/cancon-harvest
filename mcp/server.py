#!/usr/bin/env python3
"""CanCon Topic-harvest as an MCP server for Claude Desktop.

Gives Claude three tools:
  start_harvest(max_per_artist=10)  - begin/resume walking artists.txt
  harvest_status()                  - progress, current artist, tracks found
  get_results()                     - path + stats of tracks_local.jsonl

Setup:
  pip install mcp yt-dlp
  claude_desktop_config.json ->
    { "mcpServers": { "cancon-harvest": {
        "command": "python3",
        "args": ["/full/path/to/topic-harvest/mcp/server.py"] } } }

Results land in tracks_local.jsonl next to this file — upload that file
to your CanCon session to merge into the player.
"""
import json, os, subprocess, threading, time
from mcp.server.fastmcp import FastMCP

BASE = os.path.dirname(os.path.abspath(__file__))
ARTISTS = os.environ.get("ARTISTS_FILE", os.path.join(BASE, "..", "artists.txt"))
OUT = os.path.join(BASE, "..", "tracks_local.jsonl")
state = {"running": False, "done": 0, "total": 0, "current": None, "errors": 0}
lock = threading.Lock()
mcp = FastMCP("cancon-topic-harvest")

def harvested_artists():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(line)["artist"].lower())
            except Exception: pass
    return done

def count_tracks():
    return sum(1 for _ in open(OUT, encoding="utf-8")) if os.path.exists(OUT) else 0

def harvest_loop(max_per: int):
    names = [n.strip() for n in open(ARTISTS, encoding="utf-8") if n.strip()]
    done = harvested_artists()
    todo = [n for n in names if n.lower() not in done]
    with lock:
        state.update(running=True, total=len(names), done=len(done), errors=0)
    with open(OUT, "a", encoding="utf-8") as out:
        for name in todo:
            if not state["running"]:
                break
            with lock: state["current"] = name
            try:
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
                with lock: state["errors"] += 1
            with lock: state["done"] += 1
            time.sleep(1)
    with lock:
        state.update(running=False, current=None)

@mcp.tool()
def start_harvest(max_per_artist: int = 10) -> str:
    """Start (or resume) harvesting YouTube '... - Topic' channel uploads for
    every artist in artists.txt. Already-harvested artists are skipped, so
    calling this again after a stop just continues."""
    if state["running"]:
        return "Already running — use harvest_status() to check progress."
    threading.Thread(target=harvest_loop, args=(max_per_artist,), daemon=True).start()
    return f"Started. {state['total'] - state['done']} artists to go, max {max_per_artist} videos each."

@mcp.tool()
def stop_harvest() -> str:
    """Stop after the current artist finishes. Progress is saved."""
    with lock: state["running"] = False
    return "Stopping after current artist. Restart anytime with start_harvest()."

@mcp.tool()
def harvest_status() -> str:
    """Progress report: artists done, current artist, tracks found."""
    with lock: s = dict(state)
    s["tracks_found"] = count_tracks()
    return json.dumps(s, indent=2)

@mcp.tool()
def get_results() -> str:
    """Where the results file is and how many tracks it holds. Upload that file
    to your CanCon Radio session to merge everything into the player."""
    return json.dumps({"file": os.path.abspath(OUT), "tracks": count_tracks()}, indent=2)

if __name__ == "__main__":
    mcp.run()
