import asyncio
import io
import os
import requests
import tempfile
import uuid
from pathlib import Path
from pydantic import HttpUrl

from app.models.schemas import Advisory, Language, LOW_RESOURCE_LANGUAGES
from app.config import settings

# Mapping Tayari Language enums to Meta MMS-TTS models on Hugging Face
HF_TTS_MODELS = {
    Language.ENGLISH: "facebook/mms-tts-eng",
    Language.SOMALI: "facebook/mms-tts-som",
    Language.SWAHILI: "facebook/mms-tts-swh",
    Language.AMHARIC: "facebook/mms-tts-amh",
    Language.ARABIC: "facebook/mms-tts-ara",
    Language.OROMO: "facebook/mms-tts-orm",
}

# In-memory ephemeral cache mapping session/alert IDs to temporary files
_AUDIO_CACHE = {}

async def get_or_generate_voice_note(advisory: Advisory) -> Advisory:
    """
    Determines if the advisory requires manual recording or if we can use
    the Hugging Face Inference API to generate a TTS voice note ephemerally.
    """
    if advisory.language in LOW_RESOURCE_LANGUAGES:
        advisory.requires_recording = True
        advisory.voice_note_url = None
        return advisory
        
    model_id = HF_TTS_MODELS.get(advisory.language, "facebook/mms-tts-eng")
    
    text_to_speak = f"{advisory.title}. {advisory.body}. " + " ".join(advisory.actions)
    
    # We use a thread to make the sync requests call non-blocking
    try:
        audio_bytes = await asyncio.to_thread(_call_hf_inference, model_id, text_to_speak)
        if audio_bytes:
            # Store ephemerally in a temp file and serve statically, or just keep in cache
            # For this prototype, we'll write to a temp dir in static/audio
            static_dir = Path("static/audio")
            static_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"voice_{uuid.uuid4().hex}.wav"
            filepath = static_dir / filename
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
                
            # Normally this would be a full URL, relative path is fine for the prototype
            # as long as the backend serves /static
            advisory.voice_note_url = f"/static/audio/{filename}"
            advisory.requires_recording = False
    except Exception as e:
        print(f"Error generating TTS: {e}")
        # Fallback to requiring recording if TTS fails
        advisory.requires_recording = True
        advisory.voice_note_url = None

    return advisory

def _call_hf_inference(model_id: str, text: str) -> bytes:
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    # Use HF token if provided in environment, otherwise it might fail/rate limit
    headers = {}
    hf_token = os.environ.get("HF_API_TOKEN") or getattr(settings, "hf_api_token", None)
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
        
    response = requests.post(api_url, headers=headers, json={"inputs": text})
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"HF API returned {response.status_code}: {response.text}")
