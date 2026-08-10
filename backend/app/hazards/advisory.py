"""
Hazard-agnostic advisory generation.

The flood advisory pipeline in `services/advisory.py` is the most carefully
tuned text path in this codebase — a two-step generate-then-translate flow with
a leak detector, a stricter retry, an Oromo safety net for two specific
mistranslations that invert meaning, and a final script sanitizer. That work
exists because a warning that reaches someone in mangled language at the moment
it matters is worse than no warning.

None of that is flood-specific, so this module reuses all of it and supplies
only what changes: the situation description going in, and the fallback text
when the model is unavailable. What is deliberately *not* reused is the flood
prompt itself — telling a model about river discharge when the hazard is an
earthquake produces confident text about the wrong thing.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.hazards.actions import actions_for
from app.hazards.registry import meta
from app.models.hazards import HazardAdvisory, HazardRisk, HazardType, LocationRef
from app.models.schemas import Language, RiskLevel, UserRole
from app.services.advisory import (
    FALLBACK_LANGUAGE,
    HAS_GROQ,
    ROLE_DESCRIPTIONS,
    TranslationQualityError,
    _sanitize_translation,
    _split_advisory_text,
    _translate_with_groq,
)
from app.hazards.cache import TTLCache

logger = logging.getLogger(__name__)

# Six hours matches the flood advisory cache. Hazard situations move slower than
# that in every case except an active rupture, and those carry their own event
# data in the risk object rather than in the prose.
CACHE_TTL_HOURS = 6
_advisory_cache = TTLCache(ttl_seconds=CACHE_TTL_HOURS * 3600, max_entries=1024)
# Templates are served only while the model is unavailable, so they expire fast
# — otherwise one rate-limited minute serves degraded text for six hours.
_template_cache = TTLCache(ttl_seconds=20 * 60, max_entries=512)


def _cache_key(risk: HazardRisk, location: LocationRef, role: UserRole, language: Language) -> str:
    return (
        f"{risk.hazard.value}|{round(location.latitude, 1)},{round(location.longitude, 1)}"
        f"|{risk.risk_level.value}|{role.value}|{language.value}"
    )


async def generate_hazard_advisory(
    risk: HazardRisk,
    location: LocationRef,
    role: UserRole = UserRole.GENERAL,
    language: Language = Language.ENGLISH,
) -> HazardAdvisory:
    """
    Write an advisory for one hazard at one location, in one language, for one
    kind of reader.

    Falls back to human-written templates whenever the model path fails for any
    reason. That fallback is not a degraded afterthought — see
    `hazards/actions.py` — because it runs exactly when the reader most needs
    something useful.
    """
    key = _cache_key(risk, location, role, language)
    cached = _advisory_cache.get(key)
    if cached is not None:
        return cached
    cached_template = _template_cache.get(key)
    if cached_template is not None:
        return cached_template

    if HAS_GROQ and settings.groq_api_key:
        try:
            advisory = await _generate_with_model(risk, location, role, language)
            _advisory_cache.set(key, advisory)
            return advisory
        except Exception as e:  # noqa: BLE001
            logger.error(f"Hazard advisory generation failed for {risk.hazard.value}: {e}")

    advisory = _template_advisory(risk, location, role, language)
    _template_cache.set(key, advisory)
    return advisory


# ─── Model path ───────────────────────────────────────────────────────────────


def _situation_block(risk: HazardRisk, location: LocationRef) -> str:
    """
    Describe the hazard to the model in the same terms the reader will see.

    Only the indicators the assessor actually produced are listed. Inventing a
    field the assessor left empty — a wind speed for an earthquake, a magnitude
    for a drought — is how a model ends up writing fluent, specific and false
    text.
    """
    m = meta(risk.hazard)
    where = location.name or f"{location.latitude:.2f}, {location.longitude:.2f}"
    if location.country:
        where = f"{where}, {location.country}"

    lines = [
        f"HAZARD: {m.label} at {where}, {datetime.now(timezone.utc):%d %b %Y}",
        f"- Risk level: {risk.risk_level.value} (score {risk.score:.2f} of 1.00)",
        f"- Assessment: {risk.headline}",
        f"- How fast it arrives: {m.onset.value} | Warning time: {risk.lead_time or m.lead_time}",
    ]
    if not m.forecastable:
        lines.append(
            "- IMPORTANT: this hazard cannot be forecast. Do not write anything that "
            "implies a prediction, a timing, or a probability of it happening."
        )
    if risk.indicators:
        lines.append("MEASUREMENTS:")
        for ind in risk.indicators:
            detail = f" ({ind.detail})" if ind.detail else ""
            lines.append(f"- {ind.label}: {ind.value}{detail}")
    if risk.events:
        lines.append("RECENT EVENTS:")
        for event in risk.events[:3]:
            when = event.occurred_at.strftime("%d %b %H:%M UTC") if event.occurred_at else "recently"
            distance = f", {event.distance_km:.0f} km away" if event.distance_km is not None else ""
            lines.append(f"- {event.title}{distance} — {when}")
    if risk.summary:
        lines.append(f"CONTEXT: {risk.summary}")
    return "\n".join(lines)


async def _generate_with_model(
    risk: HazardRisk,
    location: LocationRef,
    role: UserRole,
    language: Language,
) -> HazardAdvisory:
    """Generate in English, then translate — the same two-step flow as floods."""
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    m = meta(risk.hazard)

    prompt = f"""You are the advisory writer for Tayari, a multi-hazard early-warning system used by people who live with these hazards.

{_situation_block(risk, location)}

READER: {ROLE_DESCRIPTIONS[role]}. Write in English.

RULES:
1. TITLE — max 10 words, specific to this hazard and this moment. Not a generic label.
2. BODY — 3 to 5 short sentences. Lead with the single most important fact. Turn one or two of the measurements into something a non-expert can feel. Never list all the numbers. No jargon, no panic, no exclamation marks.
3. ACTIONS — 3 to 5, ordered by urgency. Each starts with a verb and is doable in the next 24-48 hours with what the reader already has. Tailor them to the reader's role. At most ONE information-seeking action. Banned phrases: "stay informed", "be prepared", "monitor the situation", "stay tuned", "remain vigilant".
4. Match the tone to the risk level. At LOW, say plainly that nothing is happening and keep the actions to preparation worth doing anyway — do not manufacture urgency.
5. Never claim this hazard has been predicted if the situation says it cannot be forecast. Write about readiness and about what has already happened.
6. Never tell the reader to ignore an official warning from their own authorities.

Format your response EXACTLY as:
TITLE: [title]
BODY: [body paragraph]
ACTIONS:
- [action 1]
- [action 2]
- [action 3]
"""

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7,
    )
    english_text = response.choices[0].message.content.strip()

    delivered = language
    final_text = english_text

    if language != Language.ENGLISH:
        try:
            final_text = await _translate_with_groq(client, english_text, language)
        except TranslationQualityError as e:
            # The model cannot write this language well enough to be safe. An
            # accurate advisory in a regional lingua franca beats mother-tongue
            # nonsense when the subject is what to do to survive.
            delivered = FALLBACK_LANGUAGE.get(language, Language.ENGLISH)
            logger.warning(
                f"Unusable {language} hazard translation ({e.leaks[:4]}); delivering {delivered}"
            )
            if delivered == Language.ENGLISH:
                final_text = english_text
            else:
                try:
                    final_text = await _translate_with_groq(client, english_text, delivered)
                except TranslationQualityError:
                    delivered, final_text = Language.ENGLISH, english_text

        if delivered == Language.OROMO:
            # The same two mistranslations the flood path guards: "dhihaa" means
            # west, and "olola" means propaganda. Both have appeared in place of
            # "flood" and "people".
            final_text = (
                final_text.replace("dhihaa", "lolaa")
                .replace("Dhihaa", "Lolaa")
                .replace("olola", "namoota")
                .replace("Olola", "Namoota")
            )
        final_text = _sanitize_translation(final_text, delivered)

    title, body, actions = _split_advisory_text(final_text)

    return HazardAdvisory(
        hazard=risk.hazard,
        risk_level=risk.risk_level,
        latitude=location.latitude,
        longitude=location.longitude,
        place_name=location.name,
        role=role,
        language=delivered,
        requested_language=language,
        title=title or f"{m.label} — {risk.risk_level.value}",
        body=body or risk.summary or risk.headline,
        actions=actions or actions_for(
            risk.hazard, risk.risk_level, role, has_active_event=risk.event_driven
        ),
        ai_generated=True,
        generated_at=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS),
    )


# ─── Template path ────────────────────────────────────────────────────────────


_LEVEL_OPENERS = {
    RiskLevel.EXTREME: "This is the level at which people are hurt. Act now rather than waiting for more certainty.",
    RiskLevel.HIGH: "Conditions are dangerous. The steps below are worth doing today, not tomorrow.",
    RiskLevel.MODERATE: "Worth acting on. Nothing here needs panic, but the preparation below takes an hour and pays for itself.",
    RiskLevel.LOW: "Nothing is happening right now. The steps below are the ones worth having done in advance.",
}


def _template_advisory(
    risk: HazardRisk,
    location: LocationRef,
    role: UserRole,
    language: Language,
) -> HazardAdvisory:
    """
    The fallback when the model is unavailable.

    Always written in English regardless of the language asked for, and says so
    via `requested_language`. Machine-translating safety instructions without
    the leak detection and retry that the model path provides is precisely the
    failure this system was built to avoid — better an advisory the reader can
    tell is in the wrong language than one that is quietly wrong in the right
    one.
    """
    m = meta(risk.hazard)
    where = location.name or "your location"

    body = f"{risk.headline}. {risk.summary}".strip()
    opener = _LEVEL_OPENERS[risk.risk_level]
    if opener not in body:
        body = f"{body} {opener}"

    return HazardAdvisory(
        hazard=risk.hazard,
        risk_level=risk.risk_level,
        latitude=location.latitude,
        longitude=location.longitude,
        place_name=location.name,
        role=role,
        language=Language.ENGLISH,
        requested_language=language,
        title=f"{m.label} — {risk.risk_level.value.title()} at {where}",
        body=body,
        actions=actions_for(
            risk.hazard, risk.risk_level, role, has_active_event=risk.event_driven
        ),
        ai_generated=False,
        generated_at=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc) + timedelta(minutes=20),
    )


def sms_text(advisory: HazardAdvisory, limit: int = 480) -> str:
    """
    Flatten an advisory into SMS.

    Truncation drops whole actions from the end rather than cutting mid-sentence:
    a message ending "move livestock to hi" is worse than one action shorter.
    """
    header = f"{advisory.title}\n\n{advisory.body}"
    lines = [header]
    for action in advisory.actions:
        candidate = "\n".join(lines + [f"• {action}"])
        if len(candidate) > limit:
            break
        lines.append(f"• {action}")
    return "\n".join(lines)[:limit]
