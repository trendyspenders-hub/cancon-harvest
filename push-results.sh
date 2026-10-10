#!/usr/bin/env bash
# After every batch: commit the results with a count + timestamp and push.
# Nothing new = no-op.
set -euo pipefail
cd "$(dirname "$0")"

[ -f tracks_local.jsonl ] || { echo "No tracks_local.jsonl yet — run a batch first."; exit 0; }
git add tracks_local.jsonl
[ -f harvest_done.jsonl ] && git add harvest_done.jsonl   # resume state
for f in links_local.jsonl links_done.jsonl; do [ -f "$f" ] && git add "$f"; done   # streaming links

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
