# CanCon Topic Harvest

This folder is a self-contained job: harvest YouTube "… - Topic" channel
uploads for 17,030 Canadian artists listed in `artists.txt`.

## What's here

- `harvest_topic_local.py` — the harvester (requires `yt-dlp`: `pip3 install yt-dlp`)
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

- The script is **resumable**: artists already present in `tracks_local.jsonl`
  or `harvest_done.jsonl` are skipped — including ones that found nothing.
  Re-running the same command continues where it stopped. Failed searches
  aren't logged, so they're retried.
- `harvest_done.jsonl` records one line per artist searched:
  `{artist, source: topic|verified|none, channel, kept}`.
- Each line of output is one video: `{yt, title, artist, album, year, …}`.
- An artist's own `… - Topic` channel is preferred. If there is none, the
  script falls back to their **verified** artist channel (verified badge AND
  channel name equals the artist, or starts with "<artist> ", or is
  "<artist>VEVO"; only the single best-matching channel is kept). Never fan
  uploads or unverified same-name lookalikes.
- Be polite: the built-in 1s spacing between artists stays. Don't parallelise
  against YouTube; if requests start failing, stop and wait before resuming.
- `10` (max videos per artist) can be raised to 25 for deeper catalogs.

## When the user asks for status

Count lines in `tracks_local.jsonl` for tracks found; count distinct `artist`
values for artists done; compare to `wc -l artists.txt` (17,030 total).

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

## Done means

`tracks_local.jsonl` reaches the CanCon Radio session (Kimi) — via the GitHub
bridge or manual upload. The merge pipeline there verifies every video ID,
tags language/region/genre, rebuilds the player, and credits each artist
profile. Never edit the file format; the merger depends on the schema.
