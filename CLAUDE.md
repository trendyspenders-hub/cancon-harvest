# CanCon Topic Harvest

This folder is a self-contained job: harvest YouTube "… - Topic" channel
uploads for 20,862 Canadian artists listed in `artists.txt`.

## What's here

- `harvest_topic_local.py` — the harvester (requires `pip3 install yt-dlp ytmusicapi`)
- `artists.txt` — one artist per line, priority-sorted (francophone/Spanish first,
  then acts with no tracks in the player, then the rest)
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
