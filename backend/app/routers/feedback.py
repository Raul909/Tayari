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

def send_feedback_email_sync(rating: int, subject: str | None, comment: str | None):
    """Sends a feedback email synchronously (to be run in a background thread)."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    to_email = "contact@launchpixel.in"
    from_email = smtp_user or "noreply@tayari.app"

    # Frame the email content
    rating_map = {1: 'Angry 😠', 2: 'Sad 😞', 3: 'Neutral 😐', 4: 'Happy 🙂', 5: 'Very Happy 😄'}
    rating_text = rating_map.get(rating, str(rating))
    
    subject_text = subject if subject else "General"
    
    body = f"""New Feedback Received!

Opinion Rating: {rating_text}
Subject: {subject_text}

Comment:
{comment if comment else 'No comment provided.'}

-- 
Tayari Automated System
"""

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = f"Tayari Feedback - {subject_text} ({rating_text})"
    msg['From'] = from_email
    msg['To'] = to_email

    if not smtp_server or not smtp_password:
        logger.info("SMTP not configured. Mocking feedback email send:")
        logger.info(f"--- EMAIL TO {to_email} ---\n{msg.as_string()}\n-----------------------")
        return

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Feedback email sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}")


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
        send_feedback_email_sync, 
        feedback.rating, 
        feedback.subject, 
        feedback.comment
    )

    return {"success": True, "message": "Feedback submitted successfully"}
