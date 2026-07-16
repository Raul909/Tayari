"""
AI Advisory Generator — uses Groq (fast LLM inference) or falls back to template-based generation.

Generates plain-language, role-specific, multilingual advisories that tell people
what to DO, not just what the forecast IS. This is the "communicated" layer —
closing the gap between information generated and information acted upon.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.models.schemas import (
    Advisory, FloodRiskScore, ImpactAssessment, RiskLevel, UserRole, Language
)

logger = logging.getLogger(__name__)

# Try importing Groq
try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    logger.warning("Groq SDK not installed — using template-based advisories")

# Advisory cache (risk_level + role + language → advisory)
_advisory_cache: dict[str, tuple[Advisory, datetime]] = {}
CACHE_TTL_HOURS = 6


LANGUAGE_NAMES = {
    Language.ENGLISH: "English",
    Language.SOMALI: "Somali",
    Language.SWAHILI: "Swahili",
    Language.AMHARIC: "Amharic",
    Language.OROMO: "Oromo",
}

ROLE_DESCRIPTIONS = {
    UserRole.FARMER: "a small-scale farmer who grows crops and keeps some livestock near the river",
    UserRole.PASTORALIST: "a pastoralist herder who moves livestock and depends on grazing land near the river",
    UserRole.COUNTY_OFFICER: "a county/district disaster management officer responsible for coordinating emergency response",
    UserRole.COMMUNITY_LEADER: "a village/community leader responsible for informing and organizing their community",
    UserRole.GENERAL: "a resident living near the river floodplain",
}


async def generate_advisory(
    risk: FloodRiskScore,
    impact: ImpactAssessment,
    basin_name: str,
    river_name: str,
    country: str,
    role: UserRole = UserRole.GENERAL,
    language: Language = Language.ENGLISH,
) -> Advisory:
    """
    Generate an AI-powered advisory for a specific audience.

    Tries Claude API first, falls back to templates if unavailable.

    Args:
        risk: Current flood risk score
        impact: Impact assessment data
        basin_name: Human-readable basin name
        river_name: River name
        country: Country name
        role: Target audience role
        language: Target language

    Returns:
        Advisory with title, body, and specific actions
    """
    # Check cache
    cache_key = f"{risk.basin_id}_{risk.risk_level}_{role}_{language}"
    if cache_key in _advisory_cache:
        cached_advisory, cached_time = _advisory_cache[cache_key]
        if datetime.utcnow() - cached_time < timedelta(hours=CACHE_TTL_HOURS):
            return cached_advisory

    # Try Groq API (fast LLM inference)
    if HAS_GROQ and settings.groq_api_key:
        try:
            advisory = await _generate_with_groq(
                risk, impact, basin_name, river_name, country, role, language
            )
            _advisory_cache[cache_key] = (advisory, datetime.utcnow())
            return advisory
        except Exception as e:
            logger.error(f"Groq advisory generation failed: {e}")

    # Fall back to templates
    advisory = _generate_template_advisory(
        risk, impact, basin_name, river_name, country, role, language
    )
    _advisory_cache[cache_key] = (advisory, datetime.utcnow())
    return advisory


async def _generate_with_groq(
    risk: FloodRiskScore,
    impact: ImpactAssessment,
    basin_name: str,
    river_name: str,
    country: str,
    role: UserRole,
    language: Language,
) -> Advisory:
    """Generate advisory using Groq API (fast LLM inference)."""
    client = Groq(api_key=settings.groq_api_key)

    prompt = f"""You are Tayari, an AI flood early-warning system for East Africa. Generate a flood advisory.

CONTEXT:
- Location: {basin_name}, {river_name}, {country}
- Flood Risk Level: {risk.risk_level.value}
- Flood Probability (next 3 days): {risk.probability * 100:.0f}%
- Estimated Days Until Threshold: {risk.threshold_exceedance_days or 'Unknown'}
- 7-Day Probabilities: {', '.join(f'Day {i+1}: {p*100:.0f}%' for i, p in enumerate(risk.probabilities_7day))}

IMPACT:
- Population at risk: ~{impact.estimated_population_at_risk:,}
- Schools at risk: {impact.schools_at_risk}
- Health facilities at risk: {impact.clinics_at_risk + impact.hospitals_at_risk}
- Markets at risk: {impact.markets_at_risk}
- Flood zone: {impact.flood_zone_km} km from river

TARGET AUDIENCE:
- This advisory is for {ROLE_DESCRIPTIONS[role]}
- Write in {LANGUAGE_NAMES[language]}

INSTRUCTIONS:
1. Write a short TITLE (max 10 words). Match the tone to the risk level:
   LOW = calm reassurance, MODERATE = watchful, HIGH/EXTREME = urgent.
2. Write a BODY paragraph (3-5 sentences) that is:
   - In simple, clear language a non-expert can understand — no jargon, no panic
   - Grounded in the numbers: reference the {risk.probability * 100:.0f}% probability and,
     if given, the day the flood threshold may be crossed
   - Specific about timing ("within 2 days", "before the weekend")
   - Specific about what to do (not just "be prepared")
   - For LOW risk, reassure and give light preparedness steps — do NOT tell people to evacuate
3. List 3-5 concrete ACTIONS the person can actually do, tailored to their role and location.
   Order them by what to do first. Keep each action to one short sentence.

Format your response EXACTLY as:
TITLE: [title]
BODY: [body paragraph]
ACTIONS:
- [action 1]
- [action 2]
- [action 3]

CRITICAL: Keep the labels "TITLE:", "BODY:", and "ACTIONS:" in English exactly as shown — they are parsing markers. Write only the CONTENT (the title text, body text, and each action) in {LANGUAGE_NAMES[language]}. Do not translate or omit the labels, and do not add any other English text."""

    # The Groq SDK client is synchronous; run it off the event loop
    # so the generation doesn't block other concurrent requests.
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7,
    )

    # Parse the response
    text = response.choices[0].message.content
    return _parse_advisory_response(text, risk, role, language)


def _parse_advisory_response(
    text: str,
    risk: FloodRiskScore,
    role: UserRole,
    language: Language,
) -> Advisory:
    """Parse Claude's response into an Advisory object."""
    title = ""
    body = ""
    actions = []

    lines = text.strip().split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line[6:].strip()
            current_section = "title"
        elif line.upper().startswith("BODY:"):
            body = line[5:].strip()
            current_section = "body"
        elif line.upper().startswith("ACTIONS:"):
            current_section = "actions"
        elif current_section == "body" and line and not line.startswith("-"):
            body += " " + line
        elif current_section == "actions" and line.startswith("-"):
            actions.append(line[1:].strip())
        elif current_section == "actions" and line:
            actions.append(line)

    if not title:
        title = f"Flood Warning — {risk.risk_level.value}"
    if not body:
        body = text[:500]
    if not actions:
        actions = ["Monitor official channels for updates"]

    return Advisory(
        basin_id=risk.basin_id,
        risk_level=risk.risk_level,
        role=role,
        language=language,
        title=title,
        body=body.strip(),
        actions=actions,
        generated_at=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS),
    )


def _generate_template_advisory(
    risk: FloodRiskScore,
    impact: ImpactAssessment,
    basin_name: str,
    river_name: str,
    country: str,
    role: UserRole,
    language: Language,
) -> Advisory:
    """
    Template-based advisory fallback when Claude is unavailable.
    Supports English, Somali, and Swahili with pre-written templates.
    """
    days = risk.threshold_exceedance_days or 3

    # Role-specific actions
    role_actions = {
        UserRole.FARMER: {
            Language.ENGLISH: [
                f"Move stored grain and seeds to high ground immediately",
                f"Relocate livestock away from the {river_name} floodplain",
                "Harvest any crops that are ready — do not wait",
                "Stock clean drinking water for your family (3-day supply)",
                "Keep important documents in a waterproof bag",
            ],
            Language.SOMALI: [
                f"Dhaqso u guur hadhuudhka iyo abuurka meel sare",
                f"Xoolaha ka fogee bannaanka daadka ee {river_name}",
                "Soo gooso wixii beeraha ah ee diyaar ah — ha sugin",
                "Kaydi biyo nadiif ah oo qoyskiina ku filan 3 maalmood",
                "Dokumiintiyada muhiimka ah ku kaydi boorso biyo diidda ah",
            ],
            Language.SWAHILI: [
                f"Hamishia nafaka na mbegu kwenye ardhi ya juu mara moja",
                f"Ondoa mifugo mbali na eneo la mafuriko la {river_name}",
                "Vuna mazao yoyote yaliyo tayari — usisubiri",
                "Hifadhi maji safi ya kunywa kwa familia yako (siku 3)",
                "Weka nyaraka muhimu kwenye mfuko usioweza kupenyeza maji",
            ],
        },
        UserRole.PASTORALIST: {
            Language.ENGLISH: [
                f"Move your herds now to known high-ground grazing away from the {river_name}",
                f"Do not cross the {river_name} or flooded crossings with livestock",
                "Water and rest animals early, and keep the herd together as water rises",
                "Store fodder and veterinary supplies on raised ground",
                "Pass the warning to other herders sharing your grazing route",
            ],
            Language.SOMALI: [
                f"Hadda xoolahaaga u guuri daaqsin dhul sare oo ka fog {river_name}",
                f"Ha kula gudbin xoolaha {river_name} ama meelaha daadku qabtay",
                "Waraabi oo nasi xoolaha goor hore, xeradana isku hay marka biyuhu kordhayaan",
                "Kaydi cunto xoolaad iyo daawooyin xoolaad meel sarreysa",
                "U gudbi digniinta xoolo-dhaqatada kale ee daaqa kula wadaaga",
            ],
            Language.SWAHILI: [
                f"Hamisha mifugo yako sasa kwenye malisho ya ardhi ya juu mbali na {river_name}",
                f"Usivuke {river_name} au vivuko vilivyofurika ukiwa na mifugo",
                "Nywesha na pumzisha wanyama mapema, na weka kundi pamoja maji yanapopanda",
                "Hifadhi malisho na dawa za mifugo kwenye sehemu iliyoinuka",
                "Peleka onyo kwa wafugaji wengine mnaoshiriki njia ya malisho",
            ],
        },
        UserRole.COMMUNITY_LEADER: {
            Language.ENGLISH: [
                f"Alert every household near the {river_name}, starting with elderly, disabled and pregnant residents",
                "Agree an assembly point on high ground and the safest route to reach it",
                "Identify who has boats, vehicles or radios and put them on standby",
                "Relay the warning through mosque/church announcements and local FM radio",
                "Keep a simple list of who has moved and who still needs help",
            ],
            Language.SOMALI: [
                f"Ogeysii qoys kasta oo u dhow {river_name}, laga bilaabo waayeelka, naafada iyo dumarka uurka leh",
                "Ku heshiiya meel lagu kulmo oo dhul sare ah iyo jidka ugu ammaan badan ee loo maro",
                "Ogow cida haysata doonyo, gawaari ama raadiyayaal, oo diyaar u ah",
                "Ku gudbi digniinta dhawaaqa masaajidka/kaniisadda iyo raadiyaha FM-ka degaanka",
                "Hayso liis fudud oo ah cida guurtay iyo cida weli caawimaad u baahan",
            ],
            Language.SWAHILI: [
                f"Arifu kila kaya iliyo karibu na {river_name}, ukianza na wazee, walemavu na wajawazito",
                "Kubalianeni sehemu ya kukusanyika kwenye ardhi ya juu na njia salama ya kufika",
                "Tambua wenye mashua, magari au redio na uwaweke tayari",
                "Peleka onyo kupitia matangazo ya msikiti/kanisa na redio za FM za eneo",
                "Weka orodha rahisi ya waliohama na wanaohitaji msaada",
            ],
        },
        UserRole.COUNTY_OFFICER: {
            Language.ENGLISH: [
                f"Activate the county emergency operations center",
                f"Pre-position evacuation boats and supplies at {basin_name}",
                f"Alert health facilities to prepare for waterborne disease surge",
                f"Coordinate with ICPAC and national disaster authority",
                f"Issue public advisory through local FM radio and community leaders",
            ],
            Language.SOMALI: [
                "Hawlgeli xarunta qorshaha gurmadka degmada",
                f"Diyaari doonyaha qaxootiga iyo saadkaaga {basin_name}",
                "Dig xarumaha caafimaadka inay u diyaargaroobaan cudurrada biyaha",
                "La wadaag ICPAC iyo hay'adda qaran ee masiibada",
                "Soo saar digniin dadweyne oo ku dhex mar raadiyaha FM-ka",
            ],
            Language.SWAHILI: [
                "Anzisha kituo cha operesheni za dharura cha kaunti",
                f"Weka mashua ya uokoaji na vifaa katika {basin_name}",
                "Arifu vituo vya afya kujiandaa kwa magonjwa ya maji",
                "Wasiliana na ICPAC na mamlaka ya kitaifa ya maafa",
                "Toa ushauri wa umma kupitia redio za FM na viongozi wa jamii",
            ],
        },
        UserRole.GENERAL: {
            Language.ENGLISH: [
                f"Stay away from the {river_name} banks — water can rise suddenly",
                "Prepare an emergency bag with food, water, medicine, and documents",
                "Know your evacuation route to the nearest high ground",
                "Listen to local FM radio for official updates",
                "Help elderly and disabled neighbors prepare to move",
            ],
            Language.SOMALI: [
                f"Ka fogow xeebaha {river_name} — biyuhu si kedis ah bay u kor kacaan",
                "Diyaari boorso gurmad oo ay ku jiraan cunto, biyo, daawo, iyo dokumiintiyada",
                "Ogow wadada qaxootiga ee ugu dhow dhulka sare",
                "Dhageyso raadiyaha FM-ka ee degaanka wixii war cusub ah",
                "Caawi jaarka waayeelka ah iyo naafada inay u diyaargaroobaan guuritaanka",
            ],
            Language.SWAHILI: [
                f"Kaa mbali na kingo za {river_name} — maji yanaweza kupanda ghafla",
                "Andaa mfuko wa dharura wenye chakula, maji, dawa na nyaraka",
                "Jua njia yako ya uokoaji hadi sehemu ya juu iliyo karibu",
                "Sikiliza redio za FM za eneo lako kwa taarifa rasmi",
                "Wasaidie majirani wazee na walemavu kujiandaa kuondoka",
            ],
        },
    }

    # Get actions for the role, falling back to GENERAL if the role has no
    # template, then to English if the language has no translation.
    actions_dict = role_actions.get(role, role_actions[UserRole.GENERAL])
    actions = actions_dict.get(language, actions_dict.get(Language.ENGLISH, []))

    # Build title and body
    titles = {
        Language.ENGLISH: {
            RiskLevel.EXTREME: f"⚠️ EXTREME FLOOD WARNING — {river_name}",
            RiskLevel.HIGH: f"🔴 HIGH FLOOD RISK — {river_name}",
            RiskLevel.MODERATE: f"🟡 FLOOD WATCH — {river_name}",
            RiskLevel.LOW: f"🟢 Normal Conditions — {river_name}",
        },
        Language.SOMALI: {
            RiskLevel.EXTREME: f"⚠️ DIGNIIN DAAD AH OO AADKA AH — {river_name}",
            RiskLevel.HIGH: f"🔴 KHATAR DAAD SARE — {river_name}",
            RiskLevel.MODERATE: f"🟡 FEEJIGNAAN DAAD — {river_name}",
            RiskLevel.LOW: f"🟢 Xaalad Caadi — {river_name}",
        },
        Language.SWAHILI: {
            RiskLevel.EXTREME: f"⚠️ ONYO KALI LA MAFURIKO — {river_name}",
            RiskLevel.HIGH: f"🔴 HATARI KUBWA YA MAFURIKO — {river_name}",
            RiskLevel.MODERATE: f"🟡 TAHADHARI YA MAFURIKO — {river_name}",
            RiskLevel.LOW: f"🟢 Hali ya Kawaida — {river_name}",
        },
    }

    bodies = {
        Language.ENGLISH: (
            f"The {river_name} at {basin_name} has a {risk.probability * 100:.0f}% probability of flooding "
            f"within the next {days} days. Approximately {impact.estimated_population_at_risk:,} people, "
            f"{impact.schools_at_risk} schools, and {impact.clinics_at_risk + impact.hospitals_at_risk} "
            f"health facilities are in the projected {impact.flood_zone_km} km flood zone. "
            f"Take protective action now."
        ),
        Language.SOMALI: (
            f"Webiga {river_name} ee {basin_name} wuxuu leeyahay {risk.probability * 100:.0f}% "
            f"suurtagalnimo in daad yimaado {days} maalmood gudahood. Qiyaas ahaan "
            f"{impact.estimated_population_at_risk:,} qof, {impact.schools_at_risk} dugsiyo, iyo "
            f"{impact.clinics_at_risk + impact.hospitals_at_risk} xarumo caafimaad ayaa ku jira "
            f"aagga daadka ee {impact.flood_zone_km} km. Hadda tallaabo qaad."
        ),
        Language.SWAHILI: (
            f"Mto {river_name} katika {basin_name} una uwezekano wa {risk.probability * 100:.0f}% wa mafuriko "
            f"ndani ya siku {days} zijazo. Takriban watu {impact.estimated_population_at_risk:,}, "
            f"shule {impact.schools_at_risk}, na vituo {impact.clinics_at_risk + impact.hospitals_at_risk} "
            f"vya afya viko katika eneo la mafuriko la km {impact.flood_zone_km}. "
            f"Chukua hatua sasa."
        ),
    }

    title = titles.get(language, titles[Language.ENGLISH]).get(
        risk.risk_level, f"Flood Advisory — {river_name}"
    )
    body = bodies.get(language, bodies[Language.ENGLISH])

    return Advisory(
        basin_id=risk.basin_id,
        risk_level=risk.risk_level,
        role=role,
        language=language,
        title=title,
        body=body,
        actions=actions,
        generated_at=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS),
    )
