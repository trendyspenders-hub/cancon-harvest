#!/usr/bin/env python3
"""Streaming / profile links for every artist — sourced, never guessed.

Stage 1  wikidata     one SPARQL query: Canadian musicians & bands with
                      Spotify / Apple Music / SoundCloud / Bandcamp / Deezer IDs
                      and official website. Matched to artists.txt by exact name
                      (English or French label); names shared by 2+ Wikidata
                      entries are skipped.
Stage 2  musicbrainz  per artist, 1 request/second (MusicBrainz rule): exact
                      name match with country = CA, and only when exactly one
                      such artist exists. Pulls the artist's URL relations.

Setup:   no extra packages (stdlib only)
Usage:   python3 harvest_links.py wikidata
         python3 harvest_links.py musicbrainz [artists.txt]
Output:  links_local.jsonl — one line per artist per source:
         {artist, source, id, spotify, apple_music, soundcloud, bandcamp,
          deezer, tidal, website}   (missing = absent key)
         links_done.jsonl — MusicBrainz artists already looked up (resume).

Never touches tracks_local.jsonl. When the same field comes from both
sources, the site should prefer wikidata, then musicbrainz — and they agree
in nearly every case (same Spotify ID).
"""
import json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "links_local.jsonl")
DONE = os.path.join(HERE, "links_done.jsonl")
UA = "CanConHarvest/1.0 ( https://github.com/trendyspenders-hub/cancon-harvest )"

def get_json(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))  # 503 = MusicBrainz asking us to slow down
        except Exception:
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()

def artist_names(path):
    return [n.strip() for n in open(path, encoding="utf-8") if n.strip()]

def write(f, rec):
    f.write(json.dumps({k: v for k, v in rec.items() if v}, ensure_ascii=False) + "\n")

# ---------- Stage 1: Wikidata ----------

SPARQL = """
SELECT ?a ?name ?sp ?am ?sc ?bc ?dz ?web WHERE {
  { ?a wdt:P27 wd:Q16 } UNION { ?a wdt:P495 wd:Q16 } UNION { ?a wdt:P740/wdt:P17 wd:Q16 }
  { ?a wdt:P106/wdt:P279* wd:Q639669 } UNION { ?a wdt:P31/wdt:P279* wd:Q215380 }
  ?a rdfs:label ?name . FILTER(LANG(?name) IN ("en","fr"))
  OPTIONAL { ?a wdt:P1902 ?sp } OPTIONAL { ?a wdt:P2850 ?am } OPTIONAL { ?a wdt:P3040 ?sc }
  OPTIONAL { ?a wdt:P3283 ?bc } OPTIONAL { ?a wdt:P2722 ?dz } OPTIONAL { ?a wdt:P856 ?web }
  FILTER(BOUND(?sp) || BOUND(?am) || BOUND(?sc) || BOUND(?bc) || BOUND(?dz))
}"""

URLS = {
    "sp": ("spotify", "https://open.spotify.com/artist/{}"),
    "am": ("apple_music", "https://music.apple.com/ca/artist/{}"),
    "sc": ("soundcloud", "https://soundcloud.com/{}"),
    "bc": ("bandcamp", "https://{}.bandcamp.com/"),
    "dz": ("deezer", "https://www.deezer.com/artist/{}"),
    "web": ("website", "{}"),
}

def wikidata():
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": SPARQL, "format": "json"})
    rows = get_json(url)["results"]["bindings"]
    by_name = {}  # name -> {qid -> record}
    for x in rows:
        qid = x["a"]["value"].rsplit("/", 1)[-1]
        rec = by_name.setdefault(norm(x["name"]["value"]), {}).setdefault(qid, {"id": qid})
        for k, (field, fmt) in URLS.items():
            if k in x and field not in rec:  # first value per field
                rec[field] = fmt.format(x[k]["value"])
    names = artist_names(os.path.join(HERE, "artists.txt"))
    kept = skipped = 0
    with open(OUT, "a", encoding="utf-8") as f:
        for n in names:
            hits = by_name.get(norm(n))
            if not hits: continue
            if len(hits) > 1: skipped += 1; continue  # ambiguous name
            write(f, {"artist": n, "source": "wikidata", **next(iter(hits.values()))})
            kept += 1
    print(f"wikidata: {kept} artists linked, {skipped} skipped as ambiguous")

# ---------- Stage 2: MusicBrainz ----------

def classify(url):
    h = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    if h == "open.spotify.com" and "/artist/" in url: return "spotify"
    if h in ("music.apple.com", "itunes.apple.com") and "/artist/" in url: return "apple_music"
    if h == "soundcloud.com": return "soundcloud"
    if h.endswith("bandcamp.com"): return "bandcamp"
    if h == "deezer.com" and "/artist/" in url: return "deezer"
    if h in ("tidal.com", "listen.tidal.com") and "/artist/" in url: return "tidal"
    return None

def musicbrainz(names_file):
    names = artist_names(names_file)
    done = set()
    if os.path.exists(DONE):
        for line in open(DONE, encoding="utf-8"):
            try: done.add(norm(json.loads(line)["artist"]))
            except Exception: pass
    todo = [n for n in names if norm(n) not in done]
    print(f"musicbrainz: {len(todo)} artists queued ({len(done)} done)", flush=True)
    out, log = open(OUT, "a", encoding="utf-8"), open(DONE, "a", encoding="utf-8")
    found = 0
    for i, name in enumerate(todo):
        status = "none"
        try:
            q = urllib.parse.quote(f'artist:"{name}" AND country:CA')
            res = get_json(f"https://musicbrainz.org/ws/2/artist?query={q}&fmt=json&limit=10")
            time.sleep(1.1)
            exact = [a for a in (res or {}).get("artists", [])
                     if a.get("country") == "CA" and (norm(a.get("name")) == norm(name)
                        or any(norm(al.get("name")) == norm(name) for al in a.get("aliases") or []))]
            if len(exact) > 1:
                status = "ambiguous"
            elif exact:
                mbid = exact[0]["id"]
                art = get_json(f"https://musicbrainz.org/ws/2/artist/{mbid}?inc=url-rels&fmt=json")
                time.sleep(1.1)
                rec = {"artist": name, "source": "musicbrainz", "id": mbid}
                for r in (art or {}).get("relations", []):
                    u = (r.get("url") or {}).get("resource", "")
                    field = classify(u) or ("website" if r.get("type") == "official homepage" else None)
                    if field and field not in rec: rec[field] = u
                if len(rec) > 3:
                    write(out, rec); out.flush(); found += 1; status = "linked"
                else:
                    status = "no-links"
        except Exception as ex:
            print(f"  !! {name}: {ex}", flush=True)
            time.sleep(10)
            continue  # not logged -> retried next run
        log.write(json.dumps({"artist": name, "status": status}, ensure_ascii=False) + "\n"); log.flush()
        if i % 100 == 0:
            print(f"{time.strftime('%H:%M:%S')} [{i}/{len(todo)}] {name} | {status} | {found} linked", flush=True)
    print("DONE")

if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "wikidata": wikidata()
    elif stage == "musicbrainz": musicbrainz(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "artists.txt"))
    else: print(__doc__)
