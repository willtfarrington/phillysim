"""Where phillysim keeps its data.

The application owns a single ``data/`` root (roadmap/architecture.md, "Zones &
identifiers"). Inside it the four pipeline zones are ``raw`` -> ``intermediate``
-> ``curated`` -> ``public``; ``quarantine`` holds downloads that failed
validation and ``cache`` holds rebuildable scratch. Only ``public`` may ever
reach the repository or the site.

The root is never hard-coded. It resolves, in order, from:

1. the ``PHILLYSIM_DATA_ROOT`` environment variable, if set and non-empty;
2. ``<repo root>/data``, where the repo root is the nearest ancestor of the
   working directory (inclusive) that contains a ``.git`` entry;
3. ``<working directory>/data`` as a last resort.

Nothing here creates directories; resolution is pure.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_DATA_ROOT = "PHILLYSIM_DATA_ROOT"

PIPELINE_ZONES: tuple[str, ...] = ("raw", "intermediate", "curated", "public")
AUX_ZONES: tuple[str, ...] = ("quarantine", "cache")
ZONES: tuple[str, ...] = PIPELINE_ZONES + AUX_ZONES

SOURCE_ENV = "environment variable " + ENV_DATA_ROOT
SOURCE_REPO = "repository root"
SOURCE_CWD = "working directory"


def find_repo_root(start: Path | None = None) -> Path | None:
    """Return the nearest ancestor of ``start`` (inclusive) holding a ``.git`` entry."""
    here = (Path.cwd() if start is None else start).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def resolve_data_root(
    env: Mapping[str, str] | None = None, cwd: Path | None = None
) -> tuple[Path, str]:
    """Resolve the data root and say which rule produced it."""
    environ = os.environ if env is None else env
    override = environ.get(ENV_DATA_ROOT, "").strip()
    if override:
        return Path(override).expanduser().resolve(), SOURCE_ENV
    repo_root = find_repo_root(cwd)
    if repo_root is not None:
        return repo_root / "data", SOURCE_REPO
    base = (Path.cwd() if cwd is None else cwd).resolve()
    return base / "data", SOURCE_CWD


@dataclass(frozen=True)
class Settings:
    """Resolved application settings. Immutable; build with :meth:`load`."""

    data_root: Path
    data_root_source: str

    @classmethod
    def load(cls, env: Mapping[str, str] | None = None, cwd: Path | None = None) -> Settings:
        root, source = resolve_data_root(env=env, cwd=cwd)
        return cls(data_root=root, data_root_source=source)

    def zone(self, name: str) -> Path:
        if name not in ZONES:
            raise ValueError(f"unknown zone {name!r}; expected one of {ZONES}")
        return self.data_root / name

    def zones(self) -> dict[str, Path]:
        return {name: self.zone(name) for name in ZONES}
