"""
Alert delivery service — sends SMS via Twilio.

Real SMS goes out through the Twilio REST API whenever Twilio credentials are
present (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER). When they
are not configured, sends are *simulated* (logged only) so local development and
demos never fail on a missing provider.

We call Twilio's REST endpoint directly with aiohttp rather than pulling in the
Twilio SDK — one less dependency, and the request is a single authenticated POST.

Note: a Twilio *trial* account can only deliver to phone numbers you have
verified in the console, and prefixes each message with a trial notice.
"""

import asyncio
import logging

import aiohttp

from app.config import settings
from app.models.schemas import AlertResponse

logger = logging.getLogger(__name__)

TWILIO_API_ROOT = "https://api.twilio.com/2010-04-01"

# Keep messages under 480 chars — a 3-part concatenated SMS.
MAX_SMS_LEN = 480


def twilio_configured() -> bool:
    """True when all three Twilio credentials are present."""
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    )


async def _send_one_twilio(session: aiohttp.ClientSession, to_number: str, message: str):
    """Send a single SMS via Twilio. Returns (to_number, ok, detail)."""
    url = f"{TWILIO_API_ROOT}/Accounts/{settings.twilio_account_sid}/Messages.json"
    data = {"To": to_number, "From": settings.twilio_from_number, "Body": message}
    auth = aiohttp.BasicAuth(settings.twilio_account_sid, settings.twilio_auth_token)
    try:
        async with session.post(
            url, data=data, auth=auth, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            body = await resp.json(content_type=None)
            if resp.status in (200, 201):
                sid = body.get("sid") if isinstance(body, dict) else None
                logger.info(f"Twilio SMS queued to {to_number} (sid={sid})")
                return to_number, True, sid
            detail = body.get("message") if isinstance(body, dict) else str(body)
            logger.error(f"Twilio SMS to {to_number} failed ({resp.status}): {detail}")
            return to_number, False, detail
    except Exception as e:  # network / timeout / malformed response
        logger.error(f"Twilio SMS to {to_number} errored: {e}")
        return to_number, False, str(e)


async def _send_via_twilio(message: str, phone_numbers: list[str]) -> AlertResponse:
    """Fan out one authenticated POST per recipient, concurrently."""
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(_send_one_twilio(session, n, message) for n in phone_numbers)
        )

    sent = [n for n, ok, _ in results if ok]
    failed = [(n, d) for n, ok, d in results if not ok]

    if sent:
        msg = f"Sent to {len(sent)}/{len(phone_numbers)} recipient(s) via Twilio"
        if failed:
            msg += f" ({len(failed)} failed)"
        return AlertResponse(
            success=True, message=msg, sms_count=len(sent), advisory_preview=message[:100]
        )

    first_error = failed[0][1] if failed else "unknown error"
    return AlertResponse(
        success=False,
        message=f"All {len(phone_numbers)} Twilio send(s) failed: {first_error}",
        sms_count=0,
        advisory_preview=message[:100],
    )


async def send_sms_alert(
    message: str,
    phone_numbers: list[str],
    sender_id: str = "TAYARI",  # kept for API compatibility; unused with Twilio
) -> AlertResponse:
    """Send an SMS alert to every number, via Twilio when configured."""
    if not phone_numbers:
        return AlertResponse(
            success=False,
            message="No phone numbers provided",
            sms_count=0,
            advisory_preview=message[:100],
        )

    if len(message) > MAX_SMS_LEN:
        message = message[: MAX_SMS_LEN - 3] + "..."

    if twilio_configured():
        return await _send_via_twilio(message, phone_numbers)

    # No provider configured — simulate so the flow still completes in demos.
    logger.warning(
        f"[SIMULATED SMS] Twilio not configured — would send to "
        f"{len(phone_numbers)} recipient(s): {message[:120]}"
    )
    return AlertResponse(
        success=True,
        message=(
            f"Simulated delivery to {len(phone_numbers)} recipient(s) — "
            "no SMS provider configured (set TWILIO_* env vars to send real SMS)"
        ),
        sms_count=len(phone_numbers),
        advisory_preview=message[:100],
    )
