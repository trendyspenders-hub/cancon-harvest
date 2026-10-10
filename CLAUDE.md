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
