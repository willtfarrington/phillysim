"""Dependency policy (ADR-0001): the ``GDAL`` and ``fiona`` PyPI packages are banned.

Both are sdist-only on Windows; geo I/O goes through pyogrio. Three positive checks
cover the declared dependencies, the committed lockfile, and the active environment.
The parametrized negative checks feed the detector a lock / pyproject that *does*
contain a banned package and require it to fire, so the guard is proven on every run,
not once by hand.
"""

from __future__ import annotations

import re
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
BANNED: frozenset[str] = frozenset({"gdal", "fiona"})

_SPEC_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize(name: str) -> str:
    """PEP 503 name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def banned_in_lock(lock_text: str) -> set[str]:
    data = tomllib.loads(lock_text)
    return {p["name"] for p in data.get("package", []) if normalize(p["name"]) in BANNED}


def banned_in_pyproject(pyproject_text: str) -> set[str]:
    data = tomllib.loads(pyproject_text)
    project = data.get("project", {})
    specs: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    for group in data.get("dependency-groups", {}).values():
        specs.extend(s for s in group if isinstance(s, str))
    hits: set[str] = set()
    for spec in specs:
        match = _SPEC_NAME.match(spec)
        if match and normalize(match.group(1)) in BANNED:
            hits.add(spec)
    return hits


def banned_installed() -> set[str]:
    hits: set[str] = set()
    for dist in metadata.distributions():
        name = dist.metadata["Name"] if dist.metadata else None
        if name and normalize(name) in BANNED:
            hits.add(name)
    return hits


# --- positive checks against this repository -----------------------------------


def test_lockfile_is_committed() -> None:
    assert (PROJECT_DIR / "uv.lock").is_file(), "uv.lock must be committed (ADR-0001)"


def test_declared_dependencies_have_no_banned_packages() -> None:
    assert banned_in_pyproject((PROJECT_DIR / "pyproject.toml").read_text("utf-8")) == set()


def test_lockfile_has_no_banned_packages() -> None:
    assert banned_in_lock((PROJECT_DIR / "uv.lock").read_text("utf-8")) == set()


def test_environment_has_no_banned_packages() -> None:
    assert banned_installed() == set()


# --- negative checks: the detector must fire ------------------------------------


@pytest.mark.parametrize("name", ["fiona", "Fiona", "GDAL", "gdal"])
def test_detector_flags_banned_package_in_lock(name: str) -> None:
    lock = f'version = 1\n\n[[package]]\nname = "{name}"\nversion = "1.0"\n'
    assert banned_in_lock(lock) == {name}


@pytest.mark.parametrize(
    "spec", ["fiona>=1.9", "GDAL==3.9.1", "Fiona[s3] ; sys_platform != 'win32'"]
)
def test_detector_flags_banned_package_in_pyproject(spec: str) -> None:
    pyproject = f'[project]\nname = "x"\nversion = "0"\ndependencies = ["{spec}"]\n'
    assert banned_in_pyproject(pyproject) == {spec}


def test_detector_ignores_lookalikes() -> None:
    lock = 'version = 1\n\n[[package]]\nname = "pyogrio"\nversion = "0.13"\n'
    assert banned_in_lock(lock) == set()
    pyproject = '[project]\nname = "x"\nversion = "0"\ndependencies = ["fionatools"]\n'
    assert banned_in_pyproject(pyproject) == set()
