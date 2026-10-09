# Topic-Channel Harvest — run this on your machine

YouTube is unreachable from the CanCon build environment, so this piece runs
anywhere with normal internet access (laptop, VPS, GitHub Actions runner).

## Files

- `harvest_topic_local.py` — finds each artist's official auto-generated
  YouTube **Topic** channel ("<Name> - Topic") and lists its uploads
- `artists.txt` — 17,030 artist names from the live directory, pre-sorted:
  francophone/Spanish artists first, then every act with no tracks in the
  player, then the rest

## Run

```bash
pip install yt-dlp
python3 harvest_topic_local.py artists.txt 10   # 10 = max videos kept per artist
```

- Output goes to `tracks_local.jsonl` in the same folder, one JSON line per video.
- **Resumable** — artists already in `tracks_local.jsonl` are skipped, so you can
  Ctrl-C and restart freely, or split `artists.txt` into chunks.
- Only the artist's own Topic channel is kept (fan uploads and lookalikes are
  filtered out).
- Full list ≈ 17k artists — expect several hours. Tip: `head -2000 artists.txt > batch1.txt`
  and run batch by batch.

## Option C — Relay server (`relay/` folder, for any VPS / Render / Fly)

A tiny always-on service that harvests on your host and lets the CanCon
sandbox pull results directly — closest thing to running it in-session.

```bash
cd relay
docker build -t topic-relay . && docker run -d -p 8080:8080 -e RELAY_TOKEN=pick-a-secret topic-relay
curl -X POST http://your-host:8080/start        # begins the full 17k-artist walk
curl http://your-host:8080/status               # progress
```

Then tell me the URL (and token) in any session — I run `sync_remote.sh`,
which downloads the results, verifies every video, rebuilds the player and
restarts. Works the same for the GitHub Actions repo:
`sync_remote.sh github:OWNER/REPO`.

## Option B — GitHub Actions (fully automatic, nothing to install)

1. Create any repo on GitHub, upload three files to its root:
   `harvest_topic_local.py`, `artists.txt`, and `github-actions-workflow.yml`
   **renamed to** `.github/workflows/harvest.yml`
2. Actions tab → "Topic harvest" → Run workflow (it also runs nightly by itself).
3. Each run scrapes for up to ~5.5h, commits progress to `tracks_local.jsonl`,
   and the next run resumes where it stopped.
4. Tell me the repo name in any session — GitHub's API is reachable from my
   side, so I can pull the file and merge it myself. No manual uploads needed.

## Send it back

Upload `tracks_local.jsonl` in any session. The merge pipeline will verify every
video ID, tag region/genre/language, rebuild the player, and add credits to each
artist's profile. Nothing unverified enters rotation.
