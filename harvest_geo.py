#!/usr/bin/env python3
"""Map coordinates for artists' home towns (Road Trip Mode, Near You).

Offline: uses the GeoNames Canada dump (CC BY 4.0, geonames.org) in
geonames/CA.txt — download once:
    mkdir -p geonames && cd geonames && curl -O https://download.geonames.org/export/dump/CA.zip && unzip CA.zip

Input:   the `location` column of the site's catalog export
         (default ../canadian_music_discovery_catalog-7.csv)
Rules:   a town is only matched INSIDE the province the location names
         ("Richmond, BC" never becomes Richmond, QC). No province named -> only
         a unique town name in all of Canada is accepted. Province-only
         locations get the province centre with precision "province".
         Anything else (e.g. "Atlantic Canada") is left without coordinates.
Usage:   python3 harvest_geo.py [catalog.csv]
Output:  geo_local.jsonl — {artist, location, lat, lon, precision: town|province,
          place, province, geonameid, source}
"""
import csv, json, os, re, sys, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
GN = os.path.join(HERE, "geonames", "CA.txt")
ADMIN1 = {"01": "AB", "02": "BC", "03": "MB", "04": "NB", "05": "NL", "07": "NS", "08": "ON",
          "09": "PE", "10": "QC", "11": "SK", "12": "YT", "13": "NT", "14": "NU"}
PROV_NAMES = {
    "AB": ["ab", "alta", "alberta"], "BC": ["bc", "b c", "british columbia"],
    "MB": ["mb", "man", "manitoba"], "NB": ["nb", "n b", "new brunswick", "nouveau brunswick"],
    "NL": ["nl", "nfld", "newfoundland", "newfoundland and labrador", "labrador"],
    "NS": ["ns", "n s", "nova scotia", "nouvelle ecosse"], "ON": ["on", "ont", "ontario"],
    "PE": ["pe", "pei", "p e i", "prince edward island"], "QC": ["qc", "pq", "que", "quebec"],
    "SK": ["sk", "sask", "saskatchewan"], "YT": ["yt", "yukon"],
    "NT": ["nt", "nwt", "northwest territories"], "NU": ["nu", "nunavut"],
}

def key(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()

PROV_BY_KEY = {key(n): p for p, ns in PROV_NAMES.items() for n in ns}

def load_places():
    towns = defaultdict(list)   # (name_key) -> [(pop, prov, lat, lon, name, id)]
    centres = {}
    for line in open(GN, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 15: continue
        gid, name, ascii_, alts, lat, lon, fclass, fcode, admin1, pop = f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[10], f[14]
        prov = ADMIN1.get(admin1)
        if not prov: continue
        if fcode == "ADM1":
            centres[prov] = (float(lat), float(lon)); continue
        if fclass != "P" and fcode not in ("RESV", "RESW"): continue  # towns + First Nations reserves
        rec = (int(pop or 0), prov, float(lat), float(lon), name, gid)
        for n in {name, ascii_, *[a for a in alts.split(",") if a and not re.search(r"\d", a)]}:
            k = key(n)
            if k: towns[k].append(rec)
    return towns, centres

def geocode(loc, towns, centres):
    parts = [p.strip() for p in re.sub(r"\(.*?\)", "", loc).split(",") if p.strip()]
    parts = [p for p in parts if key(p) not in ("canada", "ca")]
    provs = [PROV_BY_KEY[key(p)] for p in parts if key(p) in PROV_BY_KEY]
    prov = provs[-1] if provs else None
    # The first segment is the town — unless it is just a province name on its own
    # ("Manitoba", "Quebec, Canada"). "Quebec, QC" / "Québec City, QC" are towns.
    first = parts[0] if parts else ""
    if first and not (key(first) in PROV_BY_KEY and len(provs) <= 1 and len(parts) == 1):
        variants = [key(first), key(re.sub(r"\b(city|ville de|town of|city of)\b", "", first, flags=re.I))]
        for k in dict.fromkeys(v for v in variants if v):
            words = k.split()
            for n in range(len(words), 0, -1):   # "toronto rap scene" -> "toronto rap" -> "toronto"
                cand = towns.get(" ".join(words[:n]), [])
                if n < len(words): cand = [c for c in cand if c[0] >= 1000]  # shortened: real towns only
                if prov: cand = [c for c in cand if c[1] == prov]
                elif len({c[1] for c in cand}) > 1:   # same name in 2+ provinces:
                    top = sorted(cand, reverse=True)       # only a dominant city wins ("Toronto")
                    other = max((c[0] for c in top if c[1] != top[0][1]), default=0)
                    cand = [top[0]] if top[0][0] >= 100000 and top[0][0] >= 10 * other else []
                if cand:
                    pop, pv, lat, lon, name, gid = max(cand)
                    return {"lat": round(lat, 4), "lon": round(lon, 4), "precision": "town",
                            "place": name, "province": pv, "geonameid": gid}
    if prov and prov in centres:
        lat, lon = centres[prov]
        return {"lat": round(lat, 4), "lon": round(lon, 4), "precision": "province",
                "place": None, "province": prov, "geonameid": None}
    return None

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "canadian_music_discovery_catalog-7.csv")
    if not os.path.exists(GN): raise SystemExit(__doc__)
    towns, centres = load_places()
    cache, stats = {}, defaultdict(int)
    with open(os.path.join(HERE, "geo_local.jsonl"), "w", encoding="utf-8") as out:
        for r in csv.DictReader(open(src, encoding="utf-8-sig")):
            loc, artist = (r.get("location") or "").strip(), (r.get("artist") or "").strip()
            if not loc or not artist: stats["no location"] += 1; continue
            if loc not in cache: cache[loc] = geocode(loc, towns, centres)
            g = cache[loc]
            if not g: stats["unmatched"] += 1; continue
            stats[g["precision"]] += 1
            out.write(json.dumps({"artist": artist, "location": loc, **g,
                                  "source": "GeoNames (CC BY 4.0)"}, ensure_ascii=False) + "\n")
    print(dict(stats))
    print("unmatched locations:", [l for l, g in cache.items() if not g][:25])

if __name__ == "__main__":
    main()
