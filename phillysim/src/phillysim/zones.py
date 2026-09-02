"""Zone layout and snapshot identifiers (roadmap/architecture.md "Zones & identifiers").

The data root holds four pipeline zones, ``raw`` -> ``intermediate`` -> ``curated``
-> ``public``, plus ``quarantine`` (snapshots that failed admission; never read
by a later stage) and ``cache`` (rebuildable scratch). Inside ``raw`` every
acquisition is an immutable snapshot directory::

    raw/<source>/<snapshot-id>/manifest.json + the acquired files

A source identifier is a lowercase slug (``snap_retailers``). A snapshot ID is
the acquisition date, ``YYYY-MM-DD``, with an optional ``-N`` sequence suffix
for a second acquisition of the same source on the same day. Both are validated
here, so a directory name can never smuggle a path component.

Resolution of the data root (``phillysim.config``) never creates directories;
:func:`ensure_layout` is the one function that does, and only when asked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from phillysim.config import ZONES

MANIFEST_FILE = "manifest.json"

SOURCE_PATTERN = r"[a-z][a-z0-9_]{0,63}"
SNAPSHOT_ID_PATTERN = r"(\d{4}-\d{2}-\d{2})(?:-(\d{1,3}))?"
_SOURCE_RE = re.compile(rf"^{SOURCE_PATTERN}$")
_SNAPSHOT_RE = re.compile(rf"^{SNAPSHOT_ID_PATTERN}$")


class ZoneLayoutError(ValueError):
    """A source name, snapshot ID, or path breaks the zone layout rules."""


def check_source(source: str) -> str:
    """Return ``source`` if it is a valid source identifier, else raise."""
    if not isinstance(source, str) or not _SOURCE_RE.match(source):
        raise ZoneLayoutError(
            f"invalid source identifier {source!r}: expected lowercase slug /{SOURCE_PATTERN}/"
        )
    return source


@dataclass(frozen=True, order=True)
class SnapshotId:
    """A parsed snapshot identifier: acquisition date plus optional same-day sequence."""

    acquired_on: date
    sequence: int = 0

    def __str__(self) -> str:
        base = self.acquired_on.isoformat()
        return base if self.sequence == 0 else f"{base}-{self.sequence}"

    @classmethod
    def parse(cls, text: str) -> SnapshotId:
        match = _SNAPSHOT_RE.match(text) if isinstance(text, str) else None
        if match is None:
            raise ZoneLayoutError(
                f"invalid snapshot id {text!r}: expected YYYY-MM-DD or YYYY-MM-DD-N"
            )
        try:
            acquired_on = date.fromisoformat(match.group(1))
        except ValueError as exc:
            raise ZoneLayoutError(f"invalid snapshot id {text!r}: {exc}") from exc
        sequence = int(match.group(2)) if match.group(2) else 0
        if match.group(2) is not None and (sequence == 0 or match.group(2) != str(sequence)):
            raise ZoneLayoutError(
                f"invalid snapshot id {text!r}: sequence suffix must be 1, 2, ... (no zero padding)"
            )
        return cls(acquired_on, sequence)


def check_snapshot_id(snapshot_id: str) -> str:
    """Return ``snapshot_id`` if it parses, else raise."""
    SnapshotId.parse(snapshot_id)
    return snapshot_id


def next_snapshot_id(source_dir: Path, acquired_on: date) -> SnapshotId:
    """The first unused snapshot ID for ``acquired_on`` under ``raw/<source>/``.

    ``YYYY-MM-DD`` if free, otherwise ``YYYY-MM-DD-1``, ``-2``, ... Existing
    snapshots are never overwritten (the raw zone is immutable).
    """
    taken = {s.sequence for s in list_snapshots(source_dir) if s.acquired_on == acquired_on}
    sequence = 0
    while sequence in taken:
        sequence += 1
    return SnapshotId(acquired_on, sequence)


def snapshot_dir(raw_zone: Path, source: str, snapshot_id: str | SnapshotId) -> Path:
    """``raw/<source>/<snapshot-id>``, with both components validated."""
    return raw_zone / check_source(source) / check_snapshot_id(str(snapshot_id))


def list_sources(raw_zone: Path) -> list[str]:
    """Source directories under the raw zone, sorted; names that are not slugs are skipped."""
    if not raw_zone.is_dir():
        return []
    return sorted(p.name for p in raw_zone.iterdir() if p.is_dir() and _SOURCE_RE.match(p.name))


def list_snapshots(source_dir: Path) -> list[SnapshotId]:
    """Snapshot directories under ``raw/<source>/``, oldest first; stray names are skipped."""
    if not source_dir.is_dir():
        return []
    found: list[SnapshotId] = []
    for entry in source_dir.iterdir():
        if entry.is_dir() and _SNAPSHOT_RE.match(entry.name):
            found.append(SnapshotId.parse(entry.name))
    return sorted(found)


def stray_entries(raw_zone: Path) -> list[Path]:
    """Entries in the raw zone that are not ``<source>/<snapshot-id>/`` directories.

    Paths are returned relative to ``raw_zone``. Used by ``verify`` to flag anything
    that has no manifest to vouch for it.
    """
    strays: list[Path] = []
    if not raw_zone.is_dir():
        return strays
    by_name = lambda p: p.name  # noqa: E731 - byte order, identical on every platform
    for entry in sorted(raw_zone.iterdir(), key=by_name):
        if not entry.is_dir() or not _SOURCE_RE.match(entry.name):
            strays.append(entry.relative_to(raw_zone))
            continue
        for child in sorted(entry.iterdir(), key=by_name):
            if not child.is_dir() or not _SNAPSHOT_RE.match(child.name):
                strays.append(child.relative_to(raw_zone))
    return strays


def ensure_layout(data_root: Path) -> dict[str, Path]:
    """Create the data root and every zone directory (idempotent). Returns the zone paths."""
    zones = {name: data_root / name for name in ZONES}
    for path in zones.values():
        path.mkdir(parents=True, exist_ok=True)
    return zones
