#!/usr/bin/env python3
"""Upcoming concerts for artists on the list -> "Playing live near you".

Providers (keys are read from the environment or a local .env file, which is
git-ignored — NEVER commit a key; this repo is public):

  ticketmaster   TICKETMASTER_API_KEY — free, self-serve at
                 developer.ticketmaster.com (My Apps -> Add New App).
                 Default quota 5,000 calls/day. We pull EVERY upcoming music
                 event in Canada (province by province, month by month), then
                 keep events whose lineup contains an artist on the list.
                 ~100–300 calls per run, not one per artist.
  bandsintown    BANDSINTOWN_APP_ID — not self-serve: must be approved by
                 Bandsintown (API@bandsintown.com). Queried per artist, only
                 for artists that have tracks in rotation, 1 request/second.

Matching: exact artist name (case/spacing-insensitive). When the provider
gives a MusicBrainz ID and links_local.jsonl has one for that artist, they
must agree, otherwise the event is dropped. Generic one-word names are not
special-cased — check `match` in the output.

Usage:   python3 harvest_events.py ticketmaster [months_ahead]   (default 6)
         python3 harvest_events.py bandsintown
Output:  events_local.jsonl — rebuilt each run (upcoming only):
         {artist, provider, event_id, date, time, venue, city, region,
          country, lat, lon, url, lineup, match: mbid|name}
Display rules: always link the provider's own event `url` for tickets and
credit the provider ("via Ticketmaster" / "via Bandsintown").
"""
import datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "events_local.jsonl")
PROVINCES = ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]

def load_env():
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            m = re.match(r"\s*([A-Z_]+)\s*=\s*(.+?)\s*$", line)
            if m: os.environ.setdefault(m.group(1), m.group(2).strip('"\''))

def get_json(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CanConHarvest/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code in (401, 403): raise SystemExit(f"Key rejected (HTTP {e.code}) — check the key in .env")
            if i == tries - 1: raise
            time.sleep(60 if e.code == 429 else 5 * (i + 1))
        except Exception:
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()

def artist_index():
    names = {norm(n): n.strip() for n in open(os.path.join(HERE, "artists.txt"), encoding="utf-8") if n.strip()}
    mbids = {}
    p = os.path.join(HERE, "links_local.jsonl")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)
            if d.get("source") == "musicbrainz": mbids[norm(d["artist"])] = d.get("id")
    return names, mbids

def write_all(events):
    with open(OUT, "w", encoding="utf-8") as f:
        for e in sorted(events.values(), key=lambda e: (e["date"], e["artist"])):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"DONE: {len(events)} upcoming events for {len({e['artist'] for e in events.values()})} artists -> events_local.jsonl")

# ---------------- Ticketmaster ----------------

TM = "https://app.ticketmaster.com/discovery/v2/events.json?"

def tm_window(key, prov, start, end, calls):
    """All music events in one province between start and end, splitting the
    window when it holds more than Ticketmaster's 1,000-result paging cap."""
    base = {"apikey": key, "countryCode": "CA", "stateCode": prov, "classificationName": "music",
            "startDateTime": start.strftime("%Y-%m-%dT00:00:00Z"),
            "endDateTime": end.strftime("%Y-%m-%dT23:59:59Z"), "size": 200, "sort": "date,asc"}
    first = get_json(TM + urllib.parse.urlencode({**base, "page": 0})); calls[0] += 1; time.sleep(0.6)
    total = ((first or {}).get("page") or {}).get("totalElements", 0)
    if total > 1000 and (end - start).days > 1:
        mid = start + (end - start) / 2
        return tm_window(key, prov, start, mid, calls) + tm_window(key, prov, mid + dt.timedelta(days=1), end, calls)
    out = ((first or {}).get("_embedded") or {}).get("events", [])
    for page in range(1, min(5, -(-total // 200))):
        d = get_json(TM + urllib.parse.urlencode({**base, "page": page})); calls[0] += 1; time.sleep(0.6)
        out += ((d or {}).get("_embedded") or {}).get("events", [])
    return out

def ticketmaster(months):
    key = os.environ.get("TICKETMASTER_API_KEY")
    if not key: raise SystemExit("Set TICKETMASTER_API_KEY in .env (free key: developer.ticketmaster.com -> My Apps -> Add New App)")
    names, mbids = artist_index()
    today = dt.date.today(); calls = [0]; events = {}
    for prov in PROVINCES:
        start = today
        while start < today + dt.timedelta(days=30 * months):
            end = start + dt.timedelta(days=30)
            for ev in tm_window(key, prov, start, end, calls):
                emb = ev.get("_embedded") or {}
                venue = (emb.get("venues") or [{}])[0]
                lineup = [a.get("name", "") for a in emb.get("attractions") or []]
                for a in emb.get("attractions") or []:
                    k = norm(a.get("name"))
                    if k not in names: continue
                    tm_mb = [x.get("id") for x in ((a.get("externalLinks") or {}).get("musicbrainz") or [])]
                    if tm_mb and mbids.get(k) and mbids[k] not in tm_mb: continue  # same name, different artist
                    loc = venue.get("location") or {}
                    events[(names[k], ev["id"])] = {
                        "artist": names[k], "provider": "ticketmaster", "event_id": ev["id"],
                        "date": (ev.get("dates") or {}).get("start", {}).get("localDate"),
                        "time": (ev.get("dates") or {}).get("start", {}).get("localTime"),
                        "venue": venue.get("name"), "city": (venue.get("city") or {}).get("name"),
                        "region": (venue.get("state") or {}).get("stateCode"), "country": "CA",
                        "lat": float(loc["latitude"]) if loc.get("latitude") else None,
                        "lon": float(loc["longitude"]) if loc.get("longitude") else None,
                        "url": ev.get("url"), "lineup": lineup,
                        "match": "mbid" if tm_mb and mbids.get(k) else "name"}
            start = end + dt.timedelta(days=1)
        print(f"{prov}: {calls[0]} calls so far, {len(events)} matched events", flush=True)
    write_all({f"{a}|{i}": e for (a, i), e in events.items()})

# ---------------- Bandsintown ----------------

def bandsintown():
    app = os.environ.get("BANDSINTOWN_APP_ID")
    if not app: raise SystemExit("Set BANDSINTOWN_APP_ID in .env (requires approval: API@bandsintown.com)")
    names, mbids = artist_index()
    in_rotation = set()
    for line in open(os.path.join(HERE, "tracks_local.jsonl"), encoding="utf-8"):
        in_rotation.add(norm(json.loads(line)["artist"]))
    events = {}
    for i, k in enumerate(sorted(in_rotation & set(names))):
        q = urllib.parse.quote(names[k], safe="")
        info = get_json(f"https://rest.bandsintown.com/artists/{q}?app_id={app}"); time.sleep(1)
        if not info or norm(info.get("name")) != k: continue
        if info.get("mbid") and mbids.get(k) and info["mbid"] != mbids[k]: continue
        for ev in get_json(f"https://rest.bandsintown.com/artists/{q}/events?app_id={app}&date=upcoming") or []:
            v = ev.get("venue") or {}
            events[f"{names[k]}|{ev.get('id')}"] = {
                "artist": names[k], "provider": "bandsintown", "event_id": ev.get("id"),
                "date": (ev.get("datetime") or "")[:10], "time": (ev.get("datetime") or "")[11:16] or None,
                "venue": v.get("name"), "city": v.get("city"), "region": v.get("region"),
                "country": v.get("country"), "lat": float(v["latitude"]) if v.get("latitude") else None,
                "lon": float(v["longitude"]) if v.get("longitude") else None,
                "url": ev.get("url"), "lineup": ev.get("lineup") or [],
                "match": "mbid" if info.get("mbid") and mbids.get(k) else "name"}
        time.sleep(1)
        if i % 200 == 0: print(f"[{i}] {names[k]} | {len(events)} events", flush=True)
    write_all(events)

if __name__ == "__main__":
    load_env()
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "ticketmaster": ticketmaster(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    elif which == "bandsintown": bandsintown()
    else: print(__doc__)
