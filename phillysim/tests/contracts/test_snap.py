"""EP-6 source contract for USDA SNAP retailers (``snap_retailers``), on the committed
sample (offline).

Positive: the sample snapshot verifies, admits through the adapter's own allowlist
and limits, reads with the county / as-of filter applied, and conforms to its
contract. Negative: each check kind fires on a crafted deviation, and a store type
the mapping does not know is a contract violation (the stop condition).
"""

from __future__ import annotations

import csv
import io
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import geopandas as gpd
import pandas as pd
import pytest

from phillysim import pipeline
from phillysim.adapters import ADAPTERS, snap
from phillysim.adapters.base import COUNTY_BOUNDS
from phillysim.classify import store_format
from phillysim.contracts import ContractViolationError, check_frame, enforce
from phillysim.download import check_terms
from phillysim.guards import check_url_allowed
from phillysim.manifest import read_manifest, verify_snapshot
from phillysim.quarantine import admit

SAMPLE_TRACTS = {
    "42101000101",
    "42101000102",
    "42101000200",
    "42101000300",
    "42101000401",
    "42101000403",
}
#: Rows in the committed sample: current Philadelphia retailers inside the six sample
#: tracts, plus control rows the filter must drop (closed spells, another county,
#: another state). tests/fixtures/spine-samples/README.md lists them.
SAMPLE_CURRENT = 26
SAMPLE_CONTROLS = 5


@pytest.fixture(scope="module")
def sample(spine_samples_dir: Path) -> Path:
    return spine_samples_dir / "raw" / snap.SOURCE / pipeline.SNAPSHOT_IDS[snap.SOURCE]


def test_adapter_is_registered_with_the_real_pipeline() -> None:
    assert snap.SOURCE in ADAPTERS and snap.SOURCE in pipeline.SOURCES
    assert ADAPTERS[snap.SOURCE].contract.name == snap.SOURCE


def test_spec_declares_dual_urls_allowlist_and_bucket() -> None:
    spec = snap.SPEC
    assert spec.acquisition_url == snap.URL and spec.acquisition_url_alt == snap.URL_ALT
    assert urlsplit(snap.URL).hostname == "www.fna.usda.gov"
    assert urlsplit(snap.URL_ALT).hostname == "www.fns.usda.gov", "pre-rename host kept"
    (only,) = spec.files
    assert only.urls == (snap.URL, snap.URL_ALT) and only.file_name == snap.FILE_NAME
    assert spec.terms.urls == (snap.PAGE_URL, snap.PAGE_URL_ALT)
    for url in (*only.urls, *spec.terms.urls):
        assert urlsplit(url).scheme == "https"
        check_url_allowed(url, spec.allowlist)
    assert spec.terms_must_contain == snap.PAGE_PHRASES
    assert any(host.endswith("azurefd.us") for host in spec.allowlist), "the redirect target"
    assert spec.license_bucket == "A" and "public domain" in spec.license_note
    assert spec.limits.max_file_bytes == 64 * 1024**2 and spec.limits.max_members == 4


def test_contract_allows_exactly_the_mapped_store_types() -> None:
    spec = next(c for c in snap.CONTRACT.columns if c.name == "Store Type")
    assert spec.allowed == frozenset(store_format.store_types())
    assert snap.CONTRACT.key == "Record ID"
    assert snap.CONTRACT.geometry is not None
    assert snap.CONTRACT.geometry.crs == snap.COORDINATE_CRS == "EPSG:4326"
    assert snap.CONTRACT.geometry.bounds == COUNTY_BOUNDS


def test_sample_snapshot_verifies_and_admits(sample: Path, tmp_path: Path) -> None:
    assert verify_snapshot(sample).ok
    staged = tmp_path / "raw" / snap.SOURCE / pipeline.SNAPSHOT_IDS[snap.SOURCE]
    shutil.copytree(sample, staged)
    manifest = admit(
        staged, tmp_path / "quarantine", allowlist=snap.SPEC.allowlist, limits=snap.SPEC.limits
    )
    assert manifest.source == snap.SOURCE and not (tmp_path / "quarantine").exists()


def test_sample_manifest_carries_the_required_fields(sample: Path) -> None:
    manifest = read_manifest(sample)
    assert manifest.snapshot_id == pipeline.SNAPSHOT_IDS[snap.SOURCE]
    assert manifest.acquisition_url == snap.URL and manifest.acquisition_url_alt == snap.URL_ALT
    assert manifest.terms_archive == snap.PAGE_FILE and manifest.terms_archive in manifest.files
    assert set(manifest.files) == {snap.FILE_NAME, snap.PAGE_FILE}
    assert manifest.license_bucket == "A" and manifest.synthetic is False
    check_terms(sample / manifest.terms_archive, snap.PAGE_PHRASES)


def test_sample_conforms_and_the_filter_drops_the_controls(sample: Path) -> None:
    everything = snap.read_all(sample)
    assert tuple(everything.columns) == snap.COLUMNS
    assert len(everything) == SAMPLE_CURRENT + SAMPLE_CONTROLS
    frame = snap.read(sample)
    enforce(snap.CONTRACT, frame, read_manifest(sample).to_dict())
    assert len(frame) == SAMPLE_CURRENT
    assert frame["End Date"].isna().all(), "open authorizations only"
    assert (frame["State"] == "PA").all() and (frame["County"] == "PHILADELPHIA").all()
    assert frame["Record ID"].astype(int).is_monotonic_increasing
    assert frame.crs.to_epsg() == 4326
    assert (frame.geometry.x == frame["Longitude"]).all()
    assert (frame.geometry.y == frame["Latitude"]).all()
    dropped = everything[~everything["Record ID"].isin(frame["Record ID"])]
    assert len(dropped) == SAMPLE_CONTROLS
    assert (dropped["State"] != "PA").any(), "a row from another state"
    assert ((dropped["State"] == "PA") & (dropped["County"] != "PHILADELPHIA")).any()
    assert dropped["End Date"].notna().any(), "a closed Philadelphia authorization"


def test_read_strips_whitespace_and_nulls_blanks(sample: Path) -> None:
    frame = snap.read(sample)
    for column in snap.COLUMNS:
        values = frame[column].dropna()
        if len(values) and values.dtype != "float64":
            assert (values.astype(str) == values.astype(str).str.strip()).all(), column
            assert (values.astype(str) != "").all(), column


def test_reads_from_the_zip_without_extracting(sample: Path) -> None:
    before = sorted(p.name for p in sample.iterdir())
    snap.read(sample)
    assert sorted(p.name for p in sample.iterdir()) == before
    with zipfile.ZipFile(sample / snap.FILE_NAME) as archive:
        assert archive.namelist() == [snap.MEMBER]


# --- negative -----------------------------------------------------------------------------


def _write_snapshot(target: Path, rows: list[list[str]]) -> Path:
    target.mkdir(parents=True)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(snap.COLUMNS)
    writer.writerows(rows)
    with zipfile.ZipFile(target / snap.FILE_NAME, "w") as archive:
        archive.writestr(snap.MEMBER, "﻿" + buffer.getvalue())
    return target


def _row(record_id: str, store_type: str = "Supermarket", **overrides: str) -> list[str]:
    base = {
        "Record ID": record_id,
        "Store Name": "Test Market",
        "Store Type": store_type,
        "Street Number": "1",
        "Street Name": "MARKET ST",
        "Additional Address": " ",
        "City": "PHILADELPHIA",
        "State": "PA",
        "Zip Code": "19107",
        "Zip4": " ",
        "County": "PHILADELPHIA",
        "Latitude": "39.9526",
        "Longitude": "-75.1652",
        "Authorization Date": "1/2/2020",
        "End Date": "",
    }
    base.update(overrides)
    return [base[column] for column in snap.COLUMNS]


def test_unknown_store_type_is_a_schema_violation_the_stop_condition(tmp_path: Path) -> None:
    snapshot = _write_snapshot(
        tmp_path / "snap_retailers" / "2026-09-02", [_row("1", "Hypermarket")]
    )
    frame = snap.read(snapshot)
    violations = check_frame(snap.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema"] and "Hypermarket" in violations[0].detail


def test_unexpected_columns_fail_the_read(tmp_path: Path) -> None:
    target = tmp_path / "snap_retailers" / "2026-09-02"
    target.mkdir(parents=True)
    with zipfile.ZipFile(target / snap.FILE_NAME, "w") as archive:
        archive.writestr(snap.MEMBER, "Record ID,Store Name\n1,X\n")
    with pytest.raises(ValueError, match="columns"):
        snap.read(target)


def test_closed_spells_and_other_counties_are_dropped(tmp_path: Path) -> None:
    rows = [
        _row("10"),
        _row("11", **{"End Date": "3/1/2016"}),
        _row("12", County="MONTGOMERY"),
        _row("13", State="NJ", County="CAMDEN"),
        _row("14", County="Philadelphia"),  # the county match is case-insensitive
    ]
    frame = snap.read(_write_snapshot(tmp_path / "snap_retailers" / "2026-09-02", rows))
    assert list(frame["Record ID"]) == ["10", "14"]
    # The county value stays the provider's: a mixed-case spelling is kept by the filter and
    # then fails the contract's allowed set, so a change in the provider's casing surfaces.
    violations = check_frame(snap.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema"] and "'County'" in violations[0].detail


def test_duplicate_record_id_is_a_key_violation(sample: Path) -> None:
    frame = snap.read(sample)
    doubled = gpd.GeoDataFrame(
        pd.concat([frame, frame.iloc[:1]], ignore_index=True), geometry="geometry", crs=frame.crs
    )
    assert {v.check for v in check_frame(snap.CONTRACT, doubled)} == {"key"}


def test_out_of_county_point_is_a_geometry_violation(sample: Path) -> None:
    frame = snap.read(sample)
    shifted = frame.set_geometry(frame.geometry.translate(xoff=1.0))
    assert {v.check for v in check_frame(snap.CONTRACT, shifted)} == {"geometry"}


def test_projected_points_are_a_geometry_violation(sample: Path) -> None:
    frame = snap.read(sample).to_crs("EPSG:26918")
    violations = check_frame(snap.CONTRACT, frame)
    assert {v.check for v in violations} == {"geometry"}
    assert any("EPSG:4326" in v.detail for v in violations), "CRS as declared"
    assert any("exceeds bounds" in v.detail for v in violations), "metres are not degrees"


def test_wrong_bucket_in_manifest_is_a_license_violation(sample: Path) -> None:
    manifest = {**read_manifest(sample).to_dict(), "license_bucket": "B"}
    with pytest.raises(ContractViolationError) as info:
        enforce(snap.CONTRACT, snap.read(sample), manifest)
    assert [v.check for v in info.value.violations] == ["license"]


def test_page_drift_is_the_terms_stop_condition(sample: Path, tmp_path: Path) -> None:
    page = tmp_path / snap.PAGE_FILE
    page.write_text(
        (sample / snap.PAGE_FILE).read_text("utf-8").replace("Dec. 31, 2025", "Dec. 31, 2026"),
        "utf-8",
    )
    with pytest.raises(Exception, match="current as of Dec. 31, 2025"):
        check_terms(page, snap.PAGE_PHRASES)
