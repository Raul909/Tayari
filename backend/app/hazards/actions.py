"""
Human-written safety actions, one set per hazard.

These are the fallback that runs when the LLM is unavailable — a rate limit, a
Groq outage, a cold start with no key configured. That makes them the most
safety-critical text in the repository, because they are what a person reads at
precisely the moment the clever machinery has failed.

They are therefore written to a stricter standard than the LLM prompt asks for:
every action starts with a verb, is doable in the next day or two with whatever
is already to hand, and is specific enough to act on without further
instruction. "Stay informed" and "remain vigilant" appear nowhere, because
they tell a person nothing they can do.

Each hazard has a routine set (what to arrange before anything happens) and an
elevated set (what to do because something is happening). EXTREME prepends a
single leave-now instruction, since at that level the only decision that matters
is whether to stay.
"""

from app.models.hazards import HazardType
from app.models.schemas import RiskLevel, UserRole

# What to do when the hazard is not currently elevated — preparation that pays
# for itself the one time it is needed.
ROUTINE_ACTIONS: dict[HazardType, list[str]] = {
    HazardType.EARTHQUAKE: [
        "Find the safest spot in each room you use — under a solid table, or against an interior wall away from windows",
        "Move heavy objects off high shelves and secure tall furniture to the wall",
        "Keep sturdy shoes and a torch where you can reach them from your bed in the dark",
        "Agree one out-of-town contact everyone in the family checks in with, since local phone lines fail first",
    ],
    HazardType.TSUNAMI: [
        "Walk your route to high ground or a tall solid building once, so you know it in the dark",
        "Treat strong shaking near the coast as the warning itself — do not wait for an official alert or for the sea to withdraw",
        "Agree a meeting point inland where your household will gather without going back for each other",
        "Keep documents and medicine in one bag you can carry while running",
    ],
    HazardType.VOLCANO: [
        "Find out which evacuation zone you live in and which route leaves it",
        "Keep dust masks (N95 or better) and eye protection for ashfall — ordinary cloth does not filter ash",
        "Store water covered; ash contaminates open tanks and blocks filters",
        "Keep vehicles fuelled, since fuel stations close early in an evacuation",
    ],
    HazardType.FLOOD: [
        "Find out whether your home sits above or below the level the river reached in its worst recent flood",
        "Keep documents, cash and medicine in a waterproof bag on a high shelf",
        "Agree where livestock and equipment go, and who moves them",
        "Identify the route to high ground that does not cross a river or low bridge",
    ],
    HazardType.CYCLONE: [
        "Check the roof for loose sheets and fixings before the season, not during the storm",
        "Identify the strongest room in the house — small, no windows, load-bearing walls",
        "Keep a week of drinking water and any medicine that cannot be replaced quickly",
        "Trim branches that would fall on the house or on power lines",
    ],
    HazardType.EXTREME_HEAT: [
        "Work out which room stays coolest and plan to spend the hottest hours there",
        "Arrange to check on anyone elderly, unwell or living alone during a hot spell",
        "Keep more drinking water than you think you need, and start drinking before you feel thirsty",
        "Shift heavy outdoor work to early morning when a hot spell is forecast",
    ],
    HazardType.WILDFIRE: [
        "Clear dry vegetation, leaves and firewood from within 10 metres of buildings",
        "Decide now what you would take and where you would go, and tell everyone in the household",
        "Keep a hose or water store that works without mains electricity",
        "Agree that you leave early rather than defend — most deaths happen to people who left too late",
    ],
    HazardType.DROUGHT: [
        "Repair leaks and cover open water storage before the dry season deepens",
        "Plan which crops or animals you would keep if water halved, and which you would sell",
        "Note where the nearest reliable water point is and how far it is to carry from",
        "Talk to neighbours about sharing transport for water and fodder — it is cheaper shared",
    ],
    HazardType.LANDSLIDE: [
        "Look at the slope above and below your home for cracks, bulges, or trees leaning downhill",
        "Keep gutters and drains clear so rainwater leaves the slope instead of soaking into it",
        "Know which way to move sideways off a slope — not downhill, which is where the debris goes",
        "Do not dig into or build on the toe of a steep slope",
    ],
}

# What to do because something is happening now.
ELEVATED_ACTIONS: dict[HazardType, list[str]] = {
    HazardType.EARTHQUAKE: [
        "Treat any building that cracked in the recent shaking as unsafe until someone qualified inspects it",
        "Expect aftershocks and drop, cover and hold on when one starts — do not run outside mid-shake",
        "Clear heavy items from above beds and doorways tonight",
        "Keep shoes, water and a torch beside you while you sleep",
    ],
    HazardType.TSUNAMI: [
        "Move inland and uphill now if you felt strong shaking — do not wait for confirmation",
        "Go on foot if roads are crowded; walking beats a stationary car",
        "Stay at height for several hours — later waves are often larger than the first",
        "Follow your national tsunami warning centre, not social media, for the all-clear",
    ],
    HazardType.VOLCANO: [
        "Follow the evacuation zone boundaries set by your volcano observatory, including any exclusion radius",
        "Wear a fitted dust mask and goggles outdoors while ash is falling",
        "Stay out of valleys and river channels downstream — lahars travel far faster than a person can run, even in dry weather",
        "Cover water tanks and bring livestock feed under shelter before ash arrives",
    ],
    HazardType.FLOOD: [
        "Move livestock, grain and equipment to high ground today, before roads flood",
        "Put documents, cash, phone and medicine in a waterproof bag you can carry",
        "Never walk or drive through moving water — 15 cm will take your footing and 60 cm will move a vehicle",
        "Switch off electricity at the mains before water reaches sockets",
    ],
    HazardType.CYCLONE: [
        "Bring inside or tie down anything outside that wind can lift — sheeting, tools, furniture",
        "Fill containers with drinking water now, as pumps stop when the power goes",
        "Shelter in the smallest interior room away from windows once winds rise",
        "Charge phones and torches and expect the network to fail at the peak",
    ],
    HazardType.EXTREME_HEAT: [
        "Drink water through the day without waiting to feel thirsty",
        "Stay out of the sun between late morning and mid-afternoon, and stop outdoor work in those hours",
        "Check on elderly neighbours and anyone living alone at least twice a day",
        "Never leave a child or an animal in a parked vehicle, even briefly",
        "Get anyone who stops sweating, becomes confused or faints into shade and cool them immediately — that is heatstroke and it is a medical emergency",
    ],
    HazardType.WILDFIRE: [
        "Leave early if you have decided to leave — roads close and visibility drops once fire is near",
        "Do not use machinery, open flame or burn rubbish while these conditions hold",
        "Keep a bag packed with documents, medicine and water in the vehicle",
        "Wet down the ground around buildings and close windows against embers",
    ],
    HazardType.DROUGHT: [
        "Sell or move the stock you cannot water now, while prices and animals still hold value",
        "Switch to a shorter-cycle or drought-tolerant seed if planting is still ahead of you",
        "Ration and cover stored water, and prioritise drinking and cooking over irrigation",
        "Register early with any local relief or destocking programme rather than waiting for it to reach you",
    ],
    HazardType.LANDSLIDE: [
        "Move away from the base of steep slopes while heavy rain continues, especially at night",
        "Leave immediately if you hear cracking, rumbling, or see mud or water suddenly change colour",
        "Avoid roads cut into hillsides — the cut face is where failures start",
        "Do not return to a slope that has already moved; the ground stays unstable for days",
    ],
}

# Prepended at EXTREME. At this level the only question worth answering is
# whether to stay, and the answer needs to be the first thing read.
EXTREME_PREFIX: dict[HazardType, str] = {
    HazardType.FLOOD: "Leave for higher ground now if you are on the floodplain — do not wait for water to reach the door",
    HazardType.TSUNAMI: "Move inland and uphill immediately and stay there",
    HazardType.VOLCANO: "Leave the evacuation zone now if the observatory has told you to",
    HazardType.CYCLONE: "Get into a strong shelter now and stay there until the wind has fully passed",
    HazardType.WILDFIRE: "Leave now if you have any plan to leave — do not wait to see the fire",
    HazardType.LANDSLIDE: "Move off and away from the slope now, especially if you are below it",
    HazardType.EXTREME_HEAT: "Get to the coolest place available and stop all outdoor work",
    HazardType.EARTHQUAKE: "Stay out of any building that was damaged in the shaking",
    HazardType.DROUGHT: "Secure drinking water for your household and animals before anything else",
}

# One extra action tailored to what a reader's day actually contains. Roles the
# LLM handles well on its own are omitted rather than padded.
ROLE_ACTIONS: dict[tuple[HazardType, UserRole], str] = {
    (HazardType.FLOOD, UserRole.FARMER): "Harvest what is ready now, even if slightly early — a partial harvest beats a flooded field",
    (HazardType.FLOOD, UserRole.PASTORALIST): "Move herds to known high ground before crossings become impassable",
    (HazardType.FLOOD, UserRole.COUNTY_OFFICER): "Pre-position boats and fuel, and warn clinics and schools in the flood zone today",
    (HazardType.FLOOD, UserRole.TEACHER): "Decide now whether the school opens tomorrow, and tell parents before nightfall",
    (HazardType.DROUGHT, UserRole.PASTORALIST): "Plan migration routes early while water points on the way still hold",
    (HazardType.DROUGHT, UserRole.FARMER): "Hold back some seed rather than planting everything into uncertain rain",
    (HazardType.EXTREME_HEAT, UserRole.TEACHER): "Move classes to the coolest rooms and cancel outdoor activity in the afternoon",
    (HazardType.EXTREME_HEAT, UserRole.COUNTY_OFFICER): "Open a cool public space and publish where it is",
    (HazardType.WILDFIRE, UserRole.PASTORALIST): "Move herds away from unburnt fuel and toward already-grazed or bare ground",
    (HazardType.EARTHQUAKE, UserRole.TEACHER): "Run a drop-cover-hold drill with your class this week and check nothing heavy hangs over the desks",
    (HazardType.VOLCANO, UserRole.COUNTY_OFFICER): "Confirm the current exclusion radius with the observatory and check evacuation routes are open",
    (HazardType.CYCLONE, UserRole.COUNTY_OFFICER): "Open shelters before the wind arrives, not after",
}


def actions_for(
    hazard: HazardType,
    risk_level: RiskLevel,
    role: UserRole,
    has_active_event: bool = True,
) -> list[str]:
    """
    The action list for a hazard at a risk level, tailored to the reader.

    `has_active_event` exists because risk level alone picks the wrong set for
    the unforecastable hazards. An earthquake card sits at MODERATE permanently
    in a seismic city — that is its readiness floor, not an event — and the
    elevated set opens with "treat any building that cracked in the recent
    shaking as unsafe", which is alarming nonsense on an ordinary Tuesday in
    Kathmandu. When nothing has actually happened, the routine set is the
    correct and more useful advice.
    """
    from app.hazards.registry import meta

    elevated = risk_level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.EXTREME)
    if elevated and not meta(hazard).forecastable and not has_active_event:
        elevated = False

    base = list((ELEVATED_ACTIONS if elevated else ROUTINE_ACTIONS).get(hazard, []))

    role_action = ROLE_ACTIONS.get((hazard, role))
    if role_action:
        # Second position: after the single most urgent generic action, but
        # above the rest, since it is the one written for this reader.
        base.insert(1, role_action)

    if risk_level == RiskLevel.EXTREME and elevated and hazard in EXTREME_PREFIX:
        base.insert(0, EXTREME_PREFIX[hazard])

    return base[:6]
