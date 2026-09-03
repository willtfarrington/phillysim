"""Shared pytest fixtures: paths to the committed fixtures, and the no-network rule.

CI is offline by policy (roadmap/quality.md). The autouse fixture below makes
that a property of the suite rather than a promise: every socket connection
attempted by any test raises, so a test that reached for a data source would
fail here and in CI alike.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--real-data-root",
        default=None,
        metavar="DIR",
        help="A real data root (after `phillysim run`) to check the invariants on; the tests "
        "that need it are skipped otherwise. CI never passes it.",
    )


@pytest.fixture(scope="session")
def real_data_root(request: pytest.FixtureRequest) -> Path:
    """The real data root given on the command line, or a skip (never reached in CI)."""
    given = request.config.getoption("--real-data-root")
    if given is None:
        pytest.skip("needs --real-data-root DIR (a manual run against the real spine)")
    root = Path(given).resolve()
    if not root.is_dir():
        pytest.fail(f"--real-data-root {given!r} is not a directory")
    return root


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(self: socket.socket, address: object) -> None:
        raise RuntimeError(f"network access is disabled in the test suite (tried {address!r})")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


@pytest.fixture(scope="session")
def tinycity_dir() -> Path:
    return FIXTURES_DIR / "tinycity"


@pytest.fixture(scope="session")
def tinycity_invalid_dir() -> Path:
    return FIXTURES_DIR / "tinycity-invalid"


@pytest.fixture(scope="session")
def spine_samples_dir() -> Path:
    return FIXTURES_DIR / "spine-samples"
