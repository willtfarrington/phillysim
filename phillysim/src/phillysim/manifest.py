"""Snapshot manifests: the one place the version-axis fields are recorded (ADR-0006).

Every raw snapshot directory carries a ``manifest.json`` in the shape
documented in ``docs/data-dictionary.md`` ("Snapshot manifest"): source and
snapshot ID, acquisition timestamp and URL (plus the dual-URL field for a
provider mid-migration), the archived terms file, the license bucket the
derived outputs fall into (ADR-0003), the data-dictionary schema version, a
synthetic flag, and a SHA-256 digest for every file in the snapshot.

The file is canonical JSON (two-space indent, sorted keys, UTF-8, trailing
newline) so that :func:`loads` followed by :meth:`Manifest.dumps` reproduces
the bytes exactly. :func:`verify_snapshot` checks a directory against its
manifest and names every file that is missing, altered, or unlisted; nothing
here knows how a snapshot was acquired.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from phillysim.contracts import LICENSE_BUCKETS
from phillysim.zones import (
    MANIFEST_FILE,
    ZoneLayoutError,
    check_snapshot_id,
    check_source,
    list_snapshots,
    list_sources,
    stray_entries,
)

SCHEMA_VERSION = 1

_HEX64 = frozenset("0123456789abcdef")
_CHUNK = 1 << 20


class ManifestError(ValueError):
    """The manifest is missing, malformed, or violates a field rule."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(payload: Any) -> bytes:
    """Serialize ``payload`` the way every manifest (and the fixture) is written."""
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


# --- field rules ---------------------------------------------------------------------


def _require_str(payload: dict[str, Any], key: str, *, nullable: bool = False) -> str | None:
    if key not in payload:
        raise ManifestError(f"missing field {key!r}")
    value = payload[key]
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"field {key!r} must be a non-empty string")
    return value


def check_file_name(name: str) -> str:
    """A manifest file entry is a bare file name inside the snapshot directory: no paths."""
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ManifestError(f"invalid file name {name!r}")
    if any(sep in name for sep in ("/", "\\", ":")) or name.startswith(("..", "~")):
        raise ManifestError(f"file name {name!r} must be a bare name, not a path")
    if name == MANIFEST_FILE:
        raise ManifestError(f"{MANIFEST_FILE} must not list itself")
    return name


def check_digest(name: str, digest: Any) -> str:
    if not isinstance(digest, str) or len(digest) != 64 or set(digest) - _HEX64:
        raise ManifestError(f"file {name!r}: digest must be 64 lowercase hex characters")
    return digest


def check_timestamp(value: str) -> str:
    """ISO-8601 with an explicit UTC offset (``Z`` or ``+00:00``); the text is kept verbatim."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ManifestError(f"acquired_at {value!r} is not ISO-8601: {exc}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds():
        raise ManifestError(f"acquired_at {value!r} must carry a UTC designator (Z or +00:00)")
    return value


def check_url(value: str, *, key: str = "acquisition_url") -> str:
    """An ``http(s)`` URL with a host and no credentials; never a local path."""
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"}:
        raise ManifestError(f"{key} {value!r} must use http or https")
    if not parts.hostname:
        raise ManifestError(f"{key} {value!r} has no host")
    if parts.username is not None or parts.password is not None:
        raise ManifestError(f"{key} must not carry credentials")
    return value


# --- the model -------------------------------------------------------------------------


@dataclass(frozen=True)
class Manifest:
    """One raw snapshot's manifest. Build with :meth:`from_dict` to get validation."""

    source: str
    snapshot_id: str
    acquired_at: str
    acquisition_url: str
    acquisition_url_alt: str | None
    terms_archive: str
    license_bucket: str
    license_note: str
    schema_version: int
    synthetic: bool
    files: dict[str, str] = field(default_factory=dict)

    def validate(self) -> Manifest:
        """Apply every field rule; raise :class:`ManifestError` on the first failure."""
        try:
            check_source(self.source)
            check_snapshot_id(self.snapshot_id)
        except ZoneLayoutError as exc:
            raise ManifestError(str(exc)) from exc
        check_timestamp(self.acquired_at)
        check_url(self.acquisition_url)
        if self.acquisition_url_alt is not None:
            check_url(self.acquisition_url_alt, key="acquisition_url_alt")
        if self.license_bucket not in LICENSE_BUCKETS:
            raise ManifestError(
                f"license_bucket {self.license_bucket!r} not in {sorted(LICENSE_BUCKETS)}"
            )
        if not isinstance(self.schema_version, int) or isinstance(self.schema_version, bool):
            raise ManifestError("schema_version must be an integer")
        if self.schema_version < 1:
            raise ManifestError("schema_version must be >= 1")
        if not isinstance(self.synthetic, bool):
            raise ManifestError("synthetic must be a boolean")
        if not isinstance(self.files, dict) or not self.files:
            raise ManifestError("files must be a non-empty {name: sha256} object")
        for name, digest in self.files.items():
            check_file_name(name)
            check_digest(name, digest)
        check_file_name(self.terms_archive)
        if self.terms_archive not in self.files:
            raise ManifestError(f"terms_archive {self.terms_archive!r} is not listed in files")
        return self

    @classmethod
    def from_dict(cls, payload: Any) -> Manifest:
        if not isinstance(payload, dict):
            raise ManifestError("manifest must be a JSON object")
        unknown = set(payload) - set(FIELD_NAMES)
        if unknown:
            raise ManifestError(f"unknown field(s) {sorted(unknown)}")
        for key in FIELD_NAMES:
            if key not in payload:
                raise ManifestError(f"missing field {key!r}")
        manifest = cls(
            source=_require_str(payload, "source"),  # type: ignore[arg-type]
            snapshot_id=_require_str(payload, "snapshot_id"),  # type: ignore[arg-type]
            acquired_at=_require_str(payload, "acquired_at"),  # type: ignore[arg-type]
            acquisition_url=_require_str(payload, "acquisition_url"),  # type: ignore[arg-type]
            acquisition_url_alt=_require_str(payload, "acquisition_url_alt", nullable=True),
            terms_archive=_require_str(payload, "terms_archive"),  # type: ignore[arg-type]
            license_bucket=_require_str(payload, "license_bucket"),  # type: ignore[arg-type]
            license_note=_require_str(payload, "license_note"),  # type: ignore[arg-type]
            schema_version=payload["schema_version"],
            synthetic=payload["synthetic"],
            files=payload["files"],
        )
        return manifest.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "snapshot_id": self.snapshot_id,
            "acquired_at": self.acquired_at,
            "acquisition_url": self.acquisition_url,
            "acquisition_url_alt": self.acquisition_url_alt,
            "terms_archive": self.terms_archive,
            "license_bucket": self.license_bucket,
            "license_note": self.license_note,
            "schema_version": self.schema_version,
            "synthetic": self.synthetic,
            "files": dict(sorted(self.files.items())),
        }

    def dumps(self) -> bytes:
        return canonical_bytes(self.to_dict())

    def with_files(self, files: dict[str, str]) -> Manifest:
        return Manifest(**{**self.to_dict(), "files": dict(files)})


#: The manifest's field names, in declaration order (the data-dictionary table order).
FIELD_NAMES: tuple[str, ...] = tuple(f.name for f in fields(Manifest))


def loads(data: bytes | str) -> Manifest:
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}") from exc
    return Manifest.from_dict(payload)


def read_manifest(snapshot_dir: Path) -> Manifest:
    path = snapshot_dir / MANIFEST_FILE
    if not path.is_file():
        raise ManifestError(f"no {MANIFEST_FILE} in snapshot directory {snapshot_dir.name!r}")
    return loads(path.read_bytes())


def write_manifest(snapshot_dir: Path, manifest: Manifest) -> Path:
    """Validate and write ``manifest.json`` into ``snapshot_dir`` (which must exist)."""
    manifest.validate()
    path = snapshot_dir / MANIFEST_FILE
    path.write_bytes(manifest.dumps())
    return path


def digest_directory(snapshot_dir: Path) -> dict[str, str]:
    """``{file name: sha256}`` for every regular file in the directory except the manifest."""
    out: dict[str, str] = {}
    for entry in sorted(snapshot_dir.iterdir()):
        if entry.name == MANIFEST_FILE:
            continue
        if not entry.is_file():
            raise ManifestError(f"snapshot contains a non-file entry {entry.name!r}")
        out[entry.name] = sha256_file(entry)
    return out


def build_manifest(snapshot_dir: Path, **fields_without_files: Any) -> Manifest:
    """Construct a manifest for the files already in ``snapshot_dir`` and validate it."""
    manifest = Manifest(files=digest_directory(snapshot_dir), **fields_without_files)
    return manifest.validate()


# --- verification --------------------------------------------------------------------


@dataclass(frozen=True)
class Problem:
    """One verification failure. ``kind`` is manifest / layout / missing / digest / extra."""

    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.detail}"


@dataclass(frozen=True)
class SnapshotReport:
    """Outcome of verifying one snapshot directory. Paths are relative to the raw zone."""

    source: str
    snapshot_id: str
    problems: tuple[Problem, ...]

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def label(self) -> str:
        return f"{self.source}/{self.snapshot_id}"


def verify_snapshot(snapshot_dir: Path) -> SnapshotReport:
    """Check that every file in ``snapshot_dir`` matches its manifest, and nothing else is there.

    The directory name must equal the manifest's ``snapshot_id`` and its parent's
    name the manifest's ``source``, so a relocated or renamed snapshot fails.
    """
    source, snapshot_id = snapshot_dir.parent.name, snapshot_dir.name
    problems: list[Problem] = []
    try:
        manifest = read_manifest(snapshot_dir)
    except ManifestError as exc:
        return SnapshotReport(source, snapshot_id, (Problem("manifest", str(exc)),))
    if manifest.source != source:
        problems.append(
            Problem("layout", f"directory {source!r} but manifest source {manifest.source!r}")
        )
    if manifest.snapshot_id != snapshot_id:
        problems.append(
            Problem(
                "layout",
                f"directory {snapshot_id!r} but manifest snapshot_id {manifest.snapshot_id!r}",
            )
        )
    present = {p.name for p in snapshot_dir.iterdir()} - {MANIFEST_FILE}
    for name, expected in sorted(manifest.files.items()):
        path = snapshot_dir / name
        if not path.is_file():
            problems.append(Problem("missing", f"{name} listed in manifest but absent"))
            continue
        actual = sha256_file(path)
        if actual != expected:
            problems.append(
                Problem("digest", f"{name}: sha256 {actual} does not match manifest {expected}")
            )
    for name in sorted(present - set(manifest.files)):
        problems.append(Problem("extra", f"{name} present but not listed in manifest"))
    return SnapshotReport(source, snapshot_id, tuple(problems))


@dataclass(frozen=True)
class ZoneReport:
    """Outcome of verifying a whole raw zone."""

    snapshots: tuple[SnapshotReport, ...]
    strays: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.strays and all(s.ok for s in self.snapshots)

    @property
    def failed(self) -> tuple[SnapshotReport, ...]:
        return tuple(s for s in self.snapshots if not s.ok)

    def lines(self) -> list[str]:
        out = []
        for report in self.snapshots:
            out.append(f"{'ok  ' if report.ok else 'FAIL'} {report.label}")
            out.extend(f"       {problem}" for problem in report.problems)
        out.extend(f"FAIL stray entry in raw zone: {stray}" for stray in self.strays)
        passed, total = len(self.snapshots) - len(self.failed), len(self.snapshots)
        strays = f", {len(self.strays)} stray entr(y/ies)" if self.strays else ""
        out.append(f"{passed} of {total} snapshot(s) verified{strays}")
        return out


def verify_raw_zone(raw_zone: Path) -> ZoneReport:
    """Verify every ``<source>/<snapshot-id>/`` under the raw zone and flag stray entries."""
    reports: list[SnapshotReport] = []
    for source in list_sources(raw_zone):
        for snapshot_id in list_snapshots(raw_zone / source):
            reports.append(verify_snapshot(raw_zone / source / str(snapshot_id)))
    strays = tuple(p.as_posix() for p in stray_entries(raw_zone))
    return ZoneReport(tuple(reports), strays)
