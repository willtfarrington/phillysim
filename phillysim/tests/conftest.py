"""Shared pytest fixtures: paths to the committed synthetic fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def tinycity_dir() -> Path:
    return FIXTURES_DIR / "tinycity"


@pytest.fixture(scope="session")
def tinycity_invalid_dir() -> Path:
    return FIXTURES_DIR / "tinycity-invalid"
