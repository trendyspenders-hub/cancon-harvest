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
Second pass: artists with no usable location but a Wikidata ID (links_local)
get their place of formation (P740) or birth (P19), only if it is in Canada.
Usage:   python3 harvest_geo.py [catalog.csv]
Output:  geo_local.jsonl — {artist, location, lat, lon, precision: town|province,
          place, province, geonameid, source, basis?, wikidata_place?}
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

PROV_QID = {"Q1951": "AB", "Q1973": "BC", "Q1948": "MB", "Q1965": "NB", "Q2003": "NL", "Q1952": "NS",
            "Q1904": "ON", "Q1979": "PE", "Q176": "QC", "Q1989": "SK", "Q2009": "YT", "Q2007": "NT", "Q2023": "NU"}

def nearest_province(lat, lon, towns):
    """Province of the nearest GeoNames town (Wikidata gives coordinates; the
    province lookup stays offline)."""
    best = None
    for recs in towns.values():
        for pop, prov, tlat, tlon, *_ in recs:
            d = (tlat - lat) ** 2 + ((tlon - lon) * 0.7) ** 2
            if best is None or d < best[0]: best = (d, prov)
    return best[1] if best else None

def _entities(ids, props):
    """Wikidata entity API (no SPARQL — lookups by ID don't time out)."""
    import time, urllib.parse, urllib.request
    out = {}
    for i in range(0, len(ids), 50):
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(ids[i:i + 50]), "props": props,
            "languages": "en|fr", "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": "CanConHarvest/1.0 (https://github.com/trendyspenders-hub/cancon-harvest)"})
        for attempt in range(3):
            try:
                out.update(json.load(urllib.request.urlopen(req, timeout=60)).get("entities", {})); break
            except Exception:
                if attempt == 2: raise
                time.sleep(10)
        time.sleep(0.5)
    return out

def _claim_ids(ent, prop):
    return [c["mainsnak"]["datavalue"]["value"]["id"] for c in (ent.get("claims") or {}).get(prop, [])
            if c.get("rank") != "deprecated" and (c.get("mainsnak") or {}).get("datavalue")]

def wikidata_places(qids):
    """Place of formation (bands, P740) or birth (people, P19) — only places
    whose country (P17) is Canada, with coordinates (P625). -> {qid: rec}"""
    artists = _entities(list(qids), "claims")
    pick = {}
    for qid, ent in artists.items():
        for prop, basis in (("P740", "formed in"), ("P19", "born in")):   # formation beats birth
            ids = _claim_ids(ent, prop)
            if ids: pick[qid] = (ids[0], basis); break
    places = _entities(sorted({p for p, _ in pick.values()}), "claims|labels")
    out = {}
    for qid, (pid, basis) in pick.items():
        pl = places.get(pid) or {}
        if "Q16" not in _claim_ids(pl, "P17"): continue                    # not in Canada
        coord = next((c["mainsnak"]["datavalue"]["value"] for c in (pl.get("claims") or {}).get("P625", [])
                      if (c.get("mainsnak") or {}).get("datavalue")), None)
        if not coord: continue
        label = ((pl.get("labels") or {}).get("en") or (pl.get("labels") or {}).get("fr") or {}).get("value")
        out[qid] = {"lat": round(coord["latitude"], 4), "lon": round(coord["longitude"], 4), "precision": "town",
                    "place": label, "province": None, "geonameid": None, "basis": basis, "wikidata_place": pid}
    return out

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "canadian_music_discovery_catalog-7.csv")
    if not os.path.exists(GN): raise SystemExit(__doc__)
    towns, centres = load_places()
    cache, stats, placed = {}, defaultdict(int), set()
    with open(os.path.join(HERE, "geo_local.jsonl"), "w", encoding="utf-8") as out:
        for r in csv.DictReader(open(src, encoding="utf-8-sig")):
            loc, artist = (r.get("location") or "").strip(), (r.get("artist") or "").strip()
            if not loc or not artist: stats["no location"] += 1; continue
            if loc not in cache: cache[loc] = geocode(loc, towns, centres)
            g = cache[loc]
            if not g: stats["unmatched"] += 1; continue
            stats[g["precision"]] += 1
            placed.add(artist.casefold())
            out.write(json.dumps({"artist": artist, "location": loc, **g,
                                  "source": "GeoNames (CC BY 4.0)"}, ensure_ascii=False) + "\n")
        # Second source: artists with no usable catalog location but a Wikidata ID
        links = os.path.join(HERE, "links_local.jsonl")
        qids = {}
        if os.path.exists(links):
            for line in open(links, encoding="utf-8"):
                d = json.loads(line)
                if d.get("source") == "wikidata" and d.get("id") and d["artist"].casefold() not in placed:
                    qids.setdefault(d["id"], d["artist"])
        for qid, g in wikidata_places(qids).items():
            g["province"] = nearest_province(g["lat"], g["lon"], towns)
            stats["wikidata town"] += 1
            out.write(json.dumps({"artist": qids[qid], "location": None, **g,
                                  "source": "Wikidata (CC0)"}, ensure_ascii=False) + "\n")
    print(dict(stats))
    print("unmatched locations:", [l for l, g in cache.items() if not g][:25])

if __name__ == "__main__":
    main()
