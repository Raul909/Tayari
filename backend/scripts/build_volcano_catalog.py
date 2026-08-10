"""
Rebuild `app/data/volcanoes.json` from the Smithsonian Global Volcanism Program.

The catalog is committed rather than fetched at runtime: it changes a few times a
year (a volcano's "last eruption" year moves, a new one is added), while a
warning system has to answer "is there a volcano near me?" in milliseconds and
must keep working when volcano.si.edu is unreachable. Live *activity* — which
volcano is erupting this week — is a separate, genuinely real-time feed
(`app/hazards/feeds.py`), so nothing time-critical depends on this snapshot.

Usage:
    python backend/scripts/build_volcano_catalog.py
"""

import json
from datetime import date, timezone, datetime
from pathlib import Path

import httpx

WFS_URL = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows"
PARAMS = {
    "service": "WFS",
    "version": "2.0.0",
    "request": "GetFeature",
    "typeName": "GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes",
    "outputFormat": "application/json",
    "propertyName": (
        "Volcano_Number,Volcano_Name,Primary_Volcano_Type,"
        "Last_Eruption_Year,Country,Region,Elevation,GeoLocation"
    ),
}

FIELDS = ["num", "name", "country", "region", "type", "last_eruption", "elevation_m", "lat", "lon"]

OUT_PATH = Path(__file__).parent.parent / "app" / "data" / "volcanoes.json"


def main() -> None:
    print(f"Fetching Holocene volcano list from {WFS_URL} …")
    resp = httpx.get(WFS_URL, params=PARAMS, timeout=120.0)
    resp.raise_for_status()
    features = resp.json()["features"]
    print(f"  → {len(features)} volcanoes")

    rows = []
    for feat in features:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        p = feat["properties"]
        rows.append(
            [
                p.get("Volcano_Number"),
                p.get("Volcano_Name"),
                p.get("Country"),
                p.get("Region"),
                p.get("Primary_Volcano_Type"),
                p.get("Last_Eruption_Year"),
                p.get("Elevation"),
                round(float(coords[1]), 3),
                round(float(coords[0]), 3),
            ]
        )

    rows.sort(key=lambda r: (r[2] or "", r[1] or ""))

    payload = {
        "source": "Smithsonian Institution, Global Volcanism Program — Volcanoes of the World (Holocene)",
        "url": "https://volcano.si.edu/",
        "license": "Free for non-commercial use with attribution to the Smithsonian GVP",
        "retrieved": date.today().isoformat(),
        "count": len(rows),
        "fields": FIELDS,
        "volcanoes": rows,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as fh:
        json.dump(payload, fh, separators=(",", ":"))
        fh.write("\n")
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUT_PATH} ({len(rows)} volcanoes, {size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
