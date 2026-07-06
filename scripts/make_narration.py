"""Render Crucible's deck narration through ElevenLabs and embed it in the deck.

The published deck ships with browser speech (Edge natural voices). This script
upgrades it to studio-quality audio: it renders each narration line via the
ElevenLabs TTS API, base64-encodes the MP3s, and injects them into the deck HTML
at the /*CRUX_AUDIO_SLOT*/ marker. The deck then plays the embedded clips
instead of browser speech — fully self-contained, CSP-safe.

Usage:
    set ELEVENLABS_API_KEY=...            (or have it in the environment)
    set ELEVENLABS_VOICE_ID=...           (optional; defaults to "Adam")
    python scripts/make_narration.py --deck "<path to crucible-deck.html>"

Cost: ~1,400 characters total — pennies. Keep LINES in sync with the deck's
CRUX array if the narration ever changes.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

import httpx

# Spoken-performance versions of the deck's CRUX lines (12 slides, same order).
# Punctuation here is stage direction: ellipses = beats, question marks = lift,
# short sentences = punch. ElevenLabs performs punctuation; don't flatten it.
LINES = [
    "Hey... I'm Crucible — your A.I. underwriting agent. I put loans... on trial. Come on, let me show you how I work.",
    "This is the world I was built for. A black box... that says no — and hangs up. Yeah... I hate it too.",
    "So they made me argue with myself. In public. Prosecutor... defender... judge. And if I can't cite it? I don't say it.",
    "Okay — enough slides. Watch me work. This is a real file. The prosecution swings... the defense answers... and I rule. And then? I start clearing conditions. Myself.",
    "See, a verdict is just my opening move. I write the conditions... I read your documents... and I clear them myself. Oh, and no — a nine-hundred-dollar bank statement does not clear a thirty-one-thousand-dollar condition. Nice try.",
    "Now this... this is my favorite trick. When a file dies? I rebuild the deal. A buydown... a product switch... whatever legally works. And the paperwork? Already written.",
    "And every single file teaches me something. What clears... what funds... what flops. I don't forget.",
    "Here's the thing — I live inside your stack... not on top of it. Salesforce in... path-to-yes back. Most files never need a human to open my console.",
    "This is my house. An AMD Instinct... the M-I three hundred X. Borrower data never leaves it. Only the hardest thinking phones a friend... over at Fireworks.",
    "I turn denials... into fundings. And I write my own Reg B paperwork. Compliance teams actually like me... that's rare.",
    "Today? I underwrite. Tomorrow... I watch rates. I shop investors. I work for the borrower. One engine... a platform.",
    "The black box says no. ... I work the file... until it's a yes. I'm Crucible.",
]

DEFAULT_VOICE = "pNInz6obpgDQGcFmaJgB"  # ElevenLabs stock "Adam"
MARKER = "/*CRUX_AUDIO_SLOT*/"


def tts(client: httpx.Client, api_key: str, voice_id: str, text: str) -> bytes:
    resp = client.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_64"},
        headers={"xi-api-key": api_key},
        json={"text": text,
              "model_id": "eleven_multilingual_v2",   # most expressive GA model
              "voice_settings": {                       # performance, not narration
                  "stability": 0.32,                    # low = more emotional range
                  "similarity_boost": 0.75,
                  "style": 0.45,                        # lean into delivery
                  "use_speaker_boost": True,
              }},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True, help="path to crucible-deck.html")
    ap.add_argument("--voice", default=os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE))
    args = ap.parse_args()

    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        print("ELEVENLABS_API_KEY not set."); return 1
    deck = Path(args.deck)
    html = deck.read_text(encoding="utf-8")
    if MARKER not in html:
        print(f"Marker {MARKER} not found in {deck} — is this the narrator deck?"); return 1

    clips, total = [], 0
    with httpx.Client() as client:
        for i, line in enumerate(LINES):
            audio = tts(client, api_key, args.voice, line)
            total += len(audio)
            clips.append("data:audio/mpeg;base64," + base64.b64encode(audio).decode())
            print(f"  [{i+1:02d}/{len(LINES)}] {len(audio)/1024:.0f} KB")

    inject = "window.CRUX_AUDIO=[" + ",".join(f'"{c}"' for c in clips) + "];"
    out = deck.with_name(deck.stem + "_voiced.html")
    out.write_text(html.replace(MARKER, inject + "\n" + MARKER), encoding="utf-8")
    print(f"\nWrote {out}  (audio total {total/1024:.0f} KB raw, ~{total*1.35/1024:.0f} KB embedded)")
    print("Open it locally to hear the ElevenLabs voice, or hand it back for republishing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
