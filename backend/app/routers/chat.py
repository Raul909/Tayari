"""
Chat router for follow-up questions on the flood advisory.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.flood_data import fetch_river_discharge
from app.services.flood_model import compute_flood_risk
from app.services.impact import compute_impact
from app.services.advisory import ROLE_DESCRIPTIONS, LANGUAGE_NAMES, FLOOD_GLOSSARY

import json
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()
_basins_path = Path(__file__).parent.parent / "data" / "basins.json"

# We reuse the limiter from main
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

def _get_basin_config(basin_id: str):
    from app.models.schemas import BasinConfig
    with open(_basins_path) as f:
        data = json.load(f)
    for b in data["basins"]:
        if b["id"] == basin_id:
            return BasinConfig(**b)
    raise HTTPException(status_code=404, detail=f"Basin '{basin_id}' not found")

@router.post("/chat/{basin_id}", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_advisory(
    request: Request,
    basin_id: str,
    chat_req: ChatRequest,
):
    """
    Follow-up chat about a flood advisory.
    Max 5 user messages per session.
    """
    if not settings.groq_api_key:
        return ChatResponse(
            reply="The chat feature requires a Groq API key to be configured.",
            messages_remaining=0
        )

    # Count user messages to enforce limit
    user_msgs_count = sum(1 for m in chat_req.session_messages if m.get("role") == "user") + 1
    if user_msgs_count > 5:
        raise HTTPException(status_code=429, detail="Maximum 5 questions per session reached.")

    basin = _get_basin_config(basin_id)

    # Re-fetch data to provide context (in production, we'd cache this or pass it from frontend)
    from app.services.weather_data import fetch_upstream_rainfall # local import to prevent circular if any

    discharge_data, rainfall_data = await asyncio.gather(
        fetch_river_discharge(basin.gauge_point.latitude, basin.gauge_point.longitude, 3, 7),
        fetch_upstream_rainfall(basin.upstream_point.latitude, basin.upstream_point.longitude, 3, 7)
    )

    risk = compute_flood_risk(basin, discharge_data, rainfall_data)
    impact = compute_impact(basin_id, risk.risk_level)

    lang_name = LANGUAGE_NAMES.get(chat_req.language.value, chat_req.language.value)
    role_desc = ROLE_DESCRIPTIONS.get(chat_req.role.value, "")

    system_prompt = f"""
You are the Tayari flood advisor for {basin.name}.
Answer the user's follow-up question about the flood advisory.
Stay factual, cite the data you were given, and keep answers under 150 words.
Write entirely in {lang_name}.

CONTEXT:
Risk Level: {risk.risk_level.value}
River: {basin.river}
Current Flow: {risk.current_discharge_m3s:.1f} m³/s
Max Forecast Flow: {risk.forecast_max_discharge_m3s:.1f} m³/s

Impact:
Population at risk: {impact.estimated_population_at_risk}
Schools: {impact.schools_at_risk}
Clinics: {impact.clinics_at_risk}

User Role: {role_desc}
"""

    messages = [{"role": "system", "content": system_prompt.strip()}]
    for m in chat_req.session_messages:
        messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    
    messages.append({"role": "user", "content": chat_req.message})

    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=settings.groq_model,
            messages=messages,
            temperature=0.6,
            max_tokens=512,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API error during chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate chat response.")

    return ChatResponse(
        reply=reply,
        messages_remaining=5 - user_msgs_count
    )
