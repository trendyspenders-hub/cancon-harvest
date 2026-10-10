#!/usr/bin/env bash
# Daily job (scheduled by launchd): refresh concerts if a Ticketmaster key is set,
# then push everything. Safe to run by hand.
set -uo pipefail
cd "$(dirname "$0")"
if grep -qs '^TICKETMASTER_API_KEY=.\+' .env; then
  python3 harvest_events.py ticketmaster 6 || echo "concert refresh failed"
else
  echo "no TICKETMASTER_API_KEY in .env — skipping concerts"
fi
bash push-results.sh
