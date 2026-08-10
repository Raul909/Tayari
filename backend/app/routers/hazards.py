"""
The location-first API.

Everything in Tayari's original API was keyed on `basin_id`, which meant the
product could only answer questions about eight places. These endpoints are
keyed on a coordinate instead, so the question becomes "what threatens where I
am standing?" — which is the question people actually have.

The basin endpoints are untouched and still served. They remain the more
trustworthy answer for the places they cover, because those thresholds are
calibrated against real floods; this is the broader, shallower layer around them.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.hazards import feeds
from app.hazards.advisory import generate_hazard_advisory, sms_text
from app.hazards.context import build_context
from app.hazards.engine import assess_location, global_events
from app.hazards.registry import catalog
from app.limiter import limiter
from app.models.hazards import (
    HazardType,
    LocationHazardProfile,
    LocationRef,
    PlaceResult,
)
from app.models.schemas import Language, UserRole

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_coords(latitude: float, longitude: float) -> None:
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status_code=422, detail="latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status_code=422, detail="longitude must be between -180 and 180")


# ─── Hazard catalog ───────────────────────────────────────────────────────────


@router.get("/hazards/types")
async def hazard_types():
    """
    Every hazard Tayari can assess, with its data sources.

    Served as an endpoint rather than hard-coded in the client so that the list
    of sources a user sees can never drift from the list the backend actually
    queries.
    """
    return {"hazards": catalog()}


# ─── Location assessment ──────────────────────────────────────────────────────


@router.get("/hazards", response_model=LocationHazardProfile)
@limiter.limit("30/minute")
async def assess(
    request: Request,
    lat: float = Query(..., description="Latitude, -90 to 90"),
    lon: float = Query(..., description="Longitude, -180 to 180"),
    name: Optional[str] = Query(None, description="Place name, if the caller already has one"),
    resolve_name: bool = Query(
        True, description="Reverse-geocode the coordinates when no name is supplied"
    ),
):
    """
    Assess every hazard at a location.

    Roughly seven upstream calls on a cold coordinate, gathered concurrently and
    then cached at tiers matched to how fast each feed's truth moves — so a
    repeat visit to the same place is close to free, while an earthquake feed
    three minutes old is never served as current.
    """
    _validate_coords(lat, lon)

    place = LocationRef(latitude=lat, longitude=lon, name=name)

    # The name lookup is cosmetic and runs alongside the hazard work rather than
    # in front of it: every score comes from the coordinates, so a geocoder
    # outage should cost a label and nothing else.
    context_task = build_context(lat, lon)
    if name or not resolve_name:
        ctx = await context_task
    else:
        ctx, resolved = await asyncio.gather(
            context_task, feeds.reverse_geocode(lat, lon), return_exceptions=True
        )
        if isinstance(ctx, BaseException):
            logger.exception(f"Context build failed at ({lat}, {lon}): {ctx}")
            raise HTTPException(status_code=502, detail="Hazard data feeds are unavailable")
        if not isinstance(resolved, BaseException) and resolved is not None:
            place.name = resolved.name
            place.country = resolved.country
            place.country_code = resolved.country_code
            place.admin1 = resolved.admin1

    return await assess_location(lat, lon, place=place, ctx=ctx)


@router.get("/hazards/{hazard}/advisory")
@limiter.limit("20/minute")
async def hazard_advisory(
    request: Request,
    hazard: HazardType,
    lat: float = Query(...),
    lon: float = Query(...),
    name: Optional[str] = Query(None),
    role: UserRole = Query(UserRole.GENERAL),
    language: Language = Query(Language.ENGLISH),
):
    """
    An AI advisory for one hazard at one location, in one language.

    Split from the profile endpoint on purpose. Generating nine advisories in
    nine languages for every page view would burn the LLM quota within minutes
    and make the profile slow for everyone; the reader wants prose for the one
    card they opened.
    """
    _validate_coords(lat, lon)

    place = LocationRef(latitude=lat, longitude=lon, name=name)
    if not name:
        # The advisory names the place in its title and body, so an unnamed
        # location produces "Earthquake — Moderate at your location", which
        # reads as a system that does not know where you are. Cached, so this
        # is nearly always free.
        resolved = await feeds.reverse_geocode(lat, lon)
        if resolved is not None:
            place.name = resolved.name
            place.country = resolved.country
            place.country_code = resolved.country_code
            place.admin1 = resolved.admin1

    profile = await assess_location(lat, lon, place=place)
    risk = next((r for r in profile.hazards if r.hazard == hazard), None)
    if risk is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{hazard.value}' is not a relevant hazard at this location. "
                f"Relevant here: {', '.join(r.hazard.value for r in profile.hazards) or 'none'}"
            ),
        )

    advisory = await generate_hazard_advisory(
        risk=risk, location=profile.location, role=role, language=language
    )
    return {
        "advisory": advisory.model_dump(mode="json"),
        "risk": risk.model_dump(mode="json"),
        "sms_text": sms_text(advisory),
    }


# ─── Live global events ───────────────────────────────────────────────────────


@router.get("/hazards/events/live")
@limiter.limit("30/minute")
async def live_events(
    request: Request,
    min_magnitude: float = Query(4.5, ge=1.0, le=9.0),
    days: int = Query(7, ge=1, le=30),
):
    """
    Significant hazard events worldwide, for the map.

    The magnitude floor defaults to 4.5 because below roughly that the map
    becomes a continuous band tracing every plate boundary, which is a beautiful
    picture of plate tectonics and a useless early-warning display.
    """
    return await global_events(min_magnitude=min_magnitude, days=days)


# ─── Places ───────────────────────────────────────────────────────────────────


@router.get("/places/search", response_model=list[PlaceResult])
@limiter.limit("40/minute")
async def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=120, description="Place name"),
    count: int = Query(8, ge=1, le=20),
):
    """Find a place by name, so a location can be chosen without GPS."""
    return await feeds.search_places(q, count=count)


@router.get("/places/reverse", response_model=Optional[PlaceResult])
@limiter.limit("40/minute")
async def reverse(
    request: Request,
    lat: float = Query(...),
    lon: float = Query(...),
):
    """Name a coordinate. Returns null rather than erroring when unresolvable."""
    _validate_coords(lat, lon)
    return await feeds.reverse_geocode(lat, lon)
