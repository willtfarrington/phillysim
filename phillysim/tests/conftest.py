"""Shared pytest fixtures: paths to the committed fixtures, the no-network rule, the
fixture pipeline's public zone and site, and the real pipeline's public zone and site
built from the committed samples on a fake transport.

CI is offline by policy (roadmap/quality.md). The autouse fixture below makes
that a property of the suite rather than a promise: every socket connection
attempted by any test raises, so a test that reached for a data source would
fail here and in CI alike.
"""

from __future__ import annotations

import io
import socket
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class SampleTransport:
    """Serves each real adapter's URLs from the committed samples; counts every call.

    The fake transport the real pipeline's ``acquire`` runs on in the suite (EP-5a): the
    same allowlist, caps, archive guards, digest checks, terms check, manifest, and
    admission as against the providers' hosts, without a network. ``terms`` replaces
    every terms page.
    """

    def __init__(self, samples: Path, *, terms: bytes | None = None) -> None:
        from phillysim.adapters import ADAPTERS
        from phillysim.pipeline import SNAPSHOT_IDS

        self.routes: dict[str, bytes] = {}
        self.calls: list[str] = []
        for source, adapter in ADAPTERS.items():
            sample = samples / "raw" / source / SNAPSHOT_IDS[source]
            for fetch in adapter.spec.files:
                self.routes[fetch.url] = (sample / fetch.file_name).read_bytes()
            page = (sample / adapter.spec.terms.file_name).read_bytes()
            self.routes[adapter.spec.terms.url] = page if terms is None else terms

    def __call__(self, url: str, allowlist, timeout: float):
        self.calls.append(url)
        return _Response(self.routes[url])


class _Response:
    def __init__(self, data: bytes) -> None:
        self._buffer = io.BytesIO(data)
        self.status = 200
        self.headers = {"Content-Length": str(len(data))}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def close(self) -> None:
        pass


def sample_pins(samples: Path) -> dict[str, dict[str, str]]:
    """The committed samples' digests in place of the adapters' pinned provider digests
    (EP-12: the OSM extract's MD5, the GTFS asset's SHA-256), so the samples admit
    through the same digest check the real files pass."""
    from phillysim.adapters import ADAPTERS
    from phillysim.download import digest_file, parse_digest
    from phillysim.pipeline import SNAPSHOT_IDS

    pins: dict[str, dict[str, str]] = {}
    for source, adapter in ADAPTERS.items():
        sample = samples / "raw" / source / SNAPSHOT_IDS[source]
        for fetch in adapter.spec.files:
            if fetch.digest is not None:
                algorithm, _ = parse_digest(fetch.digest)
                pins.setdefault(source, {})[fetch.file_name] = (
                    f"{algorithm}:{digest_file(sample / fetch.file_name, algorithm)}"
                )
    return pins


#: The OSM CI sample's node and way bands (the clip of the six sample tracts' bounds; the
#: real bands in ``phillysim.adapters.osm`` are the county's).
SAMPLE_NODE_BAND = [1_000, 200_000]
SAMPLE_WAY_BAND = [100, 50_000]


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


LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex


def _is_loopback(address: object) -> bool:
    return isinstance(address, tuple) and bool(address) and address[0] in LOOPBACK_HOSTS


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse every outbound connection except to this machine's loopback interface, which
    the site tests (EP-8a) use to fetch from the local dev server they start themselves."""

    def refuse(self: socket.socket, address: object) -> None:
        if _is_loopback(address):
            return _REAL_CONNECT(self, address)
        raise RuntimeError(f"network access is disabled in the test suite (tried {address!r})")

    def refuse_ex(self: socket.socket, address: object) -> int:
        if _is_loopback(address):
            return _REAL_CONNECT_EX(self, address)
        raise RuntimeError(f"network access is disabled in the test suite (tried {address!r})")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse_ex)


@pytest.fixture(scope="session")
def fixture_public_zone(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture pipeline run end to end in a scratch root (once per session): its gated
    public zone, the input of the site build (EP-8a)."""
    from typer.testing import CliRunner

    from phillysim.cli import app

    root = tmp_path_factory.mktemp("fixture-root")
    result = CliRunner().invoke(app, ["run", "--fixture", "--data-root", str(root)])
    assert result.exit_code == 0, result.output
    return root / "public"


@pytest.fixture(scope="session")
def built_site(
    fixture_public_zone: Path, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, dict]:
    """The slice page built from the fixture's public zone: (directory, site manifest)."""
    from phillysim.fixtures.pipeline import FIXTURE_BOUNDS
    from phillysim.publish import sitebuild

    out = tmp_path_factory.mktemp("site") / "dist"
    report = sitebuild.build_site(fixture_public_zone, out, bounds=FIXTURE_BOUNDS)
    return out, report


@pytest.fixture
def sample_transport(spine_samples_dir: Path):
    """A factory for :class:`SampleTransport` over the committed samples."""

    def make(**kwargs) -> SampleTransport:
        return SampleTransport(spine_samples_dir, **kwargs)

    return make


def sample_real_pipeline(transport, samples: Path | None = None):
    """The real pipeline on a fake transport, expecting the samples' six tracts, pinned
    to the samples' digests, with the network stage's bands set for the sample clip."""
    from phillysim.pipeline import real_pipeline

    samples = FIXTURES_DIR / "spine-samples" if samples is None else samples
    return real_pipeline(opener=transport, pins=sample_pins(samples)).with_params(
        {
            "spine": {"expected_tracts": 6},
            "network": {"node_band": SAMPLE_NODE_BAND, "way_band": SAMPLE_WAY_BAND},
        }
    )


@pytest.fixture(scope="session")
def sample_public_zone(spine_samples_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The real pipeline run end to end on the committed samples (once per session): its
    gated public zone, with the roads in the basemap (EP-8b), for the site tests."""
    from phillysim import runner

    root = tmp_path_factory.mktemp("sample-root") / "data"
    runner.run(root, sample_real_pipeline(SampleTransport(spine_samples_dir), spine_samples_dir))
    return root / "public"


@pytest.fixture(scope="session")
def sample_built_site(
    sample_public_zone: Path, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, dict]:
    """The slice page built from the sample-built real zone: (directory, site manifest)."""
    from phillysim.pipeline import real_pipeline
    from phillysim.publish import sitebuild

    bounds = tuple(float(b) for b in real_pipeline()["publish"].params["bounds"])
    out = tmp_path_factory.mktemp("sample-site") / "dist"
    report = sitebuild.build_site(sample_public_zone, out, bounds=bounds)
    return out, report


@pytest.fixture(scope="session")
def tinycity_dir() -> Path:
    return FIXTURES_DIR / "tinycity"


@pytest.fixture(scope="session")
def tinycity_invalid_dir() -> Path:
    return FIXTURES_DIR / "tinycity-invalid"


@pytest.fixture(scope="session")
def spine_samples_dir() -> Path:
    return FIXTURES_DIR / "spine-samples"
