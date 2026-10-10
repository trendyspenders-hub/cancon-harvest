#!/usr/bin/env python3
"""Explicit flags for artists harvested before harvest_topic_local.py recorded
them (log lines without "explicit": true).

Finds the artist's YouTube Music page (logged channel_id, else an exact-name
artist search on the logged channel name), reads each album's "explicit"
badge, and writes ONLY videoIds already in tracks_local.jsonl for that artist —
so a wrong page can never add or mislabel anything else.

Run AFTER the main harvest (don't hit YouTube from two processes at once).
Usage:   python3 backfill_explicit.py
Output:  appends to explicit_local.jsonl  {yt, explicit}
Resume:  explicit_backfill_done.jsonl
"""
import json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    from ytmusicapi import YTMusic
    ytm = YTMusic()
    latest = {}
    for line in open(os.path.join(HERE, "harvest_done.jsonl"), encoding="utf-8"):
        d = json.loads(line)
        if d.get("albums"): latest[d["artist"].lower()] = d
    mine = {}
    for line in open(os.path.join(HERE, "tracks_local.jsonl"), encoding="utf-8"):
        t = json.loads(line); mine.setdefault(t["artist"].lower(), set()).add(t["yt"])
    done_p = os.path.join(HERE, "explicit_backfill_done.jsonl")
    done = {json.loads(l)["artist"].lower() for l in open(done_p, encoding="utf-8")} if os.path.exists(done_p) else set()
    todo = [d for k, d in latest.items()
            if not d.get("explicit") and d.get("releases") and d.get("channel") and k not in done]
    print(f"explicit backfill: {len(todo)} artists", flush=True)
    out = open(os.path.join(HERE, "explicit_local.jsonl"), "a", encoding="utf-8")
    log = open(done_p, "a", encoding="utf-8")
    fails = 0
    for i, d in enumerate(todo):
        name, wanted, n = d["artist"], mine.get(d["artist"].lower(), set()), 0
        try:
            cid = d.get("channel_id")
            if not cid:
                target = re.sub(r"\s+-\s+topic$", "", d["channel"], flags=re.I).strip().lower()
                cid = next((r["browseId"] for r in ytm.search(target, filter="artists", limit=5)
                            if (r.get("artist") or "").strip().lower() == target and r.get("browseId")), None)
            if cid:
                art = ytm.get_artist(cid)
                albums = []
                for sec in ("albums", "singles"):
                    s = art.get(sec) or {}
                    albums += ytm.get_artist_albums(s["browseId"], s["params"], limit=None) if s.get("params") and s.get("browseId") else (s.get("results") or [])
                for a in {a["browseId"]: a for a in albums if a.get("browseId")}.values():
                    for t in ytm.get_album(a["browseId"]).get("tracks") or []:
                        v = t.get("videoId")
                        if v in wanted and t.get("isExplicit") is not None:
                            out.write(json.dumps({"yt": v, "explicit": bool(t["isExplicit"])}) + "\n"); n += 1
                    time.sleep(0.3)
                out.flush()
        except KeyError:
            pass  # no YouTube Music artist page — nothing to flag
        except Exception as ex:
            print(f"  !! {name}: {ex}", flush=True); fails += 1
            time.sleep(600 if fails >= 5 else 2); fails = 0 if fails >= 5 else fails
            continue
        fails = 0
        log.write(json.dumps({"artist": name, "flagged": n}) + "\n"); log.flush()
        if i % 25 == 0: print(f"{time.strftime('%H:%M:%S')} [{i}/{len(todo)}] {name} | {n} flagged", flush=True)
        time.sleep(1)
    print("DONE")

if __name__ == "__main__":
    main()
