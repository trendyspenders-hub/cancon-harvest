# CanCon Radio — Signature Features Brief

**For:** the CanCon Radio build session (Kimi)
**Companion to:** `BRIEF.md` (do BRIEF Phases 0–2 first — URLs, On Air hero,
performance — these features assume them).
**Data:** everything below is in `github:trendyspenders-hub/cancon-harvest`.

Same ground rules as BRIEF.md: keep the identity, **sourced, never guessed**,
never break playback, accessible (keyboard, focus, 44px targets, reduced
motion), bilingual EN/FR for every new string, and never cover or shrink the
YouTube player below 200×200.

Each feature: *What*, *Data*, *Rules*, *Done when*. Effort: S / M / L.
Recommended order: **F4 AI DJ → F1 Higher or Lower → F5 Road Trip**, then the
rest in any order.

## Data files you'll use

| File | What's in it |
|---|---|
| `tracks_local.jsonl` | Main rotation: `yt, title, artist, album, year` |
| `tracks_discogs.jsonl` | Opt-in archival videos (BRIEF 3.7) |
| `charts_tracks.jsonl` | `peak, year_end, chart, ckoi_year_end, juno, us_*` per track (BRIEF 3.8) |
| `links_local.jsonl` | Spotify / Apple / Bandcamp / SoundCloud / website; MusicBrainz `id` |
| `events_local.jsonl` | Upcoming concerts (F9), rebuilt daily (Ticketmaster) |
| `explicit_local.jsonl` | `{yt, explicit}` — Clean mode (F11). Missing = unknown |
| `relations_local.jsonl` | Band memberships / collaborations (F7), MusicBrainz |
| `geo_local.jsonl` | `{artist, lat, lon, precision: town\|province, place, province}` — Road Trip (F5), Near You (F8). Credit "GeoNames" |
| Directory (site) | artist `location`, region, era, genres, act type, sources |

All files refresh on GitHub hourly (harvest machine schedule).

---

## Games & shareable moments

### F1 — Higher or Lower: CanCon Edition (S)
- **What:** two Canadian hits side by side (title, artist, year, art); guess
  which peaked higher on the national chart. Wrong answer ends the run. A fixed
  **daily** set of 10 (same for everyone, seeded by date) plus endless mode.
  Share card: `CanCon Higher/Lower #142 🍁🍁🍁🍁⬛🍁🍁🍁🍁🍁 9/10`.
  Tap any card to play the track.
- **Data:** `charts_tracks.jsonl` — only pairs where both have `peak` on the
  **same chart family** (RPM vs RPM, Hot 100 vs Hot 100); never compare a
  `us_peak` or `vancouver_*`. Ties are skipped.
- **Done when:** a daily game is identical across browsers, every answer
  links to its chart source, and the share text copies correctly.

### F2 — Guess the Year (S)
- **What:** a track plays (title and artist **visible** — nothing hidden); drag
  the time-machine dial to guess the release year. Score = 100 − 10 × years off
  (min 0). Five rounds daily; share card.
- **Data:** `tracks_local.jsonl` `year` (album-sourced). Use only tracks whose
  `year` is set; prefer charted tracks for recognisability.
- **Rules:** the YouTube player stays visible and unobstructed.
- **Done when:** the answer screen shows the album and year with its source.

### F3 — Listening Passport + CanCon Wrapped (S)
- **What:** a passport page with 13 province/territory stamps; a stamp is
  earned after 2+ minutes of a track by an artist from that region. Badges:
  "Coast to Coast" (all 13), "True North" (YT + NT + NU), "Deep Digger" (50
  artists with ≤ 2 tracks). In December: **"Your CanCon Wrapped"** — top
  artists, provinces, decades, minutes — as a shareable image.
- **Data:** directory region per artist. Stored in `localStorage` (synced only
  if the user signs in — BRIEF 7.4). No tracking server needed.
- **Done when:** stamps persist across visits and the Wrapped image downloads.

---

## Make it feel like real radio

### F4 — AI DJ between songs (M) ★
- **What:** an optional DJ voice (toggle, off by default for embeds) that
  speaks 5–12 seconds between some tracks:
  *"That was Joni Mitchell, from Fort Macleod, Alberta — off Blue, 1971.
  Coming up: Karkwa."* French when the interface is French. Plus short station
  IDs ("CanCon Radio — coast to coast") every ~4 songs.
- **Data:** only fields present for that track/artist: `artist, title, album,
  year, location, chart peak, JUNO`. **Template-based** — e.g.
  `"That was {artist}{, from {location}}{ — off {album}, {year}}."` — missing
  fields drop out of the sentence. **Never** let a language model write facts.
  Optional lines only when the data exists: "a number one on RPM in 1972",
  "a JUNO winner".
- **Voice:** any TTS (browser `speechSynthesis` as free fallback; a neural
  TTS for quality). Duck the music, don't overlap vocals: speak during the gap
  after a track ends, before the next starts.
- **Done when:** with DJ on, every intro is factually traceable to the data,
  nothing is said for missing fields, and EN/FR both work.

### F5 — Road Trip Mode (M) ★
- **What:** enter a start and end (e.g. Halifax → Vancouver) and a drive time.
  The station plays artists from places along the route, in order, paced to the
  trip. A route map shows "now passing: Drummondville — playing Les Cowboys
  Fringants". Presets: "The Cabot Trail", "Highway 1 coast to coast",
  "Sea to Sky".
- **Data:** directory artist `location` → coordinates (geocode once and cache;
  city-level only). Route: any routing/geometry service or a straight-line
  corridor fallback (±75 km of the line).
- **Rules:** never guess a location — artists without one are skipped.
- **Done when:** a Halifax → Vancouver trip plays Maritime artists first and BC
  artists last.

### F6 — Wake up to CanCon (S)
- **What:** an alarm: pick a time and a preset; gentle volume ramp over 60s.
  Companion to the existing sleep timer.
- **Rules:** browsers block autoplay — the tab must stay open and the user must
  have interacted once; say so plainly in the UI. Works best as an installed
  PWA (BRIEF 8.1).
- **Done when:** an alarm set 2 minutes ahead plays reliably with the tab open.

---

## Discovery

### F7 — Band family trees (M)
- **What:** on artist pages, a "Family tree": member-of, side projects,
  collaborations — an interactive graph (and an accessible list). "Play the
  family" starts a station of everyone connected.
- **Data:** MusicBrainz artist-artist relationships (`member of band`,
  `collaboration`, `is person`) for artists with a MusicBrainz `id` in
  `links_local.jsonl`. The harvest can add a `relations_local.jsonl` on
  request; until then, fetch on demand (1 req/s, cache results).
- **Done when:** Neil Young's tree shows Buffalo Springfield and Crosby, Stills,
  Nash & Young, each tappable.

### F8 — Near You (S)
- **What:** "Play artists from near me": opt-in browser location, rounded to
  ~10 km, used once in the browser and never stored or sent. Radius slider
  25–200 km. Falls back to "choose your city".
- **Data:** geocoded directory locations (shared with F5).
- **Done when:** in Moncton it plays New Brunswick artists; denying location
  shows the city picker.

### F9 — Playing live near you (M)
- **What:** an "On tour" block on artist pages (next 5 shows), a "Live this
  week" strip on the home page filtered by the listener's province (or F8
  radius), and a 🎫 badge on tracks by artists with an upcoming local show.
- **Data:** `events_local.jsonl`, rebuilt daily on the harvest machine:
  `{artist, provider, event_id, date, time, venue, city, region, country,
  lat, lon, url, lineup, match}`. Providers: **Ticketmaster Discovery API**
  (free key) now; **Bandsintown** if/when approved. No API keys ever reach
  the site.
- **Rules:** always link the provider's own event `url` for tickets and show
  "via Ticketmaster" / "via Bandsintown". Hide past events. Prefer
  `match: mbid` over `match: name`; for `name` matches on one-word names, show
  the venue lineup so listeners can tell.
- **Done when:** an artist with shows lists them with working ticket links, and
  nothing past-dated is ever shown.

### F10 — Year pages (S)
- **What:** `/year/1985` (and `/fr/annee/1985`): that year's Canadian #1s, top
  10 hits, CKOI Franco hits, JUNO singles, albums released, and a one-hour
  "1985" station. Prev/next year navigation.
- **Data:** `charts_tracks.jsonl` + `tracks_local.jsonl` `year`.
- **Rules:** server-rendered/pre-rendered (BRIEF 5.1) — these are search pages.
- **Done when:** every year 1964 → today has a page; empty sections are hidden.

---

## Practical

### F11 — Clean mode (S)
- **What:** a "Clean" toggle (remembered; on by default in a `?school=1` or
  embed variant) that removes explicit tracks from rotation.
- **Data:** an explicit flag per track from YouTube Music album data — the
  harvest can provide `explicit_local.jsonl` (`{yt, explicit: true}`) on
  request. Until then, unknown = allowed, and say "Clean mode filters tracks
  marked explicit by YouTube Music".
- **Done when:** with Clean on, no `explicit: true` track ever plays.

### F12 — Listening parties (L)
- **What:** "Start a kitchen party": a room link; everyone hears the same track
  at the same position (host controls or "everyone can skip"), with a simple
  chat and emoji reactions. Max ~50 per room.
- **Tech:** a small realtime service (WebSocket) broadcasting
  `{videoId, startedAt}`; clients `seekTo` to stay within ~1s. No accounts
  needed; rooms expire after 24h idle.
- **Rules:** moderate chat (rate limits, report button, profanity filter).
- **Done when:** two phones in one room stay in sync across 5 track changes.

### F13 — Open data + "How we know" (S)
- **What:** a `/data` page: coverage (artists, tracks, % with region/year/
  links), source breakdown (YouTube Topic / verified / YouTube Music / Discogs /
  MusicBrainz / Wikidata), a coverage map, and downloads of the **directory
  facts** (artist, location, era, genres, sources) under an open licence.
- **Rules:** don't redistribute third-party content you don't own (no audio,
  no copied text). Link every source.
- **Done when:** the page's numbers match the live site exactly (BRIEF 0.8).

### F14 — "What is CanCon?" (S)
- **What:** a short, illustrated explainer (EN/FR): the CRTC Canadian-content
  rules for radio (introduced 1971), the **MAPL** system (Music, Artist,
  Performance, Lyrics) — the station's namesake — and why it shaped Canadian
  music. Link out to the CRTC for the official rules.
- **Rules:** facts from cited sources only; no claim that tracks here are
  MAPL-certified (we only know the *artist* is Canadian).
- **Done when:** the page cites its sources and links from the footer and the
  "How this station works" box.

---

## Final checklist (per feature)
- [ ] EN + FR strings
- [ ] Keyboard + screen reader pass; reduced-motion respected
- [ ] Works at 390px and 1440px, light and night modes
- [ ] Playback never interrupted by the feature
- [ ] Every fact shown traces to a data field + source
