#!/usr/bin/env python3
"""Discogs pass for artists the YouTube harvest found nothing for.

For every artist logged `source: none` in harvest_done.jsonl:
  1. Discogs artist search; accept only an EXACT name match (Discogs' " (2)"
     disambiguation suffix ignored), only if exactly one such artist exists,
     and only if at least one of their releases is marked Canada.
  2. Links from the Discogs profile (Bandcamp, SoundCloud, Spotify, website…)
     -> links_local.jsonl, source "discogs".
  3. YouTube videos attached to their releases -> tracks_discogs.jsonl, same
     schema as tracks_local.jsonl, album/year from the release.
     These are COMMUNITY-ADDED videos (often fan uploads), so they are kept
     separate from tracks_local.jsonl on purpose.

No account needed: unauthenticated Discogs API, 25 requests/minute.

Usage:   python3 harvest_discogs.py [max_releases_per_artist]
Resume:  discogs_done.jsonl. Re-run any time; new `none` artists get picked up.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "CanConHarvest/1.0 +https://github.com/trendyspenders-hub/cancon-harvest"
GAP = 2.6  # seconds between requests (25/min limit)

def get(url, tries=4):
    for i in range(tries):
        time.sleep(GAP)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if i == tries - 1: raise
            time.sleep(60 if e.code == 429 else 10)
        except Exception:
            if i == tries - 1: raise
            time.sleep(10)

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()

def bare(title):
    return re.sub(r" \(\d+\)$", "", title or "")  # "Forteresse (2)" -> "Forteresse"

def classify(url):
    h = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    if h.endswith("bandcamp.com"): return "bandcamp"
    if h == "soundcloud.com": return "soundcloud"
    if h == "open.spotify.com" and "/artist/" in url: return "spotify"
    if h in ("music.apple.com", "itunes.apple.com") and "/artist/" in url: return "apple_music"
    if h == "deezer.com" and "/artist/" in url: return "deezer"
    if h in ("youtube.com", "m.youtube.com", "music.youtube.com"): return "youtube"
    social = ("facebook.com", "instagram.com", "twitter.com", "x.com", "myspace.com",
              "last.fm", "wikipedia.org", "discogs.com", "tiktok.com", "linktr.ee")
    if any(h.endswith(s) for s in social): return None
    return "website"

def yt_id(uri):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", uri or "")
    return m.group(1) if m else None

def main():
    max_rel = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    latest = {}
    for line in open(os.path.join(HERE, "harvest_done.jsonl"), encoding="utf-8"):
        try:
            d = json.loads(line)
            if d.get("albums"): latest[norm(d["artist"])] = d
        except Exception: pass
    done_path = os.path.join(HERE, "discogs_done.jsonl")
    done = set()
    if os.path.exists(done_path):
        for line in open(done_path, encoding="utf-8"):
            try: done.add(norm(json.loads(line)["artist"]))
            except Exception: pass
    todo = [d["artist"] for k, d in latest.items() if d["source"] == "none" and k not in done]
    print(f"discogs: {len(todo)} unmatched artists queued ({len(done)} done)", flush=True)

    links = open(os.path.join(HERE, "links_local.jsonl"), "a", encoding="utf-8")
    tracks = open(os.path.join(HERE, "tracks_discogs.jsonl"), "a", encoding="utf-8")
    log = open(done_path, "a", encoding="utf-8")
    found = vids_total = 0
    for i, name in enumerate(todo):
        status, kept = "none", 0
        try:
            res = get("https://api.discogs.com/database/search?" +
                      urllib.parse.urlencode({"q": name, "type": "artist", "per_page": 25}))
            exact = [x for x in (res or {}).get("results", []) if norm(bare(x.get("title"))) == norm(name)]
            if len(exact) > 1:
                status = "ambiguous"
            elif exact:
                aid = exact[0]["id"]
                rels = (get(f"https://api.discogs.com/artists/{aid}/releases?per_page=50&sort=year") or {}).get("releases", [])
                rels = [r for r in rels if r.get("role", "Main") == "Main"]
                details, canadian = [], False
                for r in rels[:max_rel]:
                    d = get(r["resource_url"])
                    if not d: continue
                    details.append(d)
                    # masters have no country; check their main release
                    country = d.get("country")
                    if country is None and d.get("main_release_url") and not canadian:
                        mr = get(d["main_release_url"]); country = (mr or {}).get("country")
                    if "canada" in (country or "").lower(): canadian = True
                if not canadian:
                    status = "not-canadian"
                else:
                    status = "linked"; found += 1
                    prof = get(f"https://api.discogs.com/artists/{aid}") or {}
                    rec = {"artist": name, "source": "discogs", "id": str(aid)}
                    for u in prof.get("urls") or []:
                        f = classify(u)
                        if f and f not in rec: rec[f] = u
                    links.write(json.dumps(rec, ensure_ascii=False) + "\n"); links.flush()
                    seen = set()
                    for d in details:
                        year = d.get("year")
                        for v in d.get("videos") or []:
                            vid = yt_id(v.get("uri"))
                            if not vid or vid in seen: continue
                            seen.add(vid)
                            tracks.write(json.dumps({
                                "yt": vid, "title": v.get("title") or "", "artist": name,
                                "album": d.get("title") or "",
                                "year": year if isinstance(year, int) and year > 0 else None,
                                "dgenres": d.get("genres") or [], "location": "", "genre_tags": "", "act_type": "",
                            }, ensure_ascii=False) + "\n")
                            kept += 1
                    tracks.flush(); vids_total += kept
        except Exception as ex:
            print(f"  !! {name}: {ex}", flush=True)
            continue  # not logged -> retried next run
        log.write(json.dumps({"artist": name, "status": status, "videos": kept}, ensure_ascii=False) + "\n"); log.flush()
        if i % 25 == 0 or status == "linked":
            print(f"{time.strftime('%H:%M:%S')} [{i}/{len(todo)}] {name} | {status} +{kept} videos | {found} linked, {vids_total} videos", flush=True)
    print("DONE")

if __name__ == "__main__":
    main()
