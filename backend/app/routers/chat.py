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

# Shared limiter (same instance registered on app.state.limiter in main.py)
from app.limiter import limiter

def _get_basin_config(basin_id: str):
    from app.models.schemas import BasinConfig
    with open(_basins_path) as f:
        data = json.load(f)
    for b in data["basins"]:
        if b["id"] == basin_id:
            return BasinConfig(**b)
    raise HTTPException(status_code=404, detail=f"Basin '{basin_id}' not found")

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_session
from app.models.db_models import ChatMemoryORM

@router.post("/chat/{basin_id}", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_advisory(
    request: Request,
    basin_id: str,
    chat_req: ChatRequest,
    session: AsyncSession = Depends(get_session)
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

    try:
        discharge_data, rainfall_data = await asyncio.gather(
            fetch_river_discharge(basin.gauge_point.latitude, basin.gauge_point.longitude, 3, 7),
            fetch_upstream_rainfall(basin.upstream_point.latitude, basin.upstream_point.longitude, 3, 7)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fetch error: {str(e)} ({type(e).__name__})")

    risk = compute_flood_risk(basin, discharge_data, rainfall_data)
    impact = compute_impact(basin_id, risk.risk_level)

    from datetime import date
    today = date.today()
    current_discharge = 0.0
    for d in discharge_data:
        if d.date == today and d.discharge_mean is not None:
            current_discharge = d.discharge_mean
            break
    if current_discharge == 0.0:
        for d in reversed(discharge_data):
            if d.discharge_mean is not None:
                current_discharge = d.discharge_mean
                break
                
    max_discharge = 0.0
    for d in discharge_data:
        if d.discharge_mean is not None and d.discharge_mean > max_discharge:
            max_discharge = d.discharge_mean

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
Current Flow: {current_discharge:.1f} m³/s
Max Forecast Flow: {max_discharge:.1f} m³/s

Impact:
Population at risk: {impact.estimated_population_at_risk}
Schools: {impact.schools_at_risk}
Clinics: {impact.clinics_at_risk}

User Role: {role_desc}
"""

    messages = [{"role": "system", "content": system_prompt.strip()}]
    
    # Load cross-session memories from DB — best-effort context, not required.
    if chat_req.user_id:
        try:
            stmt = (
                select(ChatMemoryORM)
                .where(ChatMemoryORM.user_id == chat_req.user_id)
                .where(ChatMemoryORM.basin_id == basin_id)
                .order_by(ChatMemoryORM.created_at.desc())
                .limit(10)
            )
            result = await session.execute(stmt)
            past_memories = result.scalars().all()
            # Prepend to the session history in chronological order
            for mem in reversed(past_memories):
                messages.append({"role": mem.role, "content": mem.content})
        except Exception as e:
            logger.warning(f"Chat memory lookup failed ({e}); continuing without it")

    for m in chat_req.session_messages:
        r = m.get("role", "user")
        if r == "ai":
            r = "assistant"
        messages.append({"role": r, "content": m.get("content", "")})
    
    messages.append({"role": "user", "content": chat_req.message})

    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
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

    # Save to memory — best-effort. A DB hiccup here shouldn't cost the user
    # the reply they already got back from Groq.
    try:
        session.add(ChatMemoryORM(
            user_id=chat_req.user_id,
            basin_id=basin_id,
            role="user",
            content=chat_req.message
        ))
        session.add(ChatMemoryORM(
            user_id=chat_req.user_id,
            basin_id=basin_id,
            role="assistant",
            content=reply
        ))
        await session.commit()
    except Exception as e:
        logger.warning(f"Chat memory write failed ({e}); ignoring")
        await session.rollback()

    return ChatResponse(
        reply=reply,
        messages_remaining=5 - user_msgs_count
    )
