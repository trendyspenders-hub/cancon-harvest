#!/usr/bin/env python3
"""Builds design/mock-data.json for the homepage mockup from REAL harvest
files — no invented tracks, facts, shows or numbers.

Usage:  python3 design/build_mock.py [data_dir]   (default: repo root)
"""
import collections, datetime as dt, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
rnd = random.Random(42)

def jl(name):
    p = os.path.join(DATA, name)
    out = []
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            try: out.append(json.loads(line))
            except Exception: pass
    return out

PRESETS = [  # names + taglines as they appear on the live site today
    ("Northern Bars", "Canadian hip-hop & R&B, coast to coast"),
    ("Maritime Kitchen Party", "Folk & country from the East Coast"),
    ("Franco Classics", "Québec chanson & pop, en français et en esprit"),
    ("Coup de cœur", "Francophone voices coast to coast"),
    ("En español", "Canadian artists singing in Spanish"),
    ("MuchMusic 90s", "The decade Canada took over the dial"),
    ("Indie All-Dressed", "Two decades of indie rock & weird pop"),
    ("Indigenous Voices", "First Nations, Inuit & Métis artists"),
    ("Prairie Static", "Signals from Manitoba, Saskatchewan & Alberta"),
    ("Slow Burner", "Late-night folk, jazz, soul & country"),
    ("Full Send", "Rock, punk, metal & hip-hop at speed"),
    ("Left Field", "The weird shelf — new wave, reggae, experiments"),
    ("Fresh Pressings", "New Canadian music, 2020 and up"),
    ("Golden Era", "The classics: 1950s through 1970s"),
]

def main():
    facts = {f["yt"]: f for f in jl("dj_facts_local.jsonl")}
    albums = [a for a in jl("albums_local.jsonl") if a.get("cover") and a.get("tracks")]
    cover_of = {}
    for a in albums:
        for t in a["tracks"]: cover_of.setdefault(t["yt"], a["cover"])
    artist_cover = {}
    for a in albums: artist_cover.setdefault(a["artist"].casefold(), a["cover"])

    # broadcast queue: tracks with a cover AND a hometown, varied provinces, prefer charted
    pool = [f for yt, f in facts.items() if yt in cover_of and f.get("place") and f.get("title") and len(f["title"]) < 48]
    rnd.shuffle(pool)
    pool.sort(key=lambda f: ("peak" not in f, "awards" not in f))
    queue, seen_a, prov = [], set(), collections.Counter()
    for f in pool:
        if f["artist"] in seen_a or prov[f.get("province")] >= 3: continue
        seen_a.add(f["artist"]); prov[f.get("province")] += 1
        queue.append({**f, "cover": cover_of[f["yt"]]})
        if len(queue) == 16: break

    today = dt.date.today().isoformat()
    shows = []
    for e in jl("pregame_local.jsonl"):
        if (e.get("date") or "") < today: continue
        a = e["in_rotation"][0]
        shows.append({k: e.get(k) for k in ("date", "time", "venue", "city", "region", "url")} |
                     {"artists": e["in_rotation"], "lineup": e.get("lineup", [])[:4],
                      "tracks": len(e["tracks"]), "cover": artist_cover.get(a.casefold())})
        if len(shows) == 12: break

    recent, seen = [], set()
    for a in sorted(albums, key=lambda a: -(a.get("year") or 0)):
        if (a.get("year") or 0) < 2025 or a["artist"] in seen: continue
        seen.add(a["artist"])
        recent.append({k: a[k] for k in ("artist", "album", "type", "year", "cover")} | {"yt": a["tracks"][0]["yt"]})
        if len(recent) == 16: break

    lineages = jl("lineage_local.jsonl")
    town = next((t for t in lineages if t["town"] == "Winnipeg"), lineages[0] if lineages else None)
    lineage = None
    if town:
        arts = [a for a in town["artists"] if a.get("since")]
        step = max(1, len(arts) // 9)
        lineage = {"town": town["town"], "province": town["province"], "total": len(town["artists"]),
                   "artists": arts[::step][:9]}

    by_prov = collections.Counter(g.get("province") for g in jl("geo_local.jsonl") if g.get("province"))
    tracks = jl("tracks_local.jsonl")
    stats = {"tracks": len({t["yt"] for t in tracks}), "artists": len({t["artist"] for t in tracks}),
             "with_album": sum(1 for t in tracks if t.get("album")), "provinces": by_prov}

    out = {"built": today, "presets": [{"name": n, "tag": t} for n, t in PRESETS], "queue": queue,
           "shows": shows, "recent": recent, "lineage": lineage, "stats": stats}
    json.dump(out, open(os.path.join(HERE, "mock-data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"queue {len(queue)} · shows {len(shows)} · recent {len(recent)} · lineage {lineage and lineage['town']} "
          f"· {stats['tracks']:,} tracks · provinces {len(by_prov)}")

if __name__ == "__main__":
    main()
