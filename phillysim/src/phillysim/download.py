"""The guarded outbound acquisition path (roadmap/architecture.md "Security"; EP-5a).

The order of checks is fixed and every step reuses an EP-4a primitive:

1. **allowlist before any connection** - every URL an acquisition may touch
   (primary, alternate, terms page, and every redirect target) must pass
   :func:`phillysim.guards.check_url_allowed`: https only, host on the
   adapter's allowlist, no credentials, no IP literals;
2. **timeout and bounded backoff** - one socket timeout per operation and at
   most :data:`DEFAULT_ATTEMPTS` tries per URL, sleeping 1 s, 2 s, 4 s, ...
   capped at :data:`MAX_BACKOFF_SECONDS`, on transient failures only; a
   definitive failure (a 404, say) moves straight on to the alternate URL;
3. **cap during streaming** - bytes go through :func:`phillysim.guards.copy_capped`
   under the adapter's :class:`~phillysim.guards.Limits`, so a header that
   lies about its length cannot bypass the cap;
4. **guards before extraction** - a downloaded ``.zip`` is inspected for slip
   and bomb conditions (:func:`phillysim.guards.inspect_zip`); nothing is
   ever extracted here; a file that is not an archive (the OSM PBF extract,
   EP-12) is never opened as one;
5. **pinned digests** - a file whose :class:`Fetch` pins a digest (the
   SHA-256 GitHub records for a release asset, the MD5 Geofabrik publishes
   beside an extract) is compared against it, and a provider checksum
   sidecar fetched through the same path (``md5_of``) is compared against
   the file it vouches for; a mismatch quarantines the snapshot (reason kind
   ``digest``: the provider's bytes are not the pinned ones, a stop);
6. **terms page archived beside the data** - the terms page in force is
   fetched through the same path, stored in the snapshot under the name the
   manifest's ``terms_archive`` records, and checked for the wording the
   adapter expects in its visible text (tags removed, whitespace folded);
   different wording is the packet's stop condition and quarantines the
   snapshot (reason kind ``terms``);
7. **manifest** - built by :func:`phillysim.manifest.build_manifest` from the
   files on disk;
8. **admission only through** :func:`phillysim.quarantine.admit`.

No default allowlist exists: every adapter declares its own domains. A
secret (a Census API key, if one is ever needed) never reaches a manifest;
the optional per-request query secret is attached at request time only.
The transport is injectable (``opener``), so the test suite drives every
branch on crafted local bytes and no test reaches the network.
"""

from __future__ import annotations

import hashlib
import html
import http.client
import logging
import os
import re
import shutil
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode

from phillysim import __version__
from phillysim.guards import (
    ARCHIVE_SUFFIXES,
    GuardError,
    Limits,
    check_url_allowed,
    copy_capped,
    inspect_zip,
)
from phillysim.manifest import SCHEMA_VERSION, Manifest, build_manifest, write_manifest
from phillysim.quarantine import QuarantinedError, admit, quarantine
from phillysim.zones import next_snapshot_id, snapshot_dir

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0  # seconds, per socket operation
DEFAULT_ATTEMPTS = 3  # per URL
BASE_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 8.0
TERMS_CAP_BYTES = 8 * 1024**2  # a terms page is a web page, not a dataset
USER_AGENT = f"phillysim/{__version__} (+https://github.com/willtfarrington/phillysim)"
TERMS_KIND = "terms"  # quarantine reason kind for the stop condition
DIGEST_KIND = "digest"  # quarantine reason kind for a pinned-digest or sidecar mismatch
DIGEST_ALGORITHMS: tuple[str, ...] = ("sha256", "md5")


class DownloadError(Exception):
    """Every URL for a file failed definitively or exhausted its bounded retries."""


class TermsError(Exception):
    """The archived terms page does not carry the wording the adapter expects."""


class DigestError(Exception):
    """A delivered file's digest is not the pinned one, or not the provider's sidecar's."""


# --- transport -----------------------------------------------------------------------------


class Response(Protocol):
    """What an opener returns: the subset of ``http.client.HTTPResponse`` the path uses."""

    status: int
    headers: Mapping[str, str]

    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


#: ``opener(url, allowlist, timeout) -> Response``. The default is :func:`urllib_open`;
#: tests pass a fake that serves local bytes.
Opener = Callable[[str, Iterable[str], float], Response]


class _AllowlistedRedirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects only onto the allowlist (https only, like every other URL)."""

    def __init__(self, allowlist: Iterable[str]) -> None:
        super().__init__()
        self.allowlist = tuple(allowlist)

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        check_url_allowed(newurl, self.allowlist)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urllib_open(url: str, allowlist: Iterable[str], timeout: float) -> Response:
    """Open ``url`` over https with the standard library, honouring the allowlist on redirects.

    The opener carries no ``http://``, ``file://``, or ``ftp://`` handler, so even a
    redirect to a plain-http URL cannot be followed.
    """
    allowlist = tuple(allowlist)
    check_url_allowed(url, allowlist)
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.HTTPSHandler(),
        _AllowlistedRedirects(allowlist),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPErrorProcessor(),
        urllib.request.UnknownHandler(),
    ):
        opener.add_handler(handler)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return opener.open(request, timeout=timeout)  # type: ignore[return-value]


def _retryable(exc: BaseException) -> bool:
    """Transient: a timeout, a dropped connection, a truncated body, a 429 or a 5xx."""
    if isinstance(exc, GuardError):
        return False
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or 500 <= exc.code < 600
    return isinstance(
        exc,
        (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            http.client.HTTPException,
            ConnectionError,
        ),
    )


def backoff_seconds(attempt: int) -> float:
    """Sleep after failed attempt ``attempt`` (1-based): 1, 2, 4, ... capped at the maximum."""
    return min(BASE_BACKOFF_SECONDS * 2 ** (attempt - 1), MAX_BACKOFF_SECONDS)


# --- one file ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Fetch:
    """One file to download: where from (with the dual-URL alternate) and what to call it.

    ``digest`` pins the delivered bytes as ``"<algorithm>:<hex>"`` (``sha256`` or
    ``md5``); ``md5_of`` marks this file as the provider's MD5 sidecar for another
    file of the same snapshot (Geofabrik's ``<hex>  <file name>`` line). Either
    mismatch is a stop (:class:`DigestError`, quarantine kind ``digest``).
    """

    url: str
    file_name: str
    url_alt: str | None = None
    digest: str | None = None
    md5_of: str | None = None

    def __post_init__(self) -> None:
        if self.digest is not None:
            parse_digest(self.digest)

    @property
    def urls(self) -> tuple[str, ...]:
        return (self.url,) if self.url_alt is None else (self.url, self.url_alt)


def parse_digest(pinned: str) -> tuple[str, str]:
    """``"sha256:<hex>"`` -> ``("sha256", "<hex>")``, validated."""
    algorithm, _, value = pinned.partition(":")
    value = value.strip().lower()
    if algorithm not in DIGEST_ALGORITHMS:
        raise ValueError(f"pinned digest {pinned!r}: algorithm must be one of {DIGEST_ALGORITHMS}")
    length = {"sha256": 64, "md5": 32}[algorithm]
    if len(value) != length or set(value) - set("0123456789abcdef"):
        raise ValueError(f"pinned digest {pinned!r}: expected {length} hex characters")
    return algorithm, value


def digest_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def read_md5_sidecar(path: Path, file_name: str) -> str:
    """The MD5 a provider's ``<hex>  <file name>`` sidecar states for ``file_name``."""
    for line in path.read_text("utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == file_name:
            value = parts[0].lower()
            if len(value) == 32 and not set(value) - set("0123456789abcdef"):
                return value
    raise DigestError(f"{path.name}: no MD5 line for {file_name!r} in the provider's sidecar")


def check_digests(snapshot_dir: Path, files: Iterable[Fetch]) -> dict[str, str]:
    """Compare every pinned digest and every MD5 sidecar; return ``{file: "<algo>:<hex>"}``
    for each check that passed, or raise :class:`DigestError` on the first mismatch."""
    checked: dict[str, str] = {}
    files = tuple(files)
    names = {f.file_name for f in files}
    for fetch in files:
        if fetch.digest is not None:
            algorithm, expected = parse_digest(fetch.digest)
            actual = digest_file(snapshot_dir / fetch.file_name, algorithm)
            if actual != expected:
                raise DigestError(
                    f"{fetch.file_name}: {algorithm} {actual} differs from the pinned {expected}; "
                    "the provider's bytes are not the pinned ones (stop and surface to the owner)"
                )
            checked[fetch.file_name] = f"{algorithm}:{actual}"
        if fetch.md5_of is not None:
            if fetch.md5_of not in names:
                raise DigestError(f"{fetch.file_name}: md5_of names {fetch.md5_of!r}, not a file")
            stated = read_md5_sidecar(snapshot_dir / fetch.file_name, fetch.md5_of)
            actual = digest_file(snapshot_dir / fetch.md5_of, "md5")
            if actual != stated:
                raise DigestError(
                    f"{fetch.md5_of}: md5 {actual} differs from the provider's sidecar "
                    f"{fetch.file_name} ({stated}); the delivered bytes are not the provider's"
                )
            checked[fetch.md5_of + " (sidecar)"] = f"md5:{actual}"
    return checked


@dataclass(frozen=True)
class FetchResult:
    """What one download did. ``url`` is the URL that actually delivered the bytes."""

    file_name: str
    url: str
    bytes: int
    attempts: int
    seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "url": self.url,
            "bytes": self.bytes,
            "attempts": self.attempts,
            "seconds": round(self.seconds, 3),
        }


def _stream(
    url: str,
    partial: Path,
    *,
    allowlist: tuple[str, ...],
    max_bytes: int,
    timeout: float,
    opener: Opener,
    label: str,
    query_secret: Mapping[str, str] | None,
) -> int:
    request_url = url
    if query_secret:
        request_url = url + ("&" if "?" in url else "?") + urlencode(dict(query_secret))
    response = opener(request_url, allowlist, timeout)
    try:
        status = getattr(response, "status", 200)
        if status != 200:
            raise DownloadError(f"{label}: HTTP {status} from {url}")
        declared = response.headers.get("Content-Length")
        if declared is not None and declared.strip().isdigit() and int(declared) > max_bytes:
            raise GuardError(
                "size", f"{label}: declared {declared} bytes exceeds the cap of {max_bytes}"
            )
        with partial.open("wb") as sink:
            return copy_capped(response, sink, max_bytes, label=label)
    finally:
        response.close()


def fetch_file(
    fetch: Fetch,
    dest: Path,
    *,
    allowlist: Iterable[str],
    max_bytes: int,
    timeout: float = DEFAULT_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    opener: Opener = urllib_open,
    sleep: Callable[[float], None] = time.sleep,
    query_secret: Mapping[str, str] | None = None,
) -> FetchResult:
    """Download ``fetch`` to ``dest`` through the guarded path. Never leaves a partial file.

    Every URL is checked against ``allowlist`` before the first connection. Each URL
    gets at most ``attempts`` tries on transient failures with bounded backoff; a
    definitive failure moves on to the alternate URL at once. A guard failure
    (declared or streamed size over ``max_bytes``) is raised immediately, without
    retry and without trying the alternate. ``query_secret`` (an API key, if a
    provider demands one) is appended at request time only and never recorded.
    """
    allowlist = tuple(allowlist)
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    for url in fetch.urls:
        check_url_allowed(url, allowlist)  # before any connection
    started = time.perf_counter()
    failures: list[str] = []
    total_attempts = 0
    partial = dest.with_name(dest.name + ".part")
    for url in fetch.urls:
        for attempt in range(1, attempts + 1):
            total_attempts += 1
            log.info("GET %s (attempt %d of %d)", url, attempt, attempts)
            try:
                size = _stream(
                    url,
                    partial,
                    allowlist=allowlist,
                    max_bytes=max_bytes,
                    timeout=timeout,
                    opener=opener,
                    label=fetch.file_name,
                    query_secret=query_secret,
                )
            except GuardError:
                partial.unlink(missing_ok=True)
                raise
            except Exception as exc:
                partial.unlink(missing_ok=True)
                failures.append(f"{url} attempt {attempt}: {type(exc).__name__}: {exc}")
                if not _retryable(exc):
                    log.warning("%s: definitive failure, trying the next URL if any", url)
                    break
                if attempt < attempts:
                    delay = backoff_seconds(attempt)
                    log.warning("%s: transient failure (%s); retrying in %.0f s", url, exc, delay)
                    sleep(delay)
                continue
            os.replace(partial, dest)
            seconds = time.perf_counter() - started
            log.info("ok  %s: %d bytes in %.1f s", fetch.file_name, size, seconds)
            return FetchResult(fetch.file_name, url, size, total_attempts, seconds)
    raise DownloadError(
        f"{fetch.file_name}: every URL failed after {total_attempts} attempt(s): "
        + "; ".join(failures)
    )


# --- one snapshot --------------------------------------------------------------------------


@dataclass(frozen=True)
class SnapshotSpec:
    """Everything an adapter declares about acquiring one source.

    ``acquisition_url`` is what the manifest records (the file itself for a
    single-file source, the provider's directory for a multi-file one);
    ``files`` are the downloads; ``terms`` is the terms page in force and
    ``terms_must_contain`` the wording it must carry; ``allowlist`` and
    ``limits`` are this source's, there is no default.
    """

    source: str
    acquisition_url: str
    files: tuple[Fetch, ...]
    terms: Fetch
    terms_must_contain: tuple[str, ...]
    allowlist: tuple[str, ...]
    limits: Limits
    license_bucket: str
    license_note: str
    acquisition_url_alt: str | None = None
    schema_version: int = SCHEMA_VERSION
    timeout: float = DEFAULT_TIMEOUT
    attempts: int = DEFAULT_ATTEMPTS

    def __post_init__(self) -> None:
        if not self.files:
            raise ValueError(f"{self.source}: a snapshot spec needs at least one file")
        names = [f.file_name for f in self.files] + [self.terms.file_name]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.source}: file names must be unique within the snapshot")
        if not self.allowlist:
            raise ValueError(f"{self.source}: an adapter must declare its allowlist")
        if not self.terms_must_contain:
            raise ValueError(f"{self.source}: an adapter must say what the terms page must say")


@dataclass(frozen=True)
class Acquisition:
    """The outcome of :func:`acquire_snapshot`: the admitted manifest plus what each fetch did."""

    manifest: Manifest
    fetches: tuple[FetchResult, ...]
    seconds: float
    reused: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.manifest.source,
            "snapshot_id": self.manifest.snapshot_id,
            "acquired_at": self.manifest.acquired_at,
            "acquisition_url": self.manifest.acquisition_url,
            "reused": self.reused,
            "fetches": [f.to_dict() for f in self.fetches],
            "bytes": sum(f.bytes for f in self.fetches),
            "seconds": round(self.seconds, 3),
            **self.extra,
        }


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_TAG_RE = re.compile(r"<[^>]*>")


def visible_text(page: str) -> str:
    """The page's text with tags removed, entities decoded, and whitespace folded, so a
    phrase spanning an inline element (``created by <a>OpenStreetMap Contributors</a>``)
    is checked the way a reader sees it."""
    return " ".join(html.unescape(_TAG_RE.sub(" ", page)).split())


def check_terms(path: Path, phrases: Iterable[str]) -> None:
    """Raise :class:`TermsError` unless the archived page's visible text carries every
    phrase."""
    text = visible_text(path.read_text("utf-8", errors="replace"))
    missing = [phrase for phrase in phrases if " ".join(phrase.split()) not in text]
    if missing:
        raise TermsError(
            f"{path.name}: the archived terms page does not contain the expected wording "
            f"{missing!r}; the terms in force may have changed (stop and surface to the owner)"
        )


def new_snapshot_dir(raw_zone: Path, source: str, acquired_on: date | None = None) -> Path:
    """``raw/<source>/<next free snapshot id>`` for today (or ``acquired_on``); creates nothing."""
    acquired_on = acquired_on or datetime.now(UTC).date()
    source_dir = raw_zone / source
    return snapshot_dir(raw_zone, source, next_snapshot_id(source_dir, acquired_on))


def acquire_snapshot(
    spec: SnapshotSpec,
    target: Path,
    *,
    quarantine_zone: Path,
    opener: Opener = urllib_open,
    sleep: Callable[[float], None] = time.sleep,
    query_secret: Mapping[str, str] | None = None,
) -> Acquisition:
    """Acquire one snapshot into ``target`` (``.../raw/<source>/<snapshot-id>``) and admit it.

    ``target`` must not exist (the raw zone is immutable; the caller chooses a fresh
    ID, see :func:`new_snapshot_dir`). On any guard or terms failure the staged
    directory is moved to ``quarantine_zone`` with a reason file and
    :class:`~phillysim.quarantine.QuarantinedError` is raised; on a transport
    failure the staged directory is removed and :class:`DownloadError` is raised.
    Returns the admitted manifest and per-file results.
    """
    if target.exists():
        raise FileExistsError(f"snapshot directory exists (the raw zone is immutable): {target}")
    if target.parent.name != spec.source:
        raise ValueError(f"{target} is not under a {spec.source!r} source directory")
    started = time.perf_counter()
    target.mkdir(parents=True)
    fetches: list[FetchResult] = []
    try:
        for fetch in spec.files:
            result = fetch_file(
                fetch,
                target / fetch.file_name,
                allowlist=spec.allowlist,
                max_bytes=spec.limits.max_file_bytes,
                timeout=spec.timeout,
                attempts=spec.attempts,
                opener=opener,
                sleep=sleep,
                query_secret=query_secret,
            )
            fetches.append(result)
            if Path(fetch.file_name).suffix.lower() in ARCHIVE_SUFFIXES:
                inspect_zip(target / fetch.file_name, spec.limits)  # guards before extraction
        digests_checked = check_digests(target, spec.files)
        fetches.append(
            fetch_file(
                spec.terms,
                target / spec.terms.file_name,
                allowlist=spec.allowlist,
                max_bytes=min(TERMS_CAP_BYTES, spec.limits.max_file_bytes),
                timeout=spec.timeout,
                attempts=spec.attempts,
                opener=opener,
                sleep=sleep,
            )
        )
        check_terms(target / spec.terms.file_name, spec.terms_must_contain)
    except GuardError as exc:
        record = quarantine(target, quarantine_zone, kind=exc.guard, reason=exc.detail)
        raise QuarantinedError(record) from exc
    except TermsError as exc:
        record = quarantine(target, quarantine_zone, kind=TERMS_KIND, reason=str(exc))
        raise QuarantinedError(record) from exc
    except DigestError as exc:
        record = quarantine(target, quarantine_zone, kind=DIGEST_KIND, reason=str(exc))
        raise QuarantinedError(record) from exc
    except DownloadError:
        shutil.rmtree(target, ignore_errors=True)
        raise
    acquisition_url, acquisition_url_alt = spec.acquisition_url, spec.acquisition_url_alt
    if len(spec.files) == 1:
        # A single-file source: the manifest records the file's own dual URLs, and the URL
        # that actually delivered the bytes goes first.
        only, delivered = spec.files[0], fetches[0].url
        if acquisition_url_alt is None:
            acquisition_url_alt = only.url_alt
        if delivered == only.url_alt:
            acquisition_url, acquisition_url_alt = only.url_alt, only.url
    manifest = build_manifest(
        target,
        source=spec.source,
        snapshot_id=target.name,
        acquired_at=_utc_now(),
        acquisition_url=acquisition_url,
        acquisition_url_alt=acquisition_url_alt,
        terms_archive=spec.terms.file_name,
        license_bucket=spec.license_bucket,
        license_note=spec.license_note,
        schema_version=spec.schema_version,
        synthetic=False,
    )
    write_manifest(target, manifest)
    admitted = admit(target, quarantine_zone, allowlist=spec.allowlist, limits=spec.limits)
    return Acquisition(
        admitted,
        tuple(fetches),
        time.perf_counter() - started,
        extra={"digests_checked": digests_checked} if digests_checked else {},
    )
