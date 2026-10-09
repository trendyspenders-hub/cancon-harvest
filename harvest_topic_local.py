#!/usr/bin/env python3
"""Run this on YOUR OWN machine (anywhere YouTube is reachable).

Finds each artist's official YouTube channel and harvests their catalog:
  1. their auto-generated "<Name> - Topic" channel, else
  2. their verified artist channel (verified badge + channel name matching
     the artist), else
  3. a YouTube Music artist page whose name matches the artist exactly.
Then pulls every album, EP and single from that artist's YouTube Music page,
with album title and release year, plus up to N videos from step 1/2.

Setup:   pip install yt-dlp ytmusicapi
Usage:   python3 harvest_topic_local.py artists.txt [max_videos_per_artist]
         artists.txt = one artist name per line (export from the directory's
         Export CSV button and keep the name column)
Output:  tracks_local.jsonl — send it back / drop it next to process3.py and
         the normal merge picks it up (schema matches the Discogs harvest).
         harvest_done.jsonl — one line per artist searched:
         {artist, source: topic|verified|ytmusic|none, channel, kept,
          releases, albums: true}

Resumable: artists logged in harvest_done.jsonl with albums=true are skipped.
Older log lines (pre-album) get re-run; tracks already in tracks_local.jsonl
for that artist are never written twice.
"""
import json, os, sys, time
from collections import Counter

def topic_match(name, ch):
    return ch.startswith(name) and "topic" in ch

def verified_match(name, ch):
    # "Aliocha" -> "Aliocha Schneider" ok; "AliochaVEVO" ok; "Aliochas" not
    flat_name, flat_ch = name.replace(" ", ""), ch.replace(" ", "")
    return ch == name or ch.startswith(name + " ") or flat_ch == flat_name + "vevo"

def search(ydl, query, n):
    res = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    if res is None:  # ignoreerrors swallowed a failure — don't mistake it for "no results"
        raise RuntimeError("search failed")
    return [e for e in res.get("entries") or [] if e]

def find_channel(ydl, ytm, name, max_per):
    """-> (source, channel_name, channel_id, videos)"""
    key = name.lower()
    videos = []
    for e in search(ydl, f"{name} - Topic", max_per * 3):
        if topic_match(key, (e.get("channel") or e.get("uploader") or "").lower()):
            videos.append(e)
    if videos:
        best = Counter(e.get("channel_id") for e in videos).most_common(1)[0][0]
        videos = [e for e in videos if e.get("channel_id") == best]
        return "topic", videos[0].get("channel") or "", best, videos
    # No Topic channel: take the single best-matching verified channel
    hits = [e for e in search(ydl, name, max_per * 3)
            if e.get("channel_is_verified")
            and verified_match(key, (e.get("channel") or "").lower())]
    if hits:
        best = Counter(e.get("channel_id") for e in hits).most_common(1)[0][0]
        videos = [e for e in hits if e.get("channel_id") == best]
        return "verified", videos[0].get("channel") or "", best, videos
    # Last resort: YouTube Music artist page with exactly this name
    for r in ytm.search(name, filter="artists", limit=5):
        if (r.get("artist") or "").strip().lower() == key and r.get("browseId"):
            return "ytmusic", r["artist"], r["browseId"], []
    return "none", "", "", []

def releases(ytm, channel_id):
    """Every album/EP/single on the artist's YouTube Music page."""
    try:
        artist = ytm.get_artist(channel_id)
    except KeyError:  # channel has no YouTube Music artist page
        return []
    out = []
    for sec in ("albums", "singles"):
        s = artist.get(sec) or {}
        if s.get("params") and s.get("browseId"):
            out += ytm.get_artist_albums(s["browseId"], s["params"], limit=None)
        else:
            out += s.get("results") or []
    seen, uniq = set(), []
    for r in out:
        if r.get("browseId") and r["browseId"] not in seen:
            seen.add(r["browseId"]); uniq.append(r)
    return uniq

def row(yt, title, name, album="", year=None):
    return {"yt": yt, "title": title or "", "artist": name, "album": album, "year": year,
            "dgenres": [], "location": "", "genre_tags": "", "act_type": ""}

def main():
    names_file = sys.argv[1] if len(sys.argv) > 1 else "artists.txt"
    max_per = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "tracks_local.jsonl")
    log_path = os.path.join(here, "harvest_done.jsonl")

    names = [n.strip() for n in open(names_file, encoding="utf-8") if n.strip()]
    done, have = set(), set()
    if os.path.exists(log_path):
        for line in open(log_path, encoding="utf-8"):
            try:
                d = json.loads(line)
                if d.get("albums"): done.add(d["artist"].lower())
            except Exception: pass
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try:
                d = json.loads(line); have.add((d["artist"].lower(), d["yt"]))
            except Exception: pass
    todo = [n for n in names if n.lower() not in done]
    print(f"{len(todo)} artists queued ({len(done)} done)")

    from yt_dlp import YoutubeDL
    from ytmusicapi import YTMusic
    ytm = YTMusic()
    out = open(out_path, "a", encoding="utf-8")
    log = open(log_path, "a", encoding="utf-8")
    fails = 0
    for i, name in enumerate(todo):
        key = name.lower()
        try:
            with YoutubeDL({"quiet": True, "extract_flat": True, "ignoreerrors": True}) as ydl:
                source, channel, cid, videos = find_channel(ydl, ytm, name, max_per)
            rows = [row(e.get("id"), e.get("title"), name) for e in videos[:max_per]]
            rels = releases(ytm, cid) if cid else []
            for r in rels:
                album = ytm.get_album(r["browseId"])
                year = album.get("year") or r.get("year")
                year = int(year) if str(year or "").isdigit() else None
                for t in album.get("tracks") or []:
                    if t.get("videoId") and t.get("isAvailable", True):
                        rows.append(row(t["videoId"], t.get("title"), name, album.get("title") or r.get("title") or "", year))
                time.sleep(0.3)
        except Exception as ex:
            print(f"  !! {name}: {ex}", flush=True)
            fails += 1
            if fails >= 5:  # YouTube is pushing back — back off before continuing
                print(f"{time.strftime('%H:%M:%S')} 5 failures in a row, pausing 10 min", flush=True)
                time.sleep(600); fails = 0
            else:
                time.sleep(1)
            continue  # not logged, so it's retried on the next run
        fails = 0

        kept = 0
        for r in rows:
            if (key, r["yt"]) in have: continue
            have.add((key, r["yt"]))
            out.write(json.dumps(r) + "\n"); kept += 1
        out.flush()
        log.write(json.dumps({"artist": name, "source": source, "channel": channel,
                              "kept": kept, "releases": len(rels), "albums": True}) + "\n")
        log.flush()
        if i % 10 == 0:
            print(f"{time.strftime('%H:%M:%S')} [{i}/{len(todo)}] {name} | +{kept} tracks, {len(rels)} releases ({source})", flush=True)
        time.sleep(1)  # be polite
    print("DONE")

if __name__ == "__main__":
    main()
