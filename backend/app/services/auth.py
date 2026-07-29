"""
Authentication service for verifying Supabase JWTs.
"""

import asyncio
import logging
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db import get_session
from app.models.db_models import UserProfileORM

logger = logging.getLogger(__name__)

# Lazily-built JWKS client (fetches + caches Supabase's public signing keys).
# Used only for asymmetric (ES256/RS256) tokens; created once, reused after.
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and settings.supabase_jwks_url:
        _jwks_client = PyJWKClient(settings.supabase_jwks_url)
    return _jwks_client


def _decode_supabase_token(token: str) -> dict:
    """
    Blocking JWT verification — run in a worker thread. Chooses the verification
    method from the token's own `alg` header:

    - Asymmetric (ES256/RS256/PS*): fetch the matching public key from Supabase's
      JWKS endpoint and verify with it. This is the current Supabase signing model.
    - HS256: verify with the shared SUPABASE_JWT_SECRET (legacy projects).

    Raising here (jwt.* errors, missing config) is turned into the right HTTP
    status by the async caller.
    """
    alg = jwt.get_unverified_header(token).get("alg", "")
    if alg.startswith(("RS", "ES", "PS")):
        client = _get_jwks_client()
        if client is None:
            raise RuntimeError("asymmetric token but SUPABASE_JWKS_URL is not set")
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token, signing_key.key, algorithms=[alg], audience="authenticated"
        )
    # Legacy HS256 shared-secret path.
    if not settings.supabase_jwt_secret:
        raise RuntimeError("HS256 token but SUPABASE_JWT_SECRET is not set")
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]


async def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase JWT and return its decoded payload. Supports both the
    asymmetric (JWKS) and legacy HS256 signing schemes — see _decode_supabase_token.
    """
    if not (settings.supabase_jwks_url or settings.supabase_jwt_secret):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase auth is not configured in the backend "
                   "(set SUPABASE_JWKS_URL or SUPABASE_JWT_SECRET).",
        )

    try:
        # Verification does a (cached) network fetch for JWKS, so keep it off the
        # event loop.
        return await asyncio.to_thread(_decode_supabase_token, token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Invalid signature/audience, unknown key, JWKS unreachable, misconfig —
        # fail closed as 401 rather than leaking which check failed.
        logger.warning(f"Supabase token verification failed: {type(e).__name__}: {e}")
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
