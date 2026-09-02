"""EP-5a source contracts for the three spine sources, on the committed samples (offline).

Positive: every sample snapshot verifies against its manifest, admits through the
adapter's own allowlist and limits, reads through the adapter with the county
filter applied, and conforms to its contract. Negative: each check kind fires on
a crafted deviation. The samples are real-shaped subsets of US-public-domain
Census files (``tests/fixtures/spine-samples/README.md``).
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import geopandas as gpd
import pandas as pd
import pytest

from phillysim import pipeline
from phillysim.adapters import ADAPTERS, acs, cenpop, tiger
from phillysim.adapters.base import CENSUS_TERMS_PHRASE, COUNTY_BOUNDS, NAD83
from phillysim.contracts import ContractViolationError, check_frame, enforce
from phillysim.download import check_terms
from phillysim.guards import check_url_allowed
from phillysim.manifest import read_manifest, verify_snapshot
from phillysim.quarantine import admit

SOURCES = tuple(sorted(ADAPTERS))
SAMPLE_TRACTS = [
    "42101000101",
    "42101000102",
    "42101000200",
    "42101000300",
    "42101000401",
    "42101000403",
]


def _sample(samples: Path, source: str) -> Path:
    return samples / "raw" / source / pipeline.SNAPSHOT_ID


# --- the registry ------------------------------------------------------------------------


def test_registry_matches_the_real_pipeline() -> None:
    assert SOURCES == pipeline.SOURCES == ("acs", "cenpop", "tiger_tracts")
    for name, adapter in ADAPTERS.items():
        assert adapter.name == adapter.spec.source == adapter.contract.name == name
        assert adapter.filter_note


@pytest.mark.parametrize("source", SOURCES)
def test_every_adapter_declares_its_own_allowlist_terms_and_bucket(source: str) -> None:
    spec = ADAPTERS[source].spec
    assert spec.allowlist, "no default allowlist exists; each adapter declares its domains"
    for url in (spec.acquisition_url, spec.terms.url, *(f.url for f in spec.files)):
        assert urlsplit(url).scheme == "https"
        check_url_allowed(url, spec.allowlist)
    assert spec.terms_must_contain == (CENSUS_TERMS_PHRASE,)
    assert spec.license_bucket == "A" and "public domain" in spec.license_note
    assert ADAPTERS[source].contract.license_buckets == frozenset({"A"})
    assert spec.limits.max_file_bytes <= 256 * 1024**2, "limits are per source, not the default"


# --- the samples: verify, admit, read, conform ----------------------------------------


@pytest.mark.parametrize("source", SOURCES)
def test_sample_snapshot_verifies_and_admits(spine_samples_dir: Path, source: str, tmp_path):
    sample = _sample(spine_samples_dir, source)
    assert verify_snapshot(sample).ok
    staged = tmp_path / "raw" / source / pipeline.SNAPSHOT_ID
    shutil.copytree(sample, staged)
    spec = ADAPTERS[source].spec
    manifest = admit(staged, tmp_path / "quarantine", allowlist=spec.allowlist, limits=spec.limits)
    assert manifest.source == source and not (tmp_path / "quarantine").exists()


@pytest.mark.parametrize("source", SOURCES)
def test_sample_manifest_carries_the_required_fields(spine_samples_dir: Path, source: str):
    sample = _sample(spine_samples_dir, source)
    manifest = read_manifest(sample)
    spec = ADAPTERS[source].spec
    assert manifest.snapshot_id == pipeline.SNAPSHOT_ID
    assert (
        manifest.terms_archive == spec.terms.file_name and manifest.terms_archive in manifest.files
    )
    assert (sample / manifest.terms_archive).is_file()
    assert manifest.license_bucket == "A" and manifest.license_note.strip()
    assert manifest.synthetic is False, "the samples are subsets of real data, not synthetic"
    assert manifest.acquisition_url == spec.acquisition_url
    assert set(manifest.files) == {f.file_name for f in spec.files} | {spec.terms.file_name}
    check_terms(sample / manifest.terms_archive, spec.terms_must_contain)


@pytest.mark.parametrize("source", SOURCES)
def test_sample_conforms_to_its_contract(spine_samples_dir: Path, source: str) -> None:
    sample = _sample(spine_samples_dir, source)
    adapter = ADAPTERS[source]
    frame = adapter.read(sample)
    enforce(adapter.contract, frame, read_manifest(sample).to_dict())
    key = adapter.contract.key
    assert key is not None and sorted(frame[key]) == SAMPLE_TRACTS


def test_county_filter_drops_the_control_rows(spine_samples_dir: Path) -> None:
    tiger_zip = _sample(spine_samples_dir, "tiger_tracts") / tiger.FILE_NAME
    assert len(gpd.read_file(f"zip://{tiger_zip.as_posix()}")) == 8
    assert len(tiger.read(tiger_zip.parent)) == 6

    cenpop_file = _sample(spine_samples_dir, "cenpop") / cenpop.FILE_NAME
    assert len(cenpop_file.read_text("utf-8-sig").splitlines()) == 1 + 8
    assert len(cenpop.read(cenpop_file.parent)) == 6

    acs_dir = _sample(spine_samples_dir, "acs")
    for table in acs.TABLES:
        lines = (acs_dir / acs.file_name(table)).read_text("utf-8").splitlines()
        assert len(lines) == 1 + 8 + 2, "six tracts, two control tracts, nation and state"
        assert lines[1].startswith("0100000US|"), "the nation row is a real non-tract row"
    assert len(acs.read(acs_dir)) == 6


def test_tiger_reads_from_the_zip_without_extracting(spine_samples_dir: Path) -> None:
    sample = _sample(spine_samples_dir, "tiger_tracts")
    before = sorted(p.name for p in sample.iterdir())
    frame = tiger.read(sample)
    assert sorted(p.name for p in sample.iterdir()) == before
    assert frame.crs.to_epsg() == 4269 and set(frame.geom_type) <= {"Polygon", "MultiPolygon"}
    minx, miny, maxx, maxy = frame.total_bounds
    assert COUNTY_BOUNDS[0] < minx and COUNTY_BOUNDS[2] > maxx
    assert COUNTY_BOUNDS[1] < miny and COUNTY_BOUNDS[3] > maxy
    with zipfile.ZipFile(sample / tiger.FILE_NAME) as zf:
        assert {Path(n).suffix for n in zf.namelist()} >= {".shp", ".shx", ".dbf", ".prj"}


def test_cenpop_derives_geoid_and_points_from_the_fips_columns(spine_samples_dir: Path):
    frame = cenpop.read(_sample(spine_samples_dir, "cenpop"))
    assert list(frame.columns[:4]) == ["geoid", "STATEFP", "COUNTYFP", "TRACTCE"]
    assert (frame["geoid"] == frame["STATEFP"] + frame["COUNTYFP"] + frame["TRACTCE"]).all()
    assert frame.crs.to_epsg() == 4269
    assert (frame.geometry.x == frame["LONGITUDE"]).all()
    assert (frame.geometry.y == frame["LATITUDE"]).all()
    assert frame["POPULATION"].dtype.kind == "i"


def test_acs_read_returns_only_the_pinned_variables(spine_samples_dir: Path) -> None:
    frame = acs.read(_sample(spine_samples_dir, "acs"))
    assert list(frame.columns) == ["geoid", *acs.column_names()]
    assert acs.column_names() == ("B01003_001E", "B01003_001M", "B08201_002E", "B08201_002M")
    assert frame.dtypes["B01003_001E"] == "float64"
    assert (frame["B01003_001E"] >= 0).all() and (frame["B01003_001M"] >= 0).all()


def test_acs_annotation_values_and_blanks_become_null(tmp_path: Path) -> None:
    snap = tmp_path / "acs" / "2026-09-02"
    snap.mkdir(parents=True)
    (snap / acs.file_name("B01003")).write_text(
        "GEO_ID|B01003_E001|B01003_M001\n"
        "0100000US|334922499|-555555555\n"
        "1400000US42101000100|3200|210\n"
        "1400000US42101000200|-666666666|-222222222\n"
        "1400000US42101000300||\n",
        "utf-8",
    )
    (snap / acs.file_name("B08201")).write_text(
        "GEO_ID|B08201_E001|B08201_M001|B08201_E002|B08201_M002\n"
        "1400000US42101000100|1000|50|640|95\n"
        "1400000US42101000200|900|40|-888888888|-333333333\n"
        "1400000US42101000300|800|30|12|-999999999\n",
        "utf-8",
    )
    frame = acs.read(snap).set_index("geoid")
    assert list(frame.index) == ["42101000100", "42101000200", "42101000300"]
    assert frame.loc["42101000100"].tolist() == [3200.0, 210.0, 640.0, 95.0]
    assert frame.loc["42101000200"].isna().all()
    row = frame.loc["42101000300"]
    assert pd.isna(row["B01003_001E"]) and pd.isna(row["B01003_001M"])
    assert row["B08201_002E"] == 12.0 and pd.isna(row["B08201_002M"])
    assert check_frame(acs.CONTRACT, frame.reset_index()) == []


# --- negative: every check kind fires ---------------------------------------------------


@pytest.mark.parametrize("source", SOURCES)
def test_dropped_column_is_a_schema_violation(spine_samples_dir: Path, source: str) -> None:
    adapter = ADAPTERS[source]
    frame = adapter.read(_sample(spine_samples_dir, source))
    column = adapter.contract.columns[-1].name
    violations = check_frame(adapter.contract, frame.drop(columns=[column]))
    assert [v.check for v in violations] == ["schema"] and column in violations[0].detail


def test_wrong_county_is_a_schema_violation(spine_samples_dir: Path) -> None:
    frame = cenpop.read(_sample(spine_samples_dir, "cenpop")).copy()
    frame.loc[0, "COUNTYFP"] = "003"
    frame.loc[0, "geoid"] = "42003" + frame.loc[0, "TRACTCE"]
    checks = {v.check for v in check_frame(cenpop.CONTRACT, frame)}
    assert checks == {"schema"}


def test_reprojected_geometry_is_a_geometry_violation(spine_samples_dir: Path) -> None:
    frame = tiger.read(_sample(spine_samples_dir, "tiger_tracts")).to_crs("EPSG:4326")
    violations = check_frame(tiger.CONTRACT, frame)
    assert [v.check for v in violations] == ["geometry"] and NAD83 in violations[0].detail


def test_out_of_county_geometry_is_a_geometry_violation(spine_samples_dir: Path) -> None:
    frame = tiger.read(_sample(spine_samples_dir, "tiger_tracts"))
    shifted = frame.set_geometry(frame.geometry.translate(xoff=1.0))
    assert {v.check for v in check_frame(tiger.CONTRACT, shifted)} == {"geometry"}


@pytest.mark.parametrize("source", SOURCES)
def test_duplicate_key_is_a_key_violation(spine_samples_dir: Path, source: str) -> None:
    adapter = ADAPTERS[source]
    frame = adapter.read(_sample(spine_samples_dir, source))
    doubled = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    if isinstance(frame, gpd.GeoDataFrame):
        doubled = gpd.GeoDataFrame(doubled, geometry="geometry", crs=frame.crs)
    assert {v.check for v in check_frame(adapter.contract, doubled)} == {"key"}


def test_wrong_bucket_in_manifest_is_a_license_violation(spine_samples_dir: Path) -> None:
    sample = _sample(spine_samples_dir, "acs")
    manifest = {**read_manifest(sample).to_dict(), "license_bucket": "B"}
    with pytest.raises(ContractViolationError) as info:
        enforce(acs.CONTRACT, acs.read(sample), manifest)
    assert [v.check for v in info.value.violations] == ["license"]


def test_empty_table_is_a_rows_violation(spine_samples_dir: Path) -> None:
    frame = acs.read(_sample(spine_samples_dir, "acs")).iloc[:0]
    assert {v.check for v in check_frame(acs.CONTRACT, frame)} == {"rows"}
