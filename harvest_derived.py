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
import json, os, random
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
        t = towns.setdefault((g["place"], g["province"]), {"town": g["place"], "province": g["province"],
                                                           "lat": g["lat"], "lon": g["lon"], "artists": {}})
        t["artists"][k] = {"artist": names.get(k, g["artist"]), "since": first_year.get(k) if first_year.get(k, 9999) < 9999 else None,
                           "top_hit": hits.get(k)}
    m = 0
    with open(os.path.join(HERE, "lineage_local.jsonl"), "w", encoding="utf-8") as f:
        for t in sorted(towns.values(), key=lambda t: -len(t["artists"])):
            if len(t["artists"]) < 3: continue
            t["artists"] = sorted(t["artists"].values(), key=lambda a: (a["since"] or 9999, a["artist"]))
            f.write(json.dumps(t, ensure_ascii=False) + "\n"); m += 1
    print(f"lineage: {m} towns with 3+ artists in rotation")

if __name__ == "__main__":
    main()
