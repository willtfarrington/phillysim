"""Data-root resolution: env override, repo-root discovery, cwd fallback. No absolute paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from phillysim import config
from phillysim.config import Settings, find_repo_root, resolve_data_root


def test_env_override_wins(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    root, source = resolve_data_root(env={"PHILLYSIM_DATA_ROOT": str(target)}, cwd=tmp_path)
    assert root == target.resolve()
    assert source == config.SOURCE_ENV


def test_blank_env_override_is_ignored(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    root, source = resolve_data_root(env={"PHILLYSIM_DATA_ROOT": "   "}, cwd=tmp_path)
    assert root == tmp_path.resolve() / "data"
    assert source == config.SOURCE_REPO


def test_repo_root_found_from_nested_cwd(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "phillysim" / "src"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == tmp_path.resolve()
    root, source = resolve_data_root(env={}, cwd=nested)
    assert root == tmp_path.resolve() / "data"
    assert source == config.SOURCE_REPO


def test_git_file_counts_as_repo_marker(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("gitdir: ../somewhere\n")  # worktree / submodule layout
    assert find_repo_root(tmp_path) == tmp_path.resolve()


def test_cwd_fallback_without_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Guard against a .git somewhere above tmp_path on the host.
    monkeypatch.setattr(config, "find_repo_root", lambda start=None: None)
    root, source = resolve_data_root(env={}, cwd=tmp_path)
    assert root == tmp_path.resolve() / "data"
    assert source == config.SOURCE_CWD


def test_settings_zones(tmp_path: Path) -> None:
    settings = Settings.load(env={"PHILLYSIM_DATA_ROOT": str(tmp_path)})
    zones = settings.zones()
    assert list(zones) == ["raw", "intermediate", "curated", "public", "quarantine", "cache"]
    assert zones["public"] == tmp_path.resolve() / "public"
    with pytest.raises(ValueError):
        settings.zone("staging")


def test_this_repo_resolves_to_its_own_data_dir() -> None:
    """Running from the source tree, the default root is <repo>/data, not anywhere absolute."""
    here = Path(__file__).resolve()
    root, source = resolve_data_root(env={}, cwd=here.parent)
    assert source == config.SOURCE_REPO
    assert root.name == "data"
    assert root.parent in here.parents
