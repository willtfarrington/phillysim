"""EP-4a: zone layout and snapshot identifiers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from phillysim.config import ZONES, Settings
from phillysim.zones import (
    SnapshotId,
    ZoneLayoutError,
    check_snapshot_id,
    check_source,
    ensure_layout,
    list_snapshots,
    list_sources,
    next_snapshot_id,
    snapshot_dir,
    stray_entries,
)


@pytest.mark.parametrize("text", ["2026-01-01", "2026-01-01-1", "1999-12-31-250"])
def test_snapshot_id_round_trips(text: str) -> None:
    assert str(SnapshotId.parse(text)) == text
    assert check_snapshot_id(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "20260101",
        "2026-13-01",
        "2026-02-30",
        "2026-01-01-0",
        "2026-01-01-01",
        "2026-01-01-1234",
        "2026-01-01/x",
        "../2026-01-01",
        "latest",
        "",
    ],
)
def test_bad_snapshot_ids_are_rejected(text: str) -> None:
    with pytest.raises(ZoneLayoutError):
        SnapshotId.parse(text)


def test_snapshot_ids_order_by_date_then_sequence() -> None:
    ids = [SnapshotId.parse(t) for t in ["2026-01-02", "2026-01-01-2", "2026-01-01"]]
    assert [str(s) for s in sorted(ids)] == ["2026-01-01", "2026-01-01-2", "2026-01-02"]


@pytest.mark.parametrize("name", ["acs", "snap_retailers", "osm_network2"])
def test_valid_source_names(name: str) -> None:
    assert check_source(name) == name


@pytest.mark.parametrize("name", ["ACS", "1acs", "snap-retailers", "a/b", "..", "", "a b"])
def test_bad_source_names_are_rejected(name: str) -> None:
    with pytest.raises(ZoneLayoutError):
        check_source(name)


def test_snapshot_dir_validates_both_components(tmp_path: Path) -> None:
    assert snapshot_dir(tmp_path, "acs", "2026-01-01") == tmp_path / "acs" / "2026-01-01"
    with pytest.raises(ZoneLayoutError):
        snapshot_dir(tmp_path, "acs", "..")
    with pytest.raises(ZoneLayoutError):
        snapshot_dir(tmp_path, "../acs", "2026-01-01")


def test_ensure_layout_creates_every_zone_once(tmp_path: Path) -> None:
    root = tmp_path / "data"
    zones = ensure_layout(root)
    assert list(zones) == list(ZONES)
    assert all(path.is_dir() for path in zones.values())
    assert ensure_layout(root) == zones  # idempotent
    settings = Settings.load(env={"PHILLYSIM_DATA_ROOT": str(root)})
    assert settings.zones() == zones


def test_resolution_still_creates_nothing(tmp_path: Path) -> None:
    root = tmp_path / "never"
    Settings.load(env={"PHILLYSIM_DATA_ROOT": str(root)}).zones()
    assert not root.exists()


def test_listing_skips_strays_and_sorts(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    for rel in ["acs/2026-01-02", "acs/2026-01-01-1", "acs/2026-01-01", "gtfs/2026-03-01"]:
        (raw / rel).mkdir(parents=True)
    (raw / "acs" / "scratch").mkdir()
    (raw / "acs" / "notes.txt").write_text("x")
    (raw / "README.md").write_text("x")
    (raw / "Bad-Source").mkdir()
    assert list_sources(raw) == ["acs", "gtfs"]
    assert [str(s) for s in list_snapshots(raw / "acs")] == [
        "2026-01-01",
        "2026-01-01-1",
        "2026-01-02",
    ]
    assert [p.as_posix() for p in stray_entries(raw)] == [
        "Bad-Source",
        "README.md",
        "acs/notes.txt",
        "acs/scratch",
    ]
    assert list_sources(tmp_path / "missing") == []
    assert stray_entries(tmp_path / "missing") == []


def test_next_snapshot_id_never_reuses_a_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw" / "acs"
    day = date(2026, 1, 1)
    assert str(next_snapshot_id(source_dir, day)) == "2026-01-01"
    (source_dir / "2026-01-01").mkdir(parents=True)
    assert str(next_snapshot_id(source_dir, day)) == "2026-01-01-1"
    (source_dir / "2026-01-01-1").mkdir()
    assert str(next_snapshot_id(source_dir, day)) == "2026-01-01-2"
    assert str(next_snapshot_id(source_dir, date(2026, 1, 2))) == "2026-01-02"
