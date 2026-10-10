#!/usr/bin/env python3
"""Canadian chart history -> filters for the player.

Source: "Canadian Music Blog" (musiccanada.wordpress.com/charts), which lists
per year (1964–2019) every single by a Canadian artist that peaked in the
national Top 40 — RPM (1964–2000), Nielsen SoundScan Canadian Singles Chart
(2001–2006), Billboard Canadian Hot 100 (2007–) — plus CKOI year-end Top 50
Franco hits, JUNO Single of the Year nominees/winners, and full year-end charts
(1967–2025). Each page's own legend ("WP = Weekly chart peak position"…) is
kept next to every number, so nothing is reinterpreted.

Usage:   python3 harvest_charts.py fetch    # ~150 pages, 1.5 s apart (a few minutes)
         python3 harvest_charts.py match    # re-run whenever tracks grow
Output:  charts_local.jsonl   one line per chart table row (raw, with legend)
         charts_tracks.jsonl  one line per harvested track that charted:
           {yt, artist, title, years, chart, peak, year_end, ckoi_year_end,
            juno, us_peak, us_year_end, vancouver_peak, vancouver_year_end, sources}
         peak / year_end = national Canadian chart named in `chart`.
         us_* = U.S. Billboard Hot 100 (2019+ pages). vancouver_* = regional
         "Sounds of Vancouver" lists 1979–86. ckoi_year_end = Québec CKOI Top 50.
Matching is exact artist (an artists.txt name, also inside "A/B", "A & B",
"A feat. B") + same title once brackets, "(Remastered…)", and "Artist - "
prefixes are stripped. No fuzzy matching.
"""
import html, json, os, re, sys, time, unicodedata, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = "https://musiccanada.wordpress.com/charts/"
UA = "Mozilla/5.0 (CanConHarvest; +https://github.com/trendyspenders-hub/cancon-harvest)"
RAW = os.path.join(HERE, "charts_local.jsonl")
OUT = os.path.join(HERE, "charts_tracks.jsonl")

def fetch_html(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            if i == 3: raise
            time.sleep(5 * (i + 1))

def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()

def chart_name(year):
    if year <= 2000: return "RPM"
    if year <= 2006: return "Canadian Singles Chart"
    return "Billboard Canadian Hot 100"

def as_int(v):
    m = re.match(r"\s*#?(\d+)", v or "")
    return int(m.group(1)) if m else None

# ---------------- fetch ----------------

def page_links():
    t = fetch_html(INDEX)
    seen, out = set(), []
    for href, label in re.findall(r'<a[^>]+href="(https://musiccanada\.wordpress\.com/\d{4}/[^"]+)"[^>]*>(.*?)</a>', t, re.S):
        label = text(label)
        if not re.fullmatch(r"(19[5-9]\d|20[0-2]\d)(-\d{4})?", label) or href in seen: continue
        seen.add(href); out.append((label, href))
    return out

def parse_page(url, label):
    t = fetch_html(url)
    m = re.search(r'class="entry-content">(.*?)(<div id="jp-post-flair|<div class="sharedaddy|<footer)', t, re.S)
    body = m.group(1) if m else t
    slug = re.search(r"(\d{4})s?-biggest|of-(\d{4})|(\d{4})-year-end", url)
    year = int(next(g for g in slug.groups() if g)) if slug else int(label[:4])
    kind = "year_end" if "year-end" in url else "canadian_hits"
    legend = {}
    plain = html.unescape(re.sub(r"<[^>]+>", "\n", re.sub(r"<table.*?</table>", "", body, flags=re.S)))
    for code, meaning in re.findall(r"^\s*([A-Z]{1,3})\s*=\s*(.+?)\s*$", plain, re.M):
        legend.setdefault(code, meaning[:120])
    rows, section = [], ""
    for chunk in re.split(r"(<table.*?</table>)", body, flags=re.S):
        if not chunk.startswith("<table"):
            blocks = [text(b) for b in re.split(r"</(?:p|h\d|div|strong)>", chunk)]
            blocks = [b for b in blocks if b and len(b) < 160]
            if blocks: section = blocks[-1]
            continue
        trs = [[text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)] for tr in re.findall(r"<tr.*?</tr>", chunk, re.S)]
        if not trs: continue
        head = [h.upper() for h in trs[0]]
        ti = next((i for i, h in enumerate(head) if h in ("TITLE", "SONG", "SINGLE")), None)
        ai = next((i for i, h in enumerate(head) if h.startswith("ARTIST")), None)
        if ti is None or ai is None: continue
        for r in trs[1:]:
            if len(r) <= max(ti, ai) or not r[ti] or not r[ai]: continue
            metrics = {head[i]: v for i, v in enumerate(r) if i not in (ti, ai) and i < len(head) and v}
            rows.append({"year": year, "kind": kind, "section": section, "title": r[ti], "artist": r[ai],
                         "metrics": metrics, "legend": {k: legend[k] for k in metrics if k in legend},
                         "source_url": url})
    return rows

def fetch():
    links = page_links()
    print(f"{len(links)} chart pages", flush=True)
    total = 0
    with open(RAW, "w", encoding="utf-8") as f:
        for label, url in links:
            try:
                rows = parse_page(url, label)
            except Exception as ex:
                print(f"  !! {url}: {ex}", flush=True); continue
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
            total += len(rows)
            print(f"{label:9} {len(rows):4} rows  {url.split('/')[-2][:60]}", flush=True)
            time.sleep(1.5)
    print(f"DONE: {total} chart rows -> charts_local.jsonl")

# ---------------- match ----------------

def norm(s):
    s = unicodedata.normalize("NFKC", s or "").casefold()
    s = re.sub(r"[‘’´`]", "'", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]+", " ", s)).strip()

def norm_title(s, artist=""):
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s or "")          # (Remastered 2009), [Official Video]
    if artist and " - " in s:                               # "Neil Young - Heart of Gold"
        a, b = s.split(" - ", 1)
        s = b if norm(a) == norm(artist) else s
    s = re.sub(r"\s+-\s+(remaster|live|single|radio|edit|version|mono|stereo).*$", "", s, flags=re.I)
    return norm(s)

SPLIT = re.compile(r"\s*(?:/|&|,|\+|\bx\b|\band\b|\bet\b|\bfeat\.?|\bfeaturing\b|\bft\.?|\bwith\b|\bavec\b)\s*", re.I)

def classify(row):
    """-> dict of normalized fields from this row, using the page's own codes."""
    m, sec, out = row["metrics"], row["section"].upper(), {}
    regional = "sounds-of-vancouver" in row["source_url"]  # CFUN/CKLG-era Vancouver lists, not national
    for code, v in m.items():
        meaning = row["legend"].get(code, "").lower()
        n = as_int(v)
        if code == "JUNO" or "JUNO" in sec:
            out["juno"] = "won" if v.strip().upper().startswith("W") else "nominated"
        elif n is None or code in ("DATE", "CANCON RANK"):
            continue
        elif code in ("BW", "BY"):  # U.S. Billboard Hot 100 — kept apart from Canadian positions
            out["us_peak" if code == "BW" else "us_year_end"] = n
        elif regional:
            out["vancouver_peak" if code == "PEAK" else "vancouver_year_end"] = n
        elif row["year"] < 1964:  # pre-national lists (no Canadian chart yet)
            continue
        elif code == "CY" or "ckoi" in meaning:
            out["ckoi_year_end"] = n
        elif code in ("WP", "HW", "PEAK") or "weekly" in meaning:
            out["peak"] = n
        elif code in ("YE", "HY", "RANK", "POS", "") or "year-end" in meaning or row["kind"] == "year_end":
            out["year_end"] = n
    return out

def match():
    names = {norm(n): n.strip() for n in open(os.path.join(HERE, "artists.txt"), encoding="utf-8") if n.strip()}
    tracks = {}
    for fn in ("tracks_local.jsonl", "tracks_discogs.jsonl"):
        p = os.path.join(HERE, fn)
        if not os.path.exists(p): continue
        for line in open(p, encoding="utf-8"):
            try: t = json.loads(line)
            except Exception: continue
            tracks.setdefault(norm(t["artist"]), []).append((t["yt"], t["title"], t["artist"]))
    songs = {}  # (artist_norm, title_norm) -> merged chart info
    for line in open(RAW, encoding="utf-8"):
        row = json.loads(line)
        info = classify(row)
        if not info: continue
        parts = [row["artist"]] + SPLIT.split(row["artist"])
        for a in dict.fromkeys(norm(p) for p in parts if p.strip()):
            if a not in names: continue
            key = (a, norm_title(row["title"]))
            s = songs.setdefault(key, {"artist": names[a], "title": row["title"], "years": set(), "sources": set()})
            s["years"].add(row["year"]); s["sources"].add(row["source_url"])
            for k, v in info.items():
                if k == "juno": s[k] = "won" if "won" in (s.get(k), v) else v
                else: s[k] = min(v, s.get(k, v))
            if "peak" in info or "year_end" in info: s["chart"] = chart_name(row["year"])
    out, matched_songs = {}, 0
    for (a, t), s in songs.items():
        hits = [yt for yt, title, artist in tracks.get(a, []) if norm_title(title, artist) == t]
        if hits: matched_songs += 1
        for yt in hits:
            rec = {"yt": yt, "artist": s["artist"], "title": s["title"], "years": sorted(s["years"]),
                   **{k: s[k] for k in ("chart", "peak", "year_end", "ckoi_year_end", "juno", "us_peak",
                                         "us_year_end", "vancouver_peak", "vancouver_year_end") if k in s},
                   "sources": sorted(s["sources"])}
            old = out.get(yt)
            if not old or rec.get("peak", 999) < old.get("peak", 999): out[yt] = rec
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out.values(): f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(songs)} charted songs by artists on the list | {matched_songs} found among harvested tracks "
          f"| {len(out)} track lines -> charts_tracks.jsonl")

if __name__ == "__main__":
    {"fetch": fetch, "match": match}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
