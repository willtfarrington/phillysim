"""EP-8b source contract for TIGER/Line county roads (``tiger_roads``), on the committed
sample (offline).

Positive: the sample snapshot verifies, admits through the adapter's own allowlist
and limits, reads with the feature-class filter applied (primary and secondary
roads only), and conforms to its contract. Negative: each check kind fires on a
crafted deviation, and a local road that slipped past the filter is a contract
violation.
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
from phillysim.adapters import ADAPTERS, tiger, tiger_roads
from phillysim.adapters.base import CENSUS_TERMS_PHRASE, COUNTY_BOUNDS, COUNTY_GEOID, NAD83
from phillysim.contracts import ContractViolationError, check_frame, enforce
from phillysim.download import check_terms
from phillysim.guards import check_url_allowed
from phillysim.manifest import read_manifest, verify_snapshot
from phillysim.quarantine import admit

#: Rows in the committed sample: the major roads crossing the six sample tracts, plus
#: local-road control rows the feature-class filter must drop
#: (tests/fixtures/spine-samples/README.md).
SAMPLE_MAJOR = 48
SAMPLE_CONTROLS = 4


@pytest.fixture(scope="module")
def sample(spine_samples_dir: Path) -> Path:
    return spine_samples_dir / "raw" / tiger_roads.SOURCE / pipeline.SNAPSHOT_ID


def test_adapter_is_registered_with_the_real_pipeline() -> None:
    assert tiger_roads.SOURCE in ADAPTERS and tiger_roads.SOURCE in pipeline.SOURCES
    assert tiger_roads.SOURCE in pipeline.PUBLISH_SOURCES, "the basemap is published"
    assert ADAPTERS[tiger_roads.SOURCE].contract.name == tiger_roads.SOURCE
    assert ADAPTERS[tiger_roads.SOURCE].filter_note and ADAPTERS[tiger_roads.SOURCE].citation


def test_spec_is_the_county_file_on_the_census_host_with_the_census_terms() -> None:
    spec = tiger_roads.SPEC
    assert tiger_roads.FILE_NAME == f"tl_2025_{COUNTY_GEOID}_roads.zip"
    assert spec.acquisition_url == tiger_roads.URL and spec.acquisition_url_alt is None
    (only,) = spec.files
    assert only.urls == (tiger_roads.URL,) and only.file_name == tiger_roads.FILE_NAME
    assert urlsplit(tiger_roads.URL).hostname == "www2.census.gov"
    assert spec.terms.url == tiger.SPEC.terms.url, "the same Census terms page as the tracts"
    assert spec.terms_must_contain == (CENSUS_TERMS_PHRASE,)
    for url in (tiger_roads.URL, spec.terms.url):
        assert urlsplit(url).scheme == "https"
        check_url_allowed(url, spec.allowlist)
    assert spec.license_bucket == "A" and "public domain" in spec.license_note
    assert "S1100" in spec.license_note and "S1200" in spec.license_note
    assert spec.limits.max_file_bytes == 16 * 1024**2, "a county roads file is about 1.4 MB"
    assert spec.limits.max_file_bytes < tiger.SPEC.limits.max_file_bytes


def test_contract_allows_exactly_the_major_road_classes() -> None:
    assert tiger_roads.MAJOR_ROAD_CLASSES == frozenset({"S1100", "S1200"})
    mtfcc = next(c for c in tiger_roads.CONTRACT.columns if c.name == "MTFCC")
    assert mtfcc.allowed == tiger_roads.MAJOR_ROAD_CLASSES and not mtfcc.nullable
    route = next(c for c in tiger_roads.CONTRACT.columns if c.name == "RTTYP")
    assert route.allowed == tiger_roads.ROUTE_TYPES
    assert tiger_roads.CONTRACT.key == "LINEARID"
    assert tiger_roads.CONTRACT.geometry is not None
    assert tiger_roads.CONTRACT.geometry.crs == NAD83
    assert tiger_roads.CONTRACT.geometry.types == frozenset({"LineString", "MultiLineString"})
    assert tiger_roads.CONTRACT.license_buckets == frozenset({"A"})


# --- the sample: verify, admit, read, conform ----------------------------------------------


def test_sample_snapshot_verifies_and_admits(sample: Path, tmp_path: Path) -> None:
    assert verify_snapshot(sample).ok
    staged = tmp_path / "raw" / tiger_roads.SOURCE / pipeline.SNAPSHOT_ID
    shutil.copytree(sample, staged)
    spec = tiger_roads.SPEC
    manifest = admit(staged, tmp_path / "quarantine", allowlist=spec.allowlist, limits=spec.limits)
    assert manifest.source == tiger_roads.SOURCE and not (tmp_path / "quarantine").exists()


def test_sample_manifest_carries_the_required_fields(sample: Path) -> None:
    manifest = read_manifest(sample)
    spec = tiger_roads.SPEC
    assert manifest.snapshot_id == pipeline.SNAPSHOT_ID
    assert manifest.terms_archive == spec.terms.file_name
    assert manifest.terms_archive in manifest.files
    assert manifest.license_bucket == "A" and "CI SAMPLE" in manifest.license_note
    assert manifest.synthetic is False, "the sample is a subset of real data, not synthetic"
    assert manifest.acquisition_url == spec.acquisition_url
    assert set(manifest.files) == {tiger_roads.FILE_NAME, spec.terms.file_name}
    check_terms(sample / manifest.terms_archive, spec.terms_must_contain)


def test_sample_conforms_to_its_contract(sample: Path) -> None:
    frame = tiger_roads.read(sample)
    enforce(tiger_roads.CONTRACT, frame, read_manifest(sample).to_dict())
    assert len(frame) == SAMPLE_MAJOR
    assert frame["LINEARID"].is_unique and frame["LINEARID"].is_monotonic_increasing
    assert set(frame["MTFCC"]) == tiger_roads.MAJOR_ROAD_CLASSES, "both classes present"
    assert frame["FULLNAME"].notna().all()
    assert {"I- 95", "Market St", "Benjamin Franklin Brg"} <= set(frame["FULLNAME"])


def test_feature_class_filter_drops_the_local_road_controls(sample: Path) -> None:
    everything = tiger_roads.read_all(sample)
    assert len(everything) == SAMPLE_MAJOR + SAMPLE_CONTROLS
    dropped = everything[~everything["MTFCC"].isin(tiger_roads.MAJOR_ROAD_CLASSES)]
    assert len(dropped) == SAMPLE_CONTROLS and set(dropped["MTFCC"]) <= {"S1400", "S1630", "S1730"}
    assert len(tiger_roads.read(sample)) == SAMPLE_MAJOR


def test_roads_read_from_the_zip_without_extracting(sample: Path) -> None:
    before = sorted(p.name for p in sample.iterdir())
    frame = tiger_roads.read(sample)
    assert sorted(p.name for p in sample.iterdir()) == before
    assert frame.crs.to_epsg() == 4269 and set(frame.geom_type) <= {"LineString", "MultiLineString"}
    minx, miny, maxx, maxy = frame.total_bounds
    assert COUNTY_BOUNDS[0] < minx and COUNTY_BOUNDS[2] > maxx
    assert COUNTY_BOUNDS[1] < miny and COUNTY_BOUNDS[3] > maxy
    with zipfile.ZipFile(sample / tiger_roads.FILE_NAME) as zf:
        assert {Path(n).suffix for n in zf.namelist()} >= {".shp", ".shx", ".dbf", ".prj"}


# --- negative: every check kind fires ---------------------------------------------------


def test_dropped_column_is_a_schema_violation(sample: Path) -> None:
    frame = tiger_roads.read(sample)
    violations = check_frame(tiger_roads.CONTRACT, frame.drop(columns=["RTTYP"]))
    assert [v.check for v in violations] == ["schema"] and "RTTYP" in violations[0].detail


def test_local_road_past_the_filter_is_a_schema_violation(sample: Path) -> None:
    frame = tiger_roads.read(sample).copy()
    frame.loc[0, "MTFCC"] = "S1400"
    violations = check_frame(tiger_roads.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema"] and "S1400" in violations[0].detail


def test_reprojected_geometry_is_a_geometry_violation(sample: Path) -> None:
    frame = tiger_roads.read(sample).to_crs("EPSG:4326")
    violations = check_frame(tiger_roads.CONTRACT, frame)
    assert [v.check for v in violations] == ["geometry"] and NAD83 in violations[0].detail


def test_out_of_county_geometry_is_a_geometry_violation(sample: Path) -> None:
    frame = tiger_roads.read(sample)
    shifted = frame.set_geometry(frame.geometry.translate(xoff=1.0))
    assert {v.check for v in check_frame(tiger_roads.CONTRACT, shifted)} == {"geometry"}


def test_duplicate_key_is_a_key_violation(sample: Path) -> None:
    frame = tiger_roads.read(sample)
    doubled = gpd.GeoDataFrame(
        pd.concat([frame, frame.iloc[:1]], ignore_index=True), geometry="geometry", crs=frame.crs
    )
    assert {v.check for v in check_frame(tiger_roads.CONTRACT, doubled)} == {"key"}


def test_wrong_bucket_in_manifest_is_a_license_violation(sample: Path) -> None:
    manifest = {**read_manifest(sample).to_dict(), "license_bucket": "B"}
    with pytest.raises(ContractViolationError) as info:
        enforce(tiger_roads.CONTRACT, tiger_roads.read(sample), manifest)
    assert [v.check for v in info.value.violations] == ["license"]


def test_empty_table_is_a_rows_violation(sample: Path) -> None:
    frame = tiger_roads.read(sample).iloc[:0]
    assert {v.check for v in check_frame(tiger_roads.CONTRACT, frame)} == {"rows"}
