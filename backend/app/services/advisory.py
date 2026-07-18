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
    Language.OROMO: "Afaan Oromoo (Oromo)",
    Language.ARABIC: "Arabic",
    Language.AFAR: "Afar (Qafar af)",
    Language.DINKA: "Dinka (Thuɔŋjäŋ)",
    Language.DAASANACH: "Daasanach",
    Language.LUHYA: "Luhya (Oluluhya)",
    Language.TURKANA: "Turkana (Ŋaturkana)",
}

# Correct, safety-critical flood vocabulary for languages the LLM handles poorly.
# General LLMs mistranslate the word "flood" and the word "people" in several
# East African languages — e.g. rendering "people" as a word meaning
# "propaganda" in Oromo — so we hand the model the right words up front.
FLOOD_GLOSSARY = {
    Language.OROMO: "flood = 'lolaa' (NOT 'dhihaa', which means west); people = 'namoota' (NEVER 'olola', which means propaganda); boats = 'bidiruu' (never 'galaasaa'); schools = 'manneen barnootaa'; health facilities = 'buufataalee fayyaa'; markets = 'gabaa'",
    Language.AMHARIC: "flood = 'ጎርፍ'; people = 'ሰዎች'; boats = 'ጀልባዎች'; schools = 'ትምህርት ቤቶች'; health facilities = 'የጤና ተቋማት'; markets = 'ገበያዎች'",
    Language.ARABIC: "flood = 'فيضان'; people = 'أشخاص'; boats = 'قوارب'; schools = 'مدارس'; health facilities = 'مرافق صحية'; markets = 'أسواق'",
}

ROLE_DESCRIPTIONS = {
    UserRole.FARMER: "a small-scale farmer who grows crops and keeps some livestock near the river",
    UserRole.PASTORALIST: "a pastoralist herder who moves livestock and depends on grazing land near the river",
    UserRole.COUNTY_OFFICER: "a county/district disaster management officer responsible for coordinating emergency response",
    UserRole.COMMUNITY_LEADER: "a village/community leader responsible for informing and organizing their community",
    UserRole.TEACHER: "a school teacher or headmaster responsible for the safety of students and school property",
    UserRole.STUDENT: "a student or young person living near the river",
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

    Tries the Groq API first, falls back to templates if unavailable.

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
    """Generate advisory using Groq API (fast LLM inference) with a Two-Step Pipeline."""
    client = Groq(api_key=settings.groq_api_key)

    features = risk.model_features or {}
    hydrology_lines = []
    if features.get("discharge_current"):
        hydrology_lines.append(f"- River flow now: {features['discharge_current']:.0f} m³/s")
    if features.get("discharge_flood_ratio"):
        hydrology_lines.append(f"- Water is at {features['discharge_flood_ratio'] * 100:.0f}% of the level that floods the plain")
    if features.get("discharge_anomaly"):
        hydrology_lines.append(f"- Flow vs normal for this time of year: {features['discharge_anomaly']:.1f}× the historical median")
    if features.get("discharge_trend_3d") is not None:
        trend = features["discharge_trend_3d"]
        direction = "RISING" if trend > 0 else ("FALLING" if trend < 0 else "STEADY")
        hydrology_lines.append(f"- 3-day trend: {direction} ({trend:+.0f} m³/s per day)")
    if features.get("discharge_forecast_max"):
        hydrology_lines.append(f"- Highest forecast flow in next 7 days: {features['discharge_forecast_max']:.0f} m³/s")
    hydrology = "\n".join(hydrology_lines) if hydrology_lines else "- (no gauge detail available)"

    peak_day = (
        max(range(len(risk.probabilities_7day)), key=lambda i: risk.probabilities_7day[i]) + 1
        if risk.probabilities_7day else None
    )

    # STEP 1: Generate Base Advisory in English
    english_prompt = f"""You are the advisory writer for Tayari, a flood early-warning system for East Africa.
SITUATION — {basin_name} ({river_name}, {country}), {datetime.utcnow():%d %b %Y}:
- Risk level: {risk.risk_level.value} | Probability of flooding (next 3 days): {risk.probability * 100:.0f}%
- Day-by-day probability (next 7 days): {', '.join(f'D{i+1}: {p*100:.0f}%' for i, p in enumerate(risk.probabilities_7day))}
- Highest-risk day: {'Day ' + str(peak_day) if peak_day else 'unknown'} | Estimated days until flood threshold is crossed: {risk.threshold_exceedance_days if risk.threshold_exceedance_days is not None else 'not expected in forecast window'}

RIVER BEHAVIOUR:
{hydrology}

EXPOSURE (within the {impact.flood_zone_km} km flood zone):
- {impact.estimated_population_at_risk:,} people, {impact.schools_at_risk} schools, {impact.clinics_at_risk + impact.hospitals_at_risk} health facilities, {impact.markets_at_risk} markets

READER: {ROLE_DESCRIPTIONS[role]}. Write in English.
RULES:
1. TITLE — max 10 words, specific to this river and moment, not a generic label.
2. BODY — 3–5 short sentences. Lead with the single most important fact. Give the danger window as concrete days ("between Thursday and Saturday", "within 2 days"), not vague soon-language. Translate one or two numbers into meaning a non-expert feels (e.g. "the river is already carrying twice its normal water"). Never dump all the statistics. No jargon, no panic, no exclamation marks.
3. ACTIONS — 3 to 5, ordered by urgency. Each starts with a verb, is doable within 24–48 hours with local resources, and is tailored to the reader's role (a farmer moves grain and livestock; an officer pre-positions boats and alerts clinics). At most ONE information-type action. Banned phrases: "stay informed", "be prepared", "monitor the situation", "stay tuned", "remain vigilant".
4. Tone must match risk. If the trend is FALLING or the risk is easing, say so honestly.

Format your response EXACTLY as:
TITLE: [title]
BODY: [body paragraph]
ACTIONS:
- [action 1]
- [action 2]
- [action 3]
"""
    response_en = await asyncio.to_thread(
        client.chat.completions.create,
        model=settings.groq_model,
        messages=[{"role": "user", "content": english_prompt}],
        max_tokens=1024,
        temperature=0.7,
    )
    english_text = response_en.choices[0].message.content.strip()
    
    if language == Language.ENGLISH:
        final_text = english_text
    else:
        final_text = None

        # STEP 2a: Prefer HF NLLB-200 for the languages it covers — it's built
        # for these low-resource languages and avoids the cross-language token
        # leaks the general LLM occasionally produces. Any failure falls through
        # to the Groq translator below, so behaviour never regresses. Imported
        # lazily (like voice) so `requests` never becomes a startup dependency.
        from app.services import hf_translate

        if hf_translate.supports(language):
            try:
                final_text = await _translate_via_nllb(english_text, language)
            except Exception as e:
                logger.warning(
                    f"NLLB translation failed for {language}; falling back to Groq: {e}"
                )
                final_text = None

        # STEP 2b: Groq translation — the fallback, and the only path for
        # languages NLLB doesn't cover (Afar, Daasanach, Luhya, Turkana).
        if final_text is None:
            final_text = await _translate_with_groq(client, english_text, language)

        # STEP 3: Oromo safety net — applies to whichever translator ran, so a
        # catastrophic mistranslation ("dhihaa"=west, "olola"=propaganda) can
        # never reach the reader. Replaces are no-ops when the tokens are absent.
        if language == Language.OROMO:
            final_text = (
                final_text.replace("dhihaa", "lolaa").replace("Dhihaa", "Lolaa")
                .replace("olola", "namoota").replace("Olola", "Namoota")
            )

    advisory = _parse_advisory_response(final_text, risk, role, language, ai_generated=True)
    
    # Check for custom voice note or generate TTS
    from app.services.voice import get_or_generate_voice_note
    advisory = await get_or_generate_voice_note(advisory)

    return advisory


def _split_advisory_text(text: str) -> tuple[str, str, list[str]]:
    """
    Pull the title, body, and action lines out of a TITLE/BODY/ACTIONS block.

    Shares the parsing rules of _parse_advisory_response but returns the raw
    strings so each can be translated on its own (NLLB is a sentence-level model
    and mangles the structured labels if handed the whole block at once).
    """
    title, body, actions = "", "", []
    current = None
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line[6:].strip()
            current = "title"
        elif line.upper().startswith("BODY:"):
            body = line[5:].strip()
            current = "body"
        elif line.upper().startswith("ACTIONS:"):
            current = "actions"
        elif current == "body" and line and not line.startswith("-"):
            body += " " + line
        elif current == "actions" and line.startswith("-"):
            actions.append(line[1:].strip())
        elif current == "actions" and line:
            actions.append(line)
    return title, body, actions


async def _translate_via_nllb(english_text: str, language: Language) -> str:
    """
    Translate an English advisory into `language` with NLLB, field by field,
    then rebuild the TITLE/BODY/ACTIONS block (labels stay English so the
    downstream parser still works). Raises if the English text can't be parsed
    or NLLB fails — the caller then falls back to the Groq translator.
    """
    from app.services import hf_translate

    title, body, actions = _split_advisory_text(english_text)
    if not title and not body:
        raise RuntimeError("Could not parse English advisory for NLLB translation")

    fields = [title, body, *actions]
    translated = await hf_translate.translate_fields(fields, language)
    t_title, t_body, t_actions = translated[0], translated[1], translated[2:]

    lines = [f"TITLE: {t_title}", f"BODY: {t_body}", "ACTIONS:"]
    lines += [f"- {a}" for a in t_actions]
    return "\n".join(lines)


async def _translate_with_groq(client, english_text: str, language: Language) -> str:
    """Translate an English advisory into `language` via the Groq LLM."""
    glossary = FLOOD_GLOSSARY.get(language, "")
    translate_prompt = f"""Translate the following flood advisory into natural, fluent {LANGUAGE_NAMES[language]}.
RULES:
1. Translate every word of the content. Do NOT leave any English words (like Thursday or Saturday) in the output.
2. Keep all numbers as digits exactly as given (e.g. 50,000; 126%). Never spell them out.
3. Keep the labels "TITLE:", "BODY:", and "ACTIONS:" in English exactly as shown. Only translate the text after them.
4. IMPORTANT VOCABULARY TO USE strictly (failure to use these is life-threatening): {glossary}
"""
    if language == Language.OROMO:
        translate_prompt += """
Example translation for Oromo:
English:
TITLE: Flood Warning — Omo River (High Level)
BODY: Omo River discharge has reached 126% and may cross the flood threshold within one day (Thursday to Saturday). In the danger zone are 50,000 people, 7 schools, 4 health facilities, and 4 markets.
ACTIONS:
- Prepare boats and ambulances in advance.

Oromo Translation:
TITLE: Akeekkachiisa Lolaa — Laga Omoo (Sadarkaa Ol'aanaa)
BODY: Dhangala'iinsi Laga Omoo %126 gahee, guyyaa tokko keessatti daangaa lolaa darbuu danda'a (Kamisa hanga Sanbataa). Naannoo balaa keessa namoonni 50,000, manneen barnootaa 7, buufataalee fayyaa 4, fi gabaan 4 argamu.
ACTIONS:
- Bidiruuwwanii fi ambulaansota dursanii qopheessaa.
"""
    translate_prompt += f"""

Source Advisory in English:
{english_text}"""

    response_tl = await asyncio.to_thread(
        client.chat.completions.create,
        model=settings.groq_model,
        messages=[{"role": "user", "content": translate_prompt}],
        max_tokens=1024,
        temperature=0.3,
    )
    return response_tl.choices[0].message.content.strip()


def _parse_advisory_response(
    text: str,
    risk: FloodRiskScore,
    role: UserRole,
    language: Language,
    ai_generated: bool = False,
) -> Advisory:
    """Parse the LLM response into an Advisory object."""
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
        ai_generated=ai_generated,
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
    Template-based advisory fallback when the LLM is unavailable.
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
        UserRole.TEACHER: {
            Language.ENGLISH: [
                "Dismiss students early so they can walk home safely before waters rise",
                "Move school records, books, and computers to the highest floor or shelves",
                f"Keep children away from the {river_name} and flooded drainage ditches",
                "Communicate with parents about emergency pickup points",
                "Turn off main electricity switches before leaving the school building",
            ],
            Language.SOMALI: [
                "Ardayda xilli hore sii daa si ay ammaan ugu gaaraan guryahooda",
                "Diiwaanka iskuulka, buugaagta, iyo kombiyuutarada gee dabaqa ugu sarreeya",
                f"Carruurta ka fogee {river_name} iyo meelaha daadku maro",
                "Waalidiinta la socodsii meelaha carruurta loogu yimaado xilliga gurmadka",
                "Dami korontada guud ee iskuulka inta aadan bixin",
            ],
            Language.SWAHILI: [
                "Waruhusu wanafunzi waende nyumbani mapema kabla ya maji kupanda",
                "Hamishia rekodi za shule, vitabu, na kompyuta kwenye ghorofa ya juu au rafu za juu",
                f"Waweke watoto mbali na {river_name} na mitaro iliyofurika",
                "Wasiliana na wazazi kuhusu maeneo salama ya kuwachukua watoto",
                "Zima swichi kuu ya umeme kabla ya kuondoka shuleni",
            ],
        },
        UserRole.STUDENT: {
            Language.ENGLISH: [
                "Walk home in groups and do not stop to play near the floodwaters",
                f"Never try to cross the {river_name} or flooded roads — water is stronger than it looks",
                "Tell your parents or teacher immediately if you see the water rising quickly",
                "Help carry important light items like documents when your family moves",
                "Stay on high ground and do not drink or swim in floodwater",
            ],
            Language.SOMALI: [
                "Idinkoo koox ah guryaha aada oo ha ku ciyaarina biyaha daadka agtooda",
                f"Weligaa ha isku dayin inaad ka gudubto {river_name} — biyuhu way ka xoog badan yihiin sida ay u muuqdaan",
                "Isla markiiba u sheeg waalidkaa ama macalinkaaga haddii aad aragto biyaha oo kor u kacaya",
                "Caawi qoyskaaga inaad qaado waraaqaha muhiimka ah marka aad guuraysaan",
                "Dhul sare joog oo ha cabin hana ku dabbaalan biyaha daadka",
            ],
            Language.SWAHILI: [
                "Tembeeni kwa vikundi kwenda nyumbani na msicheze karibu na mafuriko",
                f"Usijaribu kuvuka {river_name} — maji yana nguvu sana",
                "Mjulishe mzazi au mwalimu mara moja ukiona maji yakipanda haraka",
                "Saidia kubeba vitu vyepesi na muhimu wakati familia inahama",
                "Kaa kwenye ardhi ya juu na usinywe wala kuogelea kwenye maji ya mafuriko",
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
