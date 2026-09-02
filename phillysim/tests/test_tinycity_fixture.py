"""EP-3 acceptance: the tinycity fixture is deterministic and the committed copy is current.

Text files (CSV, GeoJSON, GTFS, JSON, TERMS) are compared byte-for-byte against
the committed golden files and against ``CHECKSUMS.txt``. Parquet files are
compared by content (frame equality) against a fresh regeneration, because
their bytes legitimately change when the pinned pyarrow / geopandas writers
change; a lockfile bump therefore never breaks this suite, while any edit to a
golden table does.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.fixtures import tinycity
from phillysim.fixtures.tinycity import (
    CATEGORIES,
    CENSOR_MIN,
    CHECKSUMS_FILE,
    MODES,
    SITES,
    Variant,
    read_checksums,
    write_fixture,
)

TEXT_SUFFIXES = {".csv", ".geojson", ".json", ".txt"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_table(path: Path) -> pd.DataFrame:
    try:
        return gpd.read_parquet(path)
    except ValueError:  # no geo metadata: a plain table
        return pd.read_parquet(path)


@pytest.mark.parametrize("variant", list(Variant))
def test_two_generations_are_byte_identical(tmp_path: Path, variant: Variant) -> None:
    first = write_fixture(tmp_path / "a", variant)
    second = write_fixture(tmp_path / "b", variant)
    assert first == second
    for relative in first:
        assert (tmp_path / "a" / relative).read_bytes() == (tmp_path / "b" / relative).read_bytes()
    assert (tmp_path / "a" / CHECKSUMS_FILE).read_bytes() == (
        tmp_path / "b" / CHECKSUMS_FILE
    ).read_bytes()


@pytest.mark.parametrize(
    ("variant", "fixture_name"),
    [(Variant.VALID, "tinycity_dir"), (Variant.INVALID, "tinycity_invalid_dir")],
)
def test_committed_fixture_matches_regeneration(
    tmp_path: Path, variant: Variant, fixture_name: str, request: pytest.FixtureRequest
) -> None:
    committed: Path = request.getfixturevalue(fixture_name)
    fresh = write_fixture(tmp_path, variant)
    recorded = read_checksums((committed / CHECKSUMS_FILE).read_text("utf-8"))
    assert set(recorded) == set(fresh), "committed CHECKSUMS.txt lists a different file set"
    for relative, digest in fresh.items():
        path = committed / relative
        assert path.is_file(), f"missing committed file {relative}"
        if path.suffix in TEXT_SUFFIXES:
            assert recorded[relative] == digest, f"{relative}: CHECKSUMS.txt is stale"
            assert _sha256(path) == digest, f"{relative}: committed bytes differ from generator"
        else:
            assert path.suffix == ".parquet", relative
            pd.testing.assert_frame_equal(_read_table(path), _read_table(tmp_path / relative))


def test_committed_text_files_use_lf_only(tinycity_dir: Path) -> None:
    """Guards the .gitattributes: a CRLF checkout would silently change every checksum."""
    for path in tinycity_dir.rglob("*"):
        if path.suffix in TEXT_SUFFIXES:
            assert b"\r\n" not in path.read_bytes(), f"{path.name} has CRLF line ends"


def test_cli_generates_fixture(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["gen-tinycity", "--out", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / CHECKSUMS_FILE).is_file()
    assert (tmp_path / "out" / "expected" / "tract_metrics.parquet").is_file()


def test_cli_rejects_unknown_variant(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["gen-tinycity", "--out", str(tmp_path), "--variant", "x"])
    assert result.exit_code != 0


# --- the fixture exercises what the brief asks for --------------------------------


def test_every_category_and_every_hours_edge_case_is_present() -> None:
    assert {s.category for s in SITES} == set(CATEGORIES)
    markets = [s for s in SITES if s.category == "farmers_market"]
    statuses = {s.hours_status for s in markets}
    assert {"parsed", "missing", "malformed"} <= statuses
    assert any(s.open_weekend and not s.open_weekday for s in markets), "weekend-only market"
    assert any(s.open_in_season_week and s.open_off_season_week is False for s in markets), (
        "seasonal market"
    )
    meals = [s for s in SITES if s.category == "meal_site"]
    assert {"parsed", "missing", "malformed"} <= {s.hours_status for s in meals}


def test_expected_tables_are_internally_consistent(tinycity_dir: Path) -> None:
    expected = tinycity_dir / "expected"
    spine = gpd.read_parquet(expected / "tracts_spine.parquet")
    sites = pd.read_parquet(expected / "sites.parquet")
    matrix = pd.read_parquet(expected / "travel_times.parquet")
    metrics = pd.read_parquet(expected / "tract_metrics.parquet")

    assert len(spine) == 6
    assert spine.crs is not None and spine.crs.to_epsg() == 4326
    assert spine.geometry.is_valid.all()
    assert set(sites["geoid"]) <= set(spine["geoid"])
    # Every site sits inside the tract it is assigned to.
    joined = gpd.sjoin(
        gpd.GeoDataFrame(
            sites, geometry=gpd.points_from_xy(sites["longitude"], sites["latitude"]), crs=4326
        ),
        spine[["geoid", "geometry"]].rename(columns={"geoid": "tract_geoid"}),
        predicate="within",
    )
    assert (joined["geoid"] == joined["tract_geoid"]).all()

    assert len(matrix) == 6 * len(SITES) * len(MODES)
    assert matrix["time_median_min"].between(0, CENSOR_MIN).all()
    assert (matrix["time_p85_min"] >= matrix["time_median_min"]).all()
    assert (matrix["time_p85_min"] <= CENSOR_MIN).all()

    # The golden time-to-nearest equals the minimum over the matrix, per tract x category x mode.
    lookup = sites.set_index("site_id")["category"]
    matrix = matrix.assign(category=matrix["site_id"].map(lookup))
    nearest = matrix.groupby(["origin_geoid", "category", "mode"])["time_median_min"].min()
    ttn = metrics[metrics["metric_id"] == "time_to_nearest_min"]
    assert len(ttn) == 6 * len(CATEGORIES) * len(MODES)
    for row in ttn.itertuples(index=False):
        assert row.estimate == nearest[(row.geoid, row.category, row.mode)]

    population = metrics[metrics["metric_id"] == "population_total"].set_index("geoid")
    assert set(population["cv_tier"].dropna()) == {1, 2, 3}, "all three CV tiers must occur"
    assert (
        population.loc[population["cv_tier"] == 3, "reliability_action"] == "interval-only"
    ).all()
    assert (population.loc[population["cv_tier"] != 3, "reliability_action"] == "none").all()


def test_transit_is_never_slower_than_walking(tinycity_dir: Path) -> None:
    matrix = pd.read_parquet(tinycity_dir / "expected" / "travel_times.parquet")
    wide = matrix.pivot(index=["origin_geoid", "site_id"], columns="mode", values="time_median_min")
    assert (wide["walk_transit"] <= wide["walk"]).all()
    assert (wide["walk_transit"] < wide["walk"]).any(), "the stub route must matter somewhere"


def test_cv_tier_rule() -> None:
    assert tinycity.cv_tier(3200, 210) == 1
    assert tinycity.cv_tier(4100, 900) == 2
    assert tinycity.cv_tier(2750, 2100) == 3
    assert tinycity.cv_tier(None, 10) is None
    assert tinycity.cv_tier(0, 10) is None
    assert tinycity.reliability_action(3) == "interval-only"
    assert tinycity.reliability_action(None) == "none"
