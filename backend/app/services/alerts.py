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


async def send_sms_alert(
    message: str,
    phone_numbers: list[str],
    sender_id: str = "TAYARI",
) -> AlertResponse:
    """
    Send an SMS alert to the specified phone numbers.

    In sandbox mode, messages are simulated in the AT dashboard.

    Args:
        message: The advisory text to send
        phone_numbers: List of phone numbers in international format
        sender_id: SMS sender ID (used in production)

    Returns:
        AlertResponse with success status and delivery info
    """
    _init_at()

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

    if _sms_service is not None:
        try:
            response = _sms_service.send(message, phone_numbers)
            sms_data = response.get("SMSMessageData", {})
            recipients = sms_data.get("Recipients", [])
            success_count = sum(
                1 for r in recipients
                if r.get("statusCode") == 101  # 101 = Sent
            )

            logger.info(
                f"SMS sent to {len(phone_numbers)} numbers, "
                f"{success_count} successful"
            )

            return AlertResponse(
                success=success_count > 0,
                message=f"Sent to {success_count}/{len(phone_numbers)} recipients",
                sms_count=success_count,
                advisory_preview=message[:100],
            )

        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return AlertResponse(
                success=False,
                message=f"SMS delivery failed: {str(e)}",
                sms_count=0,
                advisory_preview=message[:100],
            )
    else:
        # Simulate SMS for demo
        logger.info(
            f"[SIMULATED SMS] To: {phone_numbers} | Message: {message[:80]}..."
        )
        return AlertResponse(
            success=True,
            message=f"[Simulated] Would send to {len(phone_numbers)} recipients. "
                    f"Configure AT_API_KEY in .env for real SMS delivery.",
            sms_count=len(phone_numbers),
            advisory_preview=message[:100],
        )
