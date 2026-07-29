import logging
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

FEEDBACK_EMAIL = "contact@launchpixel.in"


class FeedbackCreate(BaseModel):
    rating: int
    subject: str | None = None
    comment: str | None = None


RATING_MAP = {
    1: "Angry 😠",
    2: "Sad 😞",
    3: "Neutral 😐",
    4: "Happy 🙂",
    5: "Very Happy 😄",
}


async def _send_feedback_email(
    rating: int, subject: str | None, comment: str | None
) -> bool:
    """Send feedback to contact@launchpixel.in via FormSubmit.co.

    Returns True on success, False on failure.  Never raises — the caller
    decides what to do with the result.
    """
    import httpx

    rating_text = RATING_MAP.get(rating, str(rating))
    subject_text = subject or "General"

    body = (
        f"New Feedback Received!\n\n"
        f"Opinion Rating: {rating_text}\n"
        f"Subject: {subject_text}\n\n"
        f"Comment:\n{comment or 'No comment provided.'}\n"
    )

    payload = {
        "rating": rating_text,
        "subject": subject_text,
        "message": body,
        "_subject": f"Tayari Feedback - {subject_text} ({rating_text})",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                f"https://formsubmit.co/ajax/{FEEDBACK_EMAIL}",
                json=payload,
            )
            res.raise_for_status()
        logger.info("Feedback email sent to %s via FormSubmit.co.", FEEDBACK_EMAIL)
        return True
    except Exception as e:
        logger.error("FormSubmit.co delivery failed: %s", e)
        return False


async def _save_to_db(rating: int, subject: str | None, comment: str | None) -> bool:
    """Best-effort persist to the database. Returns True on success."""
    try:
        from app.db import SessionLocal
        from app.models.db_models import FeedbackORM

        async with SessionLocal() as session:
            session.add(FeedbackORM(
                rating=rating, subject=subject, comment=comment,
            ))
            await session.commit()
        logger.info("Feedback saved to database.")
        return True
    except Exception as e:
        logger.warning("Could not save feedback to DB (non-fatal): %s", e)
        return False


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate):
    """Submit user feedback — always sends the email, tries DB save.

    The email to contact@launchpixel.in is the primary delivery channel.
    The DB save is secondary (nice-to-have for analytics).  Neither
    failing should block the other, and the endpoint returns 200 as long
    as the email goes out.
    """
    if not (1 <= feedback.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # 1. Send the email (primary — must succeed for a 200 response).
    email_ok = await _send_feedback_email(
        feedback.rating, feedback.subject, feedback.comment,
    )

    # 2. Try to save to database (secondary — failure is logged, not fatal).
    db_ok = await _save_to_db(
        feedback.rating, feedback.subject, feedback.comment,
    )

    if not email_ok:
        raise HTTPException(
            status_code=502,
            detail="Could not deliver feedback email. Please try again.",
        )

    return {
        "success": True,
        "message": "Feedback submitted successfully",
        "saved_to_db": db_ok,
    }
