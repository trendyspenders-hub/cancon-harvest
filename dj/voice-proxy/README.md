# CanCon Radio — DJ voice service

A tiny Vercel Function that turns DJ lines (written by `dj/dj.js` from sourced
facts) into speech with Azure's Canadian neural voices. The Azure key lives
only here, as an environment variable — never in the website.

## 1. Azure (free tier)
1. portal.azure.com → **Create a resource** → **Speech** (Azure AI Speech).
2. Region: **Canada Central** (`canadacentral`). Pricing tier: **Free F0**.
   On F0, running out of the monthly free quota pauses the voice (HTTP 429 —
   the DJ falls back to the browser voice); it never bills you.
3. Resource → **Keys and Endpoint** → copy **KEY 1** and the **Location/Region**.

## 2. Pick the voices (optional, on the harvest Mac)
Add to `~/cancon-harvest/.env`:
```
AZURE_SPEECH_KEY=…
AZURE_SPEECH_REGION=canadacentral
```
then `python3 dj/audition.py` and listen in `dj/audition/`
(Clara, Liam · Sylvie, Antoine, Jean, Thierry).

## 3. Deploy
```
cd dj/voice-proxy
npx vercel --prod
npx vercel env add AZURE_SPEECH_KEY production
npx vercel env add AZURE_SPEECH_REGION production     # canadacentral
npx vercel env add ALLOWED_ORIGINS production         # e.g. https://7xlil6gv532hu.kimi.pro,http://localhost:8765
npx vercel env add VOICE_EN production                # optional, default en-CA-ClaraNeural
npx vercel env add VOICE_FR production                # optional, default fr-CA-SylvieNeural
npx vercel --prod                                     # redeploy so the env vars apply
```

## 4. Use it
In the site: `CanConDJ.create({ …, voiceUrl: "https://<project>.vercel.app/api/voice" })`.
Demo: `dj/demo.html?voice=https://<project>.vercel.app/api/voice`
(add `http://localhost:8765` to ALLOWED_ORIGINS to test locally).

## Guards
- Only origins in `ALLOWED_ORIGINS` (checked on Origin/Referer).
- Text ≤ 400 characters, plain text (XML-escaped into SSML).
- Identical lines are cached by Vercel's CDN — station IDs cost once.
