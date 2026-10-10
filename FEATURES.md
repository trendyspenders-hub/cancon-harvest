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

# Part 2 — Make it a destination (F15–F28)

Recommended order: **F15 covers → F21 Pre-game → F22 Battle of the
Provinces**, then the rest.

| New file | What's in it |
|---|---|
| `albums_local.jsonl` | One line per album: `{artist, album, type, year, browse_id, playlist_id, cover, tracks: [{n, yt, title}]}` — official YouTube Music cover (544px) + track order |
| `bios_local.jsonl` | `{artist, qid, lang: en\|fr, title, extract, url, license}` — Wikipedia summaries, **CC BY-SA 4.0: credit Wikipedia + link `url`** |
| `awards_local.jsonl` | `{award, year, result: winner\|shortlist\|nominee, artist, album, on_list, note, source_url}` — Polaris 2006–, Polaris Heritage, JUNO Album of the Year 1975– |
| `pregame_local.jsonl` | Per upcoming show: lineup artists in rotation + up to 30 track IDs |
| `lineage_local.jsonl` | Per town (3+ artists): artists ordered by first year, each with best chart hit |

## Look & feel

### F15 — Real album covers + crate-digging view (M) ★
- **What:** use `albums_local.jsonl` `cover` everywhere a track or album
  appears (player, Discover, artist pages, share cards); fall back to the
  YouTube thumbnail. New **Crate** view: a horizontally flippable bin of album
  covers (drag / arrow keys), filterable by the existing dials; tap = play.
- **Rules:** lazy-load covers, `width`/`height` set (no layout shift), `alt` =
  "Album cover: {album} by {artist}".
- **Done when:** every track from a harvested album shows its real cover.

### F16 — Full-album mode (S)
- **What:** "▶ Play the album" on album cards and artist pages — plays
  `tracks` in `n` order, then returns to the station. Show the tracklist with
  the current song highlighted.
- **Data:** `albums_local.jsonl` (`tracks` already ordered; skip track IDs that
  fail verification).
- **Done when:** *Blue* (if present) plays track 1 → last in order.

### F17 — Café / TV mode (S)
- **What:** `/tv` — full-screen Now Playing: big cover, title/artist in display
  type, a QR code to the track's page, "CanCon Radio" bug, next-up strip.
  Auto-hides controls; cast-friendly; stays awake (Wake Lock API).
- **Rules:** the YouTube player stays visible ≥ 200×200 (e.g. as the "cover"
  panel while playing).
- **Done when:** it runs for an hour on a TV without interaction.

## Stories & depth

### F18 — Story behind the artist (S)
- **What:** on artist pages, the Wikipedia summary in the interface language
  (fall back to the other), with **"From Wikipedia — CC BY-SA"** and a "Read
  more" link to `url`. Optional DJ line (F4) may quote ≤ 1 sentence.
- **Rules:** show the text as-is; never paraphrase into new claims.
- **Done when:** artists with a bio show it with attribution; others show nothing.

### F19 — Polaris & JUNO stations and badges (S)
- **What:** presets "Polaris Shortlists", "Polaris Winners", "Heritage
  Classics", "JUNO Album of the Year"; badges on albums/artists:
  `POLARIS 2012 SHORTLIST`, `JUNO ALBUM OF THE YEAR 1999`. Match album titles to
  `albums_local.jsonl` (exact, case/accents ignored) to play the actual album.
- **Rules:** show `note` when present (e.g. "rescinded in 2025") next to the
  badge — never hide it.
- **Done when:** "Polaris Shortlists" plays tracks from shortlisted albums only.

### F20 — Hometown lineage (S)
- **What:** on town pages and artist pages: "From Winnipeg: The Guess Who →
  … → Boy Golden", a timeline ordered by `since`, each with its top hit;
  "Play the lineage" station (oldest → newest).
- **Data:** `lineage_local.jsonl` (towns with 3+ artists in rotation).
- **Done when:** a town page shows its timeline and plays it in order.

## Live & community

### F21 — Pre-game the show (S) ★
- **What:** on each upcoming show (F9): "Pre-game: tracks from tonight's
  lineup" one-tap station + ticket link. Home strip: "Tonight in {city}".
- **Data:** `pregame_local.jsonl` (`tracks` = shuffled lineup tracks).
- **Rules:** ticket link = provider `url`, credited.
- **Done when:** a show with 2 lineup artists in rotation plays both.

### F22 — Battle of the Provinces (M) ★
- **What:** a seasonal bracket: each province/territory's best song (seeded by
  chart peaks + listener plays), head-to-head rounds over 4 weeks; each round
  is its own station; results page + share cards.
- **Tech:** votes need a backend (one vote per device per matchup, rate
  limits, basic bot protection). Show vote counts only after voting.
- **Done when:** a full bracket runs end to end with a winner page.

### F23 — Request line (M)
- **What:** listeners request a track (search the catalogue), with optional
  first name + city; popular requests get weighted into rotation within the
  hour; "Requested by Sam in Moncton" on the player and in the DJ intro (F4).
- **Rules:** moderation for names (profanity filter, length limit); requests
  only for tracks already in the catalogue.
- **Done when:** a request appears in rotation and is credited on air.

## Discovery tricks

### F24 — "Describe a vibe" (M)
- **What:** a search box: "rainy Sunday in Halifax", "cottage dock, 90s" →
  sets the dials (era, mood, region, genre, language, chart) and starts.
- **Rules:** an AI model may only output a **dial setting** from the existing
  options (strict JSON schema); it never writes facts, titles, or track IDs.
  Show the chosen dials so listeners can tweak them.
- **Done when:** 10 test prompts produce sensible, valid dial settings.

### F25 — Canadiana presets (S)
- **What:** curated stations with personality: *Snow Day*, *Cottage Dock*,
  *Long Weekend*, *Drive-Thru Double-Double*, *Hockey Night*, *Kitchen Party
  Last Call*.
- **Rules:** curated by the owner (a list of track IDs per preset, editable in
  an admin file) — label them "Curated".
- **Done when:** each preset has ≥ 40 tracks and plays.

### F26 — Support the artist (S)
- **What:** a visible "Support {artist}" button in the player and on artist
  pages → Bandcamp (preferred), else official site / store, from
  `links_local.jsonl`. A "Bandcamp Friday" banner on those days.
- **Done when:** artists with a Bandcamp link show the button.

## Growth

### F27 — Song of the Day (S)
- **What:** a daily pick (deep cut or anniversary) with a generated share
  card (cover, title/artist, one sourced fact: chart peak, award, or
  hometown) sized for Instagram story (1080×1920), square, and X; page
  `/today` with prev/next; RSS feed. Auto-posting to social accounts is
  optional and needs the owner's accounts/keys.
- **Done when:** `/today` updates daily and the card downloads.

### F28 — Easter eggs (S)
- **What:** hidden stations: type **"much"** on the dial → *MuchMusic
  Countdown* (90s charted hits), **"degrassi"** → teen-drama-era tracks,
  ↑↑↓↓←→←→BA → *Golden Era*. Subtle toast: "You found a secret station."
- **Done when:** each trigger works on desktop and mobile (via the search box).

---

## Final checklist (per feature)
- [ ] EN + FR strings
- [ ] Keyboard + screen reader pass; reduced-motion respected
- [ ] Works at 390px and 1440px, light and night modes
- [ ] Playback never interrupted by the feature
- [ ] Every fact shown traces to a data field + source
