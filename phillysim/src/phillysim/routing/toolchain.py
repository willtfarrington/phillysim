"""The pinned routing toolchain: Temurin JDK 21 and the R5 jar, project-local (EP-13).

ADR-0008 names the exact JDK build and the exact jar; this module installs them
under the project directory (``<repo>/phillysim/.jdk/jdk-21.0.12.1+1/`` and
``<repo>/phillysim/.r5/r5-v7.5.1-r5py-all.jar``, both gitignored) and checks them:

* both files come through :func:`phillysim.download.fetch_file` (allowlist,
  https only, timeout and bounded backoff, capped streaming), so a redirect
  off the release-asset hosts or an oversize body is refused before a byte
  lands anywhere it could be used;
* the delivered bytes are compared against the recorded byte count and
  SHA-256 **before** anything is installed; a mismatch deletes the download
  and stops (:class:`ToolchainError`);
* the JDK archive is the one archive the project ever extracts: it goes
  through :func:`phillysim.guards.extract_zip` (Windows) or
  :func:`phillysim.guards.extract_tar` (Linux) under the zip-slip and bomb
  guards with the packet's limits, into a scratch directory first, and the
  JDK moves into place only after its own ``java -version`` reports the pinned
  version; the jar is a file, not an archive to the guards;
* nothing is put on ``PATH``, in the registry, or in the system: ``JAVA_HOME``
  is set in the routing child's environment per invocation
  (:mod:`phillysim.routing.harness`) and nowhere else;
* ``toolchain.json`` beside the two directories records what was installed and
  its digests, with paths relative to the project directory.

Everything the network delivers is injectable (the opener, the pins, the
``java -version`` probe), so the tests install a crafted archive and jar from
local bytes and exercise every refusal offline.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from phillysim.download import DownloadError, Fetch, Opener, digest_file, fetch_file, urllib_open
from phillysim.guards import GuardError, Limits, check_url_allowed, extract_tar, extract_zip
from phillysim.preflight import Check

MIB = 1024**2
GIB = 1024**3

#: ADR-0008: Eclipse Temurin 21.0.12.1+1, the JDK 21 LTS build on the decision date.
JDK_RELEASE = "jdk-21.0.12.1+1"
JDK_VERSION = "21.0.12.1"
JDK_DIR_NAME = JDK_RELEASE
JDK_RELEASE_URL = (
    "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/"
)
#: ADR-0008 as amended 2026-09-03 (EP-13): the r5py project's R5 7.5.1 build, the jar r5py
#: 1.1.7 pins in its own source, passed to r5py as its classpath always.
JAR_RELEASE = "v7.5.1-r5py"
JAR_NAME = "r5-v7.5.1-r5py-all.jar"
JAR_URL = f"https://github.com/r5py/r5/releases/download/{JAR_RELEASE}/{JAR_NAME}"
JAR_BYTES = 64_437_972
JAR_SHA256 = "d50be106cadd7b636cfc0e209052767d7df570629f79fdf98ecd5cf5d2d89be7"

#: GitHub's release pages and both release-asset hosts (EP-12 observed the second).
ALLOWLIST: tuple[str, ...] = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)
#: The JDK archive is extracted: file / extracted / ratio / members caps (the packet's).
JDK_LIMITS = Limits(
    max_file_bytes=256 * MIB,
    max_extracted_bytes=1 * GIB,
    max_compression_ratio=10.0,
    max_members=2_000,
)
#: The jar is a file to the guards (never opened as an archive): a size cap only.
JAR_MAX_BYTES = 128 * MIB

JDK_DIR = ".jdk"
JAR_DIR = ".r5"
RECORD_NAME = "toolchain.json"
RECORD_SCHEMA_VERSION = 1
#: The Python side of the toolchain (the ``routing`` dependency group; psutil is core).
PYTHON_PACKAGES: tuple[str, ...] = ("r5py", "jpype1", "psutil")


class ToolchainError(Exception):
    """The toolchain could not be installed or is not the pinned one."""


@dataclass(frozen=True)
class Archive:
    """One pinned download: name, URL, exact byte count, SHA-256, and archive kind."""

    file_name: str
    url: str
    bytes: int
    sha256: str
    kind: str  # "zip", "tar.gz", or "file"

    def fetch(self) -> Fetch:
        return Fetch(self.url, self.file_name, digest=f"sha256:{self.sha256}")


JDK_ARCHIVES: Mapping[str, Archive] = {
    "windows": Archive(
        "OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip",
        JDK_RELEASE_URL + "OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip",
        205_073_461,
        "f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e",
        "zip",
    ),
    "linux": Archive(
        "OpenJDK21U-jdk_x64_linux_hotspot_21.0.12.1_1.tar.gz",
        JDK_RELEASE_URL + "OpenJDK21U-jdk_x64_linux_hotspot_21.0.12.1_1.tar.gz",
        207_473_347,
        "ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94",
        "tar.gz",
    ),
}
JAR = Archive(JAR_NAME, JAR_URL, JAR_BYTES, JAR_SHA256, "file")


def platform_key(platform: str = sys.platform) -> str:
    """``"windows"`` or ``"linux"``; anything else is unsupported (ADR-0001)."""
    if platform == "win32":
        return "windows"
    if platform.startswith("linux"):
        return "linux"
    raise ToolchainError(f"unsupported platform {platform!r}: Windows x64 or Linux x64 only")


def default_home() -> Path:
    """The uv project directory (``<repo>/phillysim/``), found from this module."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return here.parents[3]  # pragma: no cover - a source checkout always has pyproject.toml


@dataclass(frozen=True)
class Toolchain:
    """Where the toolchain lives for one project directory (``home``)."""

    home: Path
    platform: str = platform_key()

    @property
    def jdk_root(self) -> Path:
        return self.home / JDK_DIR

    @property
    def jdk_dir(self) -> Path:
        """``JAVA_HOME`` for the routing child."""
        return self.jdk_root / JDK_DIR_NAME

    @property
    def java(self) -> Path:
        name = "java.exe" if self.platform == "windows" else "java"
        return self.jdk_dir / "bin" / name

    @property
    def jar(self) -> Path:
        return self.home / JAR_DIR / JAR_NAME

    @property
    def record_path(self) -> Path:
        return self.home / RECORD_NAME

    @property
    def jdk_archive(self) -> Archive:
        return JDK_ARCHIVES[self.platform]

    def relative(self, path: Path) -> str:
        """``path`` relative to ``home`` in POSIX form (what the record stores)."""
        return path.relative_to(self.home).as_posix()

    @classmethod
    def default(cls) -> Toolchain:
        return cls(default_home())


# --- probes --------------------------------------------------------------------------------


def java_version_string(java: Path) -> str:
    """``java -version``'s output (it goes to stderr), without a ``JAVA_HOME`` or ``PATH``."""
    try:
        completed = subprocess.run(
            [str(java), "-version"], capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolchainError(f"{java}: cannot run `java -version`: {exc}") from exc
    if completed.returncode != 0:
        raise ToolchainError(
            f"{java}: `java -version` exited {completed.returncode}: {completed.stderr.strip()}"
        )
    return (completed.stderr + completed.stdout).strip()


JavaVersionProbe = Callable[[Path], str]


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


# --- install -------------------------------------------------------------------------------


def _verify_download(path: Path, archive: Archive, pins: Mapping[str, Archive] | None) -> str:
    """The delivered file's byte count and SHA-256 against the pin; a mismatch deletes it."""
    pinned = (pins or {}).get(archive.file_name, archive)
    size = path.stat().st_size
    actual = digest_file(path, "sha256")
    if size != pinned.bytes or actual != pinned.sha256:
        path.unlink(missing_ok=True)
        raise ToolchainError(
            f"{archive.file_name}: delivered {size} bytes, sha256 {actual}; the pin is "
            f"{pinned.bytes} bytes, sha256 {pinned.sha256} (ADR-0008); the download was deleted "
            "and nothing was installed (stop and surface to the owner)"
        )
    return actual


def _download(
    archive: Archive,
    dest: Path,
    *,
    max_bytes: int,
    opener: Opener,
    pins: Mapping[str, Archive] | None,
) -> tuple[str, float, int]:
    """Fetch through the guarded path and verify; return (sha256, seconds, bytes)."""
    check_url_allowed(archive.url, ALLOWLIST)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    try:
        result = fetch_file(
            archive.fetch() if pins is None else Fetch(archive.url, archive.file_name),
            dest,
            allowlist=ALLOWLIST,
            max_bytes=max_bytes,
            opener=opener,
        )
    except (DownloadError, GuardError) as exc:
        raise ToolchainError(f"{archive.file_name}: {exc}") from exc
    sha256 = _verify_download(dest, archive, pins)
    return sha256, result.seconds, result.bytes


def _find_jdk_root(extracted: Path, platform: str) -> Path:
    """The one directory in the extracted tree holding ``bin/java``."""
    java = "java.exe" if platform == "windows" else "java"
    candidates = sorted(p.parent.parent for p in extracted.rglob(java) if p.parent.name == "bin")
    if len(candidates) != 1:
        raise ToolchainError(
            f"the JDK archive holds {len(candidates)} JDK root(s) (expected one); refusing"
        )
    return candidates[0]


def install_jdk(
    toolchain: Toolchain,
    *,
    opener: Opener | None = None,
    pins: Mapping[str, Archive] | None = None,
    java_version: JavaVersionProbe | None = None,
    echo: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Install the pinned JDK under ``home/.jdk/`` unless it is already there and answers
    with the pinned version. Returns the record entry."""
    say = echo or (lambda _line: None)
    opener = opener or urllib_open
    java_version = java_version or java_version_string
    archive = toolchain.jdk_archive
    if toolchain.java.exists():
        version = java_version(toolchain.java)
        if JDK_VERSION in version:
            where = toolchain.relative(toolchain.jdk_dir)
            say(f"jdk: already installed at {where} ({version.splitlines()[0]})")
            return _jdk_entry(toolchain, archive, version, downloaded=False)
        raise ToolchainError(
            f"{toolchain.relative(toolchain.jdk_dir)} exists but `java -version` does not report "
            f"{JDK_VERSION}: {version.splitlines()[0]!r}; delete it by hand to reinstall"
        )
    downloads = toolchain.jdk_root / ".download"
    scratch = toolchain.jdk_root / ".extract"
    say(f"jdk: GET {archive.url} ({archive.bytes} bytes)")
    try:
        sha256, seconds, size = _download(
            archive,
            downloads / archive.file_name,
            max_bytes=JDK_LIMITS.max_file_bytes,
            opener=opener,
            pins=pins,
        )
        say(f"jdk: {size} bytes in {seconds:.1f} s, sha256 {sha256} (verified against the pin)")
        shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir(parents=True)
        extractor = extract_zip if archive.kind == "zip" else extract_tar
        written = extractor(downloads / archive.file_name, scratch, JDK_LIMITS)
        say(f"jdk: extracted {len(written)} member(s) under the guards")
        root = _find_jdk_root(scratch, toolchain.platform)
        version = java_version(root / "bin" / toolchain.java.name)
        if JDK_VERSION not in version:
            raise ToolchainError(
                f"the extracted JDK reports {version.splitlines()[0]!r}, not {JDK_VERSION}; "
                "nothing was installed"
            )
        toolchain.jdk_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root), str(toolchain.jdk_dir))
    except GuardError as exc:
        raise ToolchainError(f"{archive.file_name}: {exc}") from exc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(downloads, ignore_errors=True)
    say(f"jdk: installed at {toolchain.relative(toolchain.jdk_dir)} ({version.splitlines()[0]})")
    entry = _jdk_entry(toolchain, archive, version, downloaded=True)
    entry["download_seconds"] = round(seconds, 3)
    return entry


def _jdk_entry(
    toolchain: Toolchain, archive: Archive, version: str, *, downloaded: bool
) -> dict[str, Any]:
    return {
        "release": JDK_RELEASE,
        "version": JDK_VERSION,
        "archive": archive.file_name,
        "url": archive.url,
        "bytes": archive.bytes,
        "sha256": archive.sha256,
        "dir": toolchain.relative(toolchain.jdk_dir),
        "java_version": version.splitlines()[0] if version else "",
        "downloaded": downloaded,
    }


def install_jar(
    toolchain: Toolchain,
    *,
    opener: Opener | None = None,
    pins: Mapping[str, Archive] | None = None,
    echo: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Install the pinned jar under ``home/.r5/`` unless it is already there with the pinned
    digest. Returns the record entry."""
    say = echo or (lambda _line: None)
    opener = opener or urllib_open
    pinned = (pins or {}).get(JAR.file_name, JAR)
    entry = {
        "release": JAR_RELEASE,
        "name": JAR_NAME,
        "url": JAR_URL,
        "bytes": JAR.bytes,
        "sha256": JAR.sha256,
        "path": toolchain.relative(toolchain.jar),
        "downloaded": False,
    }
    if toolchain.jar.exists():
        actual = digest_file(toolchain.jar, "sha256")
        if actual == pinned.sha256 and toolchain.jar.stat().st_size == pinned.bytes:
            say(f"jar: already installed at {entry['path']} (sha256 {actual})")
            return entry
        raise ToolchainError(
            f"{entry['path']} exists with sha256 {actual}, not the pinned {pinned.sha256}; "
            "delete it by hand to reinstall"
        )
    say(f"jar: GET {JAR.url} ({JAR.bytes} bytes)")
    sha256, seconds, size = _download(
        JAR, toolchain.jar, max_bytes=JAR_MAX_BYTES, opener=opener, pins=pins
    )
    say(f"jar: {size} bytes in {seconds:.1f} s, sha256 {sha256} (verified against the pin)")
    say(f"jar: installed at {entry['path']}")
    entry["downloaded"] = True
    entry["download_seconds"] = round(seconds, 3)
    return entry


def install(
    toolchain: Toolchain,
    *,
    opener: Opener | None = None,
    pins: Mapping[str, Archive] | None = None,
    java_version: JavaVersionProbe | None = None,
    echo: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Install both components and write ``toolchain.json``. Idempotent: an installed,
    verified component is kept and not downloaded again."""
    jdk = install_jdk(toolchain, opener=opener, pins=pins, java_version=java_version, echo=echo)
    jar = install_jar(toolchain, opener=opener, pins=pins, echo=echo)
    record = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "installed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platform": toolchain.platform,
        "jdk": jdk,
        "jar": jar,
        "python": {name: package_version(name) for name in PYTHON_PACKAGES},
    }
    toolchain.record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8")
    if echo:
        echo(f"toolchain: recorded in {RECORD_NAME}")
    return record


def read_record(toolchain: Toolchain) -> dict[str, Any] | None:
    if not toolchain.record_path.is_file():
        return None
    return json.loads(toolchain.record_path.read_text("utf-8"))


# --- check ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolchainReport:
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def lines(self) -> list[str]:
        out = [f"  {'ok  ' if c.ok else 'FAIL'} {c.name:<12} {c.detail}" for c in self.checks]
        verdict = "installed and pinned" if self.ok else "not usable"
        out.append(f"toolchain: {verdict}")
        return out


def check(
    toolchain: Toolchain,
    *,
    java_version: JavaVersionProbe | None = None,
    package_version: Callable[[str], str | None] | None = None,
) -> ToolchainReport:
    """Is the pinned toolchain installed here? The JDK's ``java -version`` must contain the
    pinned version, the jar's digest must equal the pin, the record must exist, and the
    routing group must be installed (versions reported, never imported)."""
    java_version = java_version or java_version_string
    package_version = package_version or globals()["package_version"]
    checks: list[Check] = []
    if not toolchain.java.exists():
        checks.append(
            Check(
                "jdk",
                False,
                f"missing: {toolchain.relative(toolchain.jdk_dir)} "
                "(run `phillysim toolchain install`)",
            )
        )
    else:
        try:
            version = java_version(toolchain.java)
            first = version.splitlines()[0] if version else ""
            checks.append(
                Check(
                    "jdk",
                    JDK_VERSION in version,
                    f"{toolchain.relative(toolchain.jdk_dir)}: {first}"
                    + ("" if JDK_VERSION in version else f" (need {JDK_VERSION})"),
                )
            )
        except ToolchainError as exc:
            checks.append(Check("jdk", False, str(exc)))
    if not toolchain.jar.exists():
        checks.append(Check("jar", False, f"missing: {toolchain.relative(toolchain.jar)}"))
    else:
        actual = digest_file(toolchain.jar, "sha256")
        checks.append(
            Check(
                "jar",
                actual == JAR_SHA256,
                f"{toolchain.relative(toolchain.jar)}: sha256 {actual}"
                + ("" if actual == JAR_SHA256 else f" (pinned {JAR_SHA256})"),
            )
        )
    record = read_record(toolchain)
    if record is None:
        checks.append(Check("record", False, f"{RECORD_NAME} missing"))
    else:
        consistent = (
            record.get("jdk", {}).get("sha256") == toolchain.jdk_archive.sha256
            and record.get("jar", {}).get("sha256") == JAR_SHA256
        )
        checks.append(
            Check(
                "record",
                consistent,
                f"{RECORD_NAME}: installed {record.get('installed_at')} on {record.get('platform')}"
                + ("" if consistent else "; digests differ from ADR-0008"),
            )
        )
    versions = {name: package_version(name) for name in PYTHON_PACKAGES}
    missing = sorted(name for name, v in versions.items() if v is None)
    present = ", ".join(f"{name} {v}" for name, v in versions.items() if v)
    checks.append(
        Check(
            "routing",
            not missing,
            f"missing: {', '.join(missing)} (run `uv sync --locked --group routing`)"
            if missing
            else present,
        )
    )
    return ToolchainReport(tuple(checks))
