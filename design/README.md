# CanCon Radio — homepage redesign (reference mockup)

**For the build session (Kimi):** `home.html` is a working, high-fidelity
target for the homepage. Match its layout, hierarchy and behaviour; reuse its
CSS tokens. Every track, cover, show, place and number in it is real harvest
data (`mock-data.json`, built by `build_mock.py` from this repo's files).

**Run it:** `python3 -m http.server 8770` in the repo root, then open
`http://localhost:8770/design/home.html` (desktop and a phone-sized window).
Press **"Show spec labels"** (bottom-left) to see which BRIEF / FEATURES item
each block implements.

## What changed vs. the live site — and why

| # | Change | Fixes |
|---|---|---|
| 1 | **On Air hero** is the page: cover + YouTube player in a console bezel (≥200×200, 599×337 at 1440px), huge title, artist, album · year · hometown, chart/award badges, DJ transcript, one big Play | Music was in a small footer; footer player was ~160×90 (below YouTube's minimum) |
| 2 | **Red only for**: RADIO wordmark, Play, On Air lamp, live dots. Selection = ink fill (or gold on the dark era bar) | Red meant brand, headline, selection and labels at once |
| 3 | **14 preset tiles** in a 7×2 grid (4×… / 2×… on smaller screens), each with its own tuning-strip colour; tap = tune + play | Presets were a cut-off row (4 of 14 visible) |
| 4 | **Tuning**: era bar → mood cards → **FM dial as the main genre control** (17 stops, full names, staggered labels, drag + arrow keys, `role="slider"`) → **Fine tune** drawer (Language incl. **English**, Region, stacked genres) → "Now tuned to" summary | Dial and chips duplicated each other; dial labels were truncated; no English |
| 5 | Wide-tracked mono labels limited to small section labels; headings are Archivo, body Spectral | Every label shouted the same way |
| 6 | **Stats + actions** in one balanced row | Big number + scattered buttons |
| 7 | **Live queue** (sticky right column): Coming up next (never empty) + Previously on air, both with cover thumbnails and ▶ / ♡ | Empty "Coming up next"; log without art or actions |
| 8 | "How this station works" moved to the footer, with sources & credits, privacy and rights links | Prime space used for explanation |
| 9 | Copy: "Music from the 1920s to now" replaces "Est. 1920s" | Read as a claim about the station |

## New layout features

- **Sticky mini-player** — slides in at the top when the hero scrolls away
  (desktop); on phones it is a **thumb-zone bar at the bottom** with Play,
  Next and **Tune**.
- **Two-column console** on desktop: tuning left, live queue sticky right.
- **Mobile bottom sheet** for tuning (opened from the thumb bar; scrim closes it).
- **Shelves** with scroll-snap and arrow buttons: **On stage soon**
  (Ticketmaster shows + "Pre-game" station + tickets link credited) and
  **Fresh pressings** (official 2025–26 releases with real covers).
- **Signal map teaser** — a geographic tile map of the 13 provinces and
  territories, shaded by artists placed there; tap = tune to that region.
- **Hometown lineage** card — Winnipeg's artists in the order they first
  released music, with chart hits marked.
- **Night broadcast** theme (same tokens, dark console).
- **Paper grain** texture, staggered page-load reveal (respects reduced motion).

## Must-do in the real build
- **Host album covers yourself.** Hot-linking `yt3.googleusercontent.com`
  covers is unreliable — some are blocked by the browser (`ERR_BLOCKED_BY_ORB`
  in mobile Chrome during testing). Download each cover once to your own
  storage/CDN and serve it from your domain: faster, never breaks, and no
  request reaches Google before consent (Law 25, FEATURES F35).
- YouTube stays behind a **facade** until Play and uses
  `youtube-nocookie.com` (already in the mockup).
- Tap targets ≥ 44px everywhere except the map tiles on phones (32px, above
  WCAG's 24px minimum; the same regions are full-size chips in Fine tune).
- The DJ uses `dj/dj.js`; add `?voice=<voice service>/api/voice` for the
  neural voice once deployed.

## Regenerate the data
`python3 design/build_mock.py ~/cancon-harvest` (reads the live files).
