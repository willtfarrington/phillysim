"""EP-5b geospatial invariants: CRS, geometry validity, county bounds, GEOID integrity,
join cardinality (roadmap/quality.md test matrix, "Geospatial invariants").

Positive: the spine built from the committed samples (six real Philadelphia tracts,
``tests/fixtures/spine-samples/``) passes every check. Negative: each invariant
fires on a crafted deviation. The last group runs the same checks on the **real**
spine when ``pytest --real-data-root DIR`` names a data root after ``phillysim
run``; without it those tests skip, and CI never passes it.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from pyproj import CRS
from shapely.geometry import Polygon
from shapely.geometry import box as shapely_box

from phillysim import runner
from phillysim.adapters import acs, cenpop, tiger
from phillysim.adapters.base import COUNTY_BOUNDS, NAD83
from phillysim.pipeline import SNAPSHOT_ID
from phillysim.spine import (
    ACS_TRACTS,
    ANALYSIS_CRS,
    SPINE,
    SPINE_COLUMNS,
    TRACT_COUNT,
    build_spine,
    centroids_in,
    check_spine,
    county_bounds,
    enforce,
    join_demographics,
)
from phillysim.stages import StageError

SAMPLE_TRACTS = 6


@pytest.fixture(scope="module")
def samples(spine_samples_dir: Path) -> dict[str, pd.DataFrame]:
    raw = spine_samples_dir / "raw"
    return {
        "tracts": tiger.read(raw / tiger.SOURCE / SNAPSHOT_ID),
        "centers": cenpop.read(raw / cenpop.SOURCE / SNAPSHOT_ID),
        "acs": acs.read(raw / acs.SOURCE / SNAPSHOT_ID),
    }


@pytest.fixture(scope="module")
def sample_spine(samples: dict[str, pd.DataFrame]) -> gpd.GeoDataFrame:
    return build_spine(samples["tracts"], samples["centers"])


@pytest.fixture(scope="module")
def sample_acs(samples: dict[str, pd.DataFrame], sample_spine: gpd.GeoDataFrame) -> pd.DataFrame:
    return join_demographics(sample_spine["geoid"], samples["acs"])


# --- the analysis CRS ---------------------------------------------------------------------


def test_analysis_crs_is_projected_in_metres_on_nad83() -> None:
    crs = CRS.from_user_input(ANALYSIS_CRS)
    assert crs.to_epsg() == 26918 and crs.is_projected
    assert {axis.unit_name for axis in crs.axis_info} == {"metre"}
    assert crs.datum == CRS.from_user_input(NAD83).datum, "no datum shift from TIGER / CenPop"


def test_county_bounds_reproject_to_a_plausible_box() -> None:
    minx, miny, maxx, maxy = county_bounds(ANALYSIS_CRS)
    assert 20_000 < maxx - minx < 40_000 and 20_000 < maxy - miny < 40_000, "the county is ~30 km"
    assert county_bounds(NAD83) == pytest.approx(COUNTY_BOUNDS)


# --- positive: the samples ------------------------------------------------------------------


def test_sample_spine_has_the_dictionary_shape_and_passes(
    sample_spine: gpd.GeoDataFrame, samples: dict[str, pd.DataFrame], sample_acs: pd.DataFrame
) -> None:
    assert tuple(sample_spine.columns) == SPINE_COLUMNS
    assert len(sample_spine) == SAMPLE_TRACTS
    assert sample_spine["geoid"].is_monotonic_increasing
    assert sample_spine["population"].dtype == "int64"
    assert sample_spine["centroid_lon"].dtype == "float64"
    assert CRS.from_user_input(sample_spine.crs) == CRS.from_user_input(ANALYSIS_CRS)
    assert sample_spine["name"].str.startswith("Census Tract ").all()
    assert (
        check_spine(
            sample_spine, expected_tracts=SAMPLE_TRACTS, centers=samples["centers"], acs=sample_acs
        )
        == []
    )


def test_population_and_centers_come_from_cenpop_not_geometry(
    sample_spine: gpd.GeoDataFrame, samples: dict[str, pd.DataFrame]
) -> None:
    centers = samples["centers"].set_index("geoid")
    for _, row in sample_spine.iterrows():
        assert row["population"] == centers.loc[row["geoid"], "POPULATION"]
        assert row["centroid_lon"] == centers.loc[row["geoid"], "LONGITUDE"]
        assert row["centroid_lat"] == centers.loc[row["geoid"], "LATITUDE"]
    geometric = sample_spine.geometry.centroid
    projected = centroids_in(sample_spine)
    assert (geometric.distance(projected) > 0).all(), "a mean center is not the geometric one"
    assert (geometric.distance(projected) < 2_000).all(), "but it is inside the neighbourhood"


def test_sample_acs_join_keeps_moe_columns_and_nulls(sample_acs: pd.DataFrame) -> None:
    assert list(sample_acs.columns) == ["geoid", *acs.column_names()]
    assert len(sample_acs) == SAMPLE_TRACTS and sample_acs["geoid"].is_unique
    assert all(sample_acs[c].dtype == "float64" for c in acs.column_names())
    assert {c for c in acs.column_names() if c.endswith("M")} <= set(sample_acs.columns)


def test_spine_round_trips_through_geoparquet(sample_spine: gpd.GeoDataFrame, tmp_path: Path):
    path = tmp_path / "tracts_spine.parquet"
    sample_spine.to_parquet(path, index=False)
    back = gpd.read_parquet(path)
    assert CRS.from_user_input(back.crs) == CRS.from_user_input(ANALYSIS_CRS)
    pd.testing.assert_frame_equal(pd.DataFrame(back), pd.DataFrame(sample_spine))
    assert check_spine(back, expected_tracts=SAMPLE_TRACTS) == []


# --- negative: each invariant fires ---------------------------------------------------------


def _mutated(spine: gpd.GeoDataFrame, **columns: object) -> gpd.GeoDataFrame:
    out = spine.copy()
    for name, value in columns.items():
        out.loc[0, name] = value
    return out


def test_wrong_crs_is_reported_and_stops_the_bounds_check(sample_spine: gpd.GeoDataFrame):
    problems = check_spine(sample_spine.to_crs(NAD83), expected_tracts=SAMPLE_TRACTS)
    assert problems == [f"CRS is {sample_spine.to_crs(NAD83).crs!r}, expected {ANALYSIS_CRS}"]
    problems = check_spine(sample_spine.set_crs(None, allow_override=True), expected_tracts=6)
    assert problems and problems[0].startswith("CRS is None")


def test_invalid_geometry_is_reported(sample_spine: gpd.GeoDataFrame) -> None:
    minx, miny, _, _ = county_bounds(ANALYSIS_CRS)
    bowtie = Polygon(
        [
            (minx + 1, miny + 1),
            (minx + 100, miny + 100),
            (minx + 100, miny + 1),
            (minx + 1, miny + 100),
        ]
    )
    broken = _mutated(sample_spine, geometry=bowtie)
    problems = check_spine(broken, expected_tracts=SAMPLE_TRACTS)
    assert any(p.startswith("1 invalid geometr") and "Self-intersection" in p for p in problems)


def test_null_and_wrong_type_geometry_are_reported(sample_spine: gpd.GeoDataFrame) -> None:
    problems = check_spine(_mutated(sample_spine, geometry=None), expected_tracts=SAMPLE_TRACTS)
    assert "1 null/empty geometr(ies)" in problems
    point = centroids_in(sample_spine).iloc[0]
    problems = check_spine(_mutated(sample_spine, geometry=point), expected_tracts=SAMPLE_TRACTS)
    assert "geometry type(s) ['Point'] outside Polygon / MultiPolygon" in problems


def test_geometry_outside_county_bounds_is_reported(sample_spine: gpd.GeoDataFrame) -> None:
    minx, miny, maxx, maxy = county_bounds(ANALYSIS_CRS)
    far = shapely_box(maxx + 10_000, maxy + 10_000, maxx + 10_100, maxy + 10_100)
    problems = check_spine(_mutated(sample_spine, geometry=far), expected_tracts=SAMPLE_TRACTS)
    assert any(p.startswith("1 geometr(ies) outside the county bounds") for p in problems)


def test_center_outside_county_bounds_is_reported(sample_spine: gpd.GeoDataFrame) -> None:
    shifted = _mutated(sample_spine, centroid_lon=-76.5)  # Harrisburg
    problems = check_spine(shifted, expected_tracts=SAMPLE_TRACTS)
    assert any(
        p.startswith("1 population-weighted center(s) outside the county bounds") for p in problems
    )


def test_geoid_pattern_duplicates_and_count_are_reported(sample_spine: gpd.GeoDataFrame):
    problems = check_spine(_mutated(sample_spine, geoid="42001030101"), expected_tracts=6)
    assert any("not Philadelphia County 2020 tracts: ['42001030101']" in p for p in problems)
    problems = check_spine(_mutated(sample_spine, geoid="4210100010"), expected_tracts=6)
    assert any("not Philadelphia County 2020 tracts" in p for p in problems), "ten digits"
    twin = _mutated(sample_spine, geoid=str(sample_spine.loc[1, "geoid"]))
    problems = check_spine(twin, expected_tracts=SAMPLE_TRACTS)
    assert f"1 duplicate GEOID(s): ['{sample_spine.loc[1, 'geoid']}']" in problems
    assert f"{SAMPLE_TRACTS} tract(s), expected {TRACT_COUNT}" in check_spine(sample_spine)
    assert check_spine(sample_spine, expected_tracts=None) == [], "None skips the count"


def test_missing_columns_short_circuit(sample_spine: gpd.GeoDataFrame) -> None:
    assert check_spine(sample_spine.drop(columns=["population"]), expected_tracts=6) == [
        "missing column(s) ['population']"
    ]


def test_join_cardinality_one_center_and_one_acs_row_per_tract(
    sample_spine: gpd.GeoDataFrame, samples: dict[str, pd.DataFrame], sample_acs: pd.DataFrame
) -> None:
    centers = samples["centers"]
    without = centers.iloc[1:]
    doubled = pd.concat([centers, centers.iloc[:1]], ignore_index=True)
    stranger = pd.concat([centers, pd.DataFrame({"geoid": ["42101999999"]})], ignore_index=True)
    kw = {"expected_tracts": SAMPLE_TRACTS}
    assert any(
        "1 tract(s) without a CenPop center" in p
        for p in check_spine(sample_spine, centers=without, **kw)
    )
    assert any(
        "1 tract(s) with more than one CenPop center" in p
        for p in check_spine(sample_spine, centers=doubled, **kw)
    )
    assert any(
        "1 CenPop center(s) for no spine tract" in p
        for p in check_spine(sample_spine, centers=stranger, **kw)
    )
    assert any(
        "1 tract(s) without an ACS row" in p or "without a ACS row" in p
        for p in check_spine(sample_spine, acs=sample_acs.iloc[1:], **kw)
    )
    lacking = sample_acs.drop(columns=["B08201_002M"])
    assert any(
        "lacks estimate / MOE column(s) ['B08201_002M']" in p
        for p in check_spine(sample_spine, acs=lacking, **kw)
    )


def test_build_spine_refuses_vintage_disagreement(samples: dict[str, pd.DataFrame]) -> None:
    tracts, centers = samples["tracts"], samples["centers"]
    with pytest.raises(StageError, match="1 tract\\(s\\) without a center"):
        build_spine(tracts, centers.iloc[1:])
    with pytest.raises(StageError, match="1 center\\(s\\) without a tract"):
        build_spine(tracts.iloc[1:], centers)
    with pytest.raises(StageError, match="duplicate GEOIDs"):
        build_spine(pd.concat([tracts, tracts.iloc[:1]]), centers)


def test_join_demographics_refuses_missing_and_drops_strangers(
    sample_spine: gpd.GeoDataFrame, samples: dict[str, pd.DataFrame]
) -> None:
    table = samples["acs"]
    with pytest.raises(StageError, match="ACS has no row for 1 spine tract"):
        join_demographics(sample_spine["geoid"], table.iloc[1:])
    with pytest.raises(StageError, match="duplicate GEOIDs"):
        join_demographics(sample_spine["geoid"], pd.concat([table, table.iloc[:1]]))
    stranger = pd.concat([table, table.iloc[:1].assign(geoid="42101999999")], ignore_index=True)
    joined = join_demographics(sample_spine["geoid"], stranger)
    assert len(joined) == SAMPLE_TRACTS and "42101999999" not in set(joined["geoid"])


def test_enforce_raises_a_stage_error_naming_every_problem() -> None:
    enforce([], "spine")
    with pytest.raises(StageError, match="spine: 2 invariant violation\\(s\\): a; b"):
        enforce(["a", "b"], "spine")


# --- the real spine (manual: pytest --real-data-root DIR) -------------------------------------


def test_real_spine_passes_every_invariant(real_data_root: Path) -> None:
    spine_path = real_data_root / SPINE
    if not spine_path.is_file():
        pytest.fail(f"{SPINE} is missing under the data root: run `phillysim run` first")
    spine = gpd.read_parquet(spine_path)
    acs_table = pd.read_parquet(real_data_root / ACS_TRACTS)
    centers = cenpop.read(real_data_root / f"raw/{cenpop.SOURCE}/{SNAPSHOT_ID}")
    problems = check_spine(spine, centers=centers, acs=acs_table)
    assert problems == [], problems
    assert len(spine) == TRACT_COUNT and tuple(spine.columns) == SPINE_COLUMNS
    assert list(acs_table.columns) == ["geoid", *acs.column_names()]
    assert (spine["population"] >= 0).all() and spine["population"].sum() > 1_000_000
    inside_own_tract = centroids_in(spine).within(spine.geometry)
    print(
        f"real spine: {len(spine)} tracts, population {int(spine['population'].sum()):,}, "
        f"{int(inside_own_tract.sum())} centers inside their own tract, "
        f"ACS nulls {dict((c, int(acs_table[c].isna().sum())) for c in acs.column_names())}"
    )


def test_real_state_file_records_the_spine_as_done(real_data_root: Path) -> None:
    state = json.loads((real_data_root / runner.STATE_FILE).read_text("utf-8"))
    assert state["pipeline"] == "real"
    for stage in ("spine", "demographics"):
        assert state["stages"][stage]["status"] == "done", stage
    assert state["stages"]["spine"]["params"] == {
        "crs": ANALYSIS_CRS,
        "expected_tracts": TRACT_COUNT,
    }
    digest = state["stages"]["spine"]["outputs"][SPINE]
    print(f"real spine digest sha256:{digest}")
