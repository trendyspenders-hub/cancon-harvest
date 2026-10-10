#!/usr/bin/env bash
# Daily job: concerts (if a Ticketmaster key is set), dead-track check, and on
# Sundays the New Releases Radar — then push everything. Safe to run by hand.
# The dead check and radar skip themselves while the main harvest is running.
set -uo pipefail
cd "$(dirname "$0")"
if grep -qs '^TICKETMASTER_API_KEY=.\+' .env; then
  python3 harvest_events.py ticketmaster 6 || echo "concert refresh failed"
else
  echo "no TICKETMASTER_API_KEY in .env — skipping concerts"
fi
python3 check_dead.py 8000 || echo "dead check failed"
if [ "$(date +%u)" = "7" ]; then
  python3 harvest_radar.py || echo "radar failed"
fi
bash push-results.sh
