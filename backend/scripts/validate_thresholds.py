#!/usr/bin/env python3
"""
Validate calibrated thresholds against documented historical floods.

Calibration alone is not evidence that the thresholds work. A threshold set can
be internally consistent and still be useless in both directions:

  - too high  -> misses the disasters people actually died in (false negative)
  - too low   -> fires on ordinary seasonal flow, communities stop listening
                 (false positive / cry-wolf)

This script measures both against the same GloFAS reanalysis the app consumes:

  SENSITIVITY   did the river cross warning/flood level during each documented
                flood window?
  SPECIFICITY   what fraction of all days in the 34-year record sit above the
                flood threshold? A credible early-warning threshold should be
                exceeded on a small minority of days — if the river is "in
                flood" a third of the time, the signal carries no information.

Event windows below are drawn from published humanitarian reporting (OCHA /
IFRC / national disaster agencies). They are deliberately generous by a couple
of weeks because displacement reporting lags the hydrograph peak.

    python scripts/validate_thresholds.py
"""

from __future__ import annotations

import datetime as dt
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FLOOD_API = "https://flood-api.open-meteo.com/v1/flood"
BASINS_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "basins.json"
START_DATE = "1992-01-01"
END_DATE = "2025-12-31"

# Documented flood events per basin: (label, start, end)
EVENTS: dict[str, list[tuple[str, str, str]]] = {
    "shabelle": [
        ("Deyr floods 2023 (~500k displaced)", "2023-10-25", "2023-12-20"),
        ("Deyr floods 2019", "2019-10-15", "2019-12-05"),
        ("Beledweyne 2018 Gu floods", "2018-04-15", "2018-05-20"),
    ],
    "juba": [
        ("Deyr floods 2023", "2023-10-25", "2023-12-20"),
        ("Deyr floods 2020", "2020-10-10", "2020-12-20"),
        ("Gu floods 2018", "2018-04-15", "2018-05-25"),
    ],
    "tana": [
        ("Kenya floods Apr-May 2024", "2024-04-10", "2024-06-05"),
        ("Kenya floods Nov 2023", "2023-11-01", "2023-12-20"),
        ("Kenya floods Apr-May 2018", "2018-04-10", "2018-06-05"),
    ],
    "nzoia": [
        ("Budalangi floods 2020", "2020-04-15", "2020-06-20"),
        ("Kenya floods Apr-May 2024", "2024-04-10", "2024-06-05"),
        ("Budalangi floods 2019/20 OND", "2019-10-15", "2019-12-31"),
    ],
    "awash": [
        ("Afar floods 2020", "2020-07-25", "2020-09-30"),
        ("Afar floods 2023", "2023-07-25", "2023-09-30"),
        ("Afar floods 2024", "2024-07-25", "2024-09-20"),
    ],
    "white_nile": [
        ("Jonglei floods 2020", "2020-07-15", "2020-12-31"),
        ("Jonglei floods 2021", "2021-07-15", "2021-12-31"),
        ("Jonglei floods 2022", "2022-07-15", "2022-12-31"),
    ],
    "blue_nile": [
        ("Sudan record floods 2020 (~875k affected)", "2020-08-10", "2020-10-05"),
        ("Sudan floods 2019", "2019-08-10", "2019-10-05"),
        ("Sudan floods 2022", "2022-08-10", "2022-10-05"),
    ],
    "omo": [
        ("Lower Omo floods 2019", "2019-08-10", "2019-10-20"),
        ("Lower Omo floods 2023", "2023-08-01", "2023-10-20"),
        ("Lower Omo floods 2021", "2021-08-01", "2021-10-20"),
    ],
}


def _fetch(params: dict, tries: int = 5) -> dict:
    url = f"{FLOOD_API}?{urllib.parse.urlencode(params)}"
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> int:
    config = json.loads(BASINS_PATH.read_text())
    hits = misses = 0
    cry_wolf: list[str] = []

    for basin in config["basins"]:
        bid = basin["id"]
        warn = basin["warning_threshold_m3s"]
        flood = basin["flood_threshold_m3s"]
        gauge = basin["gauge_point"]

        data = _fetch({
            "latitude": gauge["latitude"], "longitude": gauge["longitude"],
            "daily": "river_discharge", "start_date": START_DATE,
            "end_date": END_DATE, "timeformat": "iso8601",
        })
        time.sleep(1.5)
        daily = data.get("daily", {})
        series = {
            t: v for t, v in zip(daily.get("time", []), daily.get("river_discharge", []))
            if v is not None
        }
        if not series:
            print(f"{bid}: NO DATA")
            continue

        values = list(series.values())
        days_over_flood = sum(1 for v in values if v >= flood)
        days_over_warn = sum(1 for v in values if v >= warn)
        pct_flood = 100.0 * days_over_flood / len(values)
        pct_warn = 100.0 * days_over_warn / len(values)

        conf = basin.get("model_confidence", "high")
        print(f"\n{'='*84}")
        print(f"{bid}  warn={warn:.0f}  flood={flood:.0f}  median={basin['historical_median_m3s']:.0f}"
              f"  confidence={conf}")
        print(f"  base rate: {pct_warn:.1f}% of days >= warning, {pct_flood:.1f}% >= flood")
        if pct_flood > 10:
            cry_wolf.append(f"{bid}: flood threshold exceeded on {pct_flood:.1f}% of all days")

        for label, start, end in EVENTS.get(bid, []):
            window = [v for t, v in series.items() if start <= t <= end]
            if not window:
                print(f"  ?  {label:<45} no data in window")
                continue
            peak = max(window)
            if peak >= flood:
                status, sym = "FLOOD", "OK "
                hits += 1
            elif peak >= warn:
                status, sym = "WARNING", "OK "
                hits += 1
            else:
                status, sym = "no alert", "MISS"
                misses += 1
            print(f"  {sym} {label:<45} peak {peak:>9.0f}  -> {status}")

    print(f"\n{'='*84}")
    total = hits + misses
    print(f"SENSITIVITY: {hits}/{total} documented flood events would have raised at least a warning")
    if cry_wolf:
        print("\nSPECIFICITY concerns (threshold likely too low):")
        for c in cry_wolf:
            print(f"  - {c}")
    else:
        print("SPECIFICITY: no basin exceeds its flood threshold on more than 10% of days")
    return 0 if misses == 0 and not cry_wolf else 1


if __name__ == "__main__":
    raise SystemExit(main())
