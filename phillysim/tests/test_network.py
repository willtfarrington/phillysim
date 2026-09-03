"""EP-12: the routing box, the way-complete OSM clip and its contract, and the feed
unwrap, on crafted PBF bytes and the committed samples (offline).

The clip is exercised on a tiny hand-built extract (nodes inside and outside a box,
ways that cross it, lie inside it, or lie wholly outside it, a turn restriction whose
members are kept and one whose member is not) so every rule of
``phillysim.adapters.osm.clip`` and ``check_clip`` is visible; the same function on the
real state extract is what the ``network`` stage runs, and its sample-scale run is the
integration suite's. The clip's determinism (byte-identical on a repeat) is asserted.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import osmium
import osmium.osm
import osmium.osm.mutable as mutable
import pytest

from phillysim.adapters import osm, septa_gtfs
from phillysim.adapters.base import COUNTY_BOUNDS, ROUTING_BUFFER_M, buffered_bounds
from phillysim.network import NETWORK_DIR, NETWORK_REPORT, routing_box
from phillysim.pipeline import real_pipeline
from phillysim.spine import ANALYSIS_CRS

BOX = (-75.20, 40.00, -75.10, 40.05)


# --- the routing box ------------------------------------------------------------------------


def test_routing_box_is_the_county_bounds_buffered_in_the_analysis_crs() -> None:
    box = routing_box(ROUTING_BUFFER_M)
    assert box == buffered_bounds(COUNTY_BOUNDS, ROUTING_BUFFER_M, ANALYSIS_CRS)
    minx, miny, maxx, maxy = box
    assert minx < COUNTY_BOUNDS[0] and miny < COUNTY_BOUNDS[1]
    assert maxx > COUNTY_BOUNDS[2] and maxy > COUNTY_BOUNDS[3]
    # 5 km is about 0.045 degrees of latitude and about 0.059 degrees of longitude here.
    assert 0.040 < COUNTY_BOUNDS[1] - miny < 0.050 and 0.040 < maxy - COUNTY_BOUNDS[3] < 0.050
    assert 0.055 < COUNTY_BOUNDS[0] - minx < 0.065 and 0.055 < maxx - COUNTY_BOUNDS[2] < 0.065
    # With no buffer the box is the envelope of the projected rectangle's corners, which
    # grows the degree bounds by about 0.0013 degrees (the quadrilateral is not axis-aligned
    # in UTM); never smaller than the bounds.
    assert routing_box(0) == pytest.approx(COUNTY_BOUNDS, abs=2e-3)
    assert routing_box(0)[0] <= COUNTY_BOUNDS[0] and routing_box(0)[2] >= COUNTY_BOUNDS[2]
    assert routing_box(10_000)[0] < box[0], "a larger buffer, a larger box"


def test_the_pinned_extent_is_a_stage_parameter() -> None:
    stage = real_pipeline()["network"]
    assert stage.params["buffer_m"] == ROUTING_BUFFER_M == 5000
    assert stage.params["crs"] == ANALYSIS_CRS
    assert stage.params["node_band"] == list(osm.CLIP_NODE_BAND)
    assert stage.params["way_band"] == list(osm.CLIP_WAY_BAND)
    assert stage.outputs == (NETWORK_DIR, NETWORK_REPORT)
    assert "raw/osm_network/2026-09-03" in stage.inputs and "raw/gtfs/2026-09-03" in stage.inputs


def test_band_parameters_are_validated() -> None:
    assert osm.band([1, 2]) == (1, 2)
    with pytest.raises(ValueError):
        osm.band([2, 1])
    with pytest.raises(ValueError):
        osm.band([-1, 1])


# --- a hand-built extract ----------------------------------------------------------------------


def _write_extract(path: Path) -> None:
    """Nodes 1-4 inside the box, 5-8 outside; way 10 inside (highway), way 11 crossing (a
    node outside; highway), way 12 wholly outside, way 13 inside without a highway tag;
    restriction 20 over kept ways, restriction 21 with an outside member, route relation 22."""
    header = osmium.io.Header()
    header.set("generator", "test")
    header.set("osmosis_replication_timestamp", "2026-08-31T20:21:20Z")
    inside = {1: (-75.19, 40.01), 2: (-75.18, 40.02), 3: (-75.17, 40.03), 4: (-75.16, 40.04)}
    outside = {5: (-75.30, 40.10), 6: (-75.31, 40.11), 7: (-75.32, 40.12), 8: (-75.33, 40.13)}
    with osmium.SimpleWriter(str(path), header=header) as writer:
        for nid, (lon, lat) in {**inside, **outside}.items():
            tags = {"highway": "crossing"} if nid == 2 else {}
            writer.add_node(mutable.Node(id=nid, location=(lon, lat), tags=tags, version=1))
        writer.add_way(mutable.Way(id=10, nodes=[1, 2], tags={"highway": "residential"}, version=1))
        writer.add_way(mutable.Way(id=11, nodes=[3, 5, 6], tags={"highway": "primary"}, version=1))
        writer.add_way(mutable.Way(id=12, nodes=[7, 8], tags={"highway": "primary"}, version=1))
        writer.add_way(mutable.Way(id=13, nodes=[2, 4], tags={"building": "yes"}, version=1))
        writer.add_relation(
            mutable.Relation(
                id=20,
                members=[("w", 10, "from"), ("n", 2, "via"), ("w", 13, "to")],
                tags={"type": "restriction", "restriction": "no_left_turn"},
                version=1,
            )
        )
        writer.add_relation(
            mutable.Relation(
                id=21,
                members=[("w", 11, "from"), ("n", 5, "via"), ("w", 12, "to")],
                tags={"type": "restriction", "restriction": "no_u_turn"},
                version=1,
            )
        )
        writer.add_relation(
            mutable.Relation(
                id=22,
                members=[("w", 10, ""), ("w", 11, "")],
                tags={"type": "route", "route": "bus"},
                version=1,
            )
        )


@pytest.fixture
def extract(tmp_path: Path) -> Path:
    path = tmp_path / "state.osm.pbf"
    _write_extract(path)
    return path


def _ids(path: Path, entity) -> list[int]:
    return [obj.id for obj in osmium.FileProcessor(str(path), entity)]


def test_clip_is_way_complete_and_keeps_local_restrictions(extract: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.osm.pbf"
    report = osm.clip(extract, out, BOX)
    assert _ids(out, osmium.osm.NODE) == [1, 2, 3, 4, 5, 6], "5 and 6 kept for way 11"
    assert _ids(out, osmium.osm.WAY) == [10, 11, 13], "12 lies wholly outside"
    assert _ids(out, osmium.osm.RELATION) == [20], (
        "21 has an outside member; 22 is not a restriction"
    )
    assert (report.nodes, report.nodes_in_box, report.ways, report.highway_ways) == (6, 4, 3, 2)
    assert report.relations == 1 and (report.source_nodes, report.source_ways) == (8, 4)
    assert report.source_relations == 3 and report.file_name == "clip.osm.pbf"
    assert report.bytes == out.stat().st_size and report.box == BOX
    header = osm.read_header(out)
    assert header["box_valid"] and tuple(round(v, 6) for v in header["bbox"]) == BOX
    assert header["generator"].startswith("phillysim clip of state.osm.pbf (test)")
    assert header["replication_timestamp"] == "2026-08-31T20:21:20Z"
    assert header["sorting"] == "Type_then_ID"
    tags = {way.id: dict(way.tags) for way in osmium.FileProcessor(str(out), osmium.osm.WAY)}
    assert tags[11] == {"highway": "primary"}, "tags and metadata kept as delivered"
    assert osm.check_clip(out, BOX, node_band=(1, 10), way_band=(1, 10)) == []


def test_clip_is_deterministic(extract: Path, tmp_path: Path) -> None:
    first, second = tmp_path / "a.osm.pbf", tmp_path / "b.osm.pbf"
    osm.clip(extract, first, BOX)
    osm.clip(extract, second, BOX)
    assert (
        hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    )


def test_clip_header_box_can_be_the_providers(extract: Path, tmp_path: Path) -> None:
    out = tmp_path / "sample.osm.pbf"
    osm.clip(extract, out, BOX, header_box=(-81.0, 38.0, -74.0, 43.0))
    assert tuple(osm.read_header(out)["bbox"]) == (-81.0, 38.0, -74.0, 43.0)
    problems = osm.check_clip(out, BOX, node_band=(1, 10), way_band=(1, 10))
    assert len(problems) == 1 and "header box" in problems[0]


def test_check_clip_names_every_violation(extract: Path, tmp_path: Path) -> None:
    out = tmp_path / "clip.osm.pbf"
    osm.clip(extract, out, BOX)
    problems = osm.check_clip(out, BOX, node_band=(100, 200), way_band=(0, 1))
    assert len(problems) == 2 and "6 nodes" in problems[0] and "3 ways" in problems[1]
    # A stray node outside the box that no kept way references breaks the invariant.
    with osmium.SimpleWriter(str(tmp_path / "stray.osm.pbf")) as writer:
        for obj in osmium.FileProcessor(str(out)):
            writer.add(obj)
        writer.add_node(mutable.Node(id=99, location=(-75.5, 40.5), version=1))
    problems = osm.check_clip(tmp_path / "stray.osm.pbf", BOX, node_band=(1, 10), way_band=(1, 10))
    assert any("referenced by no way" in p and "[99]" in p for p in problems)
    assert any("no bounding box" in p for p in problems), "the stray file was written without a box"
    no_highways = tmp_path / "nohw.osm.pbf"
    osm.clip(extract, no_highways, (-75.185, 40.035, -75.155, 40.045))  # node 4 only: way 13
    problems = osm.check_clip(
        no_highways, (-75.185, 40.035, -75.155, 40.045), node_band=(1, 10), way_band=(1, 10)
    )
    assert problems == ["no highway ways: not a street network"]


def test_unreadable_file_is_one_violation(tmp_path: Path) -> None:
    bad = tmp_path / "bad.osm.pbf"
    bad.write_bytes(b"not a pbf")
    problems = osm.check_clip(bad, BOX, node_band=(0, 1), way_band=(0, 1))
    assert len(problems) == 1 and "not a readable PBF" in problems[0]


def test_clip_file_name_carries_the_extent() -> None:
    assert osm.clip_file_name(5000) == "pennsylvania-260831-philadelphia-5km.osm.pbf"
    assert osm.clip_file_name(2500) == "pennsylvania-260831-philadelphia-2.5km.osm.pbf"


# --- the samples through the stage's helpers -------------------------------------------------


def test_sample_extract_clips_into_the_routing_box_whole(
    spine_samples_dir: Path, tmp_path: Path
) -> None:
    sample = spine_samples_dir / "raw" / osm.SOURCE / "2026-09-03" / osm.FILE_NAME
    box = routing_box(ROUTING_BUFFER_M)
    report = osm.clip(sample, tmp_path / osm.clip_file_name(ROUTING_BUFFER_M), box)
    counts = osm.count_objects(sample)
    assert report.nodes == counts["nodes"] and report.ways == counts["ways"]
    assert report.nodes_in_box == counts["nodes"], "every sample node lies inside the county box"
    assert (
        osm.check_clip(tmp_path / report.file_name, box, node_band=(1, 10**6), way_band=(1, 10**6))
        == []
    )


def test_sample_feed_unwraps_beside_the_clip(spine_samples_dir: Path, tmp_path: Path) -> None:
    sample = spine_samples_dir / "raw" / septa_gtfs.SOURCE / "2026-09-03"
    written = septa_gtfs.unwrap(sample, tmp_path / "network")
    assert sorted(written) == sorted(septa_gtfs.FEEDS)
    for feed in septa_gtfs.FEEDS:
        stops = septa_gtfs.read_stops(sample, feed)
        assert septa_gtfs.outside_box(stops, routing_box(ROUTING_BUFFER_M)) == (
            1 if feed == "google_bus.zip" else 0
        )
