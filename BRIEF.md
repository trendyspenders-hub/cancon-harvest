# CanCon Radio — Improvement Brief

**For:** the CanCon Radio build session (Kimi)
**Site:** https://7xlil6gv532hu.kimi.pro/
**Based on:** a live audit on 2026-10-09 (desktop 1440px + mobile 390px, real browser, playback tested)

Work through the phases **in order**. Each item has *What*, *Why*, and *Done when*.
Finish and verify a phase before starting the next. Report back after each phase
with what changed and anything you couldn't do.

---

## Ground rules (apply to everything)

- **Keep the identity.** The cream paper, red ink, black rules, broadcast
  vocabulary ("Band selector — Era", "Signal — Region", "Dead signals are
  skipped") are the brand. Refine it; don't replace it.
- **Keep the data ethos.** "Sourced, never guessed" stays true everywhere. No
  invented bios, years, regions or genres. Unknown = blank, not guessed.
- **Don't break playback.** After every change: press Play, skip, change a
  preset, change a dial — music must keep playing.
- **Accessibility is not optional:** every interactive element is keyboard
  reachable, has a visible focus state, an accessible name (`aria-label`, not
  only `title`), and a mobile tap target ≥ 44×44px.
- **Respect `prefers-reduced-motion`** for every animation added below.
- **Never put your own ads on, over, or around a YouTube embed.**

---

## Phase 0 — Critical fixes (do first)

### 0.1 Real URLs for every view
- **What:** Radio, Discover, Directory and each artist profile get their own
  path: `/`, `/discover`, `/directory`, `/artist/<slug>`. Use the History API
  (pushState / proper router). Station dial state also lives in the URL
  (e.g. `/?preset=northern-bars&era=1990s&region=quebec`) — the existing
  "Share dial" link should just be the current URL.
- **Why:** every view is currently `/`. Pressing the browser **Back** button
  after visiting Discover leaves the site entirely (to a blank page) and kills
  the music. Pages can't be bookmarked, shared, or indexed by Google.
- **Done when:** Back/Forward move between views without leaving the site;
  reloading `/directory` opens the Directory; pasting a dial URL into a new tab
  reproduces the station. The server/host must serve the app for all these
  paths (no 404 on refresh).

### 0.2 Scroll to top on navigation
- **What:** reset scroll to top when changing views (restore previous position
  on Back, like a normal site).
- **Why:** scrolling 1,200px on Radio then clicking Discover lands 1,200px down
  Discover.
- **Done when:** every new view opens at the top.

### 0.3 Playback survives navigation
- **What:** the player must live outside the routed views so changing pages
  never interrupts audio.
- **Done when:** play a track, visit Discover → Directory → an artist → Back —
  the track never stops.

### 0.4 Visible keyboard focus
- **What:** add a global `:focus-visible` style — 2px solid brand red outline,
  2px offset — for buttons, links, chips, cards, inputs, selects. Don't remove
  outlines anywhere.
- **Why:** tabbing through the nav and preset cards currently shows no focus
  indicator (`outline: 0`).
- **Done when:** tabbing from the top of the page shows clearly where focus is
  at every step, in both light and night modes.

### 0.5 Mobile tap targets
- **What:** genre / region / language / era chips and all player buttons
  ≥ 44px tall on touch screens (padding, not font size).
- **Why:** chips measure 31px tall on a 390px phone.
- **Done when:** no tappable element under 44×44px at 390px width.

### 0.6 Directory starts with real artists
- **What:** default sort A→Z starting at **A**; names starting with symbols or
  digits go under the **#** tab, listed last. Hide `Unresolved` entries by
  default (keep a filter to show them).
- **Why:** the Directory currently opens on "_ASH", "-403-", ".", "??JINX??".
- **Done when:** the first cards on `/directory` are real "A" artists.

### 0.7 YouTube player size compliance
- **What:** the visible YouTube player must be **at least 200×200 px** (YouTube
  API Terms requirement) and must not be hidden, covered, or shrunk below that.
  The footer player is currently ~160×90. Phase 1.1's "On Air" panel is the
  natural home for a compliant player; the footer bar can keep the controls.
- **Why:** under-sized or hidden embeds risk losing embed access entirely.
- **Done when:** while playing, a ≥200×200 YouTube player is visible on desktop
  and mobile, and nothing overlaps it.

### 0.8 Consistent numbers
- **What:** compute every count from one source. Header says 20,864 artists;
  Directory says 20,865. Track counts must update after each harvest sync.
- **Done when:** header, hero copy, Discover and Directory always agree.

### 0.9 Accessible names on icon buttons
- **What:** player icon buttons (favourite, surprise, reshuffle, prev, play,
  next, mute, link) have `aria-label`s; Play toggles to "Pause" while playing.
  The "ALL-CANADIAN AIRWAVES" header text should not be a button.
- **Done when:** a screen reader announces every control by name and state.

---

## Phase 1 — Design: from good to top-tier

### 1.1 The hero is the radio ("On Air" panel)
- **What:** replace the static hero with a live broadcast panel:
  - Large album art / video (the ≥200×200 YouTube player from 0.7, or the
    track thumbnail `https://i.ytimg.com/vi/<id>/hqdefault.jpg` before play).
  - Track title and artist set in the display face (same scale as today's
    "THE GREAT CANADIAN SONGBOOK").
  - Album · year · region · genre in the mono label style.
  - One **large** play/pause button (≥ 72px), the primary action on the page.
  - A subtle live element: waveform, VU meter, or rotating dial needle
    (static when paused; respects reduced motion).
  - Before first play: "THE GREAT CANADIAN SONGBOOK" headline + a big
    "▶ Tune in" button that starts the default station.
- **Why:** the core action (Play) is a small button in the footer; while music
  plays the hero still says "Set your dials" and nothing on screen reacts.
- **Done when:** on load, a first-time visitor's eye lands on one obvious play
  button; while playing, the top of the page shows what's on air.

### 1.2 Preset stations as one-tap tiles
- **What:** turn the 14 presets into large tiles directly under the hero:
  distinct colour or texture per station, station name in display type, a
  one-line description, and **tap = start playing that station**. On mobile,
  a 2-column grid (not a cut-off row). On desktop, a grid or a carousel with
  visible arrows and an edge fade.
- **Why:** the presets ("Northern Bars", "Maritime Kitchen Party", "Prairie
  Static"…) are the best entry point, but they sit in a row cut off on the right
  with no sign there's more.
- **Done when:** every preset is visible or obviously scrollable, and one tap
  starts music.

### 1.3 Tuning panel instead of a form
- **What:** keep **Era** and **Mood** always visible. Fold Language, Genre and
  Region into a "Fine tune" drawer/accordion. Show a live result line as dials
  change, e.g. `NORTHERN BARS · 1990S · QUEBEC → 412 TRACKS`. Show active dials
  as removable chips.
- **Why:** five stacked groups of identical chips read as a form, not a radio.
- **Done when:** the tuning area fits in roughly one screen on desktop and the
  effect of each dial is visible instantly.

### 1.4 Always-on "Now playing / Up next" column
- **What:** on desktop (≥1024px), the right column of the controls section
  always shows Now playing + the next 5–8 tracks (each playable), instead of
  sitting empty until playback starts. Remove the large blank area at the
  bottom of the page.
- **Done when:** no large empty regions at 1440px, before or after Play.

### 1.5 Calmer typography
- **What:** limit to two families (display + text) plus mono for **2–3** label
  types only. Minimum text size 12px; reduce letter-spacing on long labels. On
  mobile, shorten the eyebrow so it doesn't wrap (e.g. "COAST TO COAST").
- **Copy:** "EST. 1920S" reads as a claim about the station — change to
  something true, e.g. "MUSIC FROM THE 1920S TO NOW".
- **Done when:** no text under 12px; no wrapped eyebrow lines at 390px.

### 1.6 Player bar never covers content
- **What:** add bottom padding equal to the fixed player height on every view;
  keep the host badge from overlapping player controls (move controls inward if
  the host badge can't be moved).
- **Done when:** the last content on every page is fully visible above the
  player at 390px and 1440px.

---

## Phase 2 — Performance

| Item | Now | Target |
|---|---|---|
| Logo | `logo.png` 404 KB + `logo-dark.png` 259 KB, both always loaded | Inline **SVG** (~5 KB), recoloured via CSS for night mode |
| YouTube embed | Loaded on page load (~1 MB of player scripts) | **Facade**: show thumbnail + play button; load the iframe on first Play |
| Fonts | 3 families from Google Fonts | 2 families, `font-display: swap`, preload the display face, subset to Latin + Latin-Ext (keep é è ç ñ œ) |
| Total transfer | ~1.25 MB | < 400 KB before first Play |
| DOM ready | ~4.7 s desktop | < 2 s |

- Lazy-load Discover/Directory code and lists (virtualize long lists; 20k cards
  must never render at once).
- **Done when:** Lighthouse mobile Performance ≥ 90, LCP < 2.5 s, CLS < 0.1.

*(Owner note: the host's own analytics script — volccdn.com — and the "Kimi"
badge come from the hosting platform. They disappear when the site moves to its
own domain/host; see 5.5.)*

---

## Phase 3 — Discover & Directory

### 3.1 Discover gets artwork and variety
- **What:** add the YouTube thumbnail to every track card; group consecutive
  tracks from the same album into one album card ("Songs of Leonard Cohen ·
  1968 · 6 tracks"); default sort = shuffled/"Staff mix" rather than long runs
  of one artist (currently seven Hank Snow cards in a row).
- **Done when:** the first screen of Discover shows ≥ 6 different artists, all
  with images.

### 3.2 Connect the Directory to the music
- **What:** a "▶ IN ROTATION · N tracks" badge on artists with music; play the
  artist straight from their card; a "Has music" filter.
- **Done when:** from the Directory, one tap plays an artist.

### 3.3 Report a wrong track
- **What:** a small "Wrong artist / wrong song?" link on every track and artist
  page that adds an entry to the existing Review queue (track id, artist,
  optional note).
- **Why:** some matches come from name-only lookups; listeners are the fastest
  way to catch same-name mix-ups.
- **Done when:** a report appears in the Review queue with the track id.

### 3.4 Review the public "Export CSV" and "Review queue"
- **What:** confirm both are meant to be public. If not, put them behind an
  admin key.

### 3.5 "Listen on" streaming links
- **Data:** `links_local.jsonl` in `github:trendyspenders-hub/cancon-harvest`
  — one line per artist per source:
  `{artist, source: wikidata|musicbrainz, id, spotify, apple_music,
  soundcloud, bandcamp, deezer, tidal, website}`. Missing fields are absent.
  Every link comes from Wikidata or MusicBrainz (exact name, Canadian,
  unambiguous) — **sourced, never guessed**. ~1,800 artists from Wikidata now;
  MusicBrainz is adding more (14 of 20 known artists linked in testing).
- **Merge rule:** combine both lines for an artist; when both have the same
  field, prefer `wikidata`. Keep each link's source for the profile's
  "Sources" section.
- **What:** on artist pages and Directory cards, a "Listen on" row of platform
  icons (Spotify, Apple Music, Bandcamp, SoundCloud, Deezer, Tidal, Official
  site) — only the ones that exist, each opening in a new tab with
  `rel="noopener"`. In the player, under the current track, "More from
  <artist> on Spotify / Apple Music / Bandcamp" using the same data.
- **Done when:** an artist with links shows them on their card and page, and
  an artist without links shows no empty icons.

### 3.6 SoundCloud & Bandcamp as a second playback source
- **What:** about 44% of artists have no YouTube presence and are
  directory-only. Where `links_local.jsonl` has a `soundcloud` or `bandcamp`
  link, offer playback through the official embed widget (SoundCloud widget
  player; Bandcamp embedded player — both work without an API key). Mark these
  in the UI ("via SoundCloud" / "via Bandcamp") the same way YouTube is marked
  today. Start with play-from-artist-page; add them to rotation behind a
  "Deep indie" toggle until hand-off between sources is proven reliable.
- **Why:** puts a whole tier of small Canadian artists on air — the
  "deep cuts" spirit of the station.
- **Done when:** a directory-only artist with a Bandcamp link can be played
  from their page, and rotation can hand off YouTube → SoundCloud → Bandcamp
  without stalling.

### 3.7 Archival tracks from Discogs (opt-in)
- **Data:** `tracks_discogs.jsonl` — same schema as `tracks_local.jsonl`.
  Only for artists the YouTube harvest couldn't find; each artist was matched
  on Discogs by exact name, single match, and at least one Canadian release.
  The videos are **community-added on Discogs and often fan uploads** — e.g.
  Banned from Atlantis' 1994 demo and 1995 album.
- **What:** merge into a separate "Archival" pool, never the main rotation.
  Label them in the player ("archival · via Discogs community"), and include
  them only when the listener turns on an "Archival / deep indie" option (or a
  dedicated "Lost Tapes" preset). Verify every video ID like the main merge;
  drop dead ones.
- **Done when:** with the option off, rotation is unchanged; with it on,
  previously directory-only artists like Banned from Atlantis play, clearly
  labelled.

### 3.8 Chart history filters
- **Data:** `charts_tracks.jsonl` — one line per harvested track that charted:
  `{yt, artist, title, years, chart, peak, year_end, ckoi_year_end, juno,
  us_peak, us_year_end, vancouver_peak, vancouver_year_end, sources}`.
  `peak`/`year_end` are national Canadian positions on the chart named in
  `chart` (RPM to 2000, Canadian Singles Chart 2001–06, Billboard Canadian
  Hot 100 2007+). `us_*` are U.S. Billboard — show separately, never as
  Canadian. `vancouver_*` are regional (1979–86). `ckoi_year_end` = Québec
  CKOI Top 50. `juno` = nominated / won Single of the Year. `sources` = the
  page each number came from. Grows every time the harvest is pushed.
- **What:**
  1. A **"Chart history" dial** next to Era/Mood: `ALL · CHARTED · TOP 40 ·
     TOP 10 · #1 HITS · DEEP CUTS (never charted)`. Plus `FRANCO HITS (CKOI)`
     and `JUNO SINGLES` toggles.
  2. **Presets:** "Number Ones" (every Canadian #1), "RPM Gold" (RPM Top 10,
     1964–2000), "Hot 100 Era" (2007+ Top 20), "Palmarès CKOI", "JUNO
     Singles", "One-Hit Wonders" (artists with exactly one Top 40 hit).
  3. **Badges** on track cards and in the player: `#1 RPM 1972`,
     `PEAK #7 · HOT 100 2015`, `CKOI #5`, `JUNO WINNER`. Tap a badge → the
     source page.
  4. **Discover sorting:** "Biggest hits first" (by best peak, then year-end).
  5. **Artist pages:** a "Chart history" list — year, title, peak, chart.
  6. Pair it with the Era dial: "1985 · Top 10" should just work.
- **Done when:** choosing "#1 HITS" plays only tracks with `peak = 1`, every
  badge links to its source, and U.S. positions never appear as Canadian.

---

## Phase 4 — Unmistakably Canadian

### 4.1 Fully bilingual (EN / FR)
- **What:** an EN/FR toggle (remember choice; default from browser language).
  Translate all interface text, preset names and descriptions (e.g. "Cuisine
  des Maritimes", "Statique des Prairies"), and use `/fr/...` URLs with
  `hreflang`. Artist/track names are never translated.
- **Why:** francophone artists are a priority in the catalogue, but the
  interface is English-only.
- **Done when:** every visible string has a French version and `/fr/` pages are
  indexable.

### 4.2 Signal map
- **What:** an interactive map of Canada (simple SVG, provinces/territories,
  optional city dots from sourced artist locations). Tap a region → tune the
  station to it. Show track counts per region on hover/tap. Keyboard and screen
  reader accessible (a list fallback).
- **Done when:** tapping Nova Scotia starts a Nova Scotia station.

### 4.3 Time-machine dial
- **What:** an analog-style tuner (needle on a 1950 → 2025 scale) as an
  alternative to the era chips. Dragging plays a short burst of radio static
  between decades (≤ 0.5 s, quiet, can be muted, off under reduced motion).
- **Done when:** dragging the needle changes era and the rotation follows.

---

## Phase 5 — Search engines and sharing

### 5.1 Artist pages that Google can read
- **What:** `/artist/<slug>` for all ~20,000 artists, **server-rendered or
  pre-rendered** HTML (not client-only): name, aliases, region, era, genres,
  role, source + verification status, tracks in rotation with a play button.
  Add `MusicGroup` / `Person` structured data (schema.org).
- **Done when:** viewing source on an artist page shows the artist's details
  without JavaScript.

### 5.2 Collection pages
- **What:** province, genre, decade, and combination pages:
  `/province/nova-scotia`, `/genre/folk`, `/decade/1990s`,
  `/province/quebec/genre/hip-hop/1990s`. Each with a one-line intro (factual,
  no invented claims) and a "Play this" button.

### 5.3 Share cards
- **What:** dynamic Open Graph images for stations, artists and tracks (station
  name / artist + art in brand style), plus `twitter:card`.
- **Done when:** pasting an artist link into a chat shows a branded preview.

### 5.4 Sitemap and metadata
- **What:** `sitemap.xml` (split into files of ≤ 50,000 URLs), `robots.txt`,
  unique `<title>` and meta description per page, canonical URLs.

### 5.5 Own domain *(owner action)*
- Move from `7xlil6gv532hu.kimi.pro` to a real domain (e.g. `canconradio.ca`).
  Set up redirects so old shared links keep working.

---

## Phase 6 — Let artists promote it

### 6.1 "Get on the air" — artist submissions
- **What:** a form: artist name, location, genres, official links (website,
  YouTube channel, Bandcamp), contact email, consent checkbox. Submissions go
  to the Review queue as "Self-reported" until verified.

### 6.2 Claim your profile
- **What:** an artist can request to claim their Directory entry (verified via
  a link on their official site or social account), then correct details and
  pick featured tracks. Edits are labelled as artist-supplied.

### 6.3 "Listen on CanCon Radio" badge + artist embed
- **What:** a copy-paste badge and a mini-player embed per artist (extend the
  existing Embed feature), for artists to put on their own sites.

---

## Phase 7 — Make people come back

### 7.1 Curated hours
- **What:** scheduled blocks ("Kitchen Party, Fridays 8pm ET"), guest-curated
  stations by artists/DJs, a visible schedule.

### 7.2 On this day
- **What:** a daily strip: album anniversaries and artist birthdays — **only
  from sourced dates**, never guessed. Tap to play.

### 7.3 Live presence
- **What:** anonymous "N tuned in" counter and "now playing in <city>" (city
  from coarse, privacy-safe location only; opt-out; never store precise data).

### 7.4 Saved dials that sync
- **What:** favourites currently live in one browser. Add optional sign-in
  (email magic link) to sync favourites and saved dials across devices.

### 7.5 "Deep Cuts Dispatch" newsletter
- **What:** a weekly email with 5 deep cuts + one featured station. Signup in
  the footer and on artist pages.

---

## Phase 8 — Mobile app feel

### 8.1 Installable (PWA)
- **What:** web app manifest (name, icons, theme colour), service worker for the
  app shell, "Add to home screen" prompt after a few visits.

### 8.2 Lock-screen and headphone controls
- **What:** Media Session API — track title, artist, artwork; play/pause/next/
  previous from the lock screen, headphones, and car.

### 8.3 Be honest about locked-screen playback
- **What:** YouTube embeds usually pause when a phone screen locks or the
  browser goes to background. Detect it and show a short note ("Keep CanCon
  open to keep listening") instead of letting it look broken.

---

## Phase 8½ — Signature features → see `FEATURES.md`

Fourteen features with full specs: Higher or Lower game, Guess the Year,
Listening Passport + Wrapped, **AI DJ** (template-only, never invented facts),
**Road Trip Mode**, alarm, band family trees, Near You, **Playing live near
you** (concerts, `events_local.jsonl`), year pages, Clean mode, listening
parties, open data page, and "What is CanCon?". Start after Phases 0–2.

---

## Phase 9 — Owner notes (not a build task)

- **Funding:** FACTOR, Canada Council for the Arts, and provincial music
  associations fund discovery projects like this. Sponsored presets
  ("Prairie Static, presented by…") and a supporters page are other options.
  No ads around YouTube embeds.
- **Partners:** campus & community radio (NCRA/ANREC), Music Nova Scotia,
  Manitoba Music, Music BC, ADISQ, festivals — co-branded stations and
  cross-promotion.

---

## Data pipeline note

The harvest (`github:trendyspenders-hub/cancon-harvest`) now fills `album` and
`year` for album tracks and is adding tens of thousands of tracks. When syncing:
**drop tracks for artists no longer in `tracks_local.jsonl`** (41 lower-confidence
name-only matches were removed), and treat `source: ytmusic` matches in
`harvest_done.jsonl` as lower confidence — good candidates for the "Report a
wrong track" flow (3.3). Streaming links live in a separate file,
`links_local.jsonl` (see 3.5) — it never changes `tracks_local.jsonl`.
Discogs community videos are in `tracks_discogs.jsonl` (see 3.7) — keep them
out of the main merge.

---

## Final checklist (run after every phase)

- [ ] Play, pause, skip, change preset, change dials — audio keeps playing
- [ ] Back/Forward stay on the site; reload works on every URL
- [ ] Keyboard-only run-through: everything reachable, focus always visible
- [ ] 390px phone: no horizontal scroll, nothing hidden under the player, tap targets ≥ 44px
- [ ] Night mode checked for every new element
- [ ] YouTube player ≥ 200×200 and unobstructed while playing
- [ ] Counts agree everywhere
- [ ] Lighthouse mobile: Performance ≥ 90, Accessibility ≥ 95
