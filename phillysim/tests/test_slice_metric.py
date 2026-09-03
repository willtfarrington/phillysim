"""EP-7: the QA-only straight-line slice metric: a hand-computed golden case, the rules that
keep it honest (projected CRS only, null without destinations), and the analytic table on
the committed samples checked against an independent brute-force computation."""

from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from phillysim import destinations, pipeline
from phillysim.adapters import cenpop, snap, tiger
from phillysim.contracts import ANALYTIC_TABLE, check_frame
from phillysim.metrics import slice as qa_slice
from phillysim.spine import ANALYSIS_CRS, build_spine, centroids_in
from phillysim.stages import Stage, StageContext, StageError

METRES = "EPSG:26918"


def _points(coords, crs=METRES) -> gpd.GeoSeries:
    return gpd.GeoSeries([Point(x, y) for x, y in coords], crs=crs)


def test_golden_distances_by_hand() -> None:
    origins = _points([(0, 0), (10, 0), (3, 4)])
    stores = _points([(3, 4), (100, 100)])
    distance = qa_slice.nearest_distance(origins, stores)
    assert distance.tolist() == [5.0, 8.1, 0.0], "3-4-5 triangle; sqrt(65) rounded to 0.1 m; itself"
    assert distance.dtype == "float64" and list(distance.index) == [0, 1, 2]


def test_no_destination_means_null_and_geographic_crs_is_refused() -> None:
    origins = _points([(0, 0)])
    assert qa_slice.nearest_distance(origins, _points([])).isna().all()
    with pytest.raises(ValueError, match="projected CRS"):
        qa_slice.nearest_distance(origins.to_crs("EPSG:4326"), _points([(1, 1)], "EPSG:4326"))
    with pytest.raises(ValueError, match="CRS mismatch"):
        qa_slice.nearest_distance(origins, _points([(1, 1)], "EPSG:32129"))
    with pytest.raises(ValueError, match="carry a CRS"):
        qa_slice.nearest_distance(origins, gpd.GeoSeries([Point(1, 1)]))


@pytest.fixture(scope="module")
def spine(spine_samples_dir: Path) -> gpd.GeoDataFrame:
    raw = spine_samples_dir / "raw"
    tracts = tiger.read(raw / tiger.SOURCE / pipeline.SNAPSHOT_IDS[tiger.SOURCE])
    centers = cenpop.read(raw / cenpop.SOURCE / pipeline.SNAPSHOT_IDS[cenpop.SOURCE])
    return build_spine(tracts, centers, ANALYSIS_CRS)


@pytest.fixture(scope="module")
def layer(spine_samples_dir: Path, spine: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    retailers = snap.read(
        spine_samples_dir / "raw" / snap.SOURCE / pipeline.SNAPSHOT_IDS[snap.SOURCE]
    )
    return destinations.build_snap_layer(retailers, spine, ANALYSIS_CRS)


def test_slice_table_on_the_samples_matches_brute_force(spine, layer) -> None:
    points = layer.loc[layer["supermarket_format"], "geometry"]
    assert len(points) == 5
    table = qa_slice.slice_table(spine, points, crs=ANALYSIS_CRS)
    assert list(table.columns) == list(ANALYTIC_TABLE.column_names())
    assert check_frame(ANALYTIC_TABLE, table) == []
    assert len(table) == len(spine) == 6 and list(table["geoid"]) == sorted(spine["geoid"])
    assert (table["metric_id"] == qa_slice.METRIC_ID).all()
    assert table["metric_id"].str.startswith("qa_").all(), "the ID itself says QA"
    assert (table["category"] == qa_slice.CATEGORY).all() and table["mode"].isna().all()
    assert table["moe"].isna().all() and table["cv_tier"].isna().all()
    assert (table["reliability_action"] == "none").all()
    assert (table["methods_version"] == qa_slice.METHODS_VERSION).all()
    assert table["estimate"].notna().all() and (table["estimate"] >= 0).all()
    origins = centroids_in(spine, ANALYSIS_CRS)
    for geoid, origin in zip(spine["geoid"], origins, strict=True):
        expected = min(origin.distance(point) for point in points)
        got = float(table.loc[table["geoid"] == geoid, "estimate"].iloc[0])
        assert math.isclose(got, round(expected, 1), abs_tol=0.051), geoid
    assert table["estimate"].max() < 5000, "sample tracts are neighbours of their stores"
    report = qa_slice.summarize(table, destinations=len(points))
    assert report["qa_only"] is True and report["tracts"] == 6 and report["null_estimates"] == 0
    assert (
        report["distance_m"]["min"] <= report["distance_m"]["median"] <= report["distance_m"]["max"]
    )


def test_stage_refuses_a_foreign_methods_version(tmp_path: Path) -> None:
    stage = Stage(
        "metrics",
        qa_slice.metrics,
        inputs=("curated/tracts_spine.parquet", "curated/snap_retailers.parquet"),
        outputs=(qa_slice.TRACT_METRICS,),
        params={
            "crs": ANALYSIS_CRS,
            "category": qa_slice.CATEGORY,
            "methods_version": "slice-qa-99",
            "schema_version": 1,
        },
    )
    ctx = StageContext(stage, tmp_path, tmp_path / "staging", stage.params, cancel=_Token())
    with pytest.raises(StageError, match="methods_version"):
        qa_slice.metrics(ctx)


class _Token:
    def check(self) -> None:
        pass


def test_description_names_the_metric_as_qa_only() -> None:
    assert qa_slice.DESCRIPTIONS[qa_slice.METRIC_ID].startswith("QA-only")
    assert "not an access measure" in qa_slice.DESCRIPTION
    assert pd.Series([qa_slice.METRIC_ID]).str.startswith(qa_slice.METRIC_ID[:3]).all()
