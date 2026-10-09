#!/usr/bin/env bash
# After every batch: commit the results with a count + timestamp and push.
# Nothing new = no-op.
set -euo pipefail
cd "$(dirname "$0")"

[ -f tracks_local.jsonl ] || { echo "No tracks_local.jsonl yet — run a batch first."; exit 0; }
git add tracks_local.jsonl
[ -f harvest_done.jsonl ] && git add harvest_done.jsonl   # resume state

if git diff --cached --quiet; then
  echo "Nothing new to push."
  exit 0
fi

TRACKS=$(wc -l < tracks_local.jsonl | tr -d ' ')
ARTISTS=$(python3 -c "import json;print(len({json.loads(l)['artist'] for l in open('tracks_local.jsonl') if l.strip()}))")
git commit -q -m "Results: $TRACKS tracks, $ARTISTS artists — $(date '+%Y-%m-%d %H:%M')"
git push -q
echo "Pushed: $TRACKS tracks from $ARTISTS artists."
