"""EP-8b: the basemap roads layer built on the committed samples and its invariants
(positive, and one negative per check); the same invariants on the real layer when
``pytest --real-data-root DIR`` names a data root after ``phillysim run``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import geopandas as gpd
import pytest
from pyproj import CRS
from shapely.geometry import LineString, Point

from phillysim import basemap, pipeline, runner
from phillysim.adapters import cenpop, tiger, tiger_roads
from phillysim.spine import ANALYSIS_CRS, SPINE, TRACT_COUNT, build_spine, county_bounds
from phillysim.stages import CancelToken, Stage, StageContext, StageError

SAMPLE_ROADS = 48


@pytest.fixture(scope="module")
def spine(spine_samples_dir: Path) -> gpd.GeoDataFrame:
    raw = spine_samples_dir / "raw"
    tracts = tiger.read(raw / tiger.SOURCE / pipeline.SNAPSHOT_IDS[tiger.SOURCE])
    centers = cenpop.read(raw / cenpop.SOURCE / pipeline.SNAPSHOT_IDS[cenpop.SOURCE])
    return build_spine(tracts, centers, ANALYSIS_CRS)


@pytest.fixture(scope="module")
def roads(spine_samples_dir: Path) -> gpd.GeoDataFrame:
    return tiger_roads.read(
        spine_samples_dir / "raw" / tiger_roads.SOURCE / pipeline.SNAPSHOT_IDS[tiger_roads.SOURCE]
    )


@pytest.fixture(scope="module")
def layer(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return basemap.build_roads(roads, ANALYSIS_CRS)


def _copy(layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(layer.copy(), geometry="geometry", crs=layer.crs)


# --- positive ---------------------------------------------------------------------------------


def test_layer_shape_keys_and_crs(layer: gpd.GeoDataFrame, roads: gpd.GeoDataFrame) -> None:
    assert tuple(layer.columns) == basemap.ROAD_COLUMNS
    assert len(layer) == len(roads) == SAMPLE_ROADS
    assert CRS.from_user_input(layer.crs) == CRS.from_user_input(ANALYSIS_CRS)
    assert layer["linearid"].is_unique and layer["linearid"].is_monotonic_increasing
    assert layer["linearid"].dtype == "string" and layer["name"].dtype == "string"
    assert set(layer["mtfcc"]) == tiger_roads.MAJOR_ROAD_CLASSES
    assert set(layer["route_type"]) <= tiger_roads.ROUTE_TYPES
    assert set(layer.geom_type) == {"LineString"}


def test_geometry_is_the_providers_reprojected_and_nothing_else(layer, roads) -> None:
    by_id = roads.set_index("LINEARID")
    projected = by_id.loc[layer["linearid"]].geometry.to_crs(ANALYSIS_CRS)
    assert (projected.to_numpy() == layer.geometry.to_numpy()).all()
    assert (layer.length > 10).all(), "metres, not degrees"
    assert layer.length.sum() > 10_000, "about 30 km of major roads cross the six tracts"


def test_layer_satisfies_the_invariants(layer: gpd.GeoDataFrame, spine: gpd.GeoDataFrame):
    assert basemap.check_roads(layer, crs=ANALYSIS_CRS, spine=spine) == []
    assert basemap.check_roads(layer) == []


def test_summary_counts(layer: gpd.GeoDataFrame, spine: gpd.GeoDataFrame) -> None:
    report = basemap.summarize(layer, spine, crs=ANALYSIS_CRS)
    assert report["rows"] == SAMPLE_ROADS and report["crs"] == ANALYSIS_CRS
    assert sum(report["by_mtfcc"].values()) == SAMPLE_ROADS
    assert set(report["by_mtfcc"]) == tiger_roads.MAJOR_ROAD_CLASSES
    assert sum(report["by_route_type"].values()) == SAMPLE_ROADS
    assert report["unnamed"] == 0
    assert report["length_km"] == pytest.approx(layer.length.sum() / 1000, abs=0.01)
    assert report["length_outside_tracts_m"] > 0, "sample roads run past the six tracts"
    json.dumps(report)


def test_layer_round_trips_through_geoparquet(layer: gpd.GeoDataFrame, tmp_path: Path) -> None:
    layer.to_parquet(tmp_path / "roads.parquet", index=False)
    back = gpd.read_parquet(tmp_path / "roads.parquet")
    assert tuple(back.columns) == basemap.ROAD_COLUMNS
    assert basemap.check_roads(back) == []
    assert (back.geometry.to_numpy() == layer.geometry.to_numpy()).all()


# --- negative: one per check ----------------------------------------------------------------


def test_missing_column_is_reported_first(layer) -> None:
    problems = basemap.check_roads(layer.drop(columns=["mtfcc"]))
    assert problems == ["missing column(s) ['mtfcc']"]


def test_empty_layer(layer) -> None:
    assert "empty layer" in basemap.check_roads(_copy(layer.iloc[:0]))


def test_duplicate_or_empty_linearid(layer) -> None:
    doubled = _copy(gpd.GeoDataFrame(layer.iloc[[0, 0, 1]]))
    assert any("duplicate linearid" in p for p in basemap.check_roads(doubled))
    blank = _copy(layer)
    blank.loc[0, "linearid"] = ""
    assert any("null or empty linearid" in p for p in basemap.check_roads(blank))


def test_class_and_route_type_outside_vocabulary(layer) -> None:
    bad = _copy(layer)
    bad.loc[0, "mtfcc"] = "S1400"
    bad.loc[1, "route_type"] = "X"
    problems = basemap.check_roads(bad)
    assert any("S1400" in p and "major-road vocabulary" in p for p in problems)
    assert any("'X'" in p and "route type" in p for p in problems)


def test_wrong_crs_short_circuits(layer) -> None:
    problems = basemap.check_roads(layer.to_crs("EPSG:4326"))
    assert len(problems) == 1 and "CRS" in problems[0]


def test_empty_invalid_and_non_line_geometry(layer) -> None:
    bad = _copy(layer)
    bad.loc[0, "geometry"] = Point(500_000, 4_420_000)
    bad.loc[1, "geometry"] = LineString()
    bad.loc[2, "geometry"] = None
    problems = basemap.check_roads(bad)
    assert any("2 null/empty" in p for p in problems)
    assert any("['Point']" in p for p in problems)


def test_road_outside_county_bounds(layer) -> None:
    minx, _, _, _ = county_bounds(ANALYSIS_CRS)
    bad = _copy(layer)
    bad.loc[0, "geometry"] = LineString([(minx - 5_000, 4_420_000), (minx - 4_000, 4_421_000)])
    assert any("outside the county bounds" in p for p in basemap.check_roads(bad))


def test_road_touching_no_tract(layer, spine) -> None:
    minx, miny, maxx, maxy = county_bounds(ANALYSIS_CRS)
    far = _copy(layer)
    # Inside the county bounds, outside every sample tract (the bounds carry a margin).
    far.loc[0, "geometry"] = LineString([(minx + 10, miny + 10), (minx + 100, miny + 100)])
    problems = basemap.check_roads(far, spine=spine)
    assert any("touching no tract" in p for p in problems), problems
    assert basemap.check_roads(far) == [], "without a spine the scope is not checked"


def test_stage_writes_the_layer_and_refuses_one_the_invariants_reject(
    spine_samples_dir: Path, spine: gpd.GeoDataFrame, tmp_path: Path, monkeypatch
) -> None:
    """The stage body on the sample snapshot writes the layer and the report; with the
    adapter's read doctored so every road lies outside the county it raises and writes
    nothing."""
    raw = spine_samples_dir / "raw" / tiger_roads.SOURCE / pipeline.SNAPSHOT_IDS[tiger_roads.SOURCE]
    rel = f"raw/{tiger_roads.SOURCE}/{pipeline.SNAPSHOT_IDS[tiger_roads.SOURCE]}"
    root = tmp_path / "root"
    (root / rel).parent.mkdir(parents=True)
    shutil.copytree(raw, root / rel)
    (root / SPINE).parent.mkdir(parents=True)
    spine.to_parquet(root / SPINE, index=False)
    stage = Stage(
        "basemap",
        basemap.basemap,
        inputs=(SPINE, rel),
        outputs=(basemap.ROADS, basemap.BASEMAP_REPORT),
        params={"crs": ANALYSIS_CRS},
    )
    staging = tmp_path / "staging"

    def context(staging: Path) -> StageContext:
        return StageContext(
            stage=stage, root=root, staging=staging, params=stage.params, cancel=CancelToken()
        )

    basemap.basemap(context(staging))
    assert (staging / basemap.ROADS).is_file()
    report = json.loads((staging / basemap.BASEMAP_REPORT).read_text("utf-8"))
    assert report["rows"] == SAMPLE_ROADS and report["crs"] == ANALYSIS_CRS
    assert basemap.check_roads(gpd.read_parquet(staging / basemap.ROADS), spine=spine) == []

    real_read = tiger_roads.read

    def far_read(path: Path) -> gpd.GeoDataFrame:
        frame = real_read(path)
        return frame.set_geometry(frame.geometry.translate(xoff=1.0))

    monkeypatch.setattr(tiger_roads, "read", far_read)
    again = tmp_path / "staging2"
    with pytest.raises(StageError, match="basemap roads layer: .*outside the county bounds"):
        basemap.basemap(context(again))
    assert not (again / basemap.ROADS).exists()


# --- the real layer (manual: pytest --real-data-root DIR) ------------------------------------


def test_real_roads_layer_passes_every_invariant(real_data_root: Path) -> None:
    path = real_data_root / basemap.ROADS
    if not path.is_file():
        pytest.fail(f"{basemap.ROADS} is missing under the data root: run `phillysim run` first")
    layer = gpd.read_parquet(path)
    spine = gpd.read_parquet(real_data_root / SPINE)
    assert len(spine) == TRACT_COUNT
    problems = basemap.check_roads(layer, spine=spine)
    assert problems == [], problems
    assert tuple(layer.columns) == basemap.ROAD_COLUMNS
    report = json.loads((real_data_root / basemap.BASEMAP_REPORT).read_text("utf-8"))
    assert report["rows"] == len(layer) and report["length_outside_tracts_m"] == 0.0
    state = json.loads((real_data_root / runner.STATE_FILE).read_text("utf-8"))
    assert state["stages"]["basemap"]["status"] == "done"
    print(
        f"real roads layer: {len(layer)} roads, {report['by_mtfcc']}, "
        f"{report['length_km']} km, sha256:{state['stages']['basemap']['outputs'][basemap.ROADS]}"
    )
