"""
Hugging Face NLLB-200 translation.

Meta's NLLB-200 ("No Language Left Behind") is purpose-built for low-resource
languages and produces noticeably better East-African translations than a
general chat LLM — which occasionally leaks English or foreign-language tokens
into languages like Amharic, Oromo, or Dinka. We route those languages through
NLLB and let the Groq translator stay as the fallback (and handle the languages
NLLB does not cover: Afar, Daasanach, Luhya, Turkana).

The classic `api-inference.huggingface.co` host has been retired, so this calls
the current Inference Providers router at `router.huggingface.co`.
"""

import asyncio
import logging
import os

import requests

from app.config import settings
from app.models.schemas import Language

logger = logging.getLogger(__name__)

# Model id can be overridden (e.g. to the 1.3B variant) without a code change.
NLLB_MODEL = os.getenv("HF_NLLB_MODEL", "facebook/nllb-200-distilled-600M")
HF_ROUTER_URL = f"https://router.huggingface.co/hf-inference/models/{NLLB_MODEL}"

# Tayari Language -> NLLB-200 FLORES-200 code. Only the languages NLLB actually
# supports appear here; everything else falls back to the Groq translator.
NLLB_LANG_CODES = {
    Language.SOMALI: "som_Latn",
    Language.SWAHILI: "swh_Latn",
    Language.AMHARIC: "amh_Ethi",
    Language.ARABIC: "arb_Arab",
    Language.OROMO: "gaz_Latn",   # West Central Oromo
    Language.DINKA: "dik_Latn",   # Southwestern Dinka
}

SRC_LANG = "eng_Latn"
_TIMEOUT_SECONDS = 30


def _hf_token() -> str | None:
    """Read the HF token from either accepted env name (or settings)."""
    return (
        os.environ.get("HF_API_TOKEN")
        or os.environ.get("HF_TOKEN")
        or getattr(settings, "hf_api_token", None)
    )


def supports(language: Language) -> bool:
    """True when NLLB covers this language *and* a token is configured."""
    return language in NLLB_LANG_CODES and bool(_hf_token())


async def translate_fields(texts: list[str], language: Language) -> list[str]:
    """
    Translate each string in `texts` from English into `language`.

    Returns a list aligned 1:1 with `texts`. Raises on any failure (missing
    token, HTTP error, unexpected response shape, count mismatch) so the caller
    can fall back to the Groq translator.
    """
    tgt = NLLB_LANG_CODES[language]
    return await asyncio.to_thread(_call_nllb, texts, tgt)


def _call_nllb(texts: list[str], tgt_lang: str) -> list[str]:
    token = _hf_token()
    if not token:
        raise RuntimeError("No Hugging Face token configured")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": texts,
        "parameters": {"src_lang": SRC_LANG, "tgt_lang": tgt_lang},
    }
    resp = requests.post(
        HF_ROUTER_URL, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS
    )
    if resp.status_code != 200:
        raise RuntimeError(f"HF NLLB returned {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    # A list input yields a list of results; a single string yields one dict.
    if isinstance(data, dict):
        data = [data]

    out: list[str] = []
    for item in data:
        # Result item is normally {"translation_text": "..."}, but some
        # provider responses nest it one level deep in a list.
        if isinstance(item, list) and item:
            item = item[0]
        if isinstance(item, dict) and "translation_text" in item:
            out.append(item["translation_text"].strip())
        else:
            raise RuntimeError(f"Unexpected NLLB response item: {str(item)[:120]}")

    if len(out) != len(texts):
        raise RuntimeError(
            f"NLLB returned {len(out)} items for {len(texts)} inputs"
        )
    return out
