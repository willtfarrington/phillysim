"""Quarantine: where a snapshot goes when it fails admission (default-deny).

A staged snapshot enters the raw zone only through :func:`admit`, which runs
the download guards and then verifies the directory against its manifest. On
any failure the whole snapshot directory is moved to
``quarantine/<source>/<snapshot-id>[-N]/`` and a reason file is written beside
it (``<snapshot-id>[-N].reason.json``: what failed, which guard, when). Nothing
in the quarantine zone is ever read by a later stage; the reason file holds no
absolute paths or machine identifiers.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from phillysim.guards import DEFAULT_LIMITS, GuardError, Limits, screen_snapshot
from phillysim.manifest import (
    Manifest,
    ManifestError,
    canonical_bytes,
    read_manifest,
    verify_snapshot,
)

REASON_SUFFIX = ".reason.json"


class QuarantinedError(Exception):
    """Raised by :func:`admit` after the offending snapshot has been moved to quarantine."""

    def __init__(self, record: QuarantineRecord) -> None:
        self.record = record
        super().__init__(
            f"{record.source}/{record.snapshot_id} quarantined ({record.kind}): {record.reason}"
        )


@dataclass(frozen=True)
class QuarantineRecord:
    """What the reason file says. ``kind`` is a guard name, ``manifest``, or ``verify``."""

    source: str
    snapshot_id: str
    kind: str
    reason: str
    quarantined_at: str
    quarantined_as: str  # directory name inside quarantine/<source>/

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "snapshot_id": self.snapshot_id,
            "kind": self.kind,
            "reason": self.reason,
            "quarantined_at": self.quarantined_at,
            "quarantined_as": self.quarantined_as,
        }


def _free_name(parent: Path, name: str) -> str:
    candidate, n = name, 1
    while (parent / candidate).exists() or (parent / (candidate + REASON_SUFFIX)).exists():
        n += 1
        candidate = f"{name}-q{n}"
    return candidate


def quarantine(
    snapshot_dir: Path, quarantine_zone: Path, *, kind: str, reason: str
) -> QuarantineRecord:
    """Move ``snapshot_dir`` whole into the quarantine zone and write its reason file."""
    source, snapshot_id = snapshot_dir.parent.name, snapshot_dir.name
    target_parent = quarantine_zone / source
    target_parent.mkdir(parents=True, exist_ok=True)
    name = _free_name(target_parent, snapshot_id)
    shutil.move(str(snapshot_dir), str(target_parent / name))
    record = QuarantineRecord(
        source=source,
        snapshot_id=snapshot_id,
        kind=kind,
        reason=reason,
        quarantined_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        quarantined_as=name,
    )
    (target_parent / (name + REASON_SUFFIX)).write_bytes(canonical_bytes(record.to_dict()))
    return record


def list_quarantined(quarantine_zone: Path) -> list[QuarantineRecord]:
    """Every reason file under the quarantine zone, oldest name first."""
    records: list[QuarantineRecord] = []
    if not quarantine_zone.is_dir():
        return records
    for path in sorted(quarantine_zone.glob(f"*/*{REASON_SUFFIX}")):
        payload = json.loads(path.read_text("utf-8"))
        records.append(QuarantineRecord(**payload))
    return records


def admit(
    snapshot_dir: Path,
    quarantine_zone: Path,
    *,
    allowlist: Iterable[str],
    limits: Limits = DEFAULT_LIMITS,
) -> Manifest:
    """Guard-check and verify a staged snapshot; quarantine it on any failure.

    Order: manifest must parse (so the URLs to check are known) -> guards
    (allowlist on the recorded URLs, size, zip-slip, bomb) -> checksum
    verification. Returns the manifest on success; raises :class:`QuarantinedError`
    after moving the directory otherwise.
    """
    try:
        manifest = read_manifest(snapshot_dir)
        urls = [manifest.acquisition_url]
        if manifest.acquisition_url_alt:
            urls.append(manifest.acquisition_url_alt)
        screen_snapshot(snapshot_dir, allowlist=allowlist, urls=urls, limits=limits)
    except ManifestError as exc:
        record = quarantine(snapshot_dir, quarantine_zone, kind="manifest", reason=str(exc))
        raise QuarantinedError(record) from exc
    except GuardError as exc:
        record = quarantine(snapshot_dir, quarantine_zone, kind=exc.guard, reason=exc.detail)
        raise QuarantinedError(record) from exc
    report = verify_snapshot(snapshot_dir)
    if not report.ok:
        reason = "; ".join(str(problem) for problem in report.problems)
        raise QuarantinedError(
            quarantine(snapshot_dir, quarantine_zone, kind="verify", reason=reason)
        )
    return manifest
