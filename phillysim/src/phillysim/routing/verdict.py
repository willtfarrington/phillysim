"""The M3 verdict reader (EP-15): a night's records read against the criteria, mechanically.

``phillysim route verdict --night ID`` reads a finished (or killed) night
(:mod:`~phillysim.routing.matrix`) and prints one row per criterion of
milestones.md, methodology.md, architecture.md, and ADR-0008, each with the
document it comes from quoted, the measured number, and a status:

* **wall**: the two core runs' walls together against the plan's 8 h limit;
* **RSS**: no core run killed at the 22 GB line; the night's peak process-tree
  RSS against the 20 GB budget (a peak between the budget and the kill line is
  a pass with a finding);
* **determinism**: each core run against its repeat, **pair by pair** on the
  matrix key in integer minutes (both time columns); the band of ADR-0008 /
  OQ-C: every pair identical, or at least 99.9 % identical with no difference
  above one minute; the byte and canonicalized-value digests recorded beside;
* **finite pairs**: each core run's share of pairs under the 120-minute
  censor against methodology.md's 95 % gate, read per core run as written;
  for the walk run the straight-line **reach bound** is computed too (the
  share of pairs whose straight-line distance is within what the censor lets
  a walk cover at all), because that is what the reading of the gate turns
  on and it is the owner's decision (EP-14 handoff), not the reader's;
* **the hand check** (:mod:`~phillysim.routing.handcheck`): the tally against
  32 of 40, once the planner comparison has been done by hand; pending until;
* **the walk concordance** (:mod:`~phillysim.routing.concordance`): Spearman ρ
  against the fallback engine over finite pairs, against 0.95; pending until
  computed.

The reader never calls the outcome code: it names the criterion that fails,
lists what is pending and what the owner must read, and ``--record`` writes
the code the owner confirmed into ``verdict.json`` beside the measurements.
``night.json`` is the driver's and is not touched.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyproj import Transformer

from phillysim.routing import records
from phillysim.routing.matrix import (
    FINISHED,
    KILLED_BY_EVIDENCE,
    MATRIX_FILE,
    MATRIX_KEY,
    Night,
)
from phillysim.routing.plan import POINTS_FILE, ROLE_DESTINATION, ROLE_ORIGIN, read_points
from phillysim.routing.records import COMPLETED, KILLED_RSS
from phillysim.routing.sampler import BUDGET_BYTES, KILL_BYTES
from phillysim.spine import ANALYSIS_CRS

VERDICT_FILE = "verdict.json"
VERDICT_SCHEMA_VERSION = 1
GO, TIMEBOX_EXHAUSTED = "go", "TIMEBOX-EXHAUSTED"
OUTCOME_CODES: tuple[str, ...] = (GO, KILLED_BY_EVIDENCE, TIMEBOX_EXHAUSTED)
PASS, PASS_WITH_FINDING, FAIL, PENDING, OWNER_READING = (
    "pass",
    "pass-with-finding",
    "fail",
    "pending",
    "owner-reading",
)
#: ADR-0008 / OQ-C: the determinism band.
BAND_IDENTICAL_SHARE = 0.999
BAND_MAX_DIFF_MINUTES = 1
#: methodology.md "Validation" and ADR-0008: the sanity gates.
FINITE_SHARE_GATE = 0.95
HANDCHECK_GATE = (32, 40)
CONCORDANCE_GATE = 0.95
GB = 10**9

#: Each criterion's source, quoted (the brief: "verbatim from the baseline").
SOURCES: Mapping[str, str] = {
    "wall": (
        'milestones.md M3 row: "wall ≤8 h"; ADR-0008: "the ≤ 8 h wall applies to the two '
        'core runs together"'
    ),
    "rss": (
        'milestones.md M3 row: "process-tree RSS ≤22 GB"; architecture.md: "budget 20 GB, '
        'kill 22 GB"'
    ),
    "determinism": (
        'milestones.md M3 row: "determinism within band"; ADR-0008 / OQ-C: "every pair '
        "identical, or at least 99.9 % of pairs identical with no difference above 1 "
        'minute"; quality.md: "checksum-identical within the pinned Windows environment; '
        'canonicalized-value hashes cross-platform"'
    ),
    "finite_pairs": 'methodology.md "Validation": "≥95% finite pairs"',
    "hand_check": (
        'methodology.md "Validation": "≥80% of hand-checked OD times within tolerance"; '
        'ADR-0008: "the gate is 32 of 40"'
    ),
    "concordance": (
        'methodology.md "Validation": "walk-network concordance ρ ≥ 0.95 vs fallback engine"'
    ),
}


@dataclass
class Criterion:
    id: str
    title: str
    source: str
    threshold: str
    status: str
    measured: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "threshold": self.threshold,
            "status": self.status,
            "measured": self.measured,
            "note": self.note,
        }


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# --- determinism: pair by pair ------------------------------------------------------------


def compare_matrices(
    original: pd.DataFrame, repeat: pd.DataFrame, key: tuple[str, ...] = MATRIX_KEY
) -> dict[str, Any]:
    """Join two matrices on the key and compare both time columns pair by pair in integer
    minutes: how many pairs are identical, the share, the largest difference, and the
    distribution of the per-pair maximum difference."""
    columns = [c for c in original.columns if c not in key]
    if set(columns) != set(c for c in repeat.columns if c not in key):
        raise ValueError("the two matrices carry different columns")
    joined = original.merge(
        repeat, on=list(key), how="outer", suffixes=("", "_repeat"), indicator=True
    )
    unmatched = int((joined["_merge"] != "both").sum())
    both = joined[joined["_merge"] == "both"]
    diffs = pd.DataFrame(
        {c: (both[c] - both[f"{c}_repeat"]).abs() for c in columns}, index=both.index
    )
    per_pair = diffs.max(axis=1)
    identical = int((per_pair == 0).sum())
    pairs = int(len(both))
    bins = {
        "0": identical,
        "1": int((per_pair == 1).sum()),
        "2-5": int(((per_pair >= 2) & (per_pair <= 5)).sum()),
        ">5": int((per_pair > 5).sum()),
    }
    max_diff = float(per_pair.max()) if pairs else 0.0
    share = identical / pairs if pairs else None
    return {
        "pairs": pairs,
        "unmatched_pairs": unmatched,
        "identical_pairs": identical,
        "identical_share": round(share, 6) if share is not None else None,
        "max_abs_diff_minutes": max_diff,
        "per_column_max_abs_diff_minutes": {
            c: float(diffs[c].max()) if pairs else 0.0 for c in columns
        },
        "diff_distribution": bins,
        "within_band": bool(
            pairs
            and unmatched == 0
            and (
                identical == pairs
                or (share >= BAND_IDENTICAL_SHARE and max_diff <= BAND_MAX_DIFF_MINUTES)
            )
        ),
        "band": {
            "identical_share_at_least": BAND_IDENTICAL_SHARE,
            "max_diff_minutes": BAND_MAX_DIFF_MINUTES,
        },
    }


def compare_repeat(night: Night, run: str, repeat: str) -> dict[str, Any]:
    """The pair-by-pair comparison of a run and its repeat from their matrix files, with
    the digests the night recorded for both."""
    original = pd.read_parquet(night.dir / night.runs[run]["dir"] / MATRIX_FILE)
    again = pd.read_parquet(night.dir / night.runs[repeat]["dir"] / MATRIX_FILE)
    out = compare_matrices(original, again)
    entry, again_entry = night.runs[run], night.runs[repeat]
    out["digests"] = {
        "byte_sha256": [entry["matrix"]["byte_sha256"], again_entry["matrix"]["byte_sha256"]],
        "byte_identical": entry["matrix"]["byte_sha256"] == again_entry["matrix"]["byte_sha256"],
        "canonical_value_sha256": [
            entry["matrix"]["canonical_value_sha256"],
            again_entry["matrix"]["canonical_value_sha256"],
        ],
        "value_identical": (
            entry["matrix"]["canonical_value_sha256"]
            == again_entry["matrix"]["canonical_value_sha256"]
        ),
    }
    out["run"], out["repeat"] = run, repeat
    return out


# --- the walk reach bound -------------------------------------------------------------------


def reach_bound(
    points: pd.DataFrame, *, speed_kmh: float, max_time_minutes: int, crs: str = ANALYSIS_CRS
) -> dict[str, Any]:
    """The share of origin–destination pairs whose straight-line distance is within what a
    walk at ``speed_kmh`` covers in ``max_time_minutes``: an upper bound on the share of
    finite walk pairs any engine can report under the censor (the street path is never
    shorter than the straight line)."""
    origins = points[points["role"] == ROLE_ORIGIN]
    destinations = points[points["role"] == ROLE_DESTINATION]
    to_plane = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    ox, oy = to_plane.transform(origins["lon"].to_numpy(), origins["lat"].to_numpy())
    dx, dy = to_plane.transform(destinations["lon"].to_numpy(), destinations["lat"].to_numpy())
    distance = np.hypot(
        np.asarray(ox)[:, None] - np.asarray(dx)[None, :],
        np.asarray(oy)[:, None] - np.asarray(dy)[None, :],
    )
    radius = speed_kmh * 1000.0 * max_time_minutes / 60.0
    within = int((distance <= radius).sum())
    pairs = int(distance.size)
    return {
        "speed_kmh": speed_kmh,
        "max_time_minutes": max_time_minutes,
        "radius_m": round(radius, 1),
        "pairs": pairs,
        "pairs_within_straight_line": within,
        "share_within_straight_line": round(within / pairs, 6) if pairs else None,
        "county_extent_m": {
            "east_west": round(float(max(ox.max(), dx.max()) - min(ox.min(), dx.min())), 1),
            "north_south": round(float(max(oy.max(), dy.max()) - min(oy.min(), dy.min())), 1),
        },
    }


# --- the criteria ---------------------------------------------------------------------------


def _wall(night: Night) -> Criterion:
    data = night.data
    core = data.get("core_wall_seconds")
    limit = float(data["core_wall_limit_seconds"])
    per_run = {name: night.runs[name].get("wall_seconds") for name in data["plan"]["core_runs"]}
    done = all(night.runs[n]["status"] == COMPLETED for n in data["plan"]["core_runs"])
    measured = {
        "core_wall_seconds": core,
        "core_wall_hours": round(core / 3600, 3) if core is not None else None,
        "limit_seconds": limit,
        "per_core_run_seconds": per_run,
        "all_runs_wall_seconds": round(
            sum(float(e.get("wall_seconds") or 0.0) for e in night.runs.values()), 3
        ),
        "night_started_at": data.get("started_at"),
        "night_finished_at": data.get("finished_at"),
    }
    if not done or core is None:
        return Criterion(
            "wall",
            "wall ≤ 8 h (core runs together)",
            SOURCES["wall"],
            f"≤ {limit:.0f} s",
            PENDING,
            measured,
            "a core run has not completed",
        )
    status = PASS if core <= limit else FAIL
    return Criterion(
        "wall",
        "wall ≤ 8 h (core runs together)",
        SOURCES["wall"],
        f"≤ {limit:.0f} s ({limit / 3600:.0f} h)",
        status,
        measured,
        f"{core:.0f} s = {core / 3600:.2f} h, {core / limit:.1%} of the limit",
    )


def _rss(night: Night) -> Criterion:
    data = night.data
    core_runs = data["plan"]["core_runs"]
    killed = [n for n in core_runs if night.runs[n]["status"] == KILLED_RSS]
    peak = data.get("peak_rss_bytes")
    measured = {
        "peak_rss_bytes": peak,
        "peak_rss_gb": round(peak / GB, 3) if peak else None,
        "peak_rss_run": data.get("peak_rss_run"),
        "budget_bytes": BUDGET_BYTES,
        "kill_bytes": KILL_BYTES,
        "core_runs_killed_at_the_line": killed,
        "budget_crossed_by_any_run": any(
            bool(e.get("budget_crossed")) for e in night.runs.values()
        ),
        "per_run_peak_gb": {
            n: round((e.get("peak_rss_bytes") or 0) / GB, 3) for n, e in night.runs.items()
        },
    }
    threshold = (
        f"no core run killed at {KILL_BYTES / GB:.0f} GB; peak against the "
        f"{BUDGET_BYTES / GB:.0f} GB budget"
    )
    if killed:
        return Criterion(
            "rss",
            "process-tree RSS ≤ 22 GB",
            SOURCES["rss"],
            threshold,
            FAIL,
            measured,
            f"core run(s) killed at the line: {', '.join(killed)}",
        )
    if peak is None:
        return Criterion(
            "rss", "process-tree RSS ≤ 22 GB", SOURCES["rss"], threshold, PENDING, measured
        )
    if peak > KILL_BYTES:
        status, note = FAIL, f"peak {peak / GB:.2f} GB is over the kill line"
    elif peak > BUDGET_BYTES:
        status, note = (
            PASS_WITH_FINDING,
            f"peak {peak / GB:.2f} GB is between the budget and the kill line",
        )
    else:
        status, note = PASS, f"peak {peak / GB:.2f} GB = {peak / BUDGET_BYTES:.1%} of the budget"
    return Criterion(
        "rss", "process-tree RSS ≤ 22 GB", SOURCES["rss"], threshold, status, measured, note
    )


def _determinism(night: Night) -> list[Criterion]:
    out: list[Criterion] = []
    repeats = {e["repeat_of"]: name for name, e in night.runs.items() if e.get("repeat_of")}
    for run in night.data["plan"]["core_runs"]:
        repeat = repeats.get(run)
        title = f"determinism within band ({run})"
        threshold = (
            f"every pair identical, or ≥ {BAND_IDENTICAL_SHARE:.1%} identical and no pair "
            f"differing by > {BAND_MAX_DIFF_MINUTES} min"
        )
        if repeat is None:
            out.append(
                Criterion(
                    f"determinism:{run}",
                    title,
                    SOURCES["determinism"],
                    threshold,
                    PENDING,
                    {},
                    "the plan has no repeat of this run",
                )
            )
            continue
        if not (
            night.runs[run]["status"] == COMPLETED and night.runs[repeat]["status"] == COMPLETED
        ):
            out.append(
                Criterion(
                    f"determinism:{run}",
                    title,
                    SOURCES["determinism"],
                    threshold,
                    PENDING,
                    {},
                    f"{run} or {repeat} did not complete",
                )
            )
            continue
        measured = compare_repeat(night, run, repeat)
        if measured["within_band"]:
            if (
                measured["identical_pairs"] == measured["pairs"]
                and measured["digests"]["byte_identical"]
            ):
                note = "every pair identical; byte digests equal; value digests equal"
            else:
                note = (
                    f"{measured['identical_share']:.4%} identical, max difference "
                    f"{measured['max_abs_diff_minutes']:.0f} min"
                )
            status = PASS
        else:
            status = FAIL
            note = (
                f"{measured['identical_share']:.4%} identical, max difference "
                f"{measured['max_abs_diff_minutes']:.0f} min, "
                f"{measured['unmatched_pairs']} unmatched"
            )
        out.append(
            Criterion(
                f"determinism:{run}",
                title,
                SOURCES["determinism"],
                threshold,
                status,
                measured,
                note,
            )
        )
    return out


def _finite_pairs(night: Night, points: pd.DataFrame | None) -> list[Criterion]:
    out: list[Criterion] = []
    max_time = int(night.data["plan"]["max_time_minutes"])
    for run in night.data["plan"]["core_runs"]:
        entry = night.runs[run]
        title = f"≥ 95 % finite pairs ({run})"
        threshold = (
            f"finite share ≥ {FINITE_SHARE_GATE:.0%} (finite = typical time under {max_time} min)"
        )
        sanity = entry.get("sanity")
        if entry["status"] != COMPLETED or not sanity:
            out.append(
                Criterion(
                    f"finite_pairs:{run}",
                    title,
                    SOURCES["finite_pairs"],
                    threshold,
                    PENDING,
                    {},
                    "the run did not complete",
                )
            )
            continue
        measured = {
            "mode": entry["mode"],
            "speed_walking_kmh": entry["speed_walking_kmh"],
            "pairs_expected": sanity["pairs_expected"],
            "finite_pairs": sanity["finite_pairs"],
            "finite_share": sanity["finite_share"],
            "at_censor": sanity["at_censor"],
            "missing_rows": sanity["missing_rows"],
            "origins_without_a_finite_pair": sanity["origins_without_a_finite_pair"],
            "gate": FINITE_SHARE_GATE,
            "gate_met": sanity["finite_share_gate_met"],
        }
        met = bool(sanity["finite_share_gate_met"])
        if met:
            status, note = PASS, f"{sanity['finite_share']:.2%} finite"
        elif entry["mode"] == "walk" and points is not None:
            bound = reach_bound(
                points, speed_kmh=float(entry["speed_walking_kmh"]), max_time_minutes=max_time
            )
            measured["straight_line_reach_bound"] = bound
            measured["finite_share_of_reach_bound"] = (
                round(sanity["finite_share"] / bound["share_within_straight_line"], 4)
                if bound["share_within_straight_line"]
                else None
            )
            status = OWNER_READING
            note = (
                f"{sanity['finite_share']:.2%} finite is below the gate as written; "
                "the straight-line "
                f"reach bound at {entry['speed_walking_kmh']} km/h and {max_time} min "
                f"({bound['radius_m'] / 1000:.1f} km) admits at most "
                f"{bound['share_within_straight_line']:.2%} of the pairs, so no engine "
                "meets the gate "
                "for walk over all retailers under this censor; every origin has a finite pair "
                f"({sanity['origins_without_a_finite_pair']} without); the reading of the gate for "
                "walk (per mode, or for walk+transit only) is the owner's (EP-14 handoff)"
            )
        else:
            status, note = FAIL, f"{sanity['finite_share']:.2%} finite is below the gate"
        out.append(
            Criterion(
                f"finite_pairs:{run}",
                title,
                SOURCES["finite_pairs"],
                threshold,
                status,
                measured,
                note,
            )
        )
    return out


def _hand_check(tally: Mapping[str, Any] | None) -> Criterion:
    gate, of = HANDCHECK_GATE
    title, threshold = (
        "hand check against a public trip planner",
        f"≥ {gate} of {of} within tolerance",
    )
    if not tally or tally.get("within") is None:
        note = "pending: the forty planner checks are done by hand (`route handcheck`)"
        if tally:
            note = (
                f"pending: {tally.get('checks', of)} project-side times ready; the "
                "planner tally is not entered yet"
            )
        return Criterion(
            "hand_check", title, SOURCES["hand_check"], threshold, PENDING, dict(tally or {}), note
        )
    measured = dict(tally)
    met = int(tally["within"]) >= gate and int(tally.get("checks", of)) >= of
    return Criterion(
        "hand_check",
        title,
        SOURCES["hand_check"],
        threshold,
        PASS if met else FAIL,
        measured,
        f"{tally['within']} of {tally.get('checks', of)} within tolerance",
    )


def _concordance(report: Mapping[str, Any] | None) -> Criterion:
    title = "walk-network concordance against the fallback engine"
    threshold = f"Spearman ρ ≥ {CONCORDANCE_GATE} over finite pairs"
    if not report or report.get("spearman_rho") is None:
        return Criterion(
            "concordance",
            title,
            SOURCES["concordance"],
            threshold,
            PENDING,
            dict(report or {}),
            "pending: `route concordance` has not been run for this night",
        )
    rho = float(report["spearman_rho"])
    return Criterion(
        "concordance",
        title,
        SOURCES["concordance"],
        threshold,
        PASS if rho >= CONCORDANCE_GATE else FAIL,
        dict(report),
        f"ρ = {rho:.4f} over {report.get('pairs_compared')} finite pairs",
    )


# --- the report -----------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any] | None:
    return records.read_json(path) if path.is_file() else None


def read_verdict(
    night_dir: Path,
    *,
    handcheck: Mapping[str, Any] | None = None,
    concordance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Every criterion against the night's records. ``handcheck`` and ``concordance`` default
    to the reports those verbs leave under the night directory, when present."""
    from phillysim.routing.concordance import CONCORDANCE_DIR, CONCORDANCE_FILE  # noqa: PLC0415
    from phillysim.routing.handcheck import HANDCHECK_DIR, HANDCHECK_FILE  # noqa: PLC0415

    night = Night.load(night_dir)
    if handcheck is None:
        handcheck = _load_json(night_dir / HANDCHECK_DIR / HANDCHECK_FILE)
    if concordance is None:
        concordance = _load_json(night_dir / CONCORDANCE_DIR / CONCORDANCE_FILE)
    points_path = night_dir / POINTS_FILE
    points = read_points(points_path) if points_path.is_file() else None
    criteria = [
        _wall(night),
        _rss(night),
        *_determinism(night),
        *_finite_pairs(night, points),
        _hand_check((handcheck or {}).get("tally") if handcheck else None),
        _concordance(concordance),
    ]
    failing = [c.id for c in criteria if c.status == FAIL]
    pending = [c.id for c in criteria if c.status == PENDING]
    owner = [c.id for c in criteria if c.status == OWNER_READING]
    findings = [c.id for c in criteria if c.status == PASS_WITH_FINDING]
    if night.state not in (FINISHED, KILLED_BY_EVIDENCE):
        readable = False
        suggestion = (
            f"the night is {night.state}: no verdict is readable from it (the TIMEBOX path)"
        )
    else:
        readable = True
        if night.data.get("outcome_code") == KILLED_BY_EVIDENCE or failing:
            suggestion = KILLED_BY_EVIDENCE
        elif pending:
            suggestion = f"pending ({', '.join(pending)})"
        else:
            suggestion = GO
    existing = _load_json(night_dir / VERDICT_FILE) or {}
    return {
        "schema_version": VERDICT_SCHEMA_VERSION,
        "night_id": night.id,
        "night_state": night.state,
        "night_outcome_code": night.data.get("outcome_code"),
        "kill_reason": night.data.get("kill_reason"),
        "read_at": _utc(),
        "readable": readable,
        "criteria": [c.to_dict() for c in criteria],
        "failing": failing,
        "pending": pending,
        "owner_readings": owner,
        "findings": findings,
        "suggested_outcome": suggestion,
        "outcome_code": existing.get("outcome_code"),
        "outcome_recorded_at": existing.get("outcome_recorded_at"),
        "outcome_confirmed_by": existing.get("outcome_confirmed_by"),
        "outcome_note": existing.get("outcome_note"),
    }


def write_verdict(night_dir: Path, report: Mapping[str, Any]) -> Path:
    path = night_dir / VERDICT_FILE
    records.write_json(path, dict(report), {})
    return path


def record_outcome(
    night_dir: Path, code: str, *, confirmed_by: str, note: str = ""
) -> dict[str, Any]:
    """Write the owner's confirmed outcome code into ``verdict.json`` beside a fresh read
    of the criteria. The reader suggests; the owner calls; this records the call."""
    if code not in OUTCOME_CODES:
        raise ValueError(f"outcome code must be one of {OUTCOME_CODES}, not {code!r}")
    report = read_verdict(night_dir)
    report["outcome_code"] = code
    report["outcome_recorded_at"] = _utc()
    report["outcome_confirmed_by"] = confirmed_by
    report["outcome_note"] = note
    write_verdict(night_dir, report)
    return report


def verdict_lines(report: Mapping[str, Any]) -> list[str]:
    out = [
        f"night {report['night_id']}: {report['night_state']}"
        + (
            f" ({report['night_outcome_code']}: {report['kill_reason']})"
            if report.get("night_outcome_code")
            else ""
        )
    ]
    width = max(len(c["title"]) for c in report["criteria"])
    for c in report["criteria"]:
        out.append(f"  {c['status']:<17} {c['title']:<{width}}  {c['note']}")
    if report.get("findings"):
        out.append(f"  findings: {', '.join(report['findings'])}")
    if report.get("owner_readings"):
        out.append(f"  owner readings: {', '.join(report['owner_readings'])}")
    if report.get("pending"):
        out.append(f"  pending: {', '.join(report['pending'])}")
    if report.get("failing"):
        out.append(f"  failing: {', '.join(report['failing'])}")
    out.append(f"  suggested outcome: {report['suggested_outcome']}")
    if report.get("outcome_code"):
        out.append(
            f"  recorded outcome: {report['outcome_code']} ({report['outcome_confirmed_by']}, "
            f"{report['outcome_recorded_at']})"
        )
    else:
        out.append("  recorded outcome: none (the owner confirms; `route verdict --record CODE`)")
    return out


def to_json(report: Mapping[str, Any]) -> str:
    return json.dumps(dict(report), indent=2, sort_keys=True)
