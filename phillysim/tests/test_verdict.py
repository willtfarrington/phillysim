"""EP-15: the verdict reader on crafted records (no JVM): every criterion with its source,
number, and status from a finished night; the pair-by-pair determinism comparison and the
band; the walk reach bound; the killed night; the outcome code recorded by the owner; the
CLI's surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.routing import verdict
from phillysim.routing.matrix import KILLED_BY_EVIDENCE, run_matrix
from phillysim.routing.verdict import (
    FAIL,
    GO,
    OWNER_READING,
    PASS,
    PENDING,
    SOURCES,
    VERDICT_FILE,
    compare_matrices,
    reach_bound,
    read_verdict,
    record_outcome,
    verdict_lines,
)
from test_matrix_driver import (  # noqa: F401
    HUNGRY_CHILD,
    MATRIX_CHILD,
    make_runner,
    roots,
    small_plan,
)

runner_cli = CliRunner()


#: The scripted child with every transit pair under the censor (the 95 % gate met), so the
#: small night reads like the real one: the walk run below the gate, the transit run above.
FINITE_CHILD = MATRIX_CHILD.replace("% 140", "% 100")


@pytest.fixture
def finished_night(roots):  # noqa: F811 - the imported fixture
    data_root, chain = roots
    plan = small_plan()
    runner = make_runner({"transit-48-wed": FINITE_CHILD, "transit-30-wed": FINITE_CHILD})
    night = run_matrix(plan, data_root=data_root, toolchain=chain, runner=runner)
    assert night.runs["transit-48-wed"]["sanity"]["finite_share_gate_met"]
    return data_root, chain, night


def _by_id(report: dict) -> dict[str, dict]:
    return {c["id"]: c for c in report["criteria"]}


def test_every_criterion_quotes_its_source_and_carries_a_number(finished_night) -> None:
    data_root, _chain, night = finished_night
    report = read_verdict(night.dir)
    criteria = _by_id(report)
    assert set(criteria) == {
        "wall",
        "rss",
        "determinism:walk-48-wed",
        "determinism:transit-48-wed",
        "finite_pairs:walk-48-wed",
        "finite_pairs:transit-48-wed",
        "hand_check",
        "concordance",
    }
    for c in criteria.values():
        assert c["source"] and c["threshold"] and c["status"]
    assert criteria["wall"]["source"] == SOURCES["wall"]
    assert criteria["wall"]["status"] == PASS
    assert criteria["wall"]["measured"]["core_wall_seconds"] == night.data["core_wall_seconds"]
    assert criteria["rss"]["status"] == PASS
    assert criteria["rss"]["measured"]["peak_rss_bytes"] == night.data["peak_rss_bytes"]
    # The scripted child is deterministic: the walk repeat is pair-for-pair identical.
    walk = criteria["determinism:walk-48-wed"]
    assert walk["status"] == PASS and walk["measured"]["identical_share"] == 1.0
    assert walk["measured"]["pairs"] == 8 * 5 and walk["measured"]["digests"]["byte_identical"]
    # No repeat of the transit run in the small plan: pending, not failed.
    assert criteria["determinism:transit-48-wed"]["status"] == PENDING
    # The finite-pairs gate is read per core run; the walk run's reading is the owner's.
    for run in ("walk-48-wed", "transit-48-wed"):
        entry = night.runs[run]["sanity"]
        c = criteria[f"finite_pairs:{run}"]
        assert c["measured"]["finite_share"] == entry["finite_share"]
        if entry["finite_share_gate_met"]:
            assert c["status"] == PASS
        elif night.runs[run]["mode"] == "walk":
            assert c["status"] == OWNER_READING
            assert "straight_line_reach_bound" in c["measured"]
        else:
            assert c["status"] == FAIL
    assert criteria["hand_check"]["status"] == PENDING
    assert criteria["concordance"]["status"] == PENDING
    assert report["pending"] == ["determinism:transit-48-wed", "hand_check", "concordance"]
    assert report["suggested_outcome"].startswith("pending")
    assert report["outcome_code"] is None
    lines = verdict_lines(report)
    assert lines[0].startswith(f"night {night.id}: finished")
    assert any("suggested outcome: pending" in line for line in lines)


def test_reports_from_the_verbs_feed_the_pending_criteria(finished_night) -> None:
    _data_root, _chain, night = finished_night
    report = read_verdict(
        night.dir,
        handcheck={"tally": {"checks": 40, "within": 35, "gate": [32, 40], "gate_met": True}},
        concordance={"spearman_rho": 0.97, "pairs_compared": 100, "gate": 0.95, "gate_met": True},
    )
    criteria = _by_id(report)
    assert criteria["hand_check"]["status"] == PASS
    assert criteria["concordance"]["status"] == PASS
    assert report["pending"] == ["determinism:transit-48-wed"]
    below = read_verdict(
        night.dir,
        handcheck={"tally": {"checks": 40, "within": 31, "gate": [32, 40], "gate_met": False}},
        concordance={"spearman_rho": 0.9, "pairs_compared": 100, "gate": 0.95, "gate_met": False},
    )
    assert _by_id(below)["hand_check"]["status"] == FAIL
    assert _by_id(below)["concordance"]["status"] == FAIL
    assert below["suggested_outcome"] == KILLED_BY_EVIDENCE
    assert set(below["failing"]) == {"hand_check", "concordance"}


def test_the_verbs_reports_are_read_from_the_night_directory(finished_night) -> None:
    _data_root, _chain, night = finished_night
    from phillysim.routing.concordance import CONCORDANCE_DIR, CONCORDANCE_FILE
    from phillysim.routing.handcheck import HANDCHECK_DIR, HANDCHECK_FILE

    (night.dir / HANDCHECK_DIR).mkdir()
    (night.dir / HANDCHECK_DIR / HANDCHECK_FILE).write_text(
        json.dumps({"tally": {"checks": 40, "within": 40, "gate": [32, 40], "gate_met": True}}),
        "utf-8",
    )
    (night.dir / CONCORDANCE_DIR).mkdir()
    (night.dir / CONCORDANCE_DIR / CONCORDANCE_FILE).write_text(
        json.dumps({"spearman_rho": 0.99, "pairs_compared": 5, "gate": 0.95, "gate_met": True}),
        "utf-8",
    )
    report = read_verdict(night.dir)
    assert _by_id(report)["hand_check"]["status"] == PASS
    assert _by_id(report)["concordance"]["measured"]["spearman_rho"] == 0.99


# --- determinism, pair by pair -------------------------------------------------------------


def _matrix(values: list[tuple[str, str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "origin_geoid": o,
                "site_id": s,
                "mode": "walk",
                "time_median_min": p50,
                "time_p85_min": p85,
            }
            for o, s, p50, p85 in values
        ]
    )


def test_compare_matrices_counts_identical_pairs_and_the_largest_difference() -> None:
    a = _matrix([("o1", "s1", 10, 12), ("o1", "s2", 20, 25), ("o2", "s1", 120, 120)])
    b = _matrix([("o2", "s1", 120, 120), ("o1", "s2", 20, 26), ("o1", "s1", 10, 12)])
    out = compare_matrices(a, b)
    assert out["pairs"] == 3 and out["unmatched_pairs"] == 0
    assert out["identical_pairs"] == 2 and out["identical_share"] == round(2 / 3, 6)
    assert out["max_abs_diff_minutes"] == 1.0
    assert out["per_column_max_abs_diff_minutes"] == {"time_median_min": 0.0, "time_p85_min": 1.0}
    assert out["diff_distribution"] == {"0": 2, "1": 1, "2-5": 0, ">5": 0}
    assert out["within_band"] is False  # two thirds identical is far below 99.9 %


def test_the_band_admits_one_minute_on_a_tenth_of_a_percent_and_nothing_wider() -> None:
    rows = [(f"o{i}", "s", 10.0, 10.0) for i in range(2000)]
    a = _matrix(rows)
    one_off = rows.copy()
    one_off[0] = ("o0", "s", 11.0, 10.0)  # 1 of 2000 differs by one minute: 99.95 % identical
    assert compare_matrices(a, _matrix(one_off))["within_band"] is True
    two_off = rows.copy()
    two_off[0] = ("o0", "s", 12.0, 10.0)  # a two-minute difference is outside the band
    assert compare_matrices(a, _matrix(two_off))["within_band"] is False
    three_pairs = rows.copy()
    for i in range(3):  # 3 of 2000 = 99.85 % identical: below the share
        three_pairs[i] = (f"o{i}", "s", 11.0, 10.0)
    assert compare_matrices(a, _matrix(three_pairs))["within_band"] is False
    assert compare_matrices(a, a)["within_band"] is True
    # A pair present on one side only is unmatched and never within band.
    assert compare_matrices(a, _matrix(rows[:-1]))["unmatched_pairs"] == 1
    assert compare_matrices(a, _matrix(rows[:-1]))["within_band"] is False


def test_compare_matrices_refuses_different_columns() -> None:
    a = _matrix([("o", "s", 1, 1)])
    with pytest.raises(ValueError, match="different columns"):
        compare_matrices(a, a.drop(columns=["time_p85_min"]))


# --- the reach bound ---------------------------------------------------------------------------


def test_reach_bound_is_the_share_of_pairs_within_the_walkable_radius() -> None:
    # Two origins and three destinations on a line at 0, 5, 10, 15 km (WGS 84 near 40 N).
    lon0, lat0 = -75.16, 39.95
    km = 1 / 111.0  # a degree of latitude is about 111 km
    points = pd.DataFrame(
        {
            "role": ["origin", "origin", "destination", "destination", "destination"],
            "id": ["o1", "o2", "d1", "d2", "d3"],
            "lon": [lon0] * 5,
            "lat": [lat0, lat0 + 5 * km, lat0, lat0 + 10 * km, lat0 + 15 * km],
        }
    )
    bound = reach_bound(points, speed_kmh=4.8, max_time_minutes=120)
    assert bound["radius_m"] == 9600.0 and bound["pairs"] == 6
    # o1 reaches d1 (0) only; o2 reaches d1 (5), d2 (5); d3 is 15 / 10 km away.
    assert bound["pairs_within_straight_line"] == 3
    assert bound["share_within_straight_line"] == 0.5
    assert bound["county_extent_m"]["north_south"] == pytest.approx(15_000, rel=0.02)


# --- the killed night and the recorded code ------------------------------------------------


def test_a_killed_night_suggests_the_kill_and_names_the_reason(roots) -> None:  # noqa: F811
    data_root, chain = roots
    plan = small_plan()
    night = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        runner=make_runner(
            {"walk-48-wed": HUNGRY_CHILD}, kill_bytes=200 * 1024**2, budget_bytes=150 * 1024**2
        ),
    )
    assert night.state == KILLED_BY_EVIDENCE
    report = read_verdict(night.dir)
    assert report["readable"] is True
    assert report["suggested_outcome"] == KILLED_BY_EVIDENCE
    assert _by_id(report)["rss"]["status"] == FAIL
    assert "walk-48-wed" in _by_id(report)["rss"]["measured"]["core_runs_killed_at_the_line"]
    assert _by_id(report)["wall"]["status"] == PENDING
    assert "KILLED-BY-EVIDENCE" in verdict_lines(report)[0]


def test_record_outcome_writes_the_owners_code_beside_a_fresh_read(finished_night) -> None:
    _data_root, _chain, night = finished_night
    with pytest.raises(ValueError, match="outcome code must be one of"):
        record_outcome(night.dir, "maybe", confirmed_by="owner")
    report = record_outcome(night.dir, GO, confirmed_by="owner", note="hand check 40 of 40")
    assert report["outcome_code"] == GO and report["outcome_confirmed_by"] == "owner"
    written = json.loads((night.dir / VERDICT_FILE).read_text("utf-8"))
    assert written["outcome_code"] == GO and written["outcome_note"] == "hand check 40 of 40"
    # A later read keeps the recorded code and refreshes the criteria.
    again = read_verdict(night.dir)
    assert (
        again["outcome_code"] == GO
        and again["outcome_recorded_at"] == report["outcome_recorded_at"]
    )
    assert any("recorded outcome: go" in line for line in verdict_lines(again))
    # night.json is the driver's: untouched.
    assert night.data["outcome_code"] is None


def test_route_verdict_cli(finished_night) -> None:
    data_root, _chain, night = finished_night
    result = runner_cli.invoke(
        app, ["route", "verdict", "--data-root", str(data_root), "--night", night.id, "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["night_id"] == night.id and payload["suggested_outcome"].startswith("pending")
    result = runner_cli.invoke(
        app, ["route", "verdict", "--data-root", str(data_root), "--night", night.id, "--write"]
    )
    assert result.exit_code == 0 and (night.dir / VERDICT_FILE).is_file()
    assert "suggested outcome: pending" in result.output
    result = runner_cli.invoke(
        app,
        ["route", "verdict", "--data-root", str(data_root), "--night", night.id, "--record", "no"],
    )
    assert result.exit_code == 1 and "outcome code must be one of" in result.output
    result = runner_cli.invoke(
        app,
        [
            "route",
            "verdict",
            "--data-root",
            str(data_root),
            "--night",
            night.id,
            "--record",
            "TIMEBOX-EXHAUSTED",
            "--note",
            "test",
        ],
    )
    assert result.exit_code == 0 and "recorded outcome: TIMEBOX-EXHAUSTED" in result.output
    result = runner_cli.invoke(app, ["route", "verdict", "--data-root", str(data_root / "none")])
    assert result.exit_code == 1 and "FAIL no night" in result.output


def test_verdict_help_names_the_criteria(tmp_path: Path) -> None:
    result = runner_cli.invoke(app, ["route", "verdict", "--help"])
    assert result.exit_code == 0
    assert "determinism" in result.output and "--record" in result.output
    assert verdict.OUTCOME_CODES == ("go", "KILLED-BY-EVIDENCE", "TIMEBOX-EXHAUSTED")
