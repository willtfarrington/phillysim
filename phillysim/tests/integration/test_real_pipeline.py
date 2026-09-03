"""EP-5a / EP-5b / EP-6 / EP-7 / EP-8b / EP-12 integration: the real pipeline's nine
stages, offline.

A fake transport (``conftest.SampleTransport``) serves the committed samples
under the adapters' real URLs, so ``acquire`` and ``validate`` run exactly as
they do against the providers' hosts (allowlist, caps, archive guards, pinned
digests and the MD5 sidecar, terms check, manifest, admission) without a
network; ``spine`` / ``demographics`` (EP-5b) build the curated spine from the
six sample tracts, ``snap_retailers`` (EP-6) the classified retailer layer on
it, ``basemap`` (EP-8b) the major-roads layer, ``network`` (EP-12) the clipped
OSM sample and the unwrapped synthetic feeds (the first Bucket B output of the
real pipeline, never published), and ``metrics`` / ``publish`` (EP-7, EP-8b)
the QA slice metric and the gated public zone with its basemap file, still
Bucket A. The suite-wide socket guard in ``conftest.py`` would fail any test
that tried to connect.
"""

from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from pyproj import CRS
from typer.testing import CliRunner

from conftest import SAMPLE_NODE_BAND, SAMPLE_WAY_BAND, sample_real_pipeline
from phillysim import basemap, pipeline, runner
from phillysim.adapters import ADAPTERS, acs, osm, septa_gtfs, snap, tiger_roads
from phillysim.classify.store_format import MAPPING_VERSION
from phillysim.cli import app
from phillysim.destinations import SNAP_LAYER_COLUMNS, SNAP_REPORT, SNAP_RETAILERS, check_snap_layer
from phillysim.fixtures.pipeline import fixture_pipeline
from phillysim.metrics import slice as qa_slice
from phillysim.network import NETWORK_DIR, NETWORK_REPORT, routing_box
from phillysim.pipeline import (
    ACQUISITION,
    PUBLISH_SOURCES,
    RAW_SNAPSHOTS,
    SNAPSHOT_IDS,
    VALIDATION,
    real_pipeline,
)
from phillysim.publish.bucket import BUCKET_A, BUCKET_B
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
    "network",
    "metrics",
    "publish",
]
SAMPLE_TRACTS = 6
SAMPLE_RETAILERS = 26
SAMPLE_SUPERMARKET_FORMAT = 5
SAMPLE_ROADS = 48
SAMPLE_BUS_STOPS = 7  # six tract centers plus the control stop outside the routing box
SAMPLE_RAIL_STOPS = 2


@pytest.fixture
def samples(spine_samples_dir: Path) -> Path:
    return spine_samples_dir


def _pipeline(transport, samples: Path) -> Pipeline:
    """The real pipeline on the fake transport, expecting the samples' six tracts."""
    return sample_real_pipeline(transport, samples)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "data"


def test_acquire_and_validate_end_to_end(root: Path, sample_transport, samples: Path) -> None:
    transport = sample_transport()
    lines: list[str] = []
    report = runner.run(root, _pipeline(transport, samples), echo=lines.append)
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
        assert manifest["snapshot_id"] == SNAPSHOT_IDS[manifest["source"]] == snapshot.name
        expected_bucket = "B" if manifest["source"] == osm.SOURCE else "A"
        assert manifest["license_bucket"] == expected_bucket and manifest["license_note"]
        # The guarded path builds every manifest with synthetic=False (it acquired real
        # bytes as far as it knows); the committed GTFS sample's own manifest says
        # synthetic=True, which its contract test checks.
        assert manifest["synthetic"] is False
        assert manifest["terms_archive"] in manifest["files"]
    acquisition = json.loads((root / ACQUISITION).read_text("utf-8"))
    assert acquisition["snapshot_ids"] == SNAPSHOT_IDS
    assert (
        acquisition["snapshot_ids"][osm.SOURCE]
        == "2026-09-03"
        != acquisition["snapshot_ids"]["acs"]
    )
    for source, entry in acquisition["sources"].items():
        assert entry["reused"] is False and entry["bytes"] > 0 and entry["fetches"]
        assert entry["snapshot_id"] == SNAPSHOT_IDS[source]
        assert entry["filter"] == ADAPTERS[source].filter_note
        assert entry["limits"]["max_file_bytes"] == ADAPTERS[source].spec.limits.max_file_bytes
    # EP-12: the pinned digests and the provider's sidecar are checked and recorded.
    assert set(acquisition["sources"][osm.SOURCE]["digests_checked"]) == {
        osm.FILE_NAME,
        f"{osm.FILE_NAME} (sidecar)",
    }
    assert list(acquisition["sources"][septa_gtfs.SOURCE]["digests_checked"]) == [
        septa_gtfs.FILE_NAME
    ]
    assert "digests_checked" not in acquisition["sources"]["acs"]
    validation = json.loads((root / VALIDATION).read_text("utf-8"))
    assert (
        set(validation)
        == set(pipeline.SOURCES)
        == {"acs", "cenpop", "gtfs", "osm_network", "snap_retailers", "tiger_roads", "tiger_tracts"}
    )
    assert all(v["violations"] == [] for v in validation.values())
    assert all(
        v["rows"] == 6
        for s, v in validation.items()
        if s not in {snap.SOURCE, tiger_roads.SOURCE, osm.SOURCE, septa_gtfs.SOURCE}
    )
    assert validation[snap.SOURCE]["rows"] == SAMPLE_RETAILERS
    assert validation[tiger_roads.SOURCE]["rows"] == SAMPLE_ROADS
    assert validation[osm.SOURCE]["rows"] == 1 and validation[osm.SOURCE]["license_bucket"] == "B"
    assert validation[septa_gtfs.SOURCE]["rows"] == 2
    assert validation[septa_gtfs.SOURCE]["nulls"] == {"missing_names": 2}, "nothing missing"
    assert not any((root / "quarantine").iterdir())
    manifest = json.loads(
        (root / "raw" / snap.SOURCE / SNAPSHOT_IDS[snap.SOURCE] / "manifest.json").read_text()
    )
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

    # EP-12: the routing inputs: the OSM sample clipped into the routing box (whole, since
    # the sample lies inside it) and the two synthetic feed zips, Bucket B by derivation.
    network_dir = root / NETWORK_DIR
    clip_name = osm.clip_file_name(5000)
    assert sorted(p.name for p in network_dir.iterdir()) == sorted([clip_name, *septa_gtfs.FEEDS])
    network_report = json.loads((root / NETWORK_REPORT).read_text("utf-8"))
    assert network_report["license_bucket"] == BUCKET_B
    assert network_report["buffer_m"] == 5000 and network_report["crs"] == ANALYSIS_CRS
    assert network_report["box"] == list(routing_box(5000))
    assert network_report["sources"] == {
        osm.SOURCE: f"raw/{osm.SOURCE}/2026-09-03",
        septa_gtfs.SOURCE: f"raw/{septa_gtfs.SOURCE}/2026-09-03",
    }
    counts = osm.count_objects(root / "raw" / osm.SOURCE / "2026-09-03" / osm.FILE_NAME)
    osm_report = network_report["osm"]
    assert (
        osm_report["file"] == clip_name
        and osm_report["bytes"] == (network_dir / clip_name).stat().st_size
    )
    assert osm_report["nodes"] == osm_report["nodes_in_box"] == counts["nodes"]
    assert osm_report["ways"] == counts["ways"] and osm_report["highway_ways"] >= 50
    assert SAMPLE_NODE_BAND[0] <= osm_report["nodes"] <= SAMPLE_NODE_BAND[1]
    assert SAMPLE_WAY_BAND[0] <= osm_report["ways"] <= SAMPLE_WAY_BAND[1]
    assert osm_report["source"] == counts
    gtfs_report = network_report["gtfs"]
    assert gtfs_report["google_bus.zip"]["stops"] == SAMPLE_BUS_STOPS
    assert gtfs_report["google_bus.zip"]["stops_outside_box"] == 1
    assert gtfs_report["google_bus.zip"]["stops_in_county_tracts"] == SAMPLE_TRACTS
    assert gtfs_report["google_rail.zip"]["stops"] == SAMPLE_RAIL_STOPS
    assert gtfs_report["google_rail.zip"]["stops_outside_box"] == 0
    for feed in septa_gtfs.FEEDS:
        assert gtfs_report[feed]["bytes"] == (network_dir / feed).stat().st_size
        assert zipfile.is_zipfile(network_dir / feed)
    assert not any(p.suffix == ".txt" for p in network_dir.rglob("*")), "feeds never expanded"
    assert (
        osm.check_clip(
            network_dir / clip_name,
            routing_box(5000),
            node_band=tuple(SAMPLE_NODE_BAND),
            way_band=tuple(SAMPLE_WAY_BAND),
        )
        == []
    )
    assert state["stages"]["network"]["params"] == {
        "buffer_m": 5000,
        "crs": ANALYSIS_CRS,
        "node_band": SAMPLE_NODE_BAND,
        "way_band": SAMPLE_WAY_BAND,
    }
    assert set(state["stages"]["network"]["inputs"]) == {
        SPINE,
        VALIDATION,
        f"raw/{osm.SOURCE}/2026-09-03",
        f"raw/{septa_gtfs.SOURCE}/2026-09-03",
    }

    # EP-7: the QA slice metric on the six tracts, and the gated public zone (Bucket A:
    # nothing downstream of ``network`` reaches ``publish``; EP-12 leaves it unchanged).
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
    assert osm.SOURCE not in PUBLISH_SOURCES and septa_gtfs.SOURCE not in PUBLISH_SOURCES
    assert all(s["license_bucket"] == BUCKET_A and not s["synthetic"] for s in manifest["sources"])
    assert all(entry["bucket"] == BUCKET_A for entry in manifest["files"].values())
    assert manifest["license"]["spdx_id"] == "CC-BY-4.0"
    assert any("SNAP Retailer Locator" in line for line in manifest["attribution"])
    assert not any("OpenStreetMap" in line or "SEPTA" in line for line in manifest["attribution"])
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
    assert state["stages"]["network"]["outputs"].keys() == {NETWORK_DIR, NETWORK_REPORT}

    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 0, verify.output
    assert "7 of 7 snapshot(s) verified" in verify.output
    assert "pipeline 'real'" in verify.output and "9 of 9 stage(s) done and intact" in verify.output
    gate = CliRunner().invoke(app, ["gate", "--data-root", str(root)])
    assert gate.exit_code == 0, gate.output
    assert "Bucket A (CC-BY-4.0)" in gate.output and "pipeline 'real'" in gate.output
    assert "5 file(s) labeled, 4 source(s)" in gate.output
    # The CLI's pipeline expects the county's 408 tracts and the county clip's bands, so the
    # six-tract spine and the sample clip built with the overridden parameters are stale on
    # parameters there (and only there).
    status = CliRunner().invoke(app, ["status", "--data-root", str(root)])
    assert status.exit_code == 0 and "7 fresh, 2 stale, 0 missing, 0 incomplete" in status.output
    assert "stale      spine" in status.output and "stale      network" in status.output
    assert "changed: parameters" in status.output
    assert all(s.status == "fresh" for s in runner.status(root, _pipeline(transport, samples)))

    calls_before = len(transport.calls)
    second = runner.run(root, _pipeline(transport, samples))
    assert second.ran == [] and second.skipped == STAGES
    assert len(transport.calls) == calls_before, "a fresh run opens no connection"


def test_existing_snapshots_are_reused_never_refetched(
    root: Path, sample_transport, samples: Path
) -> None:
    transport = sample_transport()
    runner.run(root, _pipeline(transport, samples))
    calls = len(transport.calls)
    (root / runner.STATE_FILE).unlink()  # the state file is lost; the raw zone is not
    report = runner.run(root, _pipeline(transport, samples))
    assert report.ran == STAGES
    assert len(transport.calls) == calls, "verified snapshots in the raw zone are re-used"
    acquisition = json.loads((root / ACQUISITION).read_text("utf-8"))
    assert all(entry["reused"] is True for entry in acquisition["sources"].values())
    assert CliRunner().invoke(app, ["verify", "--data-root", str(root)]).exit_code == 0


def test_tampered_existing_snapshot_is_refused_not_replaced(
    root: Path, sample_transport, samples: Path
) -> None:
    transport = sample_transport()
    runner.run(root, _pipeline(transport, samples))
    target = root / "raw" / "cenpop" / SNAPSHOT_IDS["cenpop"] / "CenPop2020_Mean_TR42.txt"
    target.write_bytes(target.read_bytes() + b"tampered\n")
    (root / runner.STATE_FILE).unlink()
    with pytest.raises(StageError, match="fails verification"):
        runner.run(root, _pipeline(transport, samples))
    assert target.read_bytes().endswith(b"tampered\n"), "the raw zone is never rewritten"
    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 1 and "FAIL cenpop/2026-09-02" in verify.output


def test_terms_drift_stops_acquisition_and_quarantines(
    root: Path, sample_transport, samples: Path
) -> None:
    transport = sample_transport(terms=b"<html>The terms have changed.</html>")
    with pytest.raises(StageError, match="quarantined \\(terms\\)"):
        runner.run(root, _pipeline(transport, samples))
    records = list_quarantined(root / "quarantine")
    assert len(records) == 1 and records[0].kind == "terms" and records[0].source == "acs"
    assert "freely available" in records[0].reason
    assert not (root / "raw").exists() or not any((root / "raw").iterdir())
    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 1, verify.output
    assert "0 of 0 snapshot(s) verified" in verify.output
    assert "0 of 9 stage(s) done and intact; incomplete: acquire" in verify.output
    assert "quarantined (terms)" in verify.output
    status = CliRunner().invoke(app, ["status", "--data-root", str(root)])
    assert "incomplete acquire" in status.output


def test_replaced_provider_bytes_stop_acquisition_with_a_digest_quarantine(
    root: Path, sample_transport, samples: Path
) -> None:
    """EP-12: the pinned digest of a routing source no longer matches the delivered bytes."""
    transport = sample_transport()
    pins = {septa_gtfs.SOURCE: {septa_gtfs.FILE_NAME: "sha256:" + "0" * 64}}
    with pytest.raises(StageError, match="quarantined \\(digest\\)"):
        runner.run(root, real_pipeline(opener=transport, pins=pins))
    records = list_quarantined(root / "quarantine")
    assert [(r.kind, r.source) for r in records] == [("digest", septa_gtfs.SOURCE)]
    assert "pinned" in records[0].reason
    assert not (root / "raw" / septa_gtfs.SOURCE).exists()


def test_real_and_fixture_state_files_never_mix(
    root: Path, sample_transport, samples: Path
) -> None:
    runner.run(root, _pipeline(sample_transport(), samples))
    with pytest.raises(StateError, match="belongs to pipeline 'real'"):
        runner.run(root, fixture_pipeline())
    # The real pipeline shares the fixture's first four and last two stage names and, since
    # EP-12, the ``network`` stage name (architecture.md stage 8; different bodies);
    # `snap_retailers` (EP-6) is the first per-source destination layer and `basemap`
    # (EP-8b) the roads layer, neither with a fixture counterpart (the fixture's basemap is
    # the boundary only), and the fixture's other middle stages (M4) have no real body yet.
    assert real_pipeline().names == tuple(STAGES)
    assert real_pipeline().names[:4] == fixture_pipeline().names[:4]
    assert real_pipeline().names[-2:] == fixture_pipeline().names[-2:] == ("metrics", "publish")
    assert "network" in real_pipeline().names and "network" in fixture_pipeline().names
    assert real_pipeline()["network"].outputs[-1] == fixture_pipeline()["network"].outputs[-1]
    assert "snap_retailers" not in fixture_pipeline().names
    assert "basemap" not in fixture_pipeline().names
    assert (
        real_pipeline()["publish"].outputs == fixture_pipeline()["publish"].outputs == ("public",)
    )
