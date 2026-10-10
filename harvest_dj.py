#!/usr/bin/env python3
"""AI DJ fact sheet — one line per track, ONLY fields that were harvested from a
named source. dj/dj.js turns these into spoken intros; it never adds facts.

Output:  dj_facts_local.jsonl — {yt, artist, title, album?, year?, place?,
           province?, basis?, peak?, chart?, chart_year?, year_end?,
           ckoi?, juno_single?, awards?: [{award, year, result}]}
         dj/sample.json — 40 varied tracks for the demo page
Sources: tracks_local (YouTube/YouTube Music), geo_local (GeoNames/Wikidata),
         charts_tracks (Canadian Music Blog), awards_local (Wikipedia).
Usage:   python3 harvest_dj.py     (no network; push-results.sh runs it)
"""
import json, os, random, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
PROV = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
        "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "ON": "Ontario", "PE": "Prince Edward Island",
        "QC": "Quebec", "SK": "Saskatchewan", "YT": "Yukon", "NT": "the Northwest Territories", "NU": "Nunavut"}

def jl(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p): return []
    out = []
    for line in open(p, encoding="utf-8"):
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def key(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]+", " ", s)).strip().casefold()

def clean_title(t, artist):
    """Spoken title: drop "[Official Video]", "(Remastered 2009)", "Artist - " prefixes."""
    t = re.sub(r"\s*[\(\[][^\)\]]*(official|video|audio|lyric|visualizer|remaster|hd|hq)[^\)\]]*[\)\]]", "", t or "", flags=re.I)
    t = re.sub(r"\(\s*live\b[^\)]{12,}\)", "(Live)", t, flags=re.I)        # "(Live at Meadowlands Arena, …)" -> "(Live)"
    t = re.sub(r"\s*[\(\[][^\)\]]{28,}[\)\]]", "", t)                       # any other very long bracket
    if " - " in t and key(t.split(" - ", 1)[0]) == key(artist): t = t.split(" - ", 1)[1]
    return t.strip() or None

def main():
    geo = {}
    for g in jl("geo_local.jsonl"):
        if g.get("precision") == "town": geo.setdefault(key(g["artist"]), g)
        else: geo.setdefault(key(g["artist"]), {**g, "place": None})
    charts = {c["yt"]: c for c in jl("charts_tracks.jsonl")}
    awards = {}
    for a in jl("awards_local.jsonl"):
        if a.get("on_list") and not a.get("note"):          # rescinded/annotated awards are never spoken
            awards.setdefault((key(a["artist"]), key(a.get("album"))), []).append(
                {"award": a["award"], "year": a["year"], "result": a["result"]})
    seen, n, rows = set(), 0, []
    with open(os.path.join(HERE, "dj_facts_local.jsonl"), "w", encoding="utf-8") as f:
        for t in jl("tracks_local.jsonl"):
            if t["yt"] in seen: continue
            seen.add(t["yt"])
            r = {"yt": t["yt"], "artist": t["artist"], "title": clean_title(t["title"], t["artist"])}
            if t.get("album"): r["album"] = t["album"]
            if t.get("year"): r["year"] = t["year"]
            g = geo.get(key(t["artist"]))
            if g:
                if g.get("place"): r["place"] = g["place"]
                r["province"] = PROV.get(g.get("province"))
                if g.get("basis"): r["basis"] = g["basis"]
            c = charts.get(t["yt"])
            if c:
                if c.get("peak"): r.update(peak=c["peak"], chart=c.get("chart"), chart_year=min(c["years"]))
                if c.get("year_end"): r["year_end"] = c["year_end"]
                if c.get("ckoi_year_end"): r["ckoi"] = c["ckoi_year_end"]
                if c.get("juno"): r["juno_single"] = c["juno"]
            aw = awards.get((key(t["artist"]), key(t.get("album"))))
            if aw: r["awards"] = aw
            r = {k: v for k, v in r.items() if v is not None}
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
            rows.append(r)
    # demo sample: favour tracks with several facts, mixed provinces
    rich = [r for r in rows if sum(k in r for k in ("album", "place", "peak", "awards")) >= 2]
    random.Random(7).shuffle(rich)
    sample, provs = [], {}
    for r in rich:
        p = r.get("province")
        if provs.get(p, 0) >= 6: continue
        provs[p] = provs.get(p, 0) + 1; sample.append(r)
        if len(sample) == 40: break
    os.makedirs(os.path.join(HERE, "dj"), exist_ok=True)
    json.dump(sample, open(os.path.join(HERE, "dj", "sample.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"dj facts: {n} tracks ({sum('place' in r for r in rows)} with hometown, "
          f"{sum('peak' in r for r in rows)} charted, {sum('awards' in r for r in rows)} award albums); sample {len(sample)}")

if __name__ == "__main__":
    main()
