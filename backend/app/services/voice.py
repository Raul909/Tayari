"""
Voice notes for advisories — spoken warnings for readers who can't read them.

TTS history: this originally used Meta MMS-TTS on the classic HF Inference API.
That host was decommissioned, and (verified 2026-07-19) **no** HF inference
provider serves the ``facebook/mms-tts-*`` models through the router either —
their ``inferenceProviderMapping`` is empty. So HF-based TTS cannot work at all.

Current implementation: **Groq's Orpheus TTS models**
(``canopylabs/orpheus-v1-english`` and ``canopylabs/orpheus-arabic-saudi``)
through the same Groq account that already writes the advisories. (Groq's
earlier PlayAI TTS models were retired.) Languages without a working TTS voice
keep ``requires_recording=True`` so a community mother-tongue recording can be
attached instead — a wrong-language robot voice would be worse than none.

Orpheus caps input at 200 characters per request, so the voice note speaks the
advisory *headline* (title + leading fact) rather than the whole text — a
spoken alert, with the full detail in the written advisory.

Audio files are named by content hash, so re-generating the same advisory
(cache refresh every 6 h) reuses the existing file instead of paying for a new
synthesis.
"""

import asyncio
import hashlib
import logging
import re
from pathlib import Path

import requests

from app.models.schemas import Advisory, Language
from app.config import settings

logger = logging.getLogger(__name__)

# Language → (Groq TTS model, voice). Only languages Groq actually speaks.
GROQ_TTS_MODELS = {
    Language.ENGLISH: ("canopylabs/orpheus-v1-english", "austin"),
    Language.ARABIC: ("canopylabs/orpheus-arabic-saudi", "abdullah"),
}

GROQ_TTS_URL = "https://api.groq.com/openai/v1/audio/speech"
_TIMEOUT_SECONDS = 30

# Orpheus rejects inputs over 200 characters; stay safely under it.
_MAX_TTS_CHARS = 195

_STATIC_AUDIO_DIR = Path("static/audio")


async def get_or_generate_voice_note(advisory: Advisory) -> Advisory:
    """
    Attach a synthesized voice note to the advisory when a TTS voice exists for
    its language; otherwise flag it as needing a human recording.
    """
    tts = GROQ_TTS_MODELS.get(advisory.language)
    if tts is None or not settings.groq_api_key:
        advisory.requires_recording = True
        advisory.voice_note_url = None
        return advisory

    model, voice = tts
    text_to_speak = _headline(advisory)

    # Content-addressed filename: identical advisory text → identical file, so
    # cache refreshes and repeated requests never re-synthesize.
    digest = hashlib.sha1(
        f"{advisory.language}|{text_to_speak}".encode("utf-8")
    ).hexdigest()[:20]
    filename = f"voice_{digest}.wav"
    filepath = _STATIC_AUDIO_DIR / filename

    try:
        if not filepath.exists():
            audio_bytes = await asyncio.to_thread(
                _call_groq_tts, model, voice, text_to_speak
            )
            _STATIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(audio_bytes)

        # Relative path is fine for the prototype: the backend serves /static.
        advisory.voice_note_url = f"/static/audio/{filename}"
        advisory.requires_recording = False
    except Exception as e:
        logger.warning(f"TTS generation failed, will require manual recording: {e}")
        advisory.requires_recording = True
        advisory.voice_note_url = None

    return advisory


def _headline(advisory: Advisory) -> str:
    """
    The spoken version of the advisory: its title, then as many leading body
    sentences as fit in Orpheus's 200-character input budget. The written
    advisory carries the full detail; the voice note is the alert.
    """
    text = advisory.title.rstrip(".!؟?")
    for sentence in re.split(r"(?<=[.!؟?])\s+", advisory.body):
        sentence = sentence.strip().rstrip(".!؟?")
        if not sentence:
            continue
        candidate = f"{text}. {sentence}"
        if len(candidate) > _MAX_TTS_CHARS - 1:
            break
        text = candidate
    return f"{text}."[:_MAX_TTS_CHARS]


def _call_groq_tts(model: str, voice: str, text: str) -> bytes:
    """One synthesis call against Groq's OpenAI-compatible speech endpoint."""
    response = requests.post(
        GROQ_TTS_URL,
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "voice": voice,
            "input": text[:_MAX_TTS_CHARS],
            "response_format": "wav",
        },
        timeout=_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Groq TTS returned {response.status_code}: {response.text[:200]}"
        )
    return response.content
