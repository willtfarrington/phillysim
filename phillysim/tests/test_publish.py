"""EP-7: license buckets, build-time bins, CSV escaping, the public-zone export, and the
publish gate: positive on the fixture pipeline's own public zone, then one negative per
gate check (an intentionally mislabeled file first, the packet's acceptance criterion)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import shape

from phillysim import runner
from phillysim.fixtures import pipeline as fx
from phillysim.fixtures.pipeline import FIXTURE_BOUNDS, fixture_pipeline
from phillysim.pipeline import PUBLISH_SOURCES, real_pipeline
from phillysim.publish import bins, export, gate
from phillysim.publish.bucket import BUCKET_A, BUCKET_B, LABELS, OSM_NOTICE, derive_bucket, label_of
from phillysim.publish.export import (
    PUBLIC_FILES,
    PUBLIC_MANIFEST,
    SITES_CSV,
    SITES_GEOJSON,
    TRACTS_CSV,
    TRACTS_GEOJSON,
    PublishError,
    escape_cell,
    json_bytes,
    widen,
)
from phillysim.publish.gate import PublishGateError, check_public_zone

# --- buckets ----------------------------------------------------------------------------------


def test_bucket_b_is_contagious_and_labels_carry_their_notices() -> None:
    assert derive_bucket(["A", "A"]) == BUCKET_A
    assert derive_bucket(["A", "B", "A"]) == BUCKET_B
    assert derive_bucket(["B"]) == BUCKET_B
    with pytest.raises(ValueError, match="unknown license bucket"):
        derive_bucket(["A", "C"])
    assert label_of("A").payload()["spdx_id"] == "CC-BY-4.0"
    assert label_of("A").notices == ()
    assert OSM_NOTICE in label_of("B").payload()["notices"]
    assert any("Open Database License" in n for n in LABELS["B"].notices)


# --- bins --------------------------------------------------------------------------------------


def test_quantile_edges_and_classes_by_hand() -> None:
    values = pd.Series([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    edges = bins.bin_edges(values, 5)
    assert edges == [1.0, 2.8, 4.6, 6.4, 8.2, 10.0]
    classes = bins.assign_bins(pd.Series([1.0, 2.8, 2.9, 6.4, 6.5, 10.0, None]), edges)
    assert classes.tolist()[:-1] == [1, 1, 2, 3, 4, 5]
    assert pd.isna(classes.iloc[-1])
    assert classes.dtype == "Int64"
    assert bins.bin_edges(values, 5, "equal_interval") == [1.0, 2.8, 4.6, 6.4, 8.2, 10.0]
    assert bins.bin_edges(pd.Series([0.0, 100.0, 50.0]), 2, "equal_interval") == [0.0, 50.0, 100.0]


def test_ties_collapse_edges_and_nulls_stay_null() -> None:
    same = pd.Series([7.0, 7.0, None, 7.0])
    edges = bins.bin_edges(same, 5)
    assert edges == [7.0]
    classes = bins.assign_bins(same, edges)
    assert classes.tolist()[:2] == [1, 1] and pd.isna(classes.iloc[2])
    assert bins.bin_edges(pd.Series([None, None], dtype="float64"), 5) == []
    assert bins.assign_bins(pd.Series([None, None], dtype="float64"), []).isna().all()
    record = bins.bin_record(edges, 5, "quantile")
    assert record == {"method": "quantile", "classes_requested": 5, "classes": 0, "edges": [7.0]}
    with pytest.raises(ValueError, match="unknown bin method"):
        bins.bin_edges(same, 5, "jenks")


# --- CSV escaping ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("=SUM(A1:A9)", "'=SUM(A1:A9)"),
        ("+1", "'+1"),
        ("-1", "'-1"),
        ("@cmd", "'@cmd"),
        ("\tx", "'\tx"),
        ("\rx", "'\rx"),
        ("Corner Market", "Corner Market"),
        ("", ""),
        (5, 5),
        (None, None),
    ],
)
def test_escape_cell(cell, expected) -> None:
    assert escape_cell(cell) == expected


def test_gate_cell_rule_allows_negative_numbers_only() -> None:
    assert gate._check_cell("-5.0") and gate._check_cell("-1e3") and gate._check_cell("")
    assert gate._check_cell("'=1") and gate._check_cell("plain")
    assert (
        not gate._check_cell("-5+3") and not gate._check_cell("=1") and not gate._check_cell("+1")
    )
    assert not gate._check_cell("@x") and not gate._check_cell("\t1") and not gate._check_cell("-")


def test_prohibited_vocabulary_in_names() -> None:
    assert gate._check_name("time_to_nearest_min", "x") == []
    for bad in ("healthy_food", "access_score", "tract_rank", "food_desert", "access_index"):
        assert gate._check_name(bad, "x"), bad
    assert gate._check_name("Not-a-slug", "x")


# --- widening ----------------------------------------------------------------------------------


def test_widen_names_columns_and_needs_descriptions(tinycity_dir: Path) -> None:
    metrics = pd.read_parquet(tinycity_dir / "expected" / "tract_metrics.parquet")
    wide, fields = widen(metrics, fx.DESCRIPTIONS)
    assert list(wide.index) == sorted(metrics["geoid"].unique())
    columns = [f["column"] for f in fields]
    assert columns[0] == "population_total"
    assert "time_to_nearest_min__supermarket_format__walk_transit" in columns
    assert all(not f["qa_only"] for f in fields)
    assert {f"{c}_{s}" for c in columns for s in ("moe", "cv_tier", "reliability_action")} <= set(
        wide
    )
    with pytest.raises(PublishError, match="no description"):
        widen(metrics, {})
    doubled = pd.concat([metrics, metrics.iloc[:1]], ignore_index=True)
    with pytest.raises(PublishError, match="occurs twice"):
        widen(doubled, fx.DESCRIPTIONS)
    with pytest.raises(PublishError, match="breaks its contract"):
        widen(metrics.drop(columns=["moe"]), fx.DESCRIPTIONS)


# --- the fixture's public zone (positive) --------------------------------------------------------


@pytest.fixture(scope="module")
def zone(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture pipeline's installed public zone (built once for this module)."""
    root = tmp_path_factory.mktemp("fixture-root")
    runner.run(root, fixture_pipeline())
    return root / export.PUBLIC_ZONE


@pytest.fixture
def copy(zone: Path, tmp_path: Path) -> Path:
    """A scratch copy of the zone to tamper with."""
    target = tmp_path / "public"
    shutil.copytree(zone, target)
    return target


def _manifest(public: Path) -> dict:
    return json.loads((public / PUBLIC_MANIFEST).read_text("utf-8"))


def _write_manifest(public: Path, manifest: dict) -> None:
    (public / PUBLIC_MANIFEST).write_bytes(json_bytes(manifest))


def _problems(public: Path) -> list[str]:
    return check_public_zone(public, bounds=FIXTURE_BOUNDS)


def _assert_blocked(public: Path, *fragments: str) -> None:
    problems = _problems(public)
    assert problems, "the gate let a broken zone through"
    for fragment in fragments:
        assert any(fragment in p for p in problems), f"{fragment!r} not in {problems}"


def test_fixture_zone_is_green_bucket_b_and_complete(zone: Path) -> None:
    assert _problems(zone) == []
    assert sorted(p.name for p in zone.iterdir()) == sorted([*PUBLIC_FILES, PUBLIC_MANIFEST])
    manifest = _manifest(zone)
    assert manifest["pipeline"] == "fixture" and manifest["public_schema_version"] == 1
    assert manifest["license"]["bucket"] == BUCKET_B, "osm_network is Bucket B, so everything is"
    assert OSM_NOTICE in manifest["license"]["notices"]
    assert {s["source"] for s in manifest["sources"]} == set(fx.SOURCES)
    assert manifest["bounds"] == list(FIXTURE_BOUNDS)
    assert len(manifest["attribution"]) == 1, "identical citations are listed once"
    for name in PUBLIC_FILES:
        entry = manifest["files"][name]
        assert entry["bucket"] == BUCKET_B and entry["license"]["spdx_id"] == "ODbL-1.0"
        assert entry["sources"] == list(fx.SOURCES)
    assert manifest["files"][TRACTS_GEOJSON]["rows"] == manifest["files"][TRACTS_CSV]["rows"] == 6
    assert manifest["files"][SITES_GEOJSON]["rows"] == manifest["files"][SITES_CSV]["rows"] == 13
    assert "qa_note" not in manifest, "the fixture publishes no QA column"


def test_fixture_zone_geojson_is_rfc7946_and_labeled_in_file(zone: Path) -> None:
    tracts = json.loads((zone / TRACTS_GEOJSON).read_text("utf-8"))
    assert tracts["type"] == "FeatureCollection" and "crs" not in tracts
    assert tracts["license"] == label_of("B").payload() and tracts["table"] == "tracts"
    assert tracts["attribution"] and tracts["methods_version"] == fx.METHODS_VERSION
    for feature in tracts["features"]:
        assert feature["id"] == feature["properties"]["geoid"]
        polygon = shape(feature["geometry"])
        assert polygon.exterior.is_ccw, "exterior rings follow the right-hand rule"
        for coordinate in polygon.exterior.coords:
            assert len(str(coordinate[0]).split(".")[-1]) <= 6
    sites = json.loads((zone / SITES_GEOJSON).read_text("utf-8"))
    assert {f["geometry"]["type"] for f in sites["features"]} == {"Point"}
    assert {f["properties"]["category"] for f in sites["features"]} == set(fx.CATEGORIES)


def test_fixture_zone_bins_and_csv_parity(zone: Path) -> None:
    manifest = _manifest(zone)
    tracts = pd.read_csv(zone / TRACTS_CSV, dtype={"geoid": str})
    assert list(tracts.columns) == manifest["columns"]["tracts"]
    for field in manifest["fields"]:
        column = field["column"]
        record = manifest["bins"][column]
        assert record["method"] == "quantile" and 1 <= record["classes"] <= 5
        assert tracts[f"{column}_bin"].dropna().between(1, record["classes"]).all()
        assert tracts[f"{column}_bin"].notna().sum() == tracts[column].notna().sum()
    sites = pd.read_csv(zone / SITES_CSV, dtype=str)
    assert list(sites.columns) == manifest["columns"]["sites"]
    geo = gpd.read_file(zone / SITES_GEOJSON)
    assert set(geo["site_id"]) == set(sites["site_id"])
    assert (zone / TRACTS_CSV).read_bytes().count(b"\r") == 0


def test_public_zone_is_byte_deterministic(zone: Path, tmp_path: Path) -> None:
    root = tmp_path / "again"
    runner.run(root, fixture_pipeline())
    for name in (*PUBLIC_FILES, PUBLIC_MANIFEST):
        assert (root / "public" / name).read_bytes() == (zone / name).read_bytes(), name


def test_publish_declares_its_dag_provenance() -> None:
    fixture = fixture_pipeline()
    publish = fixture["publish"]
    upstream = set()
    for rel in publish.inputs:
        upstream.update(fixture.upstream_raw(rel))
    assert {rel for rel in publish.inputs if rel.startswith("raw/")} == upstream
    assert len(upstream) == 8
    real = real_pipeline()
    declared = {rel for rel in real["publish"].inputs if rel.startswith("raw/")}
    assert declared == {f"raw/{s}/2026-09-02" for s in PUBLISH_SOURCES}
    assert declared <= set(real.upstream_raw(real["publish"].inputs[0]))
    assert real.upstream_raw("raw/acs/2026-09-02") == ("raw/acs/2026-09-02",)


# --- the gate blocks (one negative per check) -----------------------------------------------------


def test_gate_blocks_an_intentionally_mislabeled_file(copy: Path) -> None:
    """The acceptance criterion: a file labeled Bucket A whose sources require Bucket B."""
    manifest = _manifest(copy)
    manifest["files"][TRACTS_CSV]["bucket"] = BUCKET_A
    manifest["files"][TRACTS_CSV]["license"] = label_of("A").payload()
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "labeled Bucket A but its sources require Bucket B")
    with pytest.raises(PublishGateError, match="require Bucket B"):
        gate.enforce_gate(_problems(copy))


def test_gate_blocks_a_source_bucket_downgrade(copy: Path) -> None:
    manifest = _manifest(copy)
    for record in manifest["sources"]:
        if record["source"] == "osm_network":
            record["license_bucket"] = BUCKET_A
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "labeled Bucket B but its sources require Bucket A")


def test_gate_blocks_a_bucket_b_file_without_the_osm_notice(copy: Path) -> None:
    manifest = _manifest(copy)
    manifest["files"][SITES_CSV]["license"]["notices"] = []
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "is not the Bucket B label", f"lacks the notice {OSM_NOTICE!r}")


def test_gate_blocks_unlisted_missing_and_altered_files(copy: Path) -> None:
    (copy / "notes.txt").write_text("stray", "utf-8")
    _assert_blocked(copy, "unlisted file(s)")
    (copy / "notes.txt").unlink()
    (copy / SITES_CSV).unlink()
    _assert_blocked(copy, "missing from the public zone")
    shutil.copy(copy / TRACTS_CSV, copy / SITES_CSV)  # present again, wrong content
    _assert_blocked(copy, "does not match its recorded digest")
    (copy / "sub").mkdir()
    _assert_blocked(copy, "non-file entry")


def test_gate_blocks_in_file_label_drift_and_a_crs_member(copy: Path) -> None:
    payload = json.loads((copy / TRACTS_GEOJSON).read_text("utf-8"))
    payload["license"] = label_of("A").payload()
    payload["crs"] = {"type": "name", "properties": {"name": "EPSG:26918"}}
    (copy / TRACTS_GEOJSON).write_bytes(json_bytes(payload))
    _assert_blocked(copy, "in-file license label differs", "carries a 'crs' member")


def test_gate_blocks_coordinates_outside_bounds_and_foreign_bounds(copy: Path) -> None:
    payload = json.loads((copy / SITES_GEOJSON).read_text("utf-8"))
    payload["features"][0]["geometry"]["coordinates"] = [
        -75.16,
        39.95,
    ]  # Philadelphia, not tinycity
    (copy / SITES_GEOJSON).write_bytes(json_bytes(payload))
    _assert_blocked(copy, "outside WGS 84 range or the declared bounds")
    assert any(
        "differ from the pipeline's" in p
        for p in check_public_zone(copy, bounds=(-75.3, 39.85, -74.94, 40.15))
    )


def test_gate_blocks_zone_and_absolute_path_leakage(copy: Path) -> None:
    manifest = _manifest(copy)
    manifest["fields"][0]["description"] += " (from curated/tract_metrics.parquet)"
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "contains a curated zone path")
    manifest = _manifest(copy)
    manifest["fields"][0]["description"] = "built at C:\\Users\\someone\\data"
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "contains a drive-letter path", "contains a backslash path")
    manifest["fields"][0]["description"] = "built under /home/someone/data"
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "contains a home directory path")
    manifest["fields"][0]["description"] = "see https://example.invalid/data (a URL is fine)"
    _write_manifest(copy, manifest)
    assert not any("path" in p for p in _problems(copy))


def test_gate_blocks_an_unescaped_csv_cell(copy: Path) -> None:
    text = (copy / SITES_CSV).read_text("utf-8")
    assert "Corner Market" in text
    (copy / SITES_CSV).write_text(text.replace("Corner Market", '=HYPERLINK("x")'), "utf-8")
    _assert_blocked(copy, "start with a spreadsheet formula character")


def test_gate_blocks_prohibited_vocabulary_and_undeclared_qa_columns(copy: Path) -> None:
    manifest = _manifest(copy)
    manifest["fields"].append(
        {
            "column": "access_index",
            "metric_id": "access_index",
            "category": None,
            "mode": None,
            "qa_only": False,
            "description": "no",
        }
    )
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "prohibited term(s) ['index']")
    manifest = _manifest(copy)
    manifest["fields"][-1] = {
        "column": "qa_probe",
        "metric_id": "qa_probe",
        "category": None,
        "mode": None,
        "qa_only": False,
        "description": "a probe",
    }
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "QA column but not declared qa_only")
    manifest["fields"][-1]["qa_only"] = True
    _write_manifest(copy, manifest)
    _assert_blocked(copy, "description that does not say so", "without the QA note")


def test_gate_blocks_broken_parity_between_formats(copy: Path) -> None:
    lines = (copy / TRACTS_CSV).read_text("utf-8").splitlines()
    (copy / TRACTS_CSV).write_text("\n".join(lines[:-1]) + "\n", "utf-8")
    _assert_blocked(copy, "row(s) on disk, manifest says", "do not hold the same rows")


def test_gate_needs_a_manifest_and_a_directory(tmp_path: Path) -> None:
    assert check_public_zone(tmp_path / "nowhere") == ["public zone 'nowhere' is not a directory"]
    (tmp_path / "public").mkdir()
    assert check_public_zone(tmp_path / "public") == ["public zone has no manifest.json"]
    (tmp_path / "public" / "manifest.json").write_text("{", "utf-8")
    assert "not valid JSON" in check_public_zone(tmp_path / "public")[0]
    (tmp_path / "public" / "manifest.json").write_text("{}", "utf-8")
    assert "lacks required key(s)" in check_public_zone(tmp_path / "public")[0]


def test_publish_stage_refuses_to_install_a_zone_the_gate_rejects(
    tmp_path: Path, monkeypatch
) -> None:
    """The stage-level guarantee: a gate failure inside ``publish`` leaves the public zone empty."""
    root = tmp_path / "root"
    runner.run(root, fixture_pipeline(), through="metrics")
    original = gate.check_public_zone

    def poisoned(public: Path, *, bounds=None) -> list[str]:
        return [*original(public, bounds=bounds), "injected gate failure"]

    monkeypatch.setattr(export, "check_public_zone", poisoned)
    with pytest.raises(PublishGateError, match="injected gate failure"):
        runner.run(root, fixture_pipeline())
    assert not any((root / "public").iterdir()), "nothing left the curated zone"
    assert runner.status(root, fixture_pipeline())[-1].status == "incomplete"
