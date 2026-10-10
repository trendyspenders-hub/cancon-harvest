#!/usr/bin/env python3
"""New Releases Radar — weekly. For every artist already in rotation with a
YouTube Music page, list their albums/EPs/singles and pick up any release not
seen before (browse_id not in albums_local.jsonl).

New releases are official (the artist's own YouTube Music page), so their
tracks join the main rotation:
  tracks_local.jsonl      + new tracks (same schema)
  albums_local.jsonl      + album line (cover, track order)
  explicit_local.jsonl    + flags
  new_releases_local.jsonl  {artist, album, type, year, cover, tracks, found}
                            — the "New This Week" station + badges

Never runs while the main harvest is running (one process against YouTube).
Usage:   python3 harvest_radar.py [max_artists]
"""
import datetime as dt, json, os, re, subprocess, sys, time
from harvest_topic_local import album_record, row

HERE = os.path.dirname(os.path.abspath(__file__))

def jl(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p): return []
    out = []
    for line in open(p, encoding="utf-8"):
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def main():
    if subprocess.run(["pgrep", "-f", "[h]arvest_topic_local.py artists.txt"], capture_output=True).returncode == 0:
        print("main harvest is running — radar skipped"); return
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    from ytmusicapi import YTMusic
    ytm = YTMusic()
    known = {a.get("browse_id") for a in jl("albums_local.jsonl")}
    have = {(t["artist"].lower(), t["yt"]) for t in jl("tracks_local.jsonl")}
    latest = {}
    for d in jl("harvest_done.jsonl"):
        if d.get("albums"): latest[d["artist"].lower()] = d
    backfilled = {}
    for b in jl("explicit_backfill_done.jsonl"):
        backfilled[b["artist"].lower()] = b.get("channel_id")
    for d in latest.values():                      # channel found by the backfill (older artists)
        if not d.get("channel_id") and backfilled.get(d["artist"].lower()):
            d["channel_id"] = backfilled[d["artist"].lower()]
    # only artists whose existing albums are already recorded — otherwise every
    # old album would look "unseen" and be announced as new
    artists = [d for d in latest.values() if d.get("channel_id") and d.get("source") in ("topic", "verified", "ytmusic")
               and (d.get("album_meta") or d["artist"].lower() in backfilled)]
    if subprocess.run(["pgrep", "-f", "[b]ackfill_explicit.py"], capture_output=True).returncode == 0:
        print("album backfill is running — radar skipped"); return
    if limit: artists = artists[:limit]
    today = dt.date.today().isoformat()
    files = {n: open(os.path.join(HERE, n), "a", encoding="utf-8") for n in
             ("tracks_local.jsonl", "albums_local.jsonl", "explicit_local.jsonl", "new_releases_local.jsonl")}
    found = 0
    print(f"radar: checking {len(artists)} artists", flush=True)
    for i, d in enumerate(artists):
        name = d["artist"]
        try:
            art = ytm.get_artist(d["channel_id"])
            rels = []
            for sec in ("albums", "singles"):
                s = art.get(sec) or {}
                rels += ytm.get_artist_albums(s["browseId"], s["params"], limit=None) if s.get("params") and s.get("browseId") else (s.get("results") or [])
            for r in rels:
                if not r.get("browseId") or r["browseId"] in known: continue
                album = ytm.get_album(r["browseId"]); time.sleep(0.3)
                rec = album_record(name, r, album)
                known.add(r["browseId"])
                files["albums_local.jsonl"].write(json.dumps(rec, ensure_ascii=False) + "\n")
                for t in album.get("tracks") or []:
                    v = t.get("videoId")
                    if not v or not t.get("isAvailable", True): continue
                    if t.get("isExplicit") is not None:
                        files["explicit_local.jsonl"].write(json.dumps({"yt": v, "explicit": bool(t["isExplicit"])}) + "\n")
                    if (name.lower(), v) in have: continue
                    have.add((name.lower(), v))
                    files["tracks_local.jsonl"].write(json.dumps(row(v, t.get("title"), name, rec["album"], rec["year"])) + "\n")
                # "new" = released this year or last (an older release we'd simply never seen isn't news)
                if rec["year"] and rec["year"] >= dt.date.today().year - 1:
                    files["new_releases_local.jsonl"].write(json.dumps({**{k: rec[k] for k in ("artist", "album", "type", "year", "cover", "tracks")}, "found": today}, ensure_ascii=False) + "\n")
                    found += 1
            for f in files.values(): f.flush()
        except KeyError:
            pass
        except Exception as ex:
            print(f"  !! {name}: {ex}", flush=True); time.sleep(5)
        if i % 200 == 0: print(f"{time.strftime('%H:%M:%S')} [{i}/{len(artists)}] {name} | {found} new releases", flush=True)
        time.sleep(1)
    print(f"DONE: {found} new releases this run")

if __name__ == "__main__":
    main()
