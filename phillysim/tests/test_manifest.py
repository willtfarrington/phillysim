"""EP-4a acceptance: manifests round-trip byte-for-byte, reject bad fields, and verify snapshots.

The eight tinycity raw snapshots are the positive corpus. Negative cases are
built on the fly from copies of them so the committed fixture is never touched.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.fixtures.tinycity import RAW_SOURCES, SNAPSHOT_ID
from phillysim.manifest import (
    FIELD_NAMES,
    Manifest,
    ManifestError,
    build_manifest,
    canonical_bytes,
    loads,
    read_manifest,
    verify_raw_zone,
    verify_snapshot,
    write_manifest,
)

SOURCES = sorted(RAW_SOURCES)


def _snapshot(fixture_dir: Path, source: str) -> Path:
    return fixture_dir / "raw" / source / SNAPSHOT_ID


def _copy_raw(fixture_dir: Path, tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    shutil.copytree(fixture_dir / "raw", raw)
    return raw


# --- round trip ----------------------------------------------------------------------------


@pytest.mark.parametrize("source", SOURCES)
def test_fixture_manifest_round_trips_byte_for_byte(tinycity_dir: Path, source: str) -> None:
    path = _snapshot(tinycity_dir, source) / "manifest.json"
    original = path.read_bytes()
    manifest = loads(original)
    assert manifest.source == source
    assert manifest.snapshot_id == SNAPSHOT_ID
    assert manifest.synthetic is True
    assert manifest.dumps() == original
    assert read_manifest(path.parent) == manifest


def test_field_order_matches_the_data_dictionary() -> None:
    assert FIELD_NAMES == (
        "source",
        "snapshot_id",
        "acquired_at",
        "acquisition_url",
        "acquisition_url_alt",
        "terms_archive",
        "license_bucket",
        "license_note",
        "schema_version",
        "synthetic",
        "files",
    )


def test_write_then_read_is_identity(tmp_path: Path) -> None:
    snap = tmp_path / "acs" / "2026-02-01"
    snap.mkdir(parents=True)
    (snap / "TERMS.txt").write_text("terms\n")
    (snap / "data.csv").write_text("a,b\n1,2\n")
    manifest = build_manifest(
        snap,
        source="acs",
        snapshot_id="2026-02-01",
        acquired_at="2026-02-01T12:00:00+00:00",
        acquisition_url="https://example.invalid/acs",
        acquisition_url_alt="https://alt.example.invalid/acs",
        terms_archive="TERMS.txt",
        license_bucket="A",
        license_note="test",
        schema_version=1,
        synthetic=True,
    )
    path = write_manifest(snap, manifest)
    assert read_manifest(snap) == manifest
    assert loads(path.read_bytes()).dumps() == path.read_bytes()
    assert set(manifest.files) == {"TERMS.txt", "data.csv"}
    assert verify_snapshot(snap).ok


# --- field rules ---------------------------------------------------------------------------


def _payload(tinycity_dir: Path) -> dict:
    return json.loads((_snapshot(tinycity_dir, "acs") / "manifest.json").read_text("utf-8"))


@pytest.mark.parametrize("missing", FIELD_NAMES)
def test_every_field_is_required(tinycity_dir: Path, missing: str) -> None:
    payload = _payload(tinycity_dir)
    del payload[missing]
    with pytest.raises(ManifestError, match=missing):
        Manifest.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("license_bucket", "Z", "license_bucket"),
        ("license_bucket", None, "license_bucket"),
        ("schema_version", "1", "schema_version"),
        ("schema_version", 0, "schema_version"),
        ("schema_version", True, "schema_version"),
        ("synthetic", "yes", "synthetic"),
        ("acquired_at", "2026-01-01", "acquired_at"),
        ("acquired_at", "2026-01-01T00:00:00", "UTC"),
        ("acquired_at", "2026-01-01T00:00:00-05:00", "UTC"),
        ("acquisition_url", "file:///C:/data/acs.csv", "http"),
        ("acquisition_url", "ftp://example.invalid/acs", "http"),
        ("acquisition_url", "https://user:pw@example.invalid/acs", "credentials"),
        ("acquisition_url", "https:///no-host", "host"),
        ("acquisition_url_alt", "not a url", "acquisition_url_alt"),
        ("terms_archive", "missing.txt", "terms_archive"),
        ("terms_archive", "", "terms_archive"),
        ("snapshot_id", "latest", "snapshot id"),
        ("source", "ACS", "source identifier"),
        ("files", {}, "files"),
        ("files", {"../acs.csv": "0" * 64}, "bare name"),
        ("files", {"C:\\acs.csv": "0" * 64}, "bare name"),
        ("files", {"acs.csv": "abc"}, "digest"),
        ("files", {"manifest.json": "0" * 64}, "manifest.json"),
    ],
)
def test_malformed_fields_are_rejected(
    tinycity_dir: Path, field: str, value: object, match: str
) -> None:
    payload = _payload(tinycity_dir)
    payload[field] = value
    with pytest.raises(ManifestError, match=match):
        Manifest.from_dict(payload)


def test_unknown_fields_are_rejected(tinycity_dir: Path) -> None:
    payload = _payload(tinycity_dir)
    payload["hostname"] = "somebody-laptop"
    with pytest.raises(ManifestError, match="unknown field"):
        Manifest.from_dict(payload)


def test_non_json_and_non_object_are_rejected() -> None:
    with pytest.raises(ManifestError, match="JSON"):
        loads(b"{not json")
    with pytest.raises(ManifestError, match="object"):
        loads(canonical_bytes([1, 2]))


def test_invalid_variant_manifest_fault_is_a_manifest_error(tinycity_invalid_dir: Path) -> None:
    """The injected license bucket 'Z' is caught by the engine, not just the contract harness."""
    report = verify_snapshot(_snapshot(tinycity_invalid_dir, "snap_retailers"))
    assert not report.ok
    assert report.problems[0].kind == "manifest"
    assert "license_bucket" in report.problems[0].detail


# --- verification --------------------------------------------------------------------------


def test_all_eight_fixture_snapshots_verify(tinycity_dir: Path) -> None:
    report = verify_raw_zone(tinycity_dir / "raw")
    assert report.ok, report.lines()
    assert [s.label for s in report.snapshots] == [f"{s}/{SNAPSHOT_ID}" for s in SOURCES]
    assert len(report.snapshots) == 8
    assert report.lines()[-1] == "8 of 8 snapshot(s) verified"


def test_tampered_byte_fails_naming_the_file(tinycity_dir: Path, tmp_path: Path) -> None:
    raw = _copy_raw(tinycity_dir, tmp_path)
    target = raw / "acs" / SNAPSHOT_ID / "acs.csv"
    data = bytearray(target.read_bytes())
    data[-2] ^= 0x01
    target.write_bytes(bytes(data))
    report = verify_raw_zone(raw)
    assert not report.ok
    assert [s.label for s in report.failed] == [f"acs/{SNAPSHOT_ID}"]
    (problem,) = report.failed[0].problems
    assert problem.kind == "digest"
    assert problem.detail.startswith("acs.csv:")
    assert any("FAIL acs/2026-01-01" in line for line in report.lines())


def test_missing_and_extra_files_are_reported(tinycity_dir: Path, tmp_path: Path) -> None:
    raw = _copy_raw(tinycity_dir, tmp_path)
    snap = raw / "gtfs" / SNAPSHOT_ID
    (snap / "stops.txt").unlink()
    (snap / "notes.txt").write_text("left behind\n")
    report = verify_snapshot(snap)
    assert {(p.kind, p.detail.split(" ")[0]) for p in report.problems} == {
        ("missing", "stops.txt"),
        ("extra", "notes.txt"),
    }


def test_relocated_snapshot_fails_layout(tinycity_dir: Path, tmp_path: Path) -> None:
    raw = _copy_raw(tinycity_dir, tmp_path)
    (raw / "acs" / SNAPSHOT_ID).rename(raw / "acs" / "2026-01-02")
    shutil.move(str(raw / "cenpop"), str(raw / "cenpop_old"))
    report = verify_raw_zone(raw)
    kinds = {s.label: {p.kind for p in s.problems} for s in report.failed}
    assert kinds == {"acs/2026-01-02": {"layout"}, f"cenpop_old/{SNAPSHOT_ID}": {"layout"}}


def test_stray_entries_fail_the_zone(tinycity_dir: Path, tmp_path: Path) -> None:
    raw = _copy_raw(tinycity_dir, tmp_path)
    (raw / "acs" / "scratch").mkdir()
    (raw / "download.tmp").write_bytes(b"")
    report = verify_raw_zone(raw)
    assert not report.ok
    assert report.strays == ("acs/scratch", "download.tmp")
    assert all(s.ok for s in report.snapshots)


def test_snapshot_without_manifest_fails(tmp_path: Path) -> None:
    snap = tmp_path / "raw" / "acs" / SNAPSHOT_ID
    snap.mkdir(parents=True)
    (snap / "acs.csv").write_text("x\n")
    report = verify_raw_zone(tmp_path / "raw")
    assert [p.kind for p in report.snapshots[0].problems] == ["manifest"]


# --- CLI -----------------------------------------------------------------------------------


def test_cli_verify_fixture_is_green() -> None:
    result = CliRunner().invoke(app, ["verify", "--fixture"])
    assert result.exit_code == 0, result.output
    assert "8 of 8 snapshot(s) verified" in result.output


def test_cli_verify_raw_names_the_tampered_file(tinycity_dir: Path, tmp_path: Path) -> None:
    raw = _copy_raw(tinycity_dir, tmp_path)
    target = raw / "osm_network" / SNAPSHOT_ID / "edges.geojson"
    target.write_bytes(target.read_bytes() + b" ")
    result = CliRunner().invoke(app, ["verify", "--raw", str(raw)])
    assert result.exit_code == 1, result.output
    assert "FAIL osm_network/2026-01-01" in result.output
    assert "edges.geojson" in result.output
    assert "7 of 8 snapshot(s) verified" in result.output


def test_cli_verify_data_root_without_raw_zone(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PHILLYSIM_DATA_ROOT", str(tmp_path / "root"))
    result = CliRunner().invoke(app, ["verify"])
    assert result.exit_code == 1
    assert "nothing to verify" in result.output
    assert not (tmp_path / "root").exists(), "verify must not create the data root"


def test_cli_verify_flags_are_exclusive(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["verify", "--fixture", "--raw", str(tmp_path)])
    assert result.exit_code != 0
