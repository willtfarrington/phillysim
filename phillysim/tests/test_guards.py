"""EP-4a acceptance: each download guard refuses a crafted malicious input, and admission
quarantines it. Everything here is built locally; no network is involved.
"""

from __future__ import annotations

import gzip
import io
import json
import shutil
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from phillysim.fixtures.tinycity import SNAPSHOT_ID
from phillysim.guards import (
    GuardError,
    Limits,
    check_file_size,
    check_url_allowed,
    copy_capped,
    extract_gzip,
    extract_zip,
    inspect_zip,
    safe_member_path,
    screen_snapshot,
)
from phillysim.manifest import read_manifest, sha256_file, verify_snapshot, write_manifest
from phillysim.quarantine import REASON_SUFFIX, QuarantinedError, admit, list_quarantined

ALLOWLIST = frozenset({"example.invalid", "data.census.gov"})
SMALL = Limits(
    max_file_bytes=64 * 1024,
    max_extracted_bytes=1024 * 1024,
    max_compression_ratio=50.0,
    max_members=20,
)


def _zip(path: Path, members: dict[str, bytes], *, compress: bool = True) -> Path:
    method = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(path, "w", method) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


# --- allowlist ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/tinycity/acs",
        "https://sub.example.invalid/x.zip",
        "https://EXAMPLE.invalid./x",
        "https://data.census.gov:443/api",
    ],
)
def test_allowed_urls(url: str) -> None:
    assert check_url_allowed(url, ALLOWLIST) == url


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/x",
        "https://example.invalid.evil.example/x",
        "https://notexample.invalid/x",
        "http://example.invalid/x",
        "https://user:pw@example.invalid/x",
        "https://93.184.216.34/x",
        "https://[2001:db8::1]/x",
        "file:///etc/passwd",
        "https:///x",
    ],
)
def test_off_allowlist_urls_are_refused(url: str) -> None:
    with pytest.raises(GuardError) as info:
        check_url_allowed(url, ALLOWLIST)
    assert info.value.guard == "allowlist"


def test_allowlist_entries_are_validated() -> None:
    with pytest.raises(ValueError):
        check_url_allowed("https://example.invalid/x", ["https://example.invalid"])


# --- size --------------------------------------------------------------------------------


def test_size_cap_before_copy(tmp_path: Path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(b"\0" * (SMALL.max_file_bytes + 1))
    with pytest.raises(GuardError) as info:
        check_file_size(big, SMALL)
    assert info.value.guard == "size"
    assert "big.bin" in str(info.value)
    small = tmp_path / "small.bin"
    small.write_bytes(b"\0" * SMALL.max_file_bytes)
    assert check_file_size(small, SMALL) == SMALL.max_file_bytes


def test_size_cap_during_stream_ignores_declared_length() -> None:
    sink = io.BytesIO()
    assert copy_capped(io.BytesIO(b"x" * 100), sink, 100) == 100
    with pytest.raises(GuardError) as info:
        copy_capped(io.BytesIO(b"x" * 101), io.BytesIO(), 100)
    assert info.value.guard == "size"


# --- zip-slip ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "member",
    [
        "../evil.txt",
        "ok/../../evil.txt",
        "/etc/evil.txt",
        "\\evil.txt",
        "C:\\evil.txt",
        "c:/evil.txt",
        "ok\\..\\evil.txt",
        "dir/",
        "",
    ],
)
def test_zip_slip_member_names_are_refused(tmp_path: Path, member: str) -> None:
    with pytest.raises(GuardError) as info:
        safe_member_path(tmp_path, member)
    assert info.value.guard == "zip_slip"


def test_benign_member_paths_resolve_inside_root(tmp_path: Path) -> None:
    assert safe_member_path(tmp_path, "a/b/c.txt") == (tmp_path / "a" / "b" / "c.txt").resolve()
    assert safe_member_path(tmp_path, "sub\\win.txt") == (tmp_path / "sub" / "win.txt").resolve()


def test_zip_slip_archive_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    archive = _zip(tmp_path / "slip.zip", {"good.txt": b"ok", "../escape.txt": b"bad"})
    root = tmp_path / "out"
    root.mkdir()
    with pytest.raises(GuardError) as info:
        extract_zip(archive, root, SMALL)
    assert info.value.guard == "zip_slip"
    assert list(root.iterdir()) == []
    assert not (tmp_path / "escape.txt").exists()


def test_symlink_members_are_refused(tmp_path: Path) -> None:
    archive = tmp_path / "link.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = 0o120777 << 16  # S_IFLNK | 0777
        zf.writestr(info, "../../target")
    with pytest.raises(GuardError) as err:
        inspect_zip(archive, SMALL)
    assert err.value.guard == "zip_slip"


# --- bomb --------------------------------------------------------------------------------


def test_compression_ratio_bomb_is_refused(tmp_path: Path) -> None:
    archive = _zip(tmp_path / "bomb.zip", {"zeros.bin": b"\0" * (512 * 1024)})
    assert archive.stat().st_size < 4096
    with pytest.raises(GuardError) as info:
        inspect_zip(archive, SMALL)
    assert info.value.guard == "bomb"
    assert "ratio" in info.value.detail


def test_declared_total_over_cap_is_refused(tmp_path: Path) -> None:
    payload = bytes(range(256)) * 8  # incompressible-ish, 2 KB
    archive = _zip(tmp_path / "big.zip", {f"f{i}.bin": payload for i in range(10)}, compress=False)
    limits = Limits(max_file_bytes=1 << 20, max_extracted_bytes=10_000, max_compression_ratio=50)
    with pytest.raises(GuardError) as info:
        inspect_zip(archive, limits)
    assert info.value.guard == "bomb"
    assert "declared" in info.value.detail


def test_member_count_over_cap_is_refused(tmp_path: Path) -> None:
    archive = _zip(tmp_path / "many.zip", {f"f{i}.txt": b"x" for i in range(21)}, compress=False)
    with pytest.raises(GuardError) as info:
        inspect_zip(archive, SMALL)
    assert info.value.guard == "bomb"


def test_gzip_stream_is_capped_by_actual_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "zeros.gz"
    archive.write_bytes(gzip.compress(b"\0" * (2 * 1024 * 1024)))
    assert archive.stat().st_size < SMALL.max_file_bytes
    with pytest.raises(GuardError) as info:
        extract_gzip(archive, tmp_path / "zeros.bin", SMALL)
    assert info.value.guard == "bomb"
    small = tmp_path / "small.gz"
    small.write_bytes(gzip.compress(b"hello\n"))
    assert extract_gzip(small, tmp_path / "small.txt", SMALL) == 6
    assert (tmp_path / "small.txt").read_bytes() == b"hello\n"


def test_benign_archive_extracts(tmp_path: Path) -> None:
    archive = _zip(tmp_path / "ok.zip", {"a.txt": b"A\n", "sub/b.txt": b"B\n", "empty/": b""})
    written = extract_zip(archive, tmp_path / "out", SMALL)
    assert sorted(p.relative_to(tmp_path / "out").as_posix() for p in written) == [
        "a.txt",
        "sub/b.txt",
    ]
    assert (tmp_path / "out" / "sub" / "b.txt").read_bytes() == b"B\n"


def test_not_a_zip_is_refused(tmp_path: Path) -> None:
    fake = tmp_path / "fake.zip"
    fake.write_bytes(b"PK\x03\x04 not really")
    with pytest.raises(GuardError):
        inspect_zip(fake, SMALL)


def test_limits_must_be_sane() -> None:
    with pytest.raises(ValueError):
        Limits(max_file_bytes=0)
    with pytest.raises(ValueError):
        Limits(max_compression_ratio=1.0)


# --- admission + quarantine: one negative test per guard ----------------------------


@pytest.fixture
def staged(tinycity_dir: Path, tmp_path: Path) -> tuple[Path, Path]:
    """A copy of the gtfs snapshot in a scratch raw zone, plus an empty quarantine zone."""
    snap = tmp_path / "raw" / "gtfs" / SNAPSHOT_ID
    shutil.copytree(tinycity_dir / "raw" / "gtfs" / SNAPSHOT_ID, snap)
    return snap, tmp_path / "quarantine"


def _add_file(snap: Path, name: str, data: bytes) -> None:
    """Add a file and re-sign the manifest so only the guard under test can fire."""
    (snap / name).write_bytes(data)
    manifest = read_manifest(snap)
    write_manifest(snap, manifest.with_files({**manifest.files, name: sha256_file(snap / name)}))
    assert verify_snapshot(snap).ok


def _assert_quarantined(
    info: QuarantinedError, snap: Path, quarantine_zone: Path, kind: str, *, needle: str
) -> None:
    record = info.record
    assert record.kind == kind
    assert needle in record.reason
    assert not snap.exists(), "the offending snapshot must leave the raw zone"
    assert not snap.parent.exists() or list(snap.parent.iterdir()) == []
    moved = quarantine_zone / "gtfs" / record.quarantined_as
    assert moved.is_dir() and (moved / "manifest.json").is_file()
    reason = quarantine_zone / "gtfs" / (record.quarantined_as + REASON_SUFFIX)
    payload = json.loads(reason.read_text("utf-8"))
    assert payload == record.to_dict()
    assert payload["quarantined_at"].endswith("Z")
    assert ":\\" not in reason.read_text("utf-8") and str(snap.anchor) not in payload["reason"]
    assert list_quarantined(quarantine_zone) == [record]


def test_valid_snapshot_is_admitted(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    manifest = admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    assert manifest.source == "gtfs"
    assert snap.is_dir() and not quarantine_zone.exists()


def test_oversized_input_is_refused_and_quarantined(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    _add_file(snap, "huge.bin", b"\0" * (SMALL.max_file_bytes + 1))
    with pytest.raises(QuarantinedError) as info:
        admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    _assert_quarantined(info.value, snap, quarantine_zone, "size", needle="huge.bin")


def test_zip_slip_input_is_refused_and_quarantined(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("../../escape.txt")
        info.external_attr = 0o120777 << 16  # also a symlink: refused on inspection
        zf.writestr(info, "x")
    _add_file(snap, "feed.zip", buffer.getvalue())
    with pytest.raises(QuarantinedError) as err:
        admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    _assert_quarantined(err.value, snap, quarantine_zone, "zip_slip", needle="escape.txt")


def test_decompression_bomb_is_refused_and_quarantined(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeros.bin", b"\0" * (512 * 1024))
    _add_file(snap, "feed.zip", buffer.getvalue())
    with pytest.raises(QuarantinedError) as err:
        admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    _assert_quarantined(err.value, snap, quarantine_zone, "bomb", needle="ratio")


def test_off_allowlist_input_is_refused_and_quarantined(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    with pytest.raises(QuarantinedError) as err:
        admit(snap, quarantine_zone, allowlist={"data.census.gov"}, limits=SMALL)
    _assert_quarantined(err.value, snap, quarantine_zone, "allowlist", needle="example.invalid")


def test_alt_url_is_also_checked(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    manifest = replace(read_manifest(snap), acquisition_url_alt="https://evil.example/feed")
    write_manifest(snap, manifest)
    with pytest.raises(QuarantinedError) as err:
        admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    assert err.value.record.kind == "allowlist"
    assert "evil.example" in err.value.record.reason


def test_tampered_snapshot_is_quarantined_with_verify_reason(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    (snap / "stops.txt").write_bytes(b"stop_id\n")
    with pytest.raises(QuarantinedError) as err:
        admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    _assert_quarantined(err.value, snap, quarantine_zone, "verify", needle="stops.txt")


def test_malformed_manifest_is_quarantined(staged: tuple[Path, Path]) -> None:
    snap, quarantine_zone = staged
    (snap / "manifest.json").write_bytes(b"{}")
    with pytest.raises(QuarantinedError) as err:
        admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
    _assert_quarantined(err.value, snap, quarantine_zone, "manifest", needle="missing field")


def test_repeat_quarantine_never_overwrites(staged: tuple[Path, Path], tinycity_dir: Path) -> None:
    snap, quarantine_zone = staged
    for expected in ("2026-01-01", "2026-01-01-q2"):
        (snap / "manifest.json").write_bytes(b"{}")
        with pytest.raises(QuarantinedError) as err:
            admit(snap, quarantine_zone, allowlist=ALLOWLIST, limits=SMALL)
        assert err.value.record.quarantined_as == expected
        shutil.copytree(tinycity_dir / "raw" / "gtfs" / SNAPSHOT_ID, snap)
    assert len(list_quarantined(quarantine_zone)) == 2


def test_screen_snapshot_refuses_symlink_entries(tmp_path: Path) -> None:
    snap = tmp_path / "snap"
    snap.mkdir()
    (snap / "real.txt").write_text("x")
    try:
        (snap / "link.txt").symlink_to(snap / "real.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this host")
    with pytest.raises(GuardError) as info:
        screen_snapshot(snap, allowlist=ALLOWLIST, limits=SMALL)
    assert info.value.guard == "zip_slip"
