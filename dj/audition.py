#!/usr/bin/env python3
"""Audition the Canadian neural voices with real DJ lines before deploying.

Reads AZURE_SPEECH_KEY and AZURE_SPEECH_REGION from ../.env (git-ignored).
Builds a few real links from dj/sample.json with dj.js (via node), then saves
one MP3 per voice in dj/audition/ (git-ignored). Uses ~6–8k characters of the
free monthly quota.

Usage:   python3 dj/audition.py
"""
import json, os, re, subprocess, urllib.request
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = {"en": ["en-CA-ClaraNeural", "en-CA-LiamNeural"],
          "fr": ["fr-CA-SylvieNeural", "fr-CA-AntoineNeural", "fr-CA-JeanNeural", "fr-CA-ThierryNeural"]}

def env():
    out = {}
    p = os.path.join(HERE, "..", ".env")
    for line in open(p, encoding="utf-8"):
        m = re.match(r"\s*([A-Z_]+)\s*=\s*(.+?)\s*$", line)
        if m: out[m.group(1)] = m.group(2).strip('"\'')
    return out

def lines(lang):
    js = ("require('./dj.js'); const s=require('./sample.json'); const dj=CanConDJ.create({lang:'%s', idEvery:2});"
          "const out=[]; for(let i=0;i<3;i++) out.push(dj.link(s[i], s[i+1])); console.log(JSON.stringify(out));") % lang
    return json.loads(subprocess.run(["node", "-e", js], cwd=HERE, capture_output=True, text=True, check=True).stdout)

def main():
    e = env()
    key, region = e.get("AZURE_SPEECH_KEY"), e.get("AZURE_SPEECH_REGION")
    if not key or not region: raise SystemExit("Add AZURE_SPEECH_KEY and AZURE_SPEECH_REGION to .env first")
    os.makedirs(os.path.join(HERE, "audition"), exist_ok=True)
    for lang, voices in VOICES.items():
        text = " ... ".join(lines(lang))
        for v in voices:
            ssml = (f'<speak version="1.0" xml:lang="{v[:5]}"><voice name="{v}"><prosody rate="+4%">'
                    f"{escape(text)}</prosody></voice></speak>")
            req = urllib.request.Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                                         data=ssml.encode(), headers={
                "Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "cancon-radio-dj"})
            try:
                audio = urllib.request.urlopen(req, timeout=60).read()
            except urllib.error.HTTPError as err:
                print(f"{v}: HTTP {err.code} — {err.read()[:120]!r}"); continue
            path = os.path.join(HERE, "audition", f"{v}.mp3")
            open(path, "wb").write(audio)
            print(f"{v}: {len(audio)//1024} KB -> dj/audition/{v}.mp3")
    print("Listen with:  open dj/audition")

if __name__ == "__main__":
    main()
