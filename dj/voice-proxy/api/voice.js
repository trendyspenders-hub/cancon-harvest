// CanCon Radio — DJ voice service (Vercel Function, Node.js runtime).
//
// GET /api/voice?lang=en|fr&text=...  ->  audio/mpeg (Azure neural voice)
//
// The Azure key stays here (env var), never in the website. Guards:
//  - only requests whose Origin/Referer is in ALLOWED_ORIGINS
//  - text: max 400 characters, plain text only (XML-escaped into SSML)
//  - responses are cached by Vercel's CDN per exact URL, so a repeated line
//    (station IDs, common intros) is synthesized once
// Use the Azure FREE (F0) tier: when the monthly free quota runs out Azure
// throttles (HTTP 429) instead of billing, and dj.js falls back to the
// browser voice. No surprise invoice.
//
// Env: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION (e.g. canadacentral),
//      ALLOWED_ORIGINS (comma-separated, e.g. https://canconradio.ca,http://localhost:8765)
//      optional VOICE_EN (default en-CA-ClaraNeural), VOICE_FR (default fr-CA-SylvieNeural)

const VOICES = {
  en: { lang: "en-CA", name: () => process.env.VOICE_EN || "en-CA-ClaraNeural" },
  fr: { lang: "fr-CA", name: () => process.env.VOICE_FR || "fr-CA-SylvieNeural" },
};

const xml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;").replace(/'/g, "&apos;");

function allowed(request) {
  const list = (process.env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  const origin = request.headers.get("origin") || "";
  const referer = request.headers.get("referer") || "";
  const ok = list.find((o) => origin === o || referer.startsWith(o + "/") || referer === o);
  return { ok: Boolean(ok), corsOrigin: ok || "" };
}

export default {
  async fetch(request) {
    const { ok, corsOrigin } = allowed(request);
    const cors = corsOrigin ? { "Access-Control-Allow-Origin": corsOrigin, "Vary": "Origin" } : {};
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { ...cors, "Access-Control-Allow-Methods": "GET" } });
    if (request.method !== "GET") return new Response("GET only", { status: 405, headers: cors });
    if (!ok) return new Response("Forbidden", { status: 403 });

    const url = new URL(request.url);
    const lang = url.searchParams.get("lang") === "fr" ? "fr" : "en";
    const text = (url.searchParams.get("text") || "").replace(/\s+/g, " ").trim();
    if (!text || text.length > 400) return new Response("Bad text", { status: 400, headers: cors });

    const key = process.env.AZURE_SPEECH_KEY, region = process.env.AZURE_SPEECH_REGION;
    if (!key || !region) return new Response("Voice not configured", { status: 503, headers: cors });

    const v = VOICES[lang];
    const ssml = `<speak version="1.0" xml:lang="${v.lang}"><voice name="${v.name()}">` +
                 `<prosody rate="+4%">${xml(text)}</prosody></voice></speak>`;
    const r = await fetch(`https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`, {
      method: "POST",
      headers: {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "cancon-radio-dj",
      },
      body: ssml,
    });
    if (!r.ok) return new Response(`Voice service error ${r.status}`, { status: r.status === 429 ? 429 : 502, headers: cors });

    return new Response(r.body, {
      status: 200,
      headers: { ...cors, "Content-Type": "audio/mpeg",
                 "Cache-Control": "public, max-age=86400, s-maxage=31536000, immutable" },
    });
  },
};
