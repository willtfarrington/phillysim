"""EP-12 source contract for SEPTA's GTFS feed (``gtfs``), on the committed sample (offline).

The sample is **synthetic** (a feed in SEPTA's layout over the six sample tracts, one
control stop outside the routing box; no SEPTA feed contents are committed). Positive:
it verifies, admits through the adapter's own allowlist and limits, reads in place
(the two inner zips through the nested guards, nothing extracted) and conforms to its
contract; ``unwrap`` copies the two inner zips out as files. Negative: each check kind
fires on a crafted deviation; an inner zip that fails a guard is refused before
anything is read out of it; a wrong member set is refused.
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import pytest

from phillysim import pipeline
from phillysim.adapters import ADAPTERS, septa_gtfs
from phillysim.contracts import ContractViolationError, check_frame, enforce
from phillysim.download import check_terms, parse_digest
from phillysim.guards import GuardError, check_url_allowed
from phillysim.manifest import read_manifest, verify_snapshot
from phillysim.quarantine import admit


@pytest.fixture(scope="module")
def sample(spine_samples_dir: Path) -> Path:
    return spine_samples_dir / "raw" / septa_gtfs.SOURCE / pipeline.SNAPSHOT_IDS[septa_gtfs.SOURCE]


def test_adapter_is_registered_and_never_published() -> None:
    assert septa_gtfs.SOURCE in ADAPTERS and septa_gtfs.SOURCE in pipeline.SOURCES
    assert septa_gtfs.SOURCE not in pipeline.PUBLISH_SOURCES, "the feed is never republished"
    assert pipeline.SNAPSHOT_IDS[septa_gtfs.SOURCE] == "2026-09-03"
    assert ADAPTERS[septa_gtfs.SOURCE].contract.name == septa_gtfs.SOURCE
    assert ADAPTERS[septa_gtfs.SOURCE].filter_note and ADAPTERS[septa_gtfs.SOURCE].citation
    assert septa_gtfs.RELEASE in ADAPTERS[septa_gtfs.SOURCE].citation


def test_spec_pins_the_release_asset_its_digest_and_the_agreement() -> None:
    spec = septa_gtfs.SPEC
    assert septa_gtfs.RELEASE == "v202609060" and septa_gtfs.RELEASE in septa_gtfs.URL
    assert spec.acquisition_url == septa_gtfs.URL and spec.acquisition_url_alt is None
    (only,) = spec.files
    assert only.file_name == "gtfs_public.zip" and only.urls == (septa_gtfs.URL,)
    assert parse_digest(only.digest) == ("sha256", septa_gtfs.SHA256)
    assert len(septa_gtfs.SHA256) == 64 and only.md5_of is None
    assert spec.terms.url == "https://www3.septa.org/developer/"
    assert spec.terms.file_name == "terms.html"
    assert spec.terms_must_contain == (
        "SEPTA reserves the right to alter and/or no longer provide the Trip Planning Data at "
        "any time without prior notice.",
        "SEPTA reserves the right to institute a license fee at any time in the future without "
        "prior notice.",
    )
    assert {"github.com", "objects.githubusercontent.com", "www3.septa.org"} <= set(spec.allowlist)
    assert all(urlsplit(url).scheme == "https" for url in (septa_gtfs.URL, spec.terms.url))
    check_url_allowed(septa_gtfs.URL, spec.allowlist)
    check_url_allowed(spec.terms.url, spec.allowlist)
    check_url_allowed("https://objects.githubusercontent.com/x", spec.allowlist)
    check_url_allowed("https://release-assets.githubusercontent.com/x", spec.allowlist)
    with pytest.raises(GuardError):
        check_url_allowed("https://raw.githubusercontent.com/x", spec.allowlist)
    assert spec.license_bucket == "A", "the feed is not OSM-derived; Bucket B never comes from it"
    for phrase in (
        "revocable",
        "never redistributed",
        "no feed contents are ever published",
        "facts",
        "Bucket A",
    ):
        assert phrase in spec.license_note
    assert spec.limits.max_file_bytes == 128 * 1024**2
    assert spec.limits.max_extracted_bytes == 1024**3
    assert spec.limits.max_compression_ratio == 50 and spec.limits.max_members == 50


def test_contract_pins_bucket_a_two_feeds_and_the_pinned_dates() -> None:
    assert septa_gtfs.CONTRACT.license_buckets == frozenset({"A"})
    assert septa_gtfs.CONTRACT.key == "feed"
    assert (septa_gtfs.CONTRACT.min_rows, septa_gtfs.CONTRACT.max_rows) == (2, 2)
    by_name = {column.name: column for column in septa_gtfs.CONTRACT.columns}
    assert by_name["feed"].allowed == frozenset({"google_bus.zip", "google_rail.zip"})
    assert by_name["missing_required"].maximum == 0
    assert by_name["covers_wednesday"].minimum == by_name["covers_saturday"].minimum == 1
    assert by_name["services_wednesday"].minimum == by_name["services_saturday"].minimum == 1
    assert (
        by_name["stops_outside_box"].minimum == 0 and by_name["stops_outside_box"].maximum is None
    )
    assert by_name["feed_version"].allowed == frozenset({septa_gtfs.RELEASE})
    assert by_name["agency_timezone"].allowed == frozenset({"America/New_York"})
    assert (septa_gtfs.PINNED_WEDNESDAY, septa_gtfs.PINNED_SATURDAY) == ("2026-09-23", "2026-09-26")


# --- the sample: verify, admit, read, conform ----------------------------------------------


def test_sample_snapshot_verifies_and_admits(sample: Path, tmp_path: Path) -> None:
    assert verify_snapshot(sample).ok
    staged = tmp_path / "raw" / septa_gtfs.SOURCE / pipeline.SNAPSHOT_IDS[septa_gtfs.SOURCE]
    shutil.copytree(sample, staged)
    spec = septa_gtfs.SPEC
    manifest = admit(staged, tmp_path / "quarantine", allowlist=spec.allowlist, limits=spec.limits)
    assert manifest.source == septa_gtfs.SOURCE and not (tmp_path / "quarantine").exists()


def test_sample_manifest_is_synthetic_and_bucket_a(sample: Path) -> None:
    manifest = read_manifest(sample)
    spec = septa_gtfs.SPEC
    assert manifest.snapshot_id == pipeline.SNAPSHOT_IDS[septa_gtfs.SOURCE]
    assert manifest.license_bucket == "A"
    assert manifest.synthetic is True, "no subset of the real feed is ever committed"
    assert "CI SAMPLE (synthetic)" in manifest.license_note
    assert "no SEPTA feed contents" in manifest.license_note
    assert (
        manifest.terms_archive == spec.terms.file_name and manifest.terms_archive in manifest.files
    )
    assert set(manifest.files) == {septa_gtfs.FILE_NAME, septa_gtfs.TERMS_FILE}
    assert manifest.acquisition_url == spec.acquisition_url
    check_terms(sample / manifest.terms_archive, spec.terms_must_contain)


def test_sample_conforms_to_its_contract(sample: Path) -> None:
    frame = septa_gtfs.read(sample)
    enforce(septa_gtfs.CONTRACT, frame, read_manifest(sample).to_dict())
    assert tuple(frame.columns) == septa_gtfs.SUMMARY_COLUMNS
    assert list(frame["feed"]) == list(septa_gtfs.FEEDS)
    assert list(frame["label"]) == ["bus_metro", "rail"]
    bus, rail = frame.iloc[0], frame.iloc[1]
    assert (bus["feed_start_date"], bus["feed_end_date"]) == ("20260906", "20270220")
    assert (rail["feed_start_date"], rail["feed_end_date"]) == ("20260906", "20261017")
    assert (frame["covers_wednesday"] == 1).all() and (frame["covers_saturday"] == 1).all()
    assert (frame["services_wednesday"] >= 1).all() and (frame["services_saturday"] >= 1).all()
    assert bus["stops"] == 7 and bus["stops_outside_box"] == 1, "six tract centers + the control"
    assert rail["stops"] == 2 and rail["stops_outside_box"] == 0
    assert (frame["missing_required"] == 0).all() and frame["missing_names"].isna().all()
    assert (frame["routes"] == 1).all() and (frame["trips"] == 2).all()
    assert (frame["feed_version"] == septa_gtfs.RELEASE).all()


def test_read_works_in_place_and_extracts_nothing(sample: Path) -> None:
    before = sorted(p.name for p in sample.iterdir())
    septa_gtfs.read(sample)
    stops = septa_gtfs.read_stops(sample, "google_rail.zip")
    assert sorted(p.name for p in sample.iterdir()) == before
    assert (
        list(stops.columns) == ["stop_id", "stop_name", "stop_lat", "stop_lon"] and len(stops) == 2
    )


def test_calendar_exception_removes_a_service(sample: Path) -> None:
    with zipfile.ZipFile(sample / septa_gtfs.FILE_NAME) as outer:
        inner = zipfile.ZipFile(outer.open("google_bus.zip"))
        assert septa_gtfs.services_on(inner, septa_gtfs.PINNED_WEDNESDAY) == 1
        assert septa_gtfs.services_on(inner, "2026-11-26") == 0, "calendar_dates exception type 2"
        assert septa_gtfs.services_on(inner, "2026-09-01") == 0, "before the feed window"


def test_unwrap_copies_the_two_feed_zips_as_files(sample: Path, tmp_path: Path) -> None:
    out = tmp_path / "network"
    written = septa_gtfs.unwrap(sample, out)
    assert set(written) == set(septa_gtfs.FEEDS)
    assert sorted(p.name for p in out.iterdir()) == sorted(septa_gtfs.FEEDS)
    for feed in septa_gtfs.FEEDS:
        assert zipfile.is_zipfile(out / feed) and (out / feed).stat().st_size == written[feed]
        with zipfile.ZipFile(out / feed) as inner:
            assert "stops.txt" in inner.namelist(), "the feed zip itself, unexpanded"
    assert not any(p.suffix == ".txt" for p in out.rglob("*")), "nothing inside a feed is extracted"


# --- crafted deviations ---------------------------------------------------------------------


def _outer(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def _inner(members: dict[str, bytes]) -> bytes:
    return _outer(members)


def _stage(sample: Path, tmp_path: Path, outer: bytes) -> Path:
    staged = tmp_path / "raw" / septa_gtfs.SOURCE / pipeline.SNAPSHOT_IDS[septa_gtfs.SOURCE]
    shutil.copytree(sample, staged)
    (staged / septa_gtfs.FILE_NAME).write_bytes(outer)
    return staged


def test_inner_zip_failing_a_guard_is_refused_before_anything_is_read(
    sample: Path, tmp_path: Path
) -> None:
    with zipfile.ZipFile(sample / septa_gtfs.FILE_NAME) as good:
        rail = good.read("google_rail.zip")
    bomb = _inner({"stop_times.txt": b"0" * (60 * 1024 * 1024)})  # ratio far over 50:1
    staged = _stage(sample, tmp_path, _outer({"google_bus.zip": bomb, "google_rail.zip": rail}))
    with pytest.raises(GuardError) as info:
        septa_gtfs.read(staged)
    assert info.value.guard == "bomb" and "google_bus.zip" in info.value.detail
    with pytest.raises(GuardError):
        septa_gtfs.unwrap(staged, tmp_path / "network")
    assert not (tmp_path / "network").exists() or not any((tmp_path / "network").iterdir())


def test_inner_member_that_is_not_a_zip_is_refused(sample: Path, tmp_path: Path) -> None:
    staged = _stage(
        sample, tmp_path, _outer({"google_bus.zip": b"not a zip", "google_rail.zip": b"nor this"})
    )
    with pytest.raises(GuardError) as info:
        septa_gtfs.read(staged)
    assert info.value.guard == "bomb" and "not a zip" in info.value.detail


def test_wrong_member_set_is_refused(sample: Path, tmp_path: Path) -> None:
    staged = _stage(sample, tmp_path, _outer({"google_bus.zip": _inner({"a.txt": b"x"})}))
    with pytest.raises(ValueError, match="members"):
        septa_gtfs.read(staged)
    with pytest.raises(ValueError, match="members"):
        septa_gtfs.unwrap(staged, tmp_path / "network")


def test_missing_required_file_is_a_schema_violation(sample: Path, tmp_path: Path) -> None:
    with zipfile.ZipFile(sample / septa_gtfs.FILE_NAME) as good:
        bus, rail = good.read("google_bus.zip"), good.read("google_rail.zip")
    with zipfile.ZipFile(io.BytesIO(bus)) as inner:
        members = {name: inner.read(name) for name in inner.namelist() if name != "feed_info.txt"}
        members["stops.txt"] = members["stops.txt"].replace(b"stop_lon", b"longitude", 1)
    staged = _stage(
        sample, tmp_path, _outer({"google_bus.zip": _inner(members), "google_rail.zip": rail})
    )
    frame = septa_gtfs.read(staged)
    assert frame.loc[0, "missing_required"] == 2
    assert frame.loc[0, "missing_names"] == "stops.txt:stop_lon; feed_info.txt"
    violations = check_frame(septa_gtfs.CONTRACT, frame)
    checks = {v.detail.split("'")[1] for v in violations if v.check == "schema"}
    assert {"missing_required", "covers_wednesday", "covers_saturday", "feed_version"} <= checks


def test_dates_outside_the_feed_window_are_a_schema_violation(sample: Path) -> None:
    frame = septa_gtfs.read(sample)
    frame.loc[1, "feed_end_date"] = "20260915"
    frame.loc[1, "covers_wednesday"] = 0
    frame.loc[1, "covers_saturday"] = 0
    violations = check_frame(septa_gtfs.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema", "schema"]
    assert "covers_wednesday" in violations[0].detail and "covers_saturday" in violations[1].detail


def test_no_service_on_a_pinned_day_is_a_schema_violation(sample: Path) -> None:
    frame = septa_gtfs.read(sample)
    frame.loc[0, "services_saturday"] = 0
    violations = check_frame(septa_gtfs.CONTRACT, frame)
    assert [v.check for v in violations] == ["schema"] and "services_saturday" in violations[
        0
    ].detail


def test_stops_outside_the_box_are_information_not_a_violation(sample: Path) -> None:
    frame = septa_gtfs.read(sample)
    frame.loc[0, "stops_outside_box"] = 5_000
    assert check_frame(septa_gtfs.CONTRACT, frame) == []


def test_bucket_b_in_manifest_is_a_license_violation(sample: Path) -> None:
    manifest = {**read_manifest(sample).to_dict(), "license_bucket": "B"}
    with pytest.raises(ContractViolationError) as info:
        enforce(septa_gtfs.CONTRACT, septa_gtfs.read(sample), manifest)
    assert [v.check for v in info.value.violations] == ["license"]


def test_one_feed_is_a_rows_violation(sample: Path) -> None:
    frame = septa_gtfs.read(sample).iloc[:1]
    assert {v.check for v in check_frame(septa_gtfs.CONTRACT, frame)} == {"rows"}


def test_duplicate_feed_is_a_key_violation(sample: Path) -> None:
    frame = septa_gtfs.read(sample)
    doubled = pd.concat([frame.iloc[:1], frame.iloc[:1]], ignore_index=True)
    assert {v.check for v in check_frame(septa_gtfs.CONTRACT, doubled)} == {"key"}
