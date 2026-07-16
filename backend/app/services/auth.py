"""
Authentication service for verifying Supabase JWTs.
"""

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db import get_session
from app.models.db_models import UserProfileORM

logger = logging.getLogger(__name__)


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]


async def verify_supabase_token(token: str) -> dict:
    """
    Verify the Supabase JWT token using the configured secret.
    Returns the decoded token payload.
    """
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret not configured in the backend.",
        )
    
    try:
        # Supabase uses HS256 algorithm with the provided JWT secret
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> UserProfileORM:
    """
    FastAPI dependency to get the current authenticated user.
    If the token is valid but the user doesn't exist in our profile table,
    we create a default profile on the fly (JIT provisioning).
    """
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = await verify_supabase_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    # Fetch user profile from database
    result = await session.execute(
        select(UserProfileORM).where(UserProfileORM.id == user_id)
    )
    user = result.scalars().first()

    if not user:
        # Just-In-Time provisioning: Create the user profile automatically
        email = payload.get("email", "")
        # Use the part before @ as the default display name if email exists
        default_name = email.split("@")[0] if email else "User"
        
        user = UserProfileORM(
            id=user_id,
            display_name=default_name,
            preferred_role="general",
            preferred_language="en",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Optional[UserProfileORM]:
    """
    FastAPI dependency to optionally get the current user.
    Returns None if no token is provided or if it's invalid.
    """
    token = get_token_from_request(request)
    if not token:
        return None
    
    try:
        payload = await verify_supabase_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        result = await session.execute(
            select(UserProfileORM).where(UserProfileORM.id == user_id)
        )
        return result.scalars().first()
    except HTTPException:
        return None
