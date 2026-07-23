import os
import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.db_models import FeedbackORM

logger = logging.getLogger(__name__)
router = APIRouter()

class FeedbackCreate(BaseModel):
    rating: int
    subject: str | None = None
    comment: str | None = None

async def send_feedback_email(rating: int, subject: str | None, comment: str | None):
    """Sends a feedback email via FormSubmit.co (hosted external service)."""
    import httpx
    
    rating_map = {1: 'Angry 😠', 2: 'Sad 😞', 3: 'Neutral 😐', 4: 'Happy 🙂', 5: 'Very Happy 😄'}
    rating_text = rating_map.get(rating, str(rating))
    
    subject_text = subject if subject else "General"
    
    body = f"""New Feedback Received!

Opinion Rating: {rating_text}
Subject: {subject_text}

Comment:
{comment if comment else 'No comment provided.'}
"""

    payload = {
        "rating": rating_text,
        "subject": subject_text,
        "message": body,
        "_subject": f"Tayari Feedback - {subject_text} ({rating_text})"
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://formsubmit.co/ajax/contact@launchpixel.in",
                json=payload
            )
            res.raise_for_status()
        logger.info("Feedback email sent via FormSubmit.co successfully.")
    except Exception as e:
        logger.error(f"Failed to send feedback via FormSubmit.co: {e}")


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Submit user feedback, save to DB, and notify via email."""
    if not (1 <= feedback.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Save to database
    feedback_record = FeedbackORM(
        rating=feedback.rating,
        subject=feedback.subject,
        comment=feedback.comment
    )
    session.add(feedback_record)
    await session.commit()

    # Schedule email notification
    background_tasks.add_task(
        send_feedback_email, 
        feedback.rating, 
        feedback.subject, 
        feedback.comment
    )

    return {"success": True, "message": "Feedback submitted successfully"}
