#!/usr/bin/env python3
"""Wikipedia-sourced extras (text is CC BY-SA 4.0 — the site must credit
Wikipedia and link the article).

Stage `bios`    For artists with a Wikidata ID in links_local.jsonl: find the
                English and French Wikipedia articles (Wikidata sitelinks),
                then the article summary (Wikipedia REST API).
                -> bios_local.jsonl {artist, qid, lang, title, extract, url, license}
Stage `awards`  Polaris Music Prize winners + shortlists, Polaris Heritage
                Prize, JUNO Album of the Year winners + nominees, parsed from
                the Wikipedia tables. Matched to artists.txt by exact name.
                -> awards_local.jsonl {award, year, result, artist, album,
                   on_list, source_url}

Usage:   python3 harvest_wiki.py bios | awards
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "CanConHarvest/1.0 (https://github.com/trendyspenders-hub/cancon-harvest)"

def get_json(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))
        except Exception:
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))

def norm(s):
    """Exact match, ignoring accents, case, hyphens and punctuation
    ("Céline Dion" = "Celine Dion", "Lauren Spencer-Smith" = "Lauren Spencer Smith")."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^\w&' ]+", " ", s.replace("’", "'"))).strip().casefold()

# ---------------- bios ----------------

def bios():
    qids = {}
    for line in open(os.path.join(HERE, "links_local.jsonl"), encoding="utf-8"):
        d = json.loads(line)
        if d.get("source") == "wikidata" and d.get("id"): qids.setdefault(d["id"], d["artist"])
    ids = list(qids)
    print(f"bios: {len(ids)} artists with Wikidata IDs", flush=True)
    with open(os.path.join(HERE, "bios_local.jsonl"), "w", encoding="utf-8") as out:
        n = 0
        for i in range(0, len(ids), 50):
            batch = ids[i:i + 50]
            ents = (get_json("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode({
                "action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks",
                "sitefilter": "enwiki|frwiki", "format": "json"})) or {}).get("entities", {})
            time.sleep(0.5)
            for qid in batch:
                links = (ents.get(qid) or {}).get("sitelinks") or {}
                for lang in ("en", "fr"):
                    title = (links.get(f"{lang}wiki") or {}).get("title")
                    if not title: continue
                    s = get_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe=""))
                    time.sleep(0.25)
                    if not s or s.get("type") == "disambiguation" or not s.get("extract"): continue
                    out.write(json.dumps({"artist": qids[qid], "qid": qid, "lang": lang, "title": s.get("title"),
                                          "extract": s["extract"],
                                          "url": (s.get("content_urls") or {}).get("desktop", {}).get("page"),
                                          "license": "CC BY-SA 4.0 (Wikipedia)"}, ensure_ascii=False) + "\n")
                    n += 1
            out.flush()
            print(f"  {min(i + 50, len(ids))}/{len(ids)} artists, {n} summaries", flush=True)
    print(f"DONE: {n} summaries -> bios_local.jsonl")

# ---------------- awards ----------------

def tables(page, section=None):
    q = {"action": "parse", "page": page, "prop": "text", "format": "json", "formatversion": 2}
    if section is not None: q["section"] = section
    t = (get_json("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(q)) or {}).get("parse", {}).get("text", "")
    time.sleep(1)
    out = []
    for tb in re.findall(r'<table class="wikitable.*?</table>', t, re.S):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", tb, re.S):
            cells = []
            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S):
                c = re.sub(r"<sup.*?</sup>", "", c, flags=re.S)
                items = re.split(r"<br\s*/?>|</li>|</p>", c)      # one entry per line/list item
                cells.append([pair(x) for x in items if plain(x)])
            rows.append(cells)
        out.append(rows)
    return out

def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()

class Entry(str):
    """Cell item: its plain text, plus .artist/.album split on Wikipedia's
    convention that album titles are italic (works for "Artist – Album",
    "Artist, Album" and "Album – Artist" alike)."""

def pair(fragment):
    e = Entry(plain(fragment))
    m = re.search(r"<i>(.*?)</i>", fragment, re.S)
    e.album = plain(m.group(1)) if m else None
    rest = plain(fragment[:m.start()] + " " + fragment[m.end():]) if m else str(e)
    e.artist = re.sub(r"^[\s–—,:-]+|[\s–—,:-]+$", "", rest) or None
    return e

def split_pair(e, album_first=False):
    if getattr(e, "album", None): return e.artist, e.album
    parts = re.split(r"\s+[–—-]\s+", e, maxsplit=1)          # no italics: fall back to the dash
    if len(parts) != 2: return None, None
    return (parts[1], parts[0]) if album_first else (parts[0], parts[1])

def section_index(page, title):
    secs = (get_json("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "sections", "format": "json"})) or {}).get("parse", {}).get("sections", [])
    time.sleep(1)
    return next((s["index"] for s in secs if s["line"].lower().startswith(title.lower())), None)

def awards():
    names = {norm(n): n.strip() for n in open(os.path.join(HERE, "artists.txt"), encoding="utf-8") if n.strip()}
    recs = []
    def add(award, year, result, artist, album, url):
        if not artist: return
        note = None
        m = re.search(r"\(([^)]*)\)\s*$", artist)          # "(rescinded in 2025)" etc. — keep as a note
        if m and not re.search(r"\(\d+\)$", artist):
            note, artist = m.group(1), artist[:m.start()]
        artist = re.sub(r"^.*?\b(?:announced|to be announced)\b[^.]*\.\s*", "", artist, flags=re.I)  # table notes
        artist = re.sub(r"[\s–—,:-]+$", "", artist).strip()
        if not artist: return
        k = norm(artist)
        recs.append({"award": award, "year": year, "result": result, "artist": names.get(k, artist),
                     "album": album, "on_list": k in names, "note": note, "source_url": url})

    page = "Polaris_Music_Prize"; url = "https://en.wikipedia.org/wiki/" + page
    for rows in tables(page, section_index(page, "Winners and shortlists")):
        for cells in rows[1:]:
            if len(cells) < 3 or not cells[0] or not re.match(r"\d{4}", cells[0][0]): continue
            year = int(cells[0][0][:4])
            for e in cells[1]: add("Polaris Music Prize", year, "winner", *split_pair(e), url)
            for e in cells[2]: add("Polaris Music Prize", year, "shortlist", *split_pair(e), url)
    for rows in tables(page, section_index(page, "Slaight Family Polaris Heritage")):
        year = None
        for cells in rows[1:]:
            if cells and cells[0] and re.match(r"\d{4}$", cells[0][0]): year = int(cells[0][0]); cells = cells[1:]
            if year and cells and cells[0]:
                for e in cells[0]: add("Polaris Heritage Prize", year, "winner", *split_pair(e), url)

    page = "Juno_Award_for_Album_of_the_Year"; url = "https://en.wikipedia.org/wiki/" + page
    for rows in tables(page):
        head = [norm(c[0]) if c else "" for c in rows[0]]
        if "winner" not in head or "album" not in head: continue
        wi, ai = head.index("winner"), head.index("album")
        ni = head.index("nominees") if "nominees" in head else None
        year = None
        for cells in rows[1:]:
            if cells and cells[0] and re.match(r"\d{4}$", cells[0][0]): year = int(cells[0][0])
            else: cells = [[str(year)]] + cells          # rowspan'd year
            if not year or len(cells) <= max(wi, ai): continue
            if head[1] == "award": continue                # 1974 split-category table
            add("JUNO Album of the Year", year, "winner", (cells[wi] or [""])[0], (cells[ai] or [""])[0], url)
            if ni is not None and len(cells) > ni:
                for e in cells[ni]: add("JUNO Album of the Year", year, "nominee", *split_pair(e, album_first=True), url)

    with open(os.path.join(HERE, "awards_local.jsonl"), "w", encoding="utf-8") as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in recs: by.setdefault(r["award"], [0, 0]); by[r["award"]][0] += 1; by[r["award"]][1] += r["on_list"]
    print("DONE:", {k: f"{v[0]} entries, {v[1]} artists on the list" for k, v in by.items()})

if __name__ == "__main__":
    {"bios": bios, "awards": awards}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
