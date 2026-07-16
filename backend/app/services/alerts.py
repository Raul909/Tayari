"""
Alert delivery service — sends SMS via Africa's Talking.

Uses sandbox mode for development/demo (no real SMS cost).
Supports future WhatsApp Business API integration.
"""

import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.models.schemas import AlertRequest, AlertResponse

logger = logging.getLogger(__name__)

# Try importing Africa's Talking SDK
try:
    import africastalking
    HAS_AT = True
except ImportError:
    HAS_AT = False
    logger.warning("Africa's Talking SDK not installed — SMS will be simulated")

_sms_service = None


def _init_at():
    """Initialize Africa's Talking SDK."""
    global _sms_service
    if HAS_AT and settings.at_api_key and _sms_service is None:
        try:
            africastalking.initialize(settings.at_username, settings.at_api_key)
            _sms_service = africastalking.SMS
            logger.info(f"Africa's Talking initialized (username: {settings.at_username})")
        except Exception as e:
            logger.error(f"Failed to initialize Africa's Talking: {e}")


import aiohttp

async def send_sms_alert(
    message: str,
    phone_numbers: list[str],
    sender_id: str = "TAYARI",
) -> AlertResponse:
    """
    Send an SMS alert by delegating to the Cloudflare Worker proxy.
    This ensures 24/7 high availability even if this backend process restarts.
    """
    if not phone_numbers:
        return AlertResponse(
            success=False,
            message="No phone numbers provided",
            sms_count=0,
            advisory_preview=message[:100],
        )

    # Truncate message to SMS limit (keep under 480 chars for 3-part SMS)
    if len(message) > 480:
        message = message[:477] + "..."

    payload = {
        "message": message,
        "phone_numbers": phone_numbers,
        "sender_id": sender_id
    }
    
    logger.info(f"Delegating SMS to Cloudflare Worker ({len(phone_numbers)} recipients)")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(settings.cloudflare_sms_url, json=payload, timeout=10) as resp:
                if resp.status in (200, 202):
                    return AlertResponse(
                        success=True,
                        message=f"Sent to {len(phone_numbers)} recipients via Cloudflare Worker",
                        sms_count=len(phone_numbers),
                        advisory_preview=message[:100],
                    )
                else:
                    text = await resp.text()
                    logger.error(f"Cloudflare Worker SMS failed: {resp.status} - {text}")
                    return AlertResponse(
                        success=False,
                        message=f"Cloudflare Worker failed: {resp.status}",
                        sms_count=0,
                        advisory_preview=message[:100],
                    )
    except Exception as e:
        logger.error(f"SMS Cloudflare Worker delegation failed: {e}")
        return AlertResponse(
            success=False,
            message=f"Cloudflare connection failed: {str(e)}",
            sms_count=0,
            advisory_preview=message[:100],
        )