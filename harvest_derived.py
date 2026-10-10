#!/usr/bin/env python3
"""Derived files — built only from data already harvested (no network).

pregame_local.jsonl   "Pre-game the show": one line per upcoming concert with
                      at least one lineup artist in rotation:
                      {event_id, date, time, venue, city, region, url, provider,
                       lineup, in_rotation: [artist…], tracks: [yt…] (≤30, shuffled
                       across the lineup)}
lineage_local.jsonl   "Hometown lineage": one line per town with 3+ artists in
                      rotation, artists ordered by their first known year:
                      {town, province, lat, lon, artists: [{artist, since,
                       top_hit: {title, yt, peak, chart, year} | null}]}
                      `since` = earliest year among the artist's tracks/charts.

Usage:   python3 harvest_derived.py      (cheap; push-results.sh runs it)
"""
import json, os, random, re, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

def jl(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p): return []
    out = []
    for line in open(p, encoding="utf-8"):
        try: out.append(json.loads(line))
        except Exception: pass   # a line mid-write by a running harvest
    return out

def main():
    tracks = defaultdict(list)
    first_year = {}
    for t in jl("tracks_local.jsonl"):
        k = t["artist"].casefold()
        tracks[k].append(t["yt"])
        if t.get("year"): first_year[k] = min(first_year.get(k, 9999), t["year"])
    hits = {}
    for c in jl("charts_tracks.jsonl"):
        k = c["artist"].casefold()
        if c.get("years"): first_year[k] = min(first_year.get(k, 9999), min(c["years"]))
        if c.get("peak") and (k not in hits or c["peak"] < hits[k]["peak"]):
            hits[k] = {"title": c["title"], "yt": c["yt"], "peak": c["peak"], "chart": c.get("chart"),
                       "year": min(c["years"]) if c.get("years") else None}
    names = {t["artist"].casefold(): t["artist"] for t in jl("tracks_local.jsonl")}

    n = 0
    with open(os.path.join(HERE, "pregame_local.jsonl"), "w", encoding="utf-8") as f:
        by_event = defaultdict(list)
        for e in jl("events_local.jsonl"): by_event[e["event_id"]].append(e)
        for eid, rows in sorted(by_event.items(), key=lambda kv: kv[1][0]["date"] or ""):
            e = rows[0]
            playing = list(dict.fromkeys(r["artist"] for r in rows if r["artist"].casefold() in tracks))
            if not playing: continue
            rnd = random.Random(eid)   # stable per event
            pool = [yt for a in playing for yt in rnd.sample(tracks[a.casefold()], min(12, len(tracks[a.casefold()])))]
            rnd.shuffle(pool)
            f.write(json.dumps({"event_id": eid, "date": e["date"], "time": e.get("time"), "venue": e.get("venue"),
                                "city": e.get("city"), "region": e.get("region"), "url": e.get("url"),
                                "provider": e.get("provider"), "lineup": e.get("lineup") or [],
                                "in_rotation": playing, "tracks": pool[:30]}, ensure_ascii=False) + "\n")
            n += 1
    print(f"pregame: {n} upcoming shows with a station")

    towns = {}
    for g in jl("geo_local.jsonl"):
        if g.get("precision") != "town": continue
        k = g["artist"].casefold()
        if k not in tracks: continue
        # "Montréal" (GeoNames) and "Montreal" (Wikidata) are one town; keep the accented name
        tkey = (unicodedata.normalize("NFKD", g["place"] or "").encode("ascii", "ignore").decode().casefold(), g["province"])
        t = towns.setdefault(tkey, {"town": g["place"], "province": g["province"],
                                    "lat": g["lat"], "lon": g["lon"], "artists": {}})
        if not t["town"].isascii() or g["place"].isascii(): pass
        else: t["town"] = g["place"]
        t["artists"][k] = {"artist": names.get(k, g["artist"]), "since": first_year.get(k) if first_year.get(k, 9999) < 9999 else None,
                           "top_hit": hits.get(k)}
    m = 0
    with open(os.path.join(HERE, "lineage_local.jsonl"), "w", encoding="utf-8") as f:
        for t in sorted(towns.values(), key=lambda t: -len(t["artists"])):
            if len(t["artists"]) < 3: continue
            t["artists"] = sorted(t["artists"].values(), key=lambda a: (a["since"] or 9999, a["artist"]))
            f.write(json.dumps(t, ensure_ascii=False) + "\n"); m += 1
    print(f"lineage: {m} towns with 3+ artists in rotation")

VERSION = [("live", r"\blive\b|en direct|en concert"), ("remix", r"\bremix|\bmix\b|extended|club version"),
           ("remaster", r"remaster"), ("acoustic", r"acoustic|acoustique|unplugged|a ?cappella|acappella"),
           ("demo", r"\bdemo\b"), ("instrumental", r"instrumental|karaoke"), ("edit", r"\bedit\b|radio version"),
           ("video", r"official (music )?video|clip officiel|vid[eé]oclip|lyric|paroles|visualizer")]

def kind_of(title, album=""):
    for k, rx in VERSION:
        if re.search(rx, title or "", re.I): return k
    for k, rx in VERSION[:2]:                      # a "Remixes" / "Live" album makes its tracks versions too
        if re.search(rx, album or "", re.I): return k
    return "original"

def song_key(title, artist):
    t = title or ""
    if " - " in t and t.split(" - ", 1)[0].strip().casefold() == artist.casefold(): t = t.split(" - ", 1)[1]
    t = re.sub(r"[\(\[].*?[\)\]]", " ", t)
    # only version notes after a dash ("- Remastered 2009", "- Live"); "Turandot - Act I: …" keeps its scene
    t = re.sub(r"\s+-\s+(\d{4}\b.*|.*\b(remaster\w*|live|single|radio|edit|version|mono|stereo|demo|acoustic|remix|mix)\b.*)$", "", t, flags=re.I)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]+", " ", t)).strip()

def songs():
    """songs_local.jsonl — songs that exist in 2+ versions, with one canonical
    version (original album track, earliest year) so rotation never plays the
    same song twice in a row and pages can say "4 versions"."""
    groups = defaultdict(list)
    for t in jl("tracks_local.jsonl"):
        k = song_key(t["title"], t["artist"])
        if k: groups[(t["artist"].casefold(), k)].append(t)
    n = 0
    with open(os.path.join(HERE, "songs_local.jsonl"), "w", encoding="utf-8") as f:
        for (a, k), ts in groups.items():
            vs = list({t["yt"]: t for t in ts}.values())
            if len(vs) < 2: continue
            rank = lambda t: (kind_of(t["title"], t.get("album")) != "original", not t.get("album"), t.get("year") or 9999)
            canon = min(vs, key=rank)
            f.write(json.dumps({"artist": canon["artist"], "title": canon["title"], "canonical": canon["yt"],
                                "versions": [{"yt": t["yt"], "kind": kind_of(t["title"], t.get("album")), "album": t.get("album") or None,
                                              "year": t.get("year")} for t in sorted(vs, key=rank)]}, ensure_ascii=False) + "\n")
            n += 1
    print(f"songs: {n} songs with 2+ versions")

def fresh():
    """fresh_local.jsonl — artists first seen in the last 7 days. First run only
    records a baseline (state in fresh_state.json, git-ignored)."""
    import datetime as dt
    state_p = os.path.join(HERE, "fresh_state.json")
    today = dt.date.today()
    tracks = defaultdict(list)
    for t in jl("tracks_local.jsonl"): tracks[t["artist"]].append(t["yt"])
    if not os.path.exists(state_p):
        json.dump({a: "baseline" for a in tracks}, open(state_p, "w"))
        print(f"fresh: baseline of {len(tracks)} artists recorded"); return
    seen = json.load(open(state_p))
    for a in tracks: seen.setdefault(a, today.isoformat())
    json.dump(seen, open(state_p, "w"))
    week = (today - dt.timedelta(days=7)).isoformat()
    rows = [{"artist": a, "first_seen": d, "tracks": len(tracks[a]), "sample": tracks[a][:3]}
            for a, d in seen.items() if d != "baseline" and d >= week and a in tracks]
    with open(os.path.join(HERE, "fresh_local.jsonl"), "w", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda r: r["first_seen"], reverse=True):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"fresh: {len(rows)} artists added in the last 7 days")

if __name__ == "__main__":
    main(); songs(); fresh()
