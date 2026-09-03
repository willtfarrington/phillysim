"""Preflight checks before a run: free disk, physical RAM, dependency versions, a writable root.

architecture.md's resource budgets fix the real-run thresholds: at least 150 GB
of free disk under the data root, and a routine peak RAM of 24 GB. The fixture
path is a different scale and uses fixture-scale thresholds, and the report
says which set was applied. Every check is evaluated and reported in one pass;
``ok`` is false if any failed. The probes (how free disk, RAM, and package
versions are measured) are injectable so the negative tests can simulate a
failing machine without depending on the machine they run on.

No third-party dependency: RAM is read through ``GlobalMemoryStatusEx`` on
Windows, ``/proc/meminfo`` on Linux, and ``os.sysconf`` elsewhere.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path

GB = 10**9
GIB = 2**30

#: The locked stack (ADR-0001 / ADR-0002); pyosmium joined at EP-12 (the network clip),
#: r5py joins at EP-13 in the optional ``routing`` group.
LOCKED_PACKAGES: tuple[str, ...] = (
    "geopandas",
    "pyogrio",
    "shapely",
    "pyproj",
    "duckdb",
    "pyarrow",
    "osmium",
)
MIN_PYTHON: tuple[int, int] = (3, 12)


@dataclass(frozen=True)
class Thresholds:
    """Minimum free disk and physical RAM in bytes, plus a label the report prints."""

    min_free_disk: int
    min_ram: int
    label: str


REAL_RUN = Thresholds(
    min_free_disk=150 * GB,
    min_ram=24 * GIB,
    label="real run (architecture.md resource budgets: >=150 GB free disk, 24 GB RAM)",
)
FIXTURE_SCALE = Thresholds(
    min_free_disk=1 * GIB,
    min_ram=1 * GIB,
    label="fixture scale (>=1 GiB free disk, 1 GiB RAM; not the real-run budget)",
)


# --- probes ------------------------------------------------------------------------------


def nearest_existing(path: Path) -> Path:
    """``path`` or its nearest existing ancestor (the data root may not exist yet)."""
    candidate = path.resolve()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return candidate


def free_disk_bytes(path: Path) -> int | None:
    try:
        return shutil.disk_usage(nearest_existing(path)).free
    except OSError:
        return None


def total_ram_bytes() -> int | None:
    if sys.platform == "win32":
        return _total_ram_windows()
    try:
        with open("/proc/meminfo", encoding="ascii") as handle:  # Linux
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return None


def _total_ram_windows() -> int | None:  # pragma: no cover - exercised on Windows only
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    try:
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
            return int(status.ullTotalPhys)
    except (AttributeError, OSError):
        pass
    return None


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def root_writable(path: Path) -> bool:
    return os.access(nearest_existing(path), os.W_OK)


@dataclass(frozen=True)
class Probes:
    """How the checks measure the machine; replace members to simulate a different one."""

    free_disk: Callable[[Path], int | None] = free_disk_bytes
    total_ram: Callable[[], int | None] = total_ram_bytes
    package_version: Callable[[str], str | None] = package_version
    python_version: tuple[int, int, int] = field(default_factory=lambda: sys.version_info[:3])
    writable: Callable[[Path], bool] = root_writable


DEFAULT_PROBES = Probes()


# --- the report ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PreflightReport:
    thresholds: Thresholds
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def failed(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if not check.ok)

    def lines(self) -> list[str]:
        out = [f"preflight thresholds: {self.thresholds.label}"]
        out.extend(
            f"  {'ok  ' if check.ok else 'FAIL'} {check.name:<12} {check.detail}"
            for check in self.checks
        )
        verdict = "all checks passed" if self.ok else f"{len(self.failed)} check(s) failed"
        out.append(f"preflight: {verdict}")
        return out


def _fmt_bytes(value: int) -> str:
    return f"{value / GB:.1f} GB"


def run_preflight(
    root: Path, thresholds: Thresholds, probes: Probes = DEFAULT_PROBES
) -> PreflightReport:
    """Evaluate every check against ``thresholds`` and report all of them in one pass."""
    checks: list[Check] = []

    free = probes.free_disk(root)
    if free is None:
        checks.append(
            Check("disk", False, "could not determine free disk space under the data root")
        )
    else:
        checks.append(
            Check(
                "disk",
                free >= thresholds.min_free_disk,
                f"{_fmt_bytes(free)} free under the data root "
                f"(need >= {_fmt_bytes(thresholds.min_free_disk)})",
            )
        )

    ram = probes.total_ram()
    if ram is None:
        checks.append(Check("ram", False, "could not determine physical RAM"))
    else:
        checks.append(
            Check(
                "ram",
                ram >= thresholds.min_ram,
                f"{_fmt_bytes(ram)} physical RAM (need >= {_fmt_bytes(thresholds.min_ram)})",
            )
        )

    major, minor, micro = probes.python_version
    checks.append(
        Check(
            "python",
            (major, minor) >= MIN_PYTHON,
            f"{major}.{minor}.{micro} (need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
        )
    )

    versions = {name: probes.package_version(name) for name in LOCKED_PACKAGES}
    missing = sorted(name for name, version in versions.items() if version is None)
    present = ", ".join(f"{name} {version}" for name, version in versions.items() if version)
    checks.append(
        Check(
            "packages",
            not missing,
            f"missing: {', '.join(missing)}" if missing else present,
        )
    )

    checks.append(
        Check(
            "root",
            probes.writable(root),
            "data root (or its nearest existing ancestor) is writable"
            if probes.writable(root)
            else "data root (or its nearest existing ancestor) is not writable",
        )
    )
    return PreflightReport(thresholds, tuple(checks))
