"""
User routes for Tayari, including profile preferences and saved basins.
Protected by Supabase JWT auth.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.limiter import limiter

from app.db import get_session
from app.models.db_models import UserProfileORM, SavedBasinORM, UserPrefsORM
from app.models.schemas import (
    UserProfile, UserPrefsResponse, UserPrefsUpdate, SavedBasinResponse
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/user", tags=["User"])


@router.get("/me", response_model=UserProfile)
@limiter.limit("20/minute")
async def get_my_profile(
    request: Request,
    user: UserProfileORM = Depends(get_current_user),
):
    """Get the current authenticated user's profile."""
    return user


@router.put("/me", response_model=UserProfile)
@limiter.limit("20/minute")
async def update_my_profile(
    request: Request,
    display_name: str | None = None,
    preferred_role: str | None = None,
    preferred_language: str | None = None,
    user: UserProfileORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update profile information."""
    if display_name is not None:
        user.display_name = display_name
    if preferred_role is not None:
        user.preferred_role = preferred_role
    if preferred_language is not None:
        user.preferred_language = preferred_language
    
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/basins", response_model=list[SavedBasinResponse])
@limiter.limit("20/minute")
async def get_saved_basins(
    request: Request,
    user: UserProfileORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a list of basins the user has saved."""
    result = await session.execute(
        select(SavedBasinORM).where(SavedBasinORM.user_id == user.id)
    )
    return result.scalars().all()


@router.post("/basins/{basin_id}", response_model=SavedBasinResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def save_basin(
    request: Request,
    basin_id: str,
    user: UserProfileORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Save/bookmark a basin."""
    # Check if already saved
    existing = await session.execute(
        select(SavedBasinORM)
        .where(SavedBasinORM.user_id == user.id)
        .where(SavedBasinORM.basin_id == basin_id)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Basin already saved."
        )

    saved_basin = SavedBasinORM(user_id=user.id, basin_id=basin_id)
    session.add(saved_basin)
    await session.commit()
    await session.refresh(saved_basin)
    return saved_basin


@router.delete("/basins/{basin_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def remove_saved_basin(
    request: Request,
    basin_id: str,
    user: UserProfileORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Remove a saved basin."""
    await session.execute(
        delete(SavedBasinORM)
        .where(SavedBasinORM.user_id == user.id)
        .where(SavedBasinORM.basin_id == basin_id)
    )
    await session.commit()


@router.get("/prefs", response_model=UserPrefsResponse)
@limiter.limit("20/minute")
async def get_user_prefs(
    request: Request,
    user: UserProfileORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get user SMS and notification preferences."""
    if not user.prefs:
        # Return defaults if no row exists yet
        return UserPrefsResponse(
            phone_number=None,
            sms_language="en",
            sms_role="general",
            notify_risk_level="HIGH"
        )
    return user.prefs


@router.put("/prefs", response_model=UserPrefsResponse)
@limiter.limit("20/minute")
async def update_user_prefs(
    request: Request,
    prefs_update: UserPrefsUpdate,
    user: UserProfileORM = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update user SMS and notification preferences."""
    if not user.prefs:
        user.prefs = UserPrefsORM(user_id=user.id)
        session.add(user.prefs)
    
    update_data = prefs_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user.prefs, key, value)

    await session.commit()
    await session.refresh(user.prefs)
    return user.prefs
