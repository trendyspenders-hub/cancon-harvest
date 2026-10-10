#!/usr/bin/env python3
"""Dead-track checker — rolling, nightly.

Checks the least-recently-checked videos with YouTube's public oEmbed endpoint
(no key):  200 = playable embed · 401/403 = embedding disabled · 400/404 = gone
(removed / private). Network errors are not recorded (retried next night).

State:   dead_state.json (git-ignored)  {yt: [status, "YYYY-MM-DD"]}
Output:  dead_local.jsonl — every video whose last check was NOT ok:
           {yt, status: embed_disabled|gone, checked}
         The site skips these before playing.
Never runs while the main harvest is running (one process against YouTube).
Usage:   python3 check_dead.py [how_many]   (default 8000, ~70 min)
"""
import datetime as dt, json, os, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "dead_state.json")

def status(yt):
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": f"https://www.youtube.com/watch?v={yt}", "format": "json"})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "CanConHarvest/1.0"}), timeout=30):
            return "ok"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403): return "embed_disabled"
        if e.code in (400, 404): return "gone"
        if e.code == 429: time.sleep(300)
        return None
    except Exception:
        return None

def main():
    if subprocess.run(["pgrep", "-f", "[h]arvest_topic_local.py artists.txt"], capture_output=True).returncode == 0:
        print("main harvest is running — dead check skipped"); return
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    ids = []
    for fn in ("tracks_local.jsonl", "tracks_discogs.jsonl"):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                try: ids.append(json.loads(line)["yt"])
                except Exception: pass
    ids = list(dict.fromkeys(ids))
    todo = sorted(ids, key=lambda y: state.get(y, ["", ""])[1])[:n]      # never-checked first, then oldest
    today, counts = dt.date.today().isoformat(), {}
    for i, yt in enumerate(todo):
        s = status(yt)
        if s:
            state[yt] = [s, today]; counts[s] = counts.get(s, 0) + 1
        if i % 500 == 0:
            json.dump(state, open(STATE, "w"))
            print(f"{time.strftime('%H:%M:%S')} [{i}/{len(todo)}] {counts}", flush=True)
        time.sleep(0.5)
    json.dump(state, open(STATE, "w"))
    with open(os.path.join(HERE, "dead_local.jsonl"), "w", encoding="utf-8") as f:
        for yt, (s, d) in state.items():
            if s != "ok": f.write(json.dumps({"yt": yt, "status": s, "checked": d}) + "\n")
    print(f"DONE: checked {len(todo)} — {counts}; {sum(1 for s, _ in state.values() if s != 'ok')} not playable in total")

if __name__ == "__main__":
    main()
