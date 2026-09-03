"""EP-5a / EP-5b / EP-6 / EP-7 / EP-8b integration: the real pipeline's eight stages,
offline.

A fake transport (``conftest.SampleTransport``) serves the committed samples
under the adapters' real URLs, so ``acquire`` and ``validate`` run exactly as
they do against the Census and USDA hosts (allowlist, caps, archive guards,
terms check, manifest, admission) without a network; ``spine`` /
``demographics`` (EP-5b) build the curated spine from the six sample tracts,
``snap_retailers`` (EP-6) the classified retailer layer on it, ``basemap``
(EP-8b) the major-roads layer, and ``metrics`` / ``publish`` (EP-7, EP-8b) the
QA slice metric and the gated public zone with its basemap file. The
suite-wide socket guard in ``conftest.py`` would fail any test that tried to
connect.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from pyproj import CRS
from typer.testing import CliRunner

from phillysim import basemap, pipeline, runner
from phillysim.adapters import ADAPTERS, acs, snap, tiger_roads
from phillysim.classify.store_format import MAPPING_VERSION
from phillysim.cli import app
from phillysim.destinations import SNAP_LAYER_COLUMNS, SNAP_REPORT, SNAP_RETAILERS, check_snap_layer
from phillysim.fixtures.pipeline import fixture_pipeline
from phillysim.metrics import slice as qa_slice
from phillysim.pipeline import (
    ACQUISITION,
    PUBLISH_SOURCES,
    RAW_SNAPSHOTS,
    SNAPSHOT_ID,
    VALIDATION,
    real_pipeline,
)
from phillysim.publish.bucket import BUCKET_A
from phillysim.publish.export import (
    BASEMAP_GEOJSON,
    PUBLIC_FILES,
    PUBLIC_MANIFEST,
    PUBLIC_ZONE,
    SITES_CSV,
    TRACTS_CSV,
    TRACTS_GEOJSON,
)
from phillysim.publish.gate import check_public_zone
from phillysim.quarantine import list_quarantined
from phillysim.runner import StateError
from phillysim.spine import ACS_TRACTS, ANALYSIS_CRS, SPINE, SPINE_COLUMNS, check_spine
from phillysim.stages import Pipeline, StageError

STAGES = [
    "acquire",
    "validate",
    "spine",
    "demographics",
    "snap_retailers",
    "basemap",
    "metrics",
    "publish",
]
SAMPLE_TRACTS = 6
SAMPLE_RETAILERS = 26
SAMPLE_SUPERMARKET_FORMAT = 5
SAMPLE_ROADS = 48


def _pipeline(transport) -> Pipeline:
    """The real pipeline on the fake transport, expecting the samples' six tracts."""
    return real_pipeline(opener=transport).with_params({"spine": {"expected_tracts": 6}})


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "data"


def test_acquire_and_validate_end_to_end(root: Path, sample_transport) -> None:
    transport = sample_transport()
    lines: list[str] = []
    report = runner.run(root, _pipeline(transport), echo=lines.append)
    assert report.ran == STAGES and report.skipped == []
    expected_calls = Counter(
        fetch.url for adapter in ADAPTERS.values() for fetch in adapter.spec.files
    )
    expected_calls.update(adapter.spec.terms.url for adapter in ADAPTERS.values())
    assert Counter(transport.calls) == expected_calls, "each file once, the terms page per source"

    for rel in RAW_SNAPSHOTS:
        snapshot = root / rel
        manifest = json.loads((snapshot / "manifest.json").read_text("utf-8"))
        archived = ADAPTERS[manifest["source"]].spec.terms.file_name
        assert manifest["terms_archive"] == archived and (snapshot / archived).is_file()
        assert manifest["license_bucket"] == "A" and manifest["license_note"]
        assert manifest["synthetic"] is False
        assert manifest["terms_archive"] in manifest["files"]
    acquisition = json.loads((root / ACQUISITION).read_text("utf-8"))
    assert acquisition["snapshot_id"] == SNAPSHOT_ID
    for source, entry in acquisition["sources"].items():
        assert entry["reused"] is False and entry["bytes"] > 0 and entry["fetches"]
        assert entry["filter"] == ADAPTERS[source].filter_note
        assert entry["limits"]["max_file_bytes"] == ADAPTERS[source].spec.limits.max_file_bytes
    validation = json.loads((root / VALIDATION).read_text("utf-8"))
    assert (
        set(validation)
        == set(pipeline.SOURCES)
        == {"acs", "cenpop", "snap_retailers", "tiger_roads", "tiger_tracts"}
    )
    assert all(v["violations"] == [] for v in validation.values())
    assert all(
        v["rows"] == 6 for s, v in validation.items() if s not in {snap.SOURCE, tiger_roads.SOURCE}
    )
    assert validation[snap.SOURCE]["rows"] == SAMPLE_RETAILERS
    assert validation[tiger_roads.SOURCE]["rows"] == SAMPLE_ROADS
    assert not any((root / "quarantine").iterdir())
    manifest = json.loads((root / "raw" / snap.SOURCE / SNAPSHOT_ID / "manifest.json").read_text())
    assert (
        manifest["acquisition_url"] == snap.URL and manifest["acquisition_url_alt"] == snap.URL_ALT
    )
    assert manifest["terms_archive"] == snap.PAGE_FILE

    # EP-5b: the curated spine and the ACS join on the six sample tracts.
    spine = gpd.read_parquet(root / SPINE)
    assert tuple(spine.columns) == SPINE_COLUMNS and len(spine) == SAMPLE_TRACTS
    assert CRS.from_user_input(spine.crs) == CRS.from_user_input(ANALYSIS_CRS)
    acs_tracts = pd.read_parquet(root / ACS_TRACTS)
    assert list(acs_tracts.columns) == ["geoid", *acs.column_names()]
    assert list(acs_tracts["geoid"]) == list(spine["geoid"])
    assert check_spine(spine, expected_tracts=SAMPLE_TRACTS, acs=acs_tracts) == []
    state = json.loads((root / runner.STATE_FILE).read_text("utf-8"))
    assert state["stages"]["spine"]["params"] == {"crs": ANALYSIS_CRS, "expected_tracts": 6}

    # EP-6: the classified SNAP retailer layer on the six sample tracts.
    layer = gpd.read_parquet(root / SNAP_RETAILERS)
    assert tuple(layer.columns) == SNAP_LAYER_COLUMNS and len(layer) == SAMPLE_RETAILERS
    assert CRS.from_user_input(layer.crs) == CRS.from_user_input(ANALYSIS_CRS)
    assert check_snap_layer(layer, spine_geoids=spine["geoid"]) == []
    assert layer["geoid"].notna().all() and set(layer["geoid"]) <= set(spine["geoid"])
    assert layer["supermarket_format"].sum() == 5, "the sample's Supermarket + Super Store rows"
    report = json.loads((root / SNAP_REPORT).read_text("utf-8"))
    assert report["rows"] == SAMPLE_RETAILERS and report["supermarket_format"] == 5
    assert report["mapping_version"] == MAPPING_VERSION and report["as_of"] == snap.AS_OF
    assert state["stages"]["snap_retailers"]["params"] == {
        "crs": ANALYSIS_CRS,
        "mapping_version": MAPPING_VERSION,
        "as_of": snap.AS_OF,
    }

    # EP-8b: the basemap roads layer, the major roads crossing the six sample tracts.
    roads = gpd.read_parquet(root / basemap.ROADS)
    assert tuple(roads.columns) == basemap.ROAD_COLUMNS and len(roads) == SAMPLE_ROADS
    assert CRS.from_user_input(roads.crs) == CRS.from_user_input(ANALYSIS_CRS)
    assert basemap.check_roads(roads, spine=spine) == []
    basemap_report = json.loads((root / basemap.BASEMAP_REPORT).read_text("utf-8"))
    assert basemap_report["rows"] == SAMPLE_ROADS and basemap_report["length_km"] > 20
    assert state["stages"]["basemap"]["params"] == {
        "crs": ANALYSIS_CRS,
        "road_classes": ["S1100", "S1200"],
    }

    # EP-7: the QA slice metric on the six tracts, and the gated public zone (Bucket A).
    table = pd.read_parquet(root / qa_slice.TRACT_METRICS)
    assert len(table) == SAMPLE_TRACTS and set(table["metric_id"]) == {qa_slice.METRIC_ID}
    assert table["estimate"].notna().all() and (table["estimate"] > 0).all()
    assert set(table["methods_version"]) == {qa_slice.METHODS_VERSION}
    slice_report = json.loads((root / qa_slice.SLICE_REPORT).read_text("utf-8"))
    assert slice_report["destinations"] == SAMPLE_SUPERMARKET_FORMAT and slice_report["qa_only"]
    public = root / PUBLIC_ZONE
    assert sorted(p.name for p in public.iterdir()) == sorted([*PUBLIC_FILES, PUBLIC_MANIFEST])
    assert (
        check_public_zone(public, bounds=tuple(real_pipeline()["publish"].params["bounds"])) == []
    )
    manifest = json.loads((public / PUBLIC_MANIFEST).read_text("utf-8"))
    assert (
        manifest["pipeline"] == "real" and manifest["methods_version"] == qa_slice.METHODS_VERSION
    )
    assert [s["source"] for s in manifest["sources"]] == list(PUBLISH_SOURCES)
    assert all(s["license_bucket"] == BUCKET_A and not s["synthetic"] for s in manifest["sources"])
    assert all(entry["bucket"] == BUCKET_A for entry in manifest["files"].values())
    assert manifest["license"]["spdx_id"] == "CC-BY-4.0"
    assert any("SNAP Retailer Locator" in line for line in manifest["attribution"])
    assert manifest["files"][TRACTS_GEOJSON]["rows"] == SAMPLE_TRACTS
    assert manifest["files"][SITES_CSV]["rows"] == SAMPLE_SUPERMARKET_FORMAT
    # EP-8b: the basemap file holds the boundary and every sample road (schema version 2).
    assert manifest["public_schema_version"] == 2
    assert manifest["basemap"] == {
        "file": BASEMAP_GEOJSON,
        "layers": {"county_boundary": 1, "roads": SAMPLE_ROADS},
    }
    assert manifest["files"][BASEMAP_GEOJSON]["rows"] == SAMPLE_ROADS + 1
    basemap_file = json.loads((public / BASEMAP_GEOJSON).read_text("utf-8"))
    boundary, *lines = basemap_file["features"]
    assert boundary["properties"]["layer"] == "county_boundary"
    assert boundary["properties"]["name"] == "Philadelphia County"
    assert boundary["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert {f["properties"]["layer"] for f in lines} == {"roads"}
    assert {f["geometry"]["type"] for f in lines} == {"LineString"}
    assert [f["id"] for f in lines] == sorted("roads:" + rid for rid in roads["linearid"])
    assert any("TIGER/Line Shapefiles 2025, roads" in line for line in manifest["attribution"])
    fields = manifest["fields"]
    assert len(fields) == 1 and fields[0]["qa_only"] is True
    assert fields[0]["column"] == f"{qa_slice.METRIC_ID}__{qa_slice.CATEGORY}"
    assert "qa_note" in manifest
    tracts = pd.read_csv(public / TRACTS_CSV, dtype={"geoid": str})
    assert list(tracts["geoid"]) == list(spine["geoid"])
    assert tracts[f"{fields[0]['column']}_bin"].between(1, 5).all()
    assert "Census Tract" in tracts["name"].iloc[0]
    state = json.loads((root / runner.STATE_FILE).read_text("utf-8"))
    assert state["stages"]["publish"]["outputs"] == {
        PUBLIC_ZONE: state["stages"]["publish"]["outputs"][PUBLIC_ZONE]
    }

    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 0, verify.output
    assert "5 of 5 snapshot(s) verified" in verify.output
    assert "pipeline 'real'" in verify.output and "8 of 8 stage(s) done and intact" in verify.output
    gate = CliRunner().invoke(app, ["gate", "--data-root", str(root)])
    assert gate.exit_code == 0, gate.output
    assert "Bucket A (CC-BY-4.0)" in gate.output and "pipeline 'real'" in gate.output
    assert "5 file(s) labeled, 4 source(s)" in gate.output
    # The CLI's pipeline expects the county's 408 tracts, so the six-tract spine built with
    # the overridden parameter is stale on parameters there (and only there).
    status = CliRunner().invoke(app, ["status", "--data-root", str(root)])
    assert status.exit_code == 0 and "7 fresh, 1 stale, 0 missing, 0 incomplete" in status.output
    assert "stale      spine" in status.output and "changed: parameters" in status.output
    assert runner.status(root, _pipeline(transport))[2].status == "fresh"

    calls_before = len(transport.calls)
    second = runner.run(root, _pipeline(transport))
    assert second.ran == [] and second.skipped == STAGES
    assert len(transport.calls) == calls_before, "a fresh run opens no connection"


def test_existing_snapshots_are_reused_never_refetched(root: Path, sample_transport) -> None:
    transport = sample_transport()
    runner.run(root, _pipeline(transport))
    calls = len(transport.calls)
    (root / runner.STATE_FILE).unlink()  # the state file is lost; the raw zone is not
    report = runner.run(root, _pipeline(transport))
    assert report.ran == STAGES
    assert len(transport.calls) == calls, "verified snapshots in the raw zone are re-used"
    acquisition = json.loads((root / ACQUISITION).read_text("utf-8"))
    assert all(entry["reused"] is True for entry in acquisition["sources"].values())
    assert CliRunner().invoke(app, ["verify", "--data-root", str(root)]).exit_code == 0


def test_tampered_existing_snapshot_is_refused_not_replaced(root: Path, sample_transport) -> None:
    transport = sample_transport()
    runner.run(root, _pipeline(transport))
    target = root / "raw" / "cenpop" / SNAPSHOT_ID / "CenPop2020_Mean_TR42.txt"
    target.write_bytes(target.read_bytes() + b"tampered\n")
    (root / runner.STATE_FILE).unlink()
    with pytest.raises(StageError, match="fails verification"):
        runner.run(root, _pipeline(transport))
    assert target.read_bytes().endswith(b"tampered\n"), "the raw zone is never rewritten"
    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 1 and "FAIL cenpop/2026-09-02" in verify.output


def test_terms_drift_stops_acquisition_and_quarantines(root: Path, sample_transport) -> None:
    transport = sample_transport(terms=b"<html>The terms have changed.</html>")
    with pytest.raises(StageError, match="quarantined \\(terms\\)"):
        runner.run(root, _pipeline(transport))
    records = list_quarantined(root / "quarantine")
    assert len(records) == 1 and records[0].kind == "terms" and records[0].source == "acs"
    assert "freely available" in records[0].reason
    assert not (root / "raw").exists() or not any((root / "raw").iterdir())
    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 1, verify.output
    assert "0 of 0 snapshot(s) verified" in verify.output
    assert "0 of 8 stage(s) done and intact; incomplete: acquire" in verify.output
    assert "quarantined (terms)" in verify.output
    status = CliRunner().invoke(app, ["status", "--data-root", str(root)])
    assert "incomplete acquire" in status.output


def test_real_and_fixture_state_files_never_mix(root: Path, sample_transport) -> None:
    runner.run(root, _pipeline(sample_transport()))
    with pytest.raises(StateError, match="belongs to pipeline 'real'"):
        runner.run(root, fixture_pipeline())
    # The real pipeline shares the fixture's first four and last two stage names;
    # `snap_retailers` (EP-6) is the first per-source destination layer and `basemap`
    # (EP-8b) the roads layer, neither with a fixture counterpart (the fixture's basemap is
    # the boundary only), and the fixture's middle stages (M3 / M4) have no real body yet.
    assert real_pipeline().names == tuple(STAGES)
    assert real_pipeline().names[:4] == fixture_pipeline().names[:4]
    assert real_pipeline().names[-2:] == fixture_pipeline().names[-2:] == ("metrics", "publish")
    assert "snap_retailers" not in fixture_pipeline().names
    assert "basemap" not in fixture_pipeline().names
    assert (
        real_pipeline()["publish"].outputs == fixture_pipeline()["publish"].outputs == ("public",)
    )
