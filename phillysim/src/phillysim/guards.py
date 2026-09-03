"""Download and extraction guards (roadmap/architecture.md "Security").

Four untrusted-input controls, each testable offline on local file objects:

* **allowlist** - the acquisition URL's host must be on the caller's domain
  allowlist (exact host or a subdomain of a listed domain), over ``https``,
  with no embedded credentials, and never an IP literal;
* **size** - a byte cap on any single downloaded file, applied before a copy
  begins (declared size) and while it streams (actual bytes);
* **zip-slip** - every archive member must land inside the extraction root
  once its name is normalized (no absolute paths, drive letters, ``..``
  segments, or symlink members);
* **bomb** - declared uncompressed size, compression ratio, and member count
  ceilings before extraction, and an actual-bytes cap during it, so a header
  that lies is caught too.

This module knows nothing about sources or adapters: the allowlist and limits
are always passed in. A failed guard raises :class:`GuardError`; turning that
into a quarantined snapshot is :mod:`phillysim.quarantine`'s job.
"""

from __future__ import annotations

import gzip
import ipaddress
import os
import shutil
import stat
import tarfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO
from urllib.parse import urlsplit

GUARDS: tuple[str, ...] = ("allowlist", "size", "zip_slip", "bomb")

_CHUNK = 1 << 20


class GuardError(Exception):
    """A guard refused an input. ``guard`` names which one (see :data:`GUARDS`)."""

    def __init__(self, guard: str, detail: str) -> None:
        if guard not in GUARDS:
            raise ValueError(f"unknown guard {guard!r}")
        self.guard = guard
        self.detail = detail
        super().__init__(f"[{guard}] {detail}")


@dataclass(frozen=True)
class Limits:
    """Byte and ratio ceilings. Defaults fit the largest v1 source (a regional OSM extract)."""

    max_file_bytes: int = 4 * 1024**3  # one downloaded file
    max_extracted_bytes: int = 16 * 1024**3  # total uncompressed output of one archive
    max_compression_ratio: float = 200.0  # uncompressed / compressed, per archive
    max_members: int = 10_000  # archive entries

    def __post_init__(self) -> None:
        if min(self.max_file_bytes, self.max_extracted_bytes, self.max_members) <= 0:
            raise ValueError("limits must be positive")
        if self.max_compression_ratio <= 1:
            raise ValueError("max_compression_ratio must exceed 1")


DEFAULT_LIMITS = Limits()


# --- allowlist ---------------------------------------------------------------------------


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower().rstrip(".")
    if not domain or any(ch in domain for ch in "/:@ ") or domain.startswith("."):
        raise ValueError(f"invalid allowlist domain {domain!r}")
    return domain


def check_url_allowed(url: str, allowlist: Iterable[str]) -> str:
    """Return ``url`` if its host is allowed, else raise ``GuardError('allowlist')``."""
    domains = {normalize_domain(d) for d in allowlist}
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise GuardError("allowlist", f"{url!r}: only https is allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise GuardError("allowlist", f"{url!r}: no host")
    if parts.username is not None or parts.password is not None:
        raise GuardError("allowlist", f"{url!r}: credentials in URL are not allowed")
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        raise GuardError("allowlist", f"{url!r}: IP-literal hosts are not allowed")
    if host not in domains and not any(host.endswith("." + d) for d in domains):
        raise GuardError("allowlist", f"{url!r}: host {host!r} is not on the allowlist")
    return url


# --- size --------------------------------------------------------------------------------


def check_file_size(path: Path, limits: Limits = DEFAULT_LIMITS) -> int:
    """Return the file size if within ``max_file_bytes``; else raise ``GuardError("size")``."""
    size = path.stat().st_size
    if size > limits.max_file_bytes:
        raise GuardError(
            "size", f"{path.name}: {size} bytes exceeds the cap of {limits.max_file_bytes}"
        )
    return size


def copy_capped(src: IO[bytes], dst: IO[bytes], max_bytes: int, *, label: str = "stream") -> int:
    """Stream ``src`` into ``dst``, aborting as soon as more than ``max_bytes`` arrive.

    Returns the byte count. The cap is enforced on bytes actually read, so a
    Content-Length or archive header that understates the size cannot bypass it.
    """
    total = 0
    while chunk := src.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise GuardError("size", f"{label}: exceeded {max_bytes} bytes while streaming")
        dst.write(chunk)
    return total


# --- zip-slip ----------------------------------------------------------------------------


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK(info.external_attr >> 16)


def safe_member_path(root: Path, member_name: str) -> Path:
    """Resolve an archive member name to a path strictly inside ``root``, or raise."""
    name = member_name.replace("\\", "/")
    if not name or name.endswith("/"):
        raise GuardError("zip_slip", f"member {member_name!r}: empty or directory-only name")
    posix = PurePosixPath(name)
    if posix.is_absolute() or name[:1] in "/\\" or (len(name) > 1 and name[1] == ":"):
        raise GuardError("zip_slip", f"member {member_name!r}: absolute path")
    parts = posix.parts
    if any(part in {"..", "."} or part.endswith(":") for part in parts):
        raise GuardError("zip_slip", f"member {member_name!r}: escapes the extraction root")
    target = (root / Path(*parts)).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise GuardError("zip_slip", f"member {member_name!r}: resolves outside the root")
    return target


# --- bomb --------------------------------------------------------------------------------


def _inspect_members(
    members: list[zipfile.ZipInfo], *, name: str, compressed: int, limits: Limits
) -> list[zipfile.ZipInfo]:
    """The zip-slip and bomb rules over a central directory already read."""
    if len(members) > limits.max_members:
        raise GuardError("bomb", f"{name}: {len(members)} members exceeds {limits.max_members}")
    declared = sum(m.file_size for m in members)
    if declared > limits.max_extracted_bytes:
        raise GuardError(
            "bomb",
            f"{name}: declared {declared} uncompressed bytes exceeds {limits.max_extracted_bytes}",
        )
    ratio = declared / max(compressed, 1)
    if ratio > limits.max_compression_ratio:
        raise GuardError(
            "bomb",
            f"{name}: compression ratio {ratio:.0f}:1 exceeds {limits.max_compression_ratio:.0f}:1",
        )
    for member in members:
        if _is_symlink(member):
            raise GuardError("zip_slip", f"member {member.filename!r}: symlink members refused")
    return members


def inspect_zip(archive: Path, limits: Limits = DEFAULT_LIMITS) -> list[zipfile.ZipInfo]:
    """Read the central directory and apply the zip-slip and bomb rules; extract nothing."""
    if not zipfile.is_zipfile(archive):
        raise GuardError("bomb", f"{archive.name}: not a zip archive")
    with zipfile.ZipFile(archive) as zf:
        members = [m for m in zf.infolist() if not m.is_dir()]
    return _inspect_members(
        members, name=archive.name, compressed=archive.stat().st_size, limits=limits
    )


def inspect_nested_zip(
    outer: zipfile.ZipFile, member: str, limits: Limits = DEFAULT_LIMITS
) -> list[zipfile.ZipInfo]:
    """Apply the same rules to a zip archive that is itself a member of ``outer``, read in
    place through the outer archive (nothing is written to disk); the member's stored size
    is the compressed size the ratio is measured against (EP-12: SEPTA's outer feed zip
    holds one zip per feed)."""
    info = outer.getinfo(member)
    with outer.open(info) as handle:
        if not handle.seekable():
            raise GuardError("bomb", f"{member}: nested archive is not seekable")
        try:
            inner = zipfile.ZipFile(handle)
        except zipfile.BadZipFile as exc:
            raise GuardError("bomb", f"{member}: not a zip archive ({exc})") from exc
        with inner:
            members = [m for m in inner.infolist() if not m.is_dir()]
    return _inspect_members(members, name=member, compressed=info.file_size, limits=limits)


def extract_zip(archive: Path, root: Path, limits: Limits = DEFAULT_LIMITS) -> list[Path]:
    """Extract ``archive`` under ``root`` with every guard applied. Returns the written paths.

    The central directory is checked first (:func:`inspect_zip`); every member
    path is normalized against ``root``; bytes are counted as they are written,
    so a member that inflates past its declared size is stopped at the cap.
    """
    check_file_size(archive, limits)
    members = inspect_zip(archive, limits)
    targets = {m.filename: safe_member_path(root, m.filename) for m in members}
    written: list[Path] = []
    budget = limits.max_extracted_bytes
    with zipfile.ZipFile(archive) as zf:
        for member in members:
            target = targets[member.filename]
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as dst:
                budget -= copy_capped(src, dst, budget, label=f"{archive.name}:{member.filename}")
            written.append(target)
    return written


def safe_link_target(root: Path, member_name: str, link_name: str) -> Path:
    """Resolve a symlink member's target strictly inside ``root``, or raise ``zip_slip``.

    The link is relative to the member's own directory (a JDK tarball's
    ``lib/server/libjsig.so -> ../libjsig.so``); an absolute target or one that
    climbs out of the root is refused.
    """
    if (
        not link_name
        or link_name.startswith(("/", "\\"))
        or (len(link_name) > 1 and link_name[1] == ":")
    ):
        raise GuardError(
            "zip_slip", f"member {member_name!r}: absolute symlink target {link_name!r}"
        )
    member = safe_member_path(root, member_name)
    target = (member.parent / Path(*PurePosixPath(link_name.replace("\\", "/")).parts)).resolve()
    root_resolved = root.resolve()
    if target == root_resolved or root_resolved not in target.parents:
        raise GuardError(
            "zip_slip", f"member {member_name!r}: symlink target {link_name!r} escapes the root"
        )
    return target


def inspect_tar(archive: Path, limits: Limits = DEFAULT_LIMITS) -> list[tarfile.TarInfo]:
    """Read a (gzip-compressed) tar's member list and apply the zip-slip and bomb rules;
    extract nothing. Only regular files, directories, and in-root relative symlinks are
    allowed (no hard links, devices, or FIFOs)."""
    check_file_size(archive, limits)
    if not tarfile.is_tarfile(archive):
        raise GuardError("bomb", f"{archive.name}: not a tar archive")
    with tarfile.open(archive, "r:*") as tf:
        members = tf.getmembers()
    if len(members) > limits.max_members:
        raise GuardError(
            "bomb", f"{archive.name}: {len(members)} members exceeds {limits.max_members}"
        )
    declared = sum(m.size for m in members if m.isfile())
    if declared > limits.max_extracted_bytes:
        raise GuardError(
            "bomb",
            f"{archive.name}: declared {declared} uncompressed bytes exceeds "
            f"{limits.max_extracted_bytes}",
        )
    ratio = declared / max(archive.stat().st_size, 1)
    if ratio > limits.max_compression_ratio:
        raise GuardError(
            "bomb",
            f"{archive.name}: compression ratio {ratio:.0f}:1 exceeds "
            f"{limits.max_compression_ratio:.0f}:1",
        )
    for member in members:
        if not (member.isfile() or member.isdir() or member.issym()):
            raise GuardError(
                "zip_slip", f"member {member.name!r}: only files, directories, and symlinks"
            )
    return members


def extract_tar(archive: Path, root: Path, limits: Limits = DEFAULT_LIMITS) -> list[Path]:
    """Extract a tar (optionally gzip-compressed) under ``root`` with every guard applied.

    Members are checked first (:func:`inspect_tar`); every path is normalized against
    ``root``; a symlink must point inside the root and is created last (copied where
    the platform refuses symlinks); bytes are counted as they are written. Returns the
    written paths (files and links).
    """
    members = inspect_tar(archive, limits)
    written: list[Path] = []
    links: list[tuple[Path, str, Path]] = []
    budget = limits.max_extracted_bytes
    with tarfile.open(archive, "r:*") as tf:
        for member in members:
            name = member.name.rstrip("/")
            if member.isdir():
                target = safe_member_path(root, name + "/x").parent
                target.mkdir(parents=True, exist_ok=True)
                continue
            target = safe_member_path(root, name)
            if member.issym():
                links.append(
                    (target, member.linkname, safe_link_target(root, name, member.linkname))
                )
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(member)
            if src is None:  # pragma: no cover - a regular member always yields a stream
                raise GuardError("bomb", f"member {member.name!r}: unreadable")
            with src, target.open("wb") as dst:
                budget -= copy_capped(src, dst, budget, label=f"{archive.name}:{member.name}")
            if member.mode & stat.S_IXUSR:
                target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            written.append(target)
    for link, link_name, resolved in links:
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Windows resolves a reparse point's relative target with backslashes only.
            os.symlink(link_name.replace("/", os.sep), link)
        except OSError:
            if resolved.is_file():
                shutil.copyfile(resolved, link)
            else:
                raise
        written.append(link)
    return written


def extract_gzip(archive: Path, target: Path, limits: Limits = DEFAULT_LIMITS) -> int:
    """Decompress a single-stream ``.gz`` file to ``target`` under the extracted-bytes cap."""
    check_file_size(archive, limits)
    with gzip.open(archive, "rb") as src, target.open("wb") as dst:
        try:
            return copy_capped(src, dst, limits.max_extracted_bytes, label=archive.name)
        except GuardError as exc:
            raise GuardError("bomb", exc.detail) from exc


# --- screening a staged snapshot ------------------------------------------------------


ARCHIVE_SUFFIXES: frozenset[str] = frozenset({".zip"})


def screen_snapshot(
    snapshot_dir: Path,
    *,
    allowlist: Iterable[str],
    urls: Iterable[str] = (),
    limits: Limits = DEFAULT_LIMITS,
) -> None:
    """Run every guard over a staged snapshot directory without extracting anything.

    ``urls`` are the acquisition URLs to check against ``allowlist`` (the caller
    passes what the manifest records). Every regular file is size-checked and
    every ``.zip`` is inspected for slip and bomb conditions.
    """
    for url in urls:
        check_url_allowed(url, allowlist)
    for entry in sorted(snapshot_dir.iterdir()):
        if entry.is_symlink():
            raise GuardError("zip_slip", f"{entry.name}: symlinks are not allowed in a snapshot")
        if not entry.is_file():
            continue
        check_file_size(entry, limits)
        if entry.suffix.lower() in ARCHIVE_SUFFIXES:
            inspect_zip(entry, limits)
