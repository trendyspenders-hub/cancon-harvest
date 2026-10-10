# CanCon Topic Harvest

This folder is a self-contained job: harvest YouTube "… - Topic" channel
uploads for 20,862 Canadian artists listed in `artists.txt`.

## What's here

- `harvest_topic_local.py` — the harvester (requires `pip3 install yt-dlp ytmusicapi`)
- `artists.txt` — one artist per line. First the 15,155 artists in
  `canadian_music_discovery_catalog-7.csv` (the user's final list, kept in the
  original priority order: francophone/Spanish, then acts with no tracks in the
  player, then the rest), then 5,707 older live-directory names not in
  catalog-7 — lower confidence, some aren't musicians (e.g. photographers,
  actors), harvested last
- `tracks_local.jsonl` — results accumulate here (created on first run)

## Commands

```bash
# smoke test — 20 artists only
head -20 artists.txt > test.txt && python3 harvest_topic_local.py test.txt 10

# full run
python3 harvest_topic_local.py artists.txt 10
```

## Behaviour rules

- The script is **resumable**: artists logged in `harvest_done.jsonl` with
  `"albums": true` are skipped — including ones that found nothing. Older log
  lines (from before album support) are re-run; a track already in
  `tracks_local.jsonl` for that artist is never written twice. Failed lookups
  aren't logged, so they're retried; 5 failures in a row pauses 10 minutes.
- `harvest_done.jsonl` records one line per artist searched:
  `{artist, source: topic|verified|ytmusic|none, channel, kept, releases, albums}`.
- Each line of output is one video: `{yt, title, artist, album, year, …}`.
- Finding the artist, in order: their own Topic channel (named exactly
  `<artist> - Topic`); else their
  **verified** artist channel (verified badge AND channel name equals the
  artist, or starts with "<artist> ", or is "<artist>VEVO"); else a YouTube
  Music artist page whose name equals the artist exactly (`source: ytmusic` —
  the least certain match, worth spot-checking for generic names). Only the
  single best-matching channel is kept. Never fan uploads.
- **Strict names**: artists in `strict_artists.txt` (the 5,707 extras not in
  catalog-7) accept Topic or verified channels only — no name-only ytmusic
  match. The user prefers leaving an artist directory-only over crediting a
  same-name stranger. Name-only matches already harvested for them were removed
  (log lines with `"note": "strict: …"`; backup `tracks_local.jsonl.before-strict`).
- **Albums**: every album, EP and single on that artist's YouTube Music page is
  harvested in full (via `ytmusicapi`), with `album` and `year` filled in. Up to
  N (`10`) channel videos are kept too, with `album: ""`. yt-dlp can't open
  album playlists (`OLAK5uy_…` → HTTP 400 as of 2026.08), hence ytmusicapi.
- Be polite: the built-in 1s spacing between artists stays. Don't parallelise
  against YouTube; if requests start failing, stop and wait before resuming.
- `10` caps channel videos only — album tracks are never capped.

## When the user asks for status

Count lines in `tracks_local.jsonl` for tracks found; count distinct `artist`
values for artists done; compare to `wc -l artists.txt` (20,862 total).

## The GitHub bridge (connecting back to Kimi)

This folder is meant to become a private GitHub repo named `cancon-harvest` —
the mailbox between this machine and the Kimi sandbox (Kimi can read from
GitHub but cannot reach this Mac).

- **First time**: run `bash setup-github.sh` (needs `gh auth login` once).
  It inits git, creates the private repo, pushes the kit.
- **After every batch**: run `bash push-results.sh`. It commits only
  `tracks_local.jsonl` (plus `harvest_done.jsonl`, the resume state) with a
  count+timestamp and pushes. Nothing new = no-op.
- When the user says "push the results", run push-results.sh without asking.
  When they say "sync", remind them to tell Kimi:
  `sync the harvest from github:OWNER/cancon-harvest`

## Streaming links (`harvest_links.py`)

Separate from the track harvest; never touches `tracks_local.jsonl`.

- `python3 harvest_links.py wikidata` — one SPARQL query, ~1 min. Exact
  name match (EN/FR label); names shared by 2+ Wikidata entries skipped.
  Run once (re-running appends duplicates).
- `python3 harvest_links.py musicbrainz` — resumable, 1 request/second
  (MusicBrainz rule, don't raise it), ~15–19 h for the full list. Exact name or
  alias, country CA, and only if exactly one such artist. Progress: `links.log`;
  resume state `links_done.jsonl` (status linked / no-links / none / ambiguous).
- Output `links_local.jsonl`: one line per artist per source —
  `{artist, source: wikidata|musicbrainz, id, spotify, apple_music, soundcloud,
  bandcamp, deezer, tidal, website}`; missing fields are absent. Prefer
  wikidata over musicbrainz when both have a field.
- song.link (Odesli) per-track links: API needs a key now (HTTP 401), and its
  public `song.link/y/<videoId>` pages only show YouTube links (checked
  2026-10-09) — not used. Links are artist-level only for now.
- `push-results.sh` pushes the links files too.

## Discogs pass (`harvest_discogs.py`)

For artists the YouTube harvest logged `source: none` only. Unauthenticated
Discogs API (25 requests/min — `GAP = 2.6`s, don't lower it). Accepts an
artist only on exact name (ignoring Discogs' " (2)" suffix), exactly one such
artist, AND at least one release marked Canada.

- Profile links (Bandcamp, SoundCloud, website…) -> `links_local.jsonl`,
  `source: discogs`.
- YouTube videos attached to their releases -> **`tracks_discogs.jsonl`**
  (same schema as `tracks_local.jsonl`, album/year from the release). These
  are community-added, often fan uploads, so they are deliberately NOT in
  `tracks_local.jsonl` — the site should offer them as an opt-in
  "archival / deep indie" source.
- Resume state `discogs_done.jsonl` (linked / none / ambiguous / not-canadian).
  New `none` artists are picked up on every re-run; `discogs.log` for progress.
- Bandcamp search can't be used: it serves scripts an anti-bot challenge.
  Don't try to get around it.

## Chart history (`harvest_charts.py`)

Source: Canadian Music Blog (musiccanada.wordpress.com/charts) — per year
1964–2019 every Canadian-artist single that peaked in the national Top 40,
plus year-end charts 1967–2025, CKOI Franco year-end Top 50, JUNO Single of
the Year nominees/winners. Each page's own legend is kept with every number.

- `python3 harvest_charts.py fetch` — ~150 pages, rebuilds `charts_local.jsonl`.
  Run rarely (the blog updates yearly).
- `python3 harvest_charts.py match` — links chart songs to harvested tracks
  (tracks_local + tracks_discogs) -> `charts_tracks.jsonl`. Exact artist name
  (also inside "A/B", "A feat. B") + exact title after stripping brackets,
  "Artist - " prefixes, " - 1977"/remaster suffixes, leading articles; double
  A-sides split on " / ". No fuzzy matching. `push-results.sh` re-runs it.
- Field meanings: `peak`/`year_end` = national Canadian chart named in `chart`
  (RPM ≤2000, Canadian Singles Chart 2001–06, Billboard Canadian Hot 100 2007+).
  `us_peak`/`us_year_end` = U.S. Billboard Hot 100 (only on 2019+ pages —
  never mix with Canadian). `vancouver_*` = regional 1979–86 lists.
  `ckoi_year_end` = Québec CKOI. `juno` = nominated|won.
- Pre-1964 pages (no national chart) and RPM scans are not parsed. The RPM
  magazine scans (worldradiohistory.com, 1,748 issues) have a text layer but
  multi-column OCR — a possible later project with layout-aware parsing.

## Concerts (`harvest_events.py`)

- **Keys live only in `.env`** (git-ignored; this repo is PUBLIC — never
  commit, print, or push a key):
  `TICKETMASTER_API_KEY=...` and, if ever approved, `BANDSINTOWN_APP_ID=...`
- `python3 harvest_events.py ticketmaster [months]` — every upcoming music
  event in Canada, province × month windows (auto-split past the 1,000-result
  paging cap), ~100–300 calls of the 5,000/day free quota; keeps events whose
  lineup has an artist on the list (exact name; dropped if Ticketmaster's
  MusicBrainz ID disagrees with ours). Rebuilds `events_local.jsonl`.
- `python3 harvest_events.py bandsintown` — per artist in rotation, 1 req/s.
  Bandsintown keys are NOT self-serve: approval via API@bandsintown.com.
- Run daily when keys exist; `push-results.sh` pushes `events_local.jsonl`.
- Site must link the provider's own ticket URL and credit the provider.

## Feature data (FEATURES.md)

- **Clean mode** — `explicit_local.jsonl` `{yt, explicit}` from YouTube Music's
  explicit badge (album tracks only; music videos have no flag = unknown).
  Written by `harvest_topic_local.py` for new artists (log lines carry
  `"explicit": true` and `channel_id`); `backfill_explicit.py` covers artists
  harvested earlier — run it only AFTER the main harvest (never two processes
  against YouTube). It only flags videoIds already in `tracks_local.jsonl`.
- **Family trees** — `relations_local.jsonl` `{artist, mbid, type, direction,
  other, other_mbid, begin, end, ended}`. Musical relationships only (member of
  band, collaboration, subgroup, is person, founder) — marriages/partners/family
  are deliberately excluded. Collected in the same MusicBrainz request as links;
  `python3 harvest_links.py relations` backfills earlier artists — only after
  the musicbrainz stage finishes (1 request/second total).
- **Map** (Road Trip, Near You) — `python3 harvest_geo.py [catalog.csv]` ->
  `geo_local.jsonl` `{artist, location, lat, lon, precision: town|province,
  place, province, geonameid, source}`. Offline from the GeoNames Canada dump
  in `geonames/` (git-ignored; CC BY 4.0 — credit GeoNames). Towns only inside
  the named province; no province -> only a dominant city (≥100k and 10× any
  namesake); vague regions left blank. Re-run after a new catalog export.
  Second pass: artists with no usable catalog location but a Wikidata ID get
  their place of formation (bands, P740) or birth (people, P19) — only if that
  place is in Canada — via the Wikidata entity API (SPARQL timed out).
  `source: "Wikidata (CC0)"`, `basis: "formed in" | "born in"`; province from
  the nearest GeoNames town. Re-run as `links_local.jsonl` grows.

## FEATURES Part 2 data

- `albums_local.jsonl` — covers + track order; written by
  `harvest_topic_local.py` (log `"album_meta": true`) and by
  `backfill_explicit.py` for older artists (only albums containing a track
  already harvested for that artist).
- `python3 harvest_wiki.py bios` — Wikipedia summaries EN/FR for artists with
  a Wikidata ID -> `bios_local.jsonl` (CC BY-SA: site must credit + link).
  Re-run occasionally as links grow.
- `python3 harvest_wiki.py awards` — Polaris (+ Heritage) and JUNO Album of
  the Year from Wikipedia tables -> `awards_local.jsonl`. Album = the italic
  part of each entry. `note` keeps things like "rescinded in 2025". Run yearly.
- `python3 harvest_derived.py` — `pregame_local.jsonl` + `lineage_local.jsonl`
  from events/tracks/geo/charts. No network; `push-results.sh` runs it.

## FEATURES Part 3 data + AI DJ

- **AI DJ** — `harvest_dj.py` -> `dj_facts_local.jsonl` (+ `dj/sample.json`);
  engine `dj/dj.js`, demo `dj/demo.html` (serve `dj/` over http). Wording
  varies, facts never: every clause comes from a sourced field; awards with a
  `note` (e.g. rescinded) are never spoken. Don't add an LLM to write lines.
- **New Releases Radar** — `harvest_radar.py` (Sundays, in run-daily.sh):
  artists in rotation with a channel id whose albums are already recorded;
  unseen releases -> tracks/albums/explicit files; releases from this year or
  last -> `new_releases_local.jsonl`.
- **Dead tracks** — `check_dead.py` (nightly, 8,000 oldest-checked via
  YouTube oEmbed) -> `dead_local.jsonl`; state `dead_state.json` (ignored).
- **Song versions** — `harvest_derived.py` -> `songs_local.jsonl` (version
  notes after " - " only when they ARE version notes; classical scenes stay
  separate). **Fresh** -> `fresh_local.jsonl` (first run = baseline).
- Radar and dead check both refuse to run while the main harvest runs.
- Verified-channel rule (harvest_topic_local.verified_match): a channel longer
  than the artist name is accepted only if the extra words are boilerplate
  (Official, Music, VEVO, Band, Videos, Channel…). "Alan" ≠ "Alan Walker".
  Earlier prefix matches that fail this rule were removed (log `note`).

## Schedule (background loop on this Mac)

launchd can't be used while the repo lives in `~/Downloads`: macOS privacy
protection blocks background services from reading Downloads ("Operation not
permitted", exit 126). Instead a `nohup caffeinate -i bash -c '…'` loop runs:
- every hour: `push-results.sh` (log `push.log`)
- once in the 06:00 hour: `run-daily.sh` — concerts if `TICKETMASTER_API_KEY`
  is in `.env`, then push (log `daily.log`)
It stops on reboot (like the harvesters). Check: `pgrep -fl run-daily.sh`.
Stop: `pkill -f "run-daily.sh >> daily.log"`. To make it reboot-proof, move the
repo out of Downloads (e.g. `~/cancon-harvest`) and use launchd there.

Waiter loops (also nohup) start the backfills when their harvest ends:
`backfill_explicit.py` after the track harvest, `harvest_links.py relations`
after the MusicBrainz stage; a Discogs loop re-runs every 15 min until the
track harvest ends. Patterns use `[h]arvest…` so `pgrep -f` never matches the
waiter's own command line.

## Adding artists

`artists.txt` is read once at start. To add artists from a new site export
(`canadian_music_discovery_catalog-N.csv`, `artist` column): append names not
already in the list (case-insensitive, skip 1-letter names), then restart the
harvest — finished artists are skipped.

## Done means

`tracks_local.jsonl` reaches the CanCon Radio session (Kimi) — via the GitHub
bridge or manual upload. The merge pipeline there verifies every video ID,
tags language/region/genre, rebuilds the player, and credits each artist
profile. Never edit the file format; the merger depends on the schema.
