#!/usr/bin/env python3
"""
Calibrate basin alert thresholds against the GloFAS reanalysis and documented floods.

WHY THIS EXISTS
───────────────
Tayari compares live GloFAS v4 discharge against per-basin thresholds. Getting
those numbers wrong is the single most dangerous failure this project has: a
threshold set too low cries wolf until communities stop listening, and one set
too high stays silent through a disaster. Neither failure is visible from the
dashboard — it looks confident either way. So thresholds are never hand-written.
They are derived here, from evidence, and re-checked by validate_thresholds.py.

TWO THINGS ARE TRUE AND BOTH MATTER
───────────────────────────────────
1. Thresholds must live in the model's own reference frame. GloFAS carries a
   large bias against reality in East Africa — often 2-4x — because it cannot see
   irrigation abstraction, small dams or local channel geometry. Comparing a live
   model reading against a real-world flood stage mixes reference frames, which is
   what produced a 95% EXTREME alert on the Omo while the river was running below
   its seasonal normal.

2. Statistical rarity is NOT the same as flooding. The obvious approach — treat a
   5-year return period as "flood" — was tried and measured, and it missed the
   Beledweyne 2023 disaster that displaced ~500,000 people. The discharge at which
   a place actually floods is a local property of channel capacity and floodplain,
   and it varies enormously: Beledweyne floods around its 77th flow percentile,
   the lower Omo only above its 99.5th. No global rule fits both.

So thresholds are calibrated against documented flood events (app/data/flood_events.json)
using a skill score, and every basin carries its measured skill in basins.json.

METHOD
──────
    warning_threshold_m3s  discharge maximising the True Skill Statistic
                           (TSS = probability of detection - false alarm rate)
                           against documented events
    flood_threshold_m3s    the higher of the median documented event peak and the
                           98th flow percentile, so the top alert tier stays rare
    historical_median_m3s  model median (the anomaly baseline shown to users)
    peak_season_months     months whose climatological mean exceeds the annual mean
    model_confidence       from measured TSS: >=0.7 high, >=0.5 medium, else low

USAGE
─────
    python scripts/calibrate_basins.py              # report only, changes nothing
    python scripts/calibrate_basins.py --write      # rewrite basins.json in place

Re-run whenever a basin is added, its gauge_point moves, or new events are
documented. This is the only supported way to set these numbers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FLOOD_API = "https://flood-api.open-meteo.com/v1/flood"
DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"
BASINS_PATH = DATA_DIR / "basins.json"
EVENTS_PATH = DATA_DIR / "flood_events.json"

# GloFAS v4 reanalysis starts in 1984. We begin at 1992 to stay clear of the
# early-record spin-up and keep a round 34-year sample.
START_DATE = "1992-01-01"
END_DATE = "2025-12-31"

# A channel cell is strongly seasonal. Lakes, wetlands and damped reservoir cells
# are not. Below this coefficient of variation the model is not resolving a
# free-flowing river and its short-term flood signal cannot be trusted.
MIN_CHANNEL_CV = 0.35

# Below this median the cell carries no meaningful water — the gauge_point is off
# the mapped channel and no threshold can rescue it.
MIN_CHANNEL_MEDIAN_M3S = 1.0

# The top tier must stay rare or it stops meaning anything.
FLOOD_TIER_PERCENTILE = 0.98
MIN_FLOOD_OVER_WARNING = 1.15


# ─── HTTP ─────────────────────────────────────────────────────────────────────

def _fetch(params: dict, tries: int = 5) -> dict:
    """GET the flood API with backoff. Open-Meteo rate-limits aggressively."""
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


# ─── Statistics ───────────────────────────────────────────────────────────────

def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    lo = int(math.floor(k))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def fetch_series(lat: float, lon: float) -> dict[str, float]:
    data = _fetch({
        "latitude": lat, "longitude": lon, "daily": "river_discharge",
        "start_date": START_DATE, "end_date": END_DATE, "timeformat": "iso8601",
    })
    daily = data.get("daily", {})
    return {
        t: v for t, v in zip(daily.get("time", []), daily.get("river_discharge", []))
        if v is not None
    }


def describe_cell(series: dict[str, float]) -> dict:
    """Hydrological character of the cell: is this actually a river?"""
    values = list(series.values())
    ordered = sorted(values)
    mean = statistics.fmean(values)
    cv = (statistics.pstdev(values) / mean) if mean > 0 else 0.0
    median = statistics.median(values)

    # Climatological monthly means identify the high-flow season. Deriving this
    # from data rather than hardcoding "October-December" matters: the Ethiopian
    # and Sudanese basins (Blue Nile, Omo, Awash) peak Jun-Sep with the kiremt
    # rains — the opposite of the Somali and Kenyan OND/MAM pattern.
    monthly: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    for t, v in series.items():
        monthly[int(t[5:7])].append(v)
    peak_months = sorted(
        m for m, vs in monthly.items() if vs and statistics.fmean(vs) > mean
    )

    if median < MIN_CHANNEL_MEDIAN_M3S:
        cell_type, reason = "dry", (
            f"median {median:.2f} m3/s — this cell is not on a river channel. "
            "Move gauge_point onto the mapped channel and re-run."
        )
    elif cv < MIN_CHANNEL_CV:
        cell_type, reason = "damped", (
            f"coefficient of variation {cv:.2f} is too flat for a free-flowing "
            "river — the model is treating this as a lake or wetland, so the "
            "short-term flood signal here is unreliable."
        )
    else:
        cell_type, reason = "channel", ""

    return {
        "cell_type": cell_type, "reason": reason, "median": median, "mean": mean,
        "cv": cv, "p98": _percentile(ordered, FLOOD_TIER_PERCENTILE),
        "record_max": ordered[-1], "peak_months": peak_months,
        "n_days": len(values), "n_years": len({t[:4] for t in series}),
    }


def score_thresholds(series: dict[str, float], events: list[dict]) -> dict | None:
    """
    Pick the warning threshold that maximises the True Skill Statistic against
    documented floods.

    An event counts as detected if ANY day inside its window reaches the
    threshold — operationally, one alert during the event is a hit. The false
    alarm rate is measured over days outside every event window.
    """
    windows = []
    for ev in events:
        w = {t: v for t, v in series.items() if ev["start"] <= t <= ev["end"]}
        if w:
            windows.append((ev, w))
    if not windows:
        return None

    event_days: set[str] = set()
    for _, w in windows:
        event_days |= set(w)
    non_event = [v for t, v in series.items() if t not in event_days]
    if not non_event:
        return None

    ordered = sorted(series.values())
    # Sweep the upper half of the distribution.
    candidates = sorted({
        round(_percentile(ordered, i / 400), 1) for i in range(200, 400)
    })

    best = None
    for thr in candidates:
        pod = sum(1 for _, w in windows if max(w.values()) >= thr) / len(windows)
        far = sum(1 for v in non_event if v >= thr) / len(non_event)
        tss = pod - far
        if best is None or tss > best["tss"] + 1e-9:
            best = {"warning": thr, "pod": pod, "far": far, "tss": tss}

    peaks = [max(w.values()) for _, w in windows]
    best["event_peaks"] = peaks
    best["event_peak_median"] = statistics.median(peaks)
    best["n_events"] = len(windows)
    best["undetected"] = [
        ev["label"] for ev, w in windows if max(w.values()) < best["warning"]
    ]
    return best


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="rewrite basins.json with the calibrated values")
    ap.add_argument("--basin", help="calibrate only this basin id")
    args = ap.parse_args()

    config = json.loads(BASINS_PATH.read_text())
    all_events = json.loads(EVENTS_PATH.read_text())["events"]
    targets = [b for b in config["basins"] if not args.basin or b["id"] == args.basin]
    if not targets:
        print(f"no basin matching '{args.basin}'", file=sys.stderr)
        return 1

    print(f"GloFAS v4 reanalysis {START_DATE} .. {END_DATE}")
    print(f"ground truth: {EVENTS_PATH.name}\n")
    header = (f"{'basin':<12}{'cell':>9}{'median':>10}{'CV':>6}{'warning':>10}"
              f"{'flood':>10}{'POD':>6}{'FAR':>7}{'TSS':>6}{'conf':>8}")
    print(header)
    print("-" * len(header))

    problems: list[str] = []
    for basin in targets:
        bid = basin["id"]
        gauge = basin["gauge_point"]
        series = fetch_series(gauge["latitude"], gauge["longitude"])
        time.sleep(1.5)

        if not series:
            problems.append(f"{bid}: no reanalysis data at this cell")
            print(f"{bid:<12}{'ERROR':>9}  no reanalysis data")
            continue

        cell = describe_cell(series)
        if cell["cell_type"] == "dry":
            # Refuse to emit thresholds for a cell with no water. Writing numbers
            # here would manufacture a basin that silently never alerts.
            problems.append(f"{bid}: {cell['reason']}")
            print(f"{bid:<12}{'dry':>9}{cell['median']:>10.2f}  NOT CALIBRATED")
            continue

        events = all_events.get(bid, [])
        if not events:
            problems.append(
                f"{bid}: no documented flood events — cannot calibrate. "
                f"Add events to {EVENTS_PATH.name} first."
            )
            print(f"{bid:<12}{cell['cell_type']:>9}{cell['median']:>10.1f}"
                  f"{cell['cv']:>6.2f}  NO GROUND TRUTH")
            continue

        skill = score_thresholds(series, events)
        if skill is None:
            problems.append(f"{bid}: event windows fall outside the reanalysis period")
            continue

        warning = skill["warning"]
        flood = max(skill["event_peak_median"], cell["p98"], warning * MIN_FLOOD_OVER_WARNING)

        tss = skill["tss"]
        confidence = "high" if tss >= 0.7 else "medium" if tss >= 0.5 else "low"
        if confidence == "low":
            problems.append(
                f"{bid}: TSS {tss:.2f} — the model cannot reliably separate flood "
                f"from normal flow at this cell. {cell['reason']}".strip()
            )
        if skill["undetected"]:
            problems.append(
                f"{bid}: not detectable at any threshold — "
                + "; ".join(skill["undetected"])
            )

        ordered = sorted(series.values())
        warn_base = 100.0 * sum(1 for v in ordered if v >= warning) / len(ordered)
        flood_base = 100.0 * sum(1 for v in ordered if v >= flood) / len(ordered)

        print(f"{bid:<12}{cell['cell_type']:>9}{cell['median']:>10.1f}{cell['cv']:>6.2f}"
              f"{warning:>10.0f}{flood:>10.0f}{skill['pod']:>6.2f}{skill['far']:>7.3f}"
              f"{tss:>6.2f}{confidence:>8}")

        basin["warning_threshold_m3s"] = round(warning, 1)
        basin["flood_threshold_m3s"] = round(flood, 1)
        basin["historical_median_m3s"] = round(cell["median"], 1)
        basin["peak_season_months"] = cell["peak_months"]
        basin["model_confidence"] = confidence
        basin["calibration"] = {
            "source": "Copernicus GloFAS v4 via Open-Meteo Flood API",
            "reanalysis_period": f"{START_DATE}/{END_DATE}",
            "years": cell["n_years"],
            "method": (
                "warning = TSS-optimal against documented floods; "
                "flood = max(median event peak, p98 of daily flow, 1.15x warning); "
                "median = model median"
            ),
            "ground_truth_events": skill["n_events"],
            "probability_of_detection": round(skill["pod"], 3),
            "false_alarm_rate": round(skill["far"], 4),
            "true_skill_statistic": round(tss, 3),
            "days_above_warning_pct": round(warn_base, 2),
            "days_above_flood_pct": round(flood_base, 2),
            "cell_type": cell["cell_type"],
            "coefficient_of_variation": round(cell["cv"], 3),
            "record_max_m3s": round(cell["record_max"], 1),
            "calibrated_at": dt.date.today().isoformat(),
        }
        if cell["reason"]:
            basin["calibration"]["caveat"] = cell["reason"]
        if skill["undetected"]:
            basin["calibration"]["undetectable_events"] = skill["undetected"]

    if problems:
        print("\nProblems requiring a human decision:")
        for p in problems:
            print(f"  - {p}")

    if args.write:
        BASINS_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
        print(f"\nwrote {BASINS_PATH}")
    else:
        print("\n(dry run — pass --write to apply)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
