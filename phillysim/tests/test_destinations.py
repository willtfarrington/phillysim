"""EP-6: the SNAP retailer layer built on the committed samples, and its invariants
(positive, and one negative per check)."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from phillysim import destinations, pipeline
from phillysim.adapters import cenpop, snap, tiger
from phillysim.classify import store_format
from phillysim.spine import ANALYSIS_CRS, build_spine


@pytest.fixture(scope="module")
def spine(spine_samples_dir: Path) -> gpd.GeoDataFrame:
    raw = spine_samples_dir / "raw"
    tracts = tiger.read(raw / tiger.SOURCE / pipeline.SNAPSHOT_ID)
    centers = cenpop.read(raw / cenpop.SOURCE / pipeline.SNAPSHOT_ID)
    return build_spine(tracts, centers, ANALYSIS_CRS)


@pytest.fixture(scope="module")
def retailers(spine_samples_dir: Path) -> gpd.GeoDataFrame:
    return snap.read(spine_samples_dir / "raw" / snap.SOURCE / pipeline.SNAPSHOT_ID)


@pytest.fixture(scope="module")
def layer(retailers: gpd.GeoDataFrame, spine: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return destinations.build_snap_layer(retailers, spine, ANALYSIS_CRS)


def _copy(layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(layer.copy(), geometry="geometry", crs=layer.crs)


def test_layer_shape_keys_and_crs(layer: gpd.GeoDataFrame, retailers: gpd.GeoDataFrame):
    assert tuple(layer.columns) == destinations.SNAP_LAYER_COLUMNS
    assert len(layer) == len(retailers)
    assert layer.crs.to_epsg() == 26918
    assert (layer["site_id"] == "snap_retailers:" + layer["source_record_id"]).all()
    assert layer["site_id"].is_unique and layer["site_id"].is_monotonic_increasing
    assert (layer["source"] == snap.SOURCE).all()
    assert layer["supermarket_format"].dtype == bool
    assert layer["authorized_since"].dtype.kind == "M"
    assert set(layer.geom_type) == {"Point"}


def test_coordinates_are_kept_as_delivered_and_geometry_projected(layer, retailers):
    by_id = retailers.set_index(retailers["Record ID"].astype(str))
    assert (
        layer["longitude"].to_numpy()
        == by_id.loc[layer["source_record_id"], "Longitude"].to_numpy()
    ).all()
    assert (
        layer["latitude"].to_numpy() == by_id.loc[layer["source_record_id"], "Latitude"].to_numpy()
    ).all()
    back = layer.geometry.to_crs("EPSG:4326")
    assert (abs(back.x - layer["longitude"]) < 1e-9).all()
    assert (abs(back.y - layer["latitude"]) < 1e-9).all()


def test_classification_follows_the_mapping(layer: gpd.GeoDataFrame) -> None:
    table = store_format.load_table().set_index("store_type")
    expected = layer["store_type"].map(table["format_class"]).astype(str)
    assert (layer["format_class"] == expected).all()
    assert (layer["supermarket_format"] == (layer["format_class"] == "supermarket")).all()
    assert layer["supermarket_format"].sum() == (
        layer["store_type"].isin(["Supermarket", "Super Store"]).sum()
    )
    assert layer["supermarket_format"].any(), "the sample tracts contain supermarket-format stores"


def test_every_sample_point_lands_in_a_sample_tract(layer: gpd.GeoDataFrame, spine) -> None:
    assert layer["geoid"].notna().all()
    assert set(layer["geoid"]) <= set(spine["geoid"])
    assert layer["geoid"].nunique() >= 5, "the sample spans most of the six tracts"


def test_layer_satisfies_the_invariants(layer: gpd.GeoDataFrame, spine) -> None:
    assert destinations.check_snap_layer(layer, crs=ANALYSIS_CRS, spine_geoids=spine["geoid"]) == []


def test_summary_counts(layer: gpd.GeoDataFrame) -> None:
    report = destinations.summarize(layer, crs=ANALYSIS_CRS, as_of=snap.AS_OF)
    assert (
        report["rows"] == len(layer) and report["mapping_version"] == store_format.MAPPING_VERSION
    )
    assert report["supermarket_format"] == int(layer["supermarket_format"].sum())
    assert report["unassigned_to_tract"] == 0
    assert sum(report["by_store_type"].values()) == len(layer)
    assert sum(report["by_format_class"].values()) == len(layer)
    assert report["tracts_with_supermarket_format"] <= report["tracts_with_any_retailer"]


def test_point_outside_every_tract_keeps_a_null_geoid(retailers, spine) -> None:
    shifted = retailers.copy()
    shifted.loc[shifted.index[0], "Latitude"] = 40.10  # inside the county bounds, outside
    shifted = gpd.GeoDataFrame(  # the six sample tracts
        shifted,
        geometry=gpd.points_from_xy(shifted["Longitude"], shifted["Latitude"]),
        crs=snap.COORDINATE_CRS,
    )
    layer = destinations.build_snap_layer(shifted, spine, ANALYSIS_CRS)
    assert layer["geoid"].isna().sum() == 1
    assert destinations.check_snap_layer(layer, crs=ANALYSIS_CRS, spine_geoids=spine["geoid"]) == []
    report = destinations.summarize(layer, crs=ANALYSIS_CRS, as_of=snap.AS_OF)
    assert report["unassigned_to_tract"] == 1 and report["rows"] == len(retailers)


def test_unknown_store_type_stops_the_build(retailers, spine) -> None:
    broken = retailers.copy()
    broken.loc[broken.index[0], "Store Type"] = "Hypermarket"
    with pytest.raises(ValueError, match="stop condition"):
        destinations.build_snap_layer(broken, spine, ANALYSIS_CRS)


# --- negative: one violation per invariant ------------------------------------------------


def test_missing_column_is_reported_first(layer) -> None:
    assert destinations.check_snap_layer(layer.drop(columns=["format_class"])) == [
        "missing column(s) ['format_class']"
    ]


def test_duplicate_site_id(layer) -> None:
    doubled = gpd.GeoDataFrame(
        pd.concat([layer, layer.iloc[:1]], ignore_index=True), geometry="geometry", crs=layer.crs
    )
    problems = destinations.check_snap_layer(doubled)
    assert len(problems) == 1 and "duplicate site ID" in problems[0]


def test_site_id_form(layer) -> None:
    bad = _copy(layer)
    bad.loc[0, "site_id"] = "usda:" + bad.loc[0, "source_record_id"]
    problems = destinations.check_snap_layer(bad)
    assert len(problems) == 1 and "snap_retailers:<record id>" in problems[0]


def test_class_disagreeing_with_mapping(layer) -> None:
    bad = _copy(layer)
    row = bad.index[bad["store_type"] == "Convenience Store"][0]
    bad.loc[row, "format_class"] = "supermarket"
    problems = destinations.check_snap_layer(bad)
    assert any("disagrees with the mapping" in p for p in problems)
    assert any("supermarket_format disagrees" in p for p in problems)


def test_class_outside_vocabulary_and_unknown_type(layer) -> None:
    bad = _copy(layer)
    bad.loc[0, "format_class"] = "healthy_food"
    assert any("outside the vocabulary" in p for p in destinations.check_snap_layer(bad))
    bad = _copy(layer)
    bad.loc[0, "store_type"] = "Hypermarket"
    assert any("outside the mapping" in p for p in destinations.check_snap_layer(bad))


def test_flag_not_boolean(layer) -> None:
    bad = _copy(layer)
    bad["supermarket_format"] = bad["supermarket_format"].astype(object)
    bad.loc[0, "supermarket_format"] = None
    assert any("non-null boolean" in p for p in destinations.check_snap_layer(bad))


def test_geoid_pattern_and_spine_membership(layer, spine) -> None:
    bad = _copy(layer)
    bad.loc[0, "geoid"] = "42003000100"
    problems = destinations.check_snap_layer(bad, spine_geoids=spine["geoid"])
    assert len(problems) == 2, problems
    assert "not Philadelphia County tracts" in problems[0] and "not in the spine" in problems[1]
    bad.loc[0, "geoid"] = "42101999999"  # well-formed, but no such spine tract
    problems = destinations.check_snap_layer(bad, spine_geoids=spine["geoid"])
    assert problems == ["1 tract ID(s) not in the spine: ['42101999999']"]


def test_wrong_crs_short_circuits(layer) -> None:
    problems = destinations.check_snap_layer(layer.to_crs("EPSG:4326"))
    assert problems == [f"CRS is {layer.to_crs('EPSG:4326').crs!r}, expected {ANALYSIS_CRS}"]


def test_point_outside_county_bounds(layer) -> None:
    shifted = layer.set_geometry(layer.geometry.translate(xoff=100_000.0))
    problems = destinations.check_snap_layer(shifted)
    assert len(problems) == 1 and "outside the county bounds" in problems[0]


def test_empty_layer(layer) -> None:
    assert "empty layer" in destinations.check_snap_layer(layer.iloc[:0])
