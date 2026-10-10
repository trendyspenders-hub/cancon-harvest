#!/usr/bin/env bash
# After every batch: commit the results with a count + timestamp and push.
# Nothing new = no-op.
set -euo pipefail
cd "$(dirname "$0")"

[ -f tracks_local.jsonl ] || { echo "No tracks_local.jsonl yet — run a batch first."; exit 0; }
git add tracks_local.jsonl
[ -f harvest_done.jsonl ] && git add harvest_done.jsonl   # resume state
for f in links_local.jsonl links_done.jsonl; do [ -f "$f" ] && git add "$f"; done   # streaming links
for f in tracks_discogs.jsonl discogs_done.jsonl; do [ -f "$f" ] && git add "$f"; done   # Discogs pass
[ -f events_local.jsonl ] && git add events_local.jsonl   # upcoming concerts (no keys inside)
for f in explicit_local.jsonl relations_local.jsonl geo_local.jsonl; do [ -f "$f" ] && git add "$f"; done   # clean mode, family trees, map
python3 harvest_derived.py >/dev/null 2>&1 || true   # pre-game, lineage, song versions, fresh this week
python3 harvest_dj.py >/dev/null 2>&1 || true         # AI DJ fact sheet + demo sample
for f in albums_local.jsonl bios_local.jsonl awards_local.jsonl pregame_local.jsonl lineage_local.jsonl; do [ -f "$f" ] && git add "$f"; done   # FEATURES Part 2
for f in dj_facts_local.jsonl dj/sample.json songs_local.jsonl fresh_local.jsonl dead_local.jsonl new_releases_local.jsonl; do [ -f "$f" ] && git add "$f"; done   # FEATURES Part 3
[ -f charts_local.jsonl ] && python3 harvest_charts.py match >/dev/null   # re-link charts to new tracks
for f in charts_local.jsonl charts_tracks.jsonl; do [ -f "$f" ] && git add "$f"; done   # chart history

if git diff --cached --quiet; then
  echo "Nothing new to push."
  exit 0
fi

TRACKS=$(wc -l < tracks_local.jsonl | tr -d ' ')
LINKED=$( [ -f links_local.jsonl ] && python3 -c "import json;print(len({json.loads(l)['artist'] for l in open('links_local.jsonl') if l.strip()}))" || echo 0)
ARTISTS=$(python3 -c "import json;print(len({json.loads(l)['artist'] for l in open('tracks_local.jsonl') if l.strip()}))")
git commit -q -m "Results: $TRACKS tracks, $ARTISTS artists, $LINKED with streaming links — $(date '+%Y-%m-%d %H:%M')"
git push -q
echo "Pushed: $TRACKS tracks from $ARTISTS artists; $LINKED artists with streaming links."
