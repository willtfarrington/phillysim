"""EP-12 source contract for the Geofabrik OpenStreetMap extract (``osm_network``), on the
committed sample (offline).

Positive: the sample snapshot (real OSM data clipped to the six sample tracts' bounds,
ODbL, the provider's header carried over) verifies, admits through the adapter's own
allowlist and limits, reads (the header and the MD5 checks only) and conforms to its
contract; its manifest is the first Bucket B raw manifest of the real pipeline and the
bucket derivation over it returns B. Negative: each check kind fires on a crafted
deviation, and a sidecar that no longer vouches for the file is a contract violation.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import urlsplit

import osmium
import osmium.osm
import pandas as pd
import pytest

from phillysim import pipeline
from phillysim.adapters import ADAPTERS, osm
from phillysim.adapters.base import COUNTY_BOUNDS
from phillysim.contracts import ContractViolationError, check_frame, enforce
from phillysim.download import check_terms, digest_file, parse_digest
from phillysim.guards import ARCHIVE_SUFFIXES, check_url_allowed
from phillysim.manifest import read_manifest, verify_snapshot
from phillysim.publish.bucket import BUCKET_A, BUCKET_B, derive_bucket
from phillysim.quarantine import admit


@pytest.fixture(scope="module")
def sample(spine_samples_dir: Path) -> Path:
    return spine_samples_dir / "raw" / osm.SOURCE / pipeline.SNAPSHOT_IDS[osm.SOURCE]


def test_adapter_is_registered_and_never_published() -> None:
    assert osm.SOURCE in ADAPTERS and osm.SOURCE in pipeline.SOURCES
    assert osm.SOURCE not in pipeline.PUBLISH_SOURCES, "the public zone stays Bucket A (EP-12)"
    assert pipeline.SNAPSHOT_IDS[osm.SOURCE] == "2026-09-03", "its own acquisition date"
    assert ADAPTERS[osm.SOURCE].contract.name == osm.SOURCE
    assert ADAPTERS[osm.SOURCE].filter_note and ADAPTERS[osm.SOURCE].citation
    assert "OpenStreetMap contributors" in ADAPTERS[osm.SOURCE].citation


def test_spec_pins_the_dated_extract_its_md5_and_the_region_page() -> None:
    spec = osm.SPEC
    assert osm.FILE_NAME == "pennsylvania-260831.osm.pbf" and "latest" not in osm.URL
    assert spec.acquisition_url == osm.URL and spec.acquisition_url_alt is None
    data, sidecar = spec.files
    assert data.file_name == osm.FILE_NAME and data.urls == (osm.URL,)
    assert parse_digest(data.digest) == ("md5", "a779d2ef14c8addce6eac207ab9cd851")
    assert sidecar.file_name == osm.FILE_NAME + ".md5" and sidecar.md5_of == osm.FILE_NAME
    assert sidecar.url == osm.URL + ".md5"
    assert spec.terms.url == osm.TERMS_URL and spec.terms.file_name == "terms.html"
    assert spec.terms_must_contain == ("created by OpenStreetMap Contributors", "License: ODbL")
    assert spec.allowlist == ("download.geofabrik.de",)
    for url in (osm.URL, osm.MD5_URL, osm.TERMS_URL):
        assert urlsplit(url).scheme == "https"
        check_url_allowed(url, spec.allowlist)
    assert spec.license_bucket == "B"
    assert "ODbL" in spec.license_note and "OpenStreetMap contributors" in spec.license_note
    assert "Geofabrik" in spec.license_note and osm.OSM_DATA_DATE in spec.license_note
    assert spec.limits.max_file_bytes == 1024**3, "the state extract is about 346 MB"


def test_a_pbf_is_not_an_archive_to_the_guards() -> None:
    assert Path(osm.FILE_NAME).suffix.lower() not in ARCHIVE_SUFFIXES


def test_contract_pins_bucket_b_the_sidecar_check_and_the_header_box() -> None:
    assert osm.CONTRACT.license_buckets == frozenset({"B"})
    assert osm.CONTRACT.key == "file" and (osm.CONTRACT.min_rows, osm.CONTRACT.max_rows) == (1, 1)
    by_name = {column.name: column for column in osm.CONTRACT.columns}
    assert (by_name["sidecar_match"].minimum, by_name["sidecar_match"].maximum) == (1, 1)
    assert by_name["bbox_min_lon"].maximum == COUNTY_BOUNDS[0]
    assert by_name["bbox_min_lat"].maximum == COUNTY_BOUNDS[1]
    assert by_name["bbox_max_lon"].minimum == COUNTY_BOUNDS[2]
    assert by_name["bbox_max_lat"].minimum == COUNTY_BOUNDS[3]
    assert by_name["sorting"].allowed == frozenset({"Type_then_ID"})


# --- the sample: verify, admit, read, conform ----------------------------------------------


def test_sample_snapshot_verifies_and_admits(sample: Path, tmp_path: Path) -> None:
    assert verify_snapshot(sample).ok
    staged = tmp_path / "raw" / osm.SOURCE / pipeline.SNAPSHOT_IDS[osm.SOURCE]
    shutil.copytree(sample, staged)
    spec = osm.SPEC
    manifest = admit(staged, tmp_path / "quarantine", allowlist=spec.allowlist, limits=spec.limits)
    assert manifest.source == osm.SOURCE and not (tmp_path / "quarantine").exists()


def test_sample_manifest_is_the_first_bucket_b_manifest(sample: Path) -> None:
    manifest = read_manifest(sample)
    spec = osm.SPEC
    assert manifest.snapshot_id == pipeline.SNAPSHOT_IDS[osm.SOURCE]
    assert manifest.license_bucket == "B" and manifest.synthetic is False
    assert "CI SAMPLE" in manifest.license_note and "ODbL" in manifest.license_note
    assert "OpenStreetMap contributors" in manifest.license_note
    assert (
        manifest.terms_archive == spec.terms.file_name and manifest.terms_archive in manifest.files
    )
    assert set(manifest.files) == {osm.FILE_NAME, osm.MD5_FILE, osm.TERMS_FILE}
    assert manifest.acquisition_url == spec.acquisition_url
    check_terms(sample / manifest.terms_archive, spec.terms_must_contain)
    # ADR-0003: Bucket B is contagious; the derivation over any source list holding it is B.
    assert derive_bucket([manifest.license_bucket]) == BUCKET_B
    assert derive_bucket([BUCKET_A, manifest.license_bucket, BUCKET_A]) == BUCKET_B


def test_sample_conforms_to_its_contract(sample: Path) -> None:
    frame = osm.read(sample)
    enforce(osm.CONTRACT, frame, read_manifest(sample).to_dict())
    assert tuple(frame.columns) == osm.SUMMARY_COLUMNS and len(frame) == 1
    row = frame.iloc[0]
    assert row["file"] == osm.FILE_NAME and row["bytes"] == (sample / osm.FILE_NAME).stat().st_size
    assert row["md5"] == digest_file(sample / osm.FILE_NAME, "md5") == row["md5_sidecar"]
    assert row["sidecar_match"] == 1
    assert row["md5_pinned"] == osm.PROVIDER_MD5, (
        "the pin is the real file's; the sample is pinned by its sidecar"
    )
    assert row["generator"].startswith(f"phillysim clip of {osm.FILE_NAME}")
    assert row["replication_timestamp"] == "2026-08-31T20:21:20Z", (
        "the provider's header, carried over"
    )
    assert row["sorting"] == osm.SORTING
    assert row["bbox_min_lon"] < COUNTY_BOUNDS[0] and row["bbox_min_lat"] < COUNTY_BOUNDS[1]
    assert row["bbox_max_lon"] > COUNTY_BOUNDS[2] and row["bbox_max_lat"] > COUNTY_BOUNDS[3]


def test_sample_is_a_small_way_complete_street_network(sample: Path) -> None:
    path = sample / osm.FILE_NAME
    assert path.stat().st_size < 2 * 1024**2, "a few hundred kilobytes, not the state"
    counts = osm.count_objects(path)
    assert 1_000 <= counts["nodes"] <= 200_000 and 100 <= counts["ways"] <= 50_000
    highways = sum(
        1 for way in osmium.FileProcessor(str(path), osmium.osm.WAY) if "highway" in way.tags
    )
    assert highways >= 50
    # Way-complete: every node a kept way references is in the file.
    nodes = {node.id for node in osmium.FileProcessor(str(path), osmium.osm.NODE)}
    for way in osmium.FileProcessor(str(path), osmium.osm.WAY):
        assert all(ref.ref in nodes for ref in way.nodes)


def test_read_opens_the_header_only_and_writes_nothing(sample: Path) -> None:
    before = sorted(p.name for p in sample.iterdir())
    osm.read(sample)
    assert sorted(p.name for p in sample.iterdir()) == before


# --- negative: every check kind fires ---------------------------------------------------


def test_dropped_column_is_a_schema_violation(sample: Path) -> None:
    frame = osm.read(sample)
    violations = check_frame(osm.CONTRACT, frame.drop(columns=["sorting"]))
    assert [v.check for v in violations] == ["schema"] and "sorting" in violations[0].detail


def test_sidecar_that_no_longer_vouches_for_the_file_is_a_violation(
    sample: Path, tmp_path: Path
) -> None:
    staged = tmp_path / "raw" / osm.SOURCE / pipeline.SNAPSHOT_IDS[osm.SOURCE]
    shutil.copytree(sample, staged)
    (staged / osm.MD5_FILE).write_text("0" * 32 + f"  {osm.FILE_NAME}\n", "utf-8")
    frame = osm.read(staged)
    assert frame.loc[0, "sidecar_match"] == 0
    violations = check_frame(osm.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema"] and "sidecar_match" in violations[0].detail


def test_header_box_not_enclosing_the_county_is_a_violation(sample: Path) -> None:
    frame = osm.read(sample)
    frame.loc[0, "bbox_max_lat"] = COUNTY_BOUNDS[3] - 0.01
    violations = check_frame(osm.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema"] and "bbox_max_lat" in violations[0].detail


def test_unsorted_or_foreign_file_is_a_violation(sample: Path) -> None:
    frame = osm.read(sample)
    frame.loc[0, "file"] = "pennsylvania-latest.osm.pbf"
    frame.loc[0, "sorting"] = "None"
    violations = check_frame(osm.CONTRACT, frame)
    assert {v.check for v in violations} == {"schema"} and len(violations) == 2


def test_bucket_a_in_manifest_is_a_license_violation(sample: Path) -> None:
    manifest = {**read_manifest(sample).to_dict(), "license_bucket": "A"}
    with pytest.raises(ContractViolationError) as info:
        enforce(osm.CONTRACT, osm.read(sample), manifest)
    assert [v.check for v in info.value.violations] == ["license"]


def test_two_rows_is_a_rows_violation(sample: Path) -> None:
    frame = osm.read(sample)
    doubled = pd.concat([frame, frame], ignore_index=True)
    assert {v.check for v in check_frame(osm.CONTRACT, doubled)} == {"rows", "key"}
