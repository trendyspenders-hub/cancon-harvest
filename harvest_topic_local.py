#!/usr/bin/env python3
"""Run this on YOUR OWN machine (anywhere YouTube is reachable).

Finds each artist's auto-generated YouTube "Topic" channel — the official
artist-audio pages YouTube creates ("<Name> - Topic") — and lists its uploads.
If the artist has no Topic channel, falls back to their verified artist
channel (verified badge + channel name matching the artist).

Setup:   pip install yt-dlp
Usage:   python3 harvest_topic_local.py artists.txt [max_per_artist]
         artists.txt = one artist name per line (export from the directory's
         Export CSV button and keep the name column)
Output:  tracks_local.jsonl — send it back / drop it next to process3.py and
         the normal merge picks it up (schema matches the Discogs harvest).
         harvest_done.jsonl — one line per artist searched:
         {artist, source: topic|verified|none, channel, kept}

Resumable: artists already in tracks_local.jsonl or harvest_done.jsonl are
skipped, including ones that came back empty.
"""
import json, os, re, sys, time
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

def main():
    names_file = sys.argv[1] if len(sys.argv) > 1 else "artists.txt"
    max_per = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "tracks_local.jsonl")
    log_path = os.path.join(here, "harvest_done.jsonl")

    names = [n.strip() for n in open(names_file, encoding="utf-8") if n.strip()]
    done = set()
    for path in (out_path, log_path):
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                try: done.add(json.loads(line)["artist"].lower())
                except Exception: pass
    todo = [n for n in names if n.lower() not in done]
    print(f"{len(todo)} artists queued ({len(done)} done)")

    from yt_dlp import YoutubeDL
    out = open(out_path, "a", encoding="utf-8")
    log = open(log_path, "a", encoding="utf-8")
    for i, name in enumerate(todo):
        key = name.lower()
        picked, source, channel = [], "none", ""
        try:
            with YoutubeDL({"quiet": True, "extract_flat": True, "ignoreerrors": True}) as ydl:
                for e in search(ydl, f"{name} - Topic", max_per * 3):
                    ch = (e.get("channel") or e.get("uploader") or "").lower()
                    if topic_match(key, ch):
                        picked.append(e)
                if picked:
                    source = "topic"
                else:
                    # No Topic channel: take the single best-matching verified channel
                    hits = [e for e in search(ydl, name, max_per * 3)
                            if e.get("channel_is_verified")
                            and verified_match(key, (e.get("channel") or "").lower())]
                    if hits:
                        best = Counter(e.get("channel_id") for e in hits).most_common(1)[0][0]
                        picked = [e for e in hits if e.get("channel_id") == best]
                        source = "verified"
                if picked:
                    channel = picked[0].get("channel") or picked[0].get("uploader") or ""
        except Exception as ex:
            print(f"  !! {name}: {ex}")
            time.sleep(1)
            continue  # not logged, so it's retried on the next run

        kept = 0
        for e in picked[:max_per]:
            out.write(json.dumps({
                "yt": e.get("id"), "title": e.get("title") or "",
                "artist": name, "album": "", "year": None,
                "dgenres": [], "location": "", "genre_tags": "", "act_type": "",
            }) + "\n")
            kept += 1
        out.flush()
        log.write(json.dumps({"artist": name, "source": source, "channel": channel, "kept": kept}) + "\n")
        log.flush()
        if i % 10 == 0:
            print(f"{time.strftime('%H:%M:%S')} [{i}/{len(todo)}] {name} | +{kept} vids ({source})", flush=True)
        time.sleep(1)  # be polite
    print("DONE")

if __name__ == "__main__":
    main()
