#!/usr/bin/env bash
# Supervisor (launchd com.cancon.jobs: at login + every 15 min).
# Starts any long-running job that should be running but isn't. Every job is
# resumable, so restarting after a reboot just continues where it stopped.
# Patterns use [x]yz so pgrep never matches this script's own command line.
set -uo pipefail
cd "$(dirname "$0")"

running() { pgrep -f "$1" >/dev/null; }
start()   { nohup caffeinate -i bash -c "$1" >> "$2" 2>&1 & echo "$(date '+%F %T') started: $1"; }   # start "<command>" <log>

# 1. Main YouTube harvest (exits quickly once every artist is done)
if ! running "[h]arvest_topic_local.py artists.txt" && ! running "[b]ackfill_explicit.py" && ! running "[h]arvest_radar.py" && ! running "[c]heck_dead.py"; then
  if [ ! -f .harvest_complete ]; then
    start "python3 -u harvest_topic_local.py artists.txt 10 && touch .harvest_complete" harvest.log
  elif [ ! -f .backfill_complete ]; then
    # 2. after the harvest: album/explicit backfill (never alongside the harvest)
    start "python3 -u backfill_explicit.py && touch .backfill_complete" explicit.log
  fi
fi

# 3. MusicBrainz links (1 req/s), then relations backfill
if ! running "[h]arvest_links.py"; then
  if [ ! -f .links_complete ]; then
    start "python3 -u harvest_links.py musicbrainz && touch .links_complete" links.log
  elif [ ! -f .relations_complete ]; then
    start "python3 -u harvest_links.py relations && touch .relations_complete" relations.log
  fi
fi

# 4. Discogs pass for unmatched artists (re-runs pick up newly unmatched ones)
if ! running "[h]arvest_discogs.py" && [ ! -f .discogs_complete ]; then
  if [ -f .harvest_complete ]; then
    start "python3 -u harvest_discogs.py && touch .discogs_complete" discogs.log
  else
    start "python3 -u harvest_discogs.py" discogs.log
  fi
fi
exit 0
