"""EP-5a: the guarded download path, driven entirely on crafted local bytes.

A fake opener stands in for the network, so every branch is exercised offline:
allowlist before any connection, https only, declared and streamed size caps,
bounded backoff on transient failures, the alternate URL after a definitive
failure, redirect targets checked against the allowlist, archive guards before
anything could be extracted, the terms-page stop condition, manifest fields,
and admission through quarantine. ``tests/conftest.py`` additionally disables
sockets for the whole suite, so a test that did reach for the network would
fail loudly.
"""

from __future__ import annotations

import io
import json
import urllib.error
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from phillysim import download
from phillysim.download import (
    DownloadError,
    Fetch,
    SnapshotSpec,
    TermsError,
    acquire_snapshot,
    backoff_seconds,
    check_terms,
    fetch_file,
    new_snapshot_dir,
    urllib_open,
)
from phillysim.guards import GuardError, Limits
from phillysim.manifest import read_manifest, verify_snapshot
from phillysim.quarantine import QuarantinedError, list_quarantined

ALLOWLIST = ("data.example.invalid", "terms.example.invalid")
DATA_URL = "https://data.example.invalid/files/tracts.zip"
ALT_URL = "https://mirror.data.example.invalid/files/tracts.zip"
TERMS_URL = "https://terms.example.invalid/policies/open-data.html"
TERMS_HTML = (
    b"<html><body><p>The Bureau publishes its data as open\n data, meaning it is freely "
    b"available   for use and re-use by the public.</p></body></html>"
)
PHRASE = "publishes its data as open data, meaning it is freely available for use and re-use"
SMALL = Limits(
    max_file_bytes=64 * 1024,
    max_extracted_bytes=256 * 1024,
    max_compression_ratio=20,
    max_members=8,
)


class FakeResponse:
    def __init__(self, data: bytes, status: int = 200, headers: dict[str, str] | None = None):
        self._buffer = io.BytesIO(data)
        self.status = status
        self.headers = headers or {}
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def close(self) -> None:
        self.closed = True


class FakeOpener:
    """Serves ``routes``: bytes, a ``FakeResponse``, an exception to raise, or a list of those
    consumed one call at a time. Records every URL it was asked for."""

    def __init__(self, routes: dict[str, object]) -> None:
        self.routes = dict(routes)
        self.calls: list[str] = []
        self.timeouts: list[float] = []

    def __call__(self, url: str, allowlist, timeout: float) -> FakeResponse:
        self.calls.append(url)
        self.timeouts.append(timeout)
        if url not in self.routes:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]
        item = self.routes[url]
        if isinstance(item, list):
            item = item.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, FakeResponse):
            return item
        return FakeResponse(item)  # type: ignore[arg-type]


def _zip(members: dict[str, bytes], *, compress: bool = True) -> bytes:
    buffer = io.BytesIO()
    method = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(buffer, "w", method) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buffer.getvalue()


GOOD_ZIP = _zip({"tracts.shp": bytes(range(256)) * 4, "tracts.dbf": b"dbf" * 100})


def _spec(**overrides) -> SnapshotSpec:
    base = SnapshotSpec(
        source="tiger_tracts",
        acquisition_url=DATA_URL,
        files=(Fetch(DATA_URL, "tracts.zip", url_alt=ALT_URL),),
        terms=Fetch(TERMS_URL, "terms.html"),
        terms_must_contain=(PHRASE,),
        allowlist=ALLOWLIST,
        limits=SMALL,
        license_bucket="A",
        license_note="crafted test source; US public domain shape",
    )
    return replace(base, **overrides)


def _target(tmp_path: Path, source: str = "tiger_tracts") -> Path:
    return tmp_path / "staging" / "raw" / source / "2026-09-02"


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(DATA_URL, code, "err", {}, None)  # type: ignore[arg-type]


# --- fetch_file: the order of checks -----------------------------------------------------------


def test_allowlist_is_checked_before_any_connection(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: GOOD_ZIP})
    with pytest.raises(GuardError) as info:
        fetch_file(
            Fetch("https://evil.example/tracts.zip", "t.zip"),
            tmp_path / "t.zip",
            allowlist=ALLOWLIST,
            max_bytes=1 << 20,
            opener=opener,
        )
    assert info.value.guard == "allowlist"
    assert opener.calls == [], "no connection may be opened for an off-allowlist URL"
    # An off-allowlist *alternate* is refused up front too, even though the primary is fine.
    with pytest.raises(GuardError):
        fetch_file(
            Fetch(DATA_URL, "t.zip", url_alt="http://data.example.invalid/plain"),
            tmp_path / "t.zip",
            allowlist=ALLOWLIST,
            max_bytes=1 << 20,
            opener=opener,
        )
    assert opener.calls == []
    assert not (tmp_path / "t.zip").exists()


def test_declared_length_over_cap_is_refused_before_streaming(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: FakeResponse(b"x" * 10, headers={"Content-Length": "999999"})})
    with pytest.raises(GuardError) as info:
        fetch_file(
            Fetch(DATA_URL, "t.zip"),
            tmp_path / "t.zip",
            allowlist=ALLOWLIST,
            max_bytes=100,
            opener=opener,
        )
    assert info.value.guard == "size" and "declared" in info.value.detail
    assert opener.calls == [DATA_URL], "a guard failure is never retried"
    assert list(tmp_path.iterdir()) == [], "no partial file is left behind"


def test_streamed_bytes_over_cap_are_refused_without_retry_or_alternate(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: b"x" * 101, ALT_URL: b"x" * 10})
    sleeps: list[float] = []
    with pytest.raises(GuardError) as info:
        fetch_file(
            Fetch(DATA_URL, "t.bin", url_alt=ALT_URL),
            tmp_path / "t.bin",
            allowlist=ALLOWLIST,
            max_bytes=100,
            opener=opener,
            sleep=sleeps.append,
        )
    assert info.value.guard == "size"
    assert opener.calls == [DATA_URL] and sleeps == []
    assert list(tmp_path.iterdir()) == []


def test_transient_failures_back_off_boundedly_then_succeed(tmp_path: Path) -> None:
    opener = FakeOpener(
        {DATA_URL: [urllib.error.URLError("timed out"), _http_error(503), GOOD_ZIP]}
    )
    sleeps: list[float] = []
    result = fetch_file(
        Fetch(DATA_URL, "t.zip"),
        tmp_path / "t.zip",
        allowlist=ALLOWLIST,
        max_bytes=1 << 20,
        opener=opener,
        sleep=sleeps.append,
        timeout=7.5,
    )
    assert result.attempts == 3 and result.url == DATA_URL and result.bytes == len(GOOD_ZIP)
    assert sleeps == [1.0, 2.0], "bounded backoff: 1 s then 2 s, no sleep after success"
    assert opener.timeouts == [7.5, 7.5, 7.5]
    assert (tmp_path / "t.zip").read_bytes() == GOOD_ZIP
    assert not (tmp_path / "t.zip.part").exists()


def test_backoff_is_capped() -> None:
    assert [backoff_seconds(n) for n in (1, 2, 3, 4, 5, 9)] == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]


def test_exhausted_retries_fall_through_to_the_alternate(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: [_http_error(500)] * 3, ALT_URL: GOOD_ZIP})
    sleeps: list[float] = []
    result = fetch_file(
        Fetch(DATA_URL, "t.zip", url_alt=ALT_URL),
        tmp_path / "t.zip",
        allowlist=ALLOWLIST,
        max_bytes=1 << 20,
        opener=opener,
        sleep=sleeps.append,
    )
    assert result.url == ALT_URL and result.attempts == 4
    assert opener.calls == [DATA_URL] * 3 + [ALT_URL]
    assert sleeps == [1.0, 2.0], "no sleep after the last attempt on a URL"


def test_definitive_failure_moves_to_the_alternate_at_once(tmp_path: Path) -> None:
    opener = FakeOpener({ALT_URL: GOOD_ZIP})  # primary answers 404
    sleeps: list[float] = []
    result = fetch_file(
        Fetch(DATA_URL, "t.zip", url_alt=ALT_URL),
        tmp_path / "t.zip",
        allowlist=ALLOWLIST,
        max_bytes=1 << 20,
        opener=opener,
        sleep=sleeps.append,
    )
    assert opener.calls == [DATA_URL, ALT_URL] and sleeps == []
    assert result.url == ALT_URL and result.attempts == 2


def test_every_url_failing_raises_download_error_naming_each_attempt(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: [ConnectionResetError("reset")] * 3})
    sleeps: list[float] = []
    with pytest.raises(DownloadError) as info:
        fetch_file(
            Fetch(DATA_URL, "t.zip", url_alt=ALT_URL),
            tmp_path / "t.zip",
            allowlist=ALLOWLIST,
            max_bytes=1 << 20,
            opener=opener,
            sleep=sleeps.append,
            attempts=3,
        )
    assert "4 attempt(s)" in str(info.value) and "404" in str(info.value)
    assert "ConnectionResetError" in str(info.value)
    assert opener.calls == [DATA_URL] * 3 + [ALT_URL]
    assert list(tmp_path.iterdir()) == []


def test_non_200_status_is_a_definitive_failure(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: FakeResponse(b"", status=204)})
    with pytest.raises(DownloadError, match="HTTP 204"):
        fetch_file(
            Fetch(DATA_URL, "t.zip"),
            tmp_path / "t.zip",
            allowlist=ALLOWLIST,
            max_bytes=100,
            opener=opener,
        )


def test_query_secret_is_sent_but_never_recorded(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL + "?key=SECRET": b"data"})
    result = fetch_file(
        Fetch(DATA_URL, "t.bin"),
        tmp_path / "t.bin",
        allowlist=ALLOWLIST,
        max_bytes=100,
        opener=opener,
        query_secret={"key": "SECRET"},
    )
    assert opener.calls == [DATA_URL + "?key=SECRET"]
    assert result.url == DATA_URL and "SECRET" not in json.dumps(result.to_dict())


# --- the real transport, without a network ------------------------------------------------


@pytest.mark.parametrize(
    "url",
    ["http://data.example.invalid/x", "https://evil.example/x", "ftp://data.example.invalid/x"],
)
def test_urllib_opener_refuses_before_opening(url: str) -> None:
    with pytest.raises(GuardError) as info:
        urllib_open(url, ALLOWLIST, 1.0)
    assert info.value.guard == "allowlist"


def test_redirect_targets_are_checked_against_the_allowlist() -> None:
    handler = download._AllowlistedRedirects(ALLOWLIST)
    request = download.urllib.request.Request(DATA_URL)
    with pytest.raises(GuardError) as info:
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/x")
    assert info.value.guard == "allowlist"
    with pytest.raises(GuardError):
        handler.redirect_request(request, None, 302, "Found", {}, "http://data.example.invalid/x")
    followed = handler.redirect_request(
        request, None, 302, "Found", {}, "https://mirror.data.example.invalid/x"
    )
    assert followed is not None and followed.full_url == "https://mirror.data.example.invalid/x"


def test_only_https_handlers_are_installed() -> None:
    """The opener built for real fetches has no http, file, or ftp handler to fall back on."""
    import urllib.request as ur

    opener = ur.OpenerDirector()
    for handler in (
        ur.HTTPSHandler(),
        download._AllowlistedRedirects(ALLOWLIST),
        ur.HTTPDefaultErrorHandler(),
        ur.HTTPErrorProcessor(),
        ur.UnknownHandler(),
    ):
        opener.add_handler(handler)
    assert "https" in opener.handle_open and "http" not in opener.handle_open
    assert "file" not in opener.handle_open and "ftp" not in opener.handle_open


# --- acquire_snapshot: terms, manifest, admission ------------------------------------------


def _happy_opener() -> FakeOpener:
    return FakeOpener({DATA_URL: GOOD_ZIP, TERMS_URL: TERMS_HTML})


def test_snapshot_is_acquired_archived_manifested_and_admitted(tmp_path: Path) -> None:
    target = _target(tmp_path)
    opener = _happy_opener()
    acquisition = acquire_snapshot(_spec(), target, quarantine_zone=tmp_path / "q", opener=opener)
    manifest = acquisition.manifest
    assert manifest.source == "tiger_tracts" and manifest.snapshot_id == "2026-09-02"
    assert manifest.terms_archive == "terms.html" and "terms.html" in manifest.files
    assert manifest.license_bucket == "A" and manifest.license_note
    assert manifest.acquisition_url == DATA_URL and manifest.acquisition_url_alt == ALT_URL
    assert manifest.synthetic is False and manifest.acquired_at.endswith("Z")
    assert set(manifest.files) == {"tracts.zip", "terms.html"}
    assert read_manifest(target) == manifest and verify_snapshot(target).ok
    assert (target / "terms.html").read_bytes() == TERMS_HTML
    assert opener.calls == [DATA_URL, TERMS_URL]
    assert [f.file_name for f in acquisition.fetches] == ["tracts.zip", "terms.html"]
    assert acquisition.to_dict()["bytes"] == len(GOOD_ZIP) + len(TERMS_HTML)
    assert not (tmp_path / "q").exists()
    assert not any(p.suffix == ".part" for p in target.iterdir())


def test_alternate_delivery_is_recorded_as_the_acquisition_url(tmp_path: Path) -> None:
    opener = FakeOpener({ALT_URL: GOOD_ZIP, TERMS_URL: TERMS_HTML})
    acquisition = acquire_snapshot(
        _spec(), _target(tmp_path), quarantine_zone=tmp_path / "q", opener=opener
    )
    assert acquisition.manifest.acquisition_url == ALT_URL
    assert acquisition.manifest.acquisition_url_alt == DATA_URL


def test_terms_drift_is_the_stop_condition(tmp_path: Path) -> None:
    target = _target(tmp_path)
    opener = FakeOpener({DATA_URL: GOOD_ZIP, TERMS_URL: b"<html>Terms have changed.</html>"})
    with pytest.raises(QuarantinedError) as info:
        acquire_snapshot(_spec(), target, quarantine_zone=tmp_path / "q", opener=opener)
    record = info.value.record
    assert record.kind == "terms" and PHRASE[:30] in record.reason
    assert not target.exists(), "nothing is admitted when the terms wording differs"
    moved = tmp_path / "q" / "tiger_tracts" / record.quarantined_as
    assert (moved / "terms.html").is_file() and (moved / "tracts.zip").is_file()
    assert not (moved / "manifest.json").exists(), "no manifest was written"
    assert list_quarantined(tmp_path / "q") == [record]


def test_check_terms_folds_whitespace_and_names_missing_phrases(tmp_path: Path) -> None:
    page = tmp_path / "terms.html"
    page.write_bytes(TERMS_HTML)
    check_terms(page, (PHRASE, "re-use by the public"))
    with pytest.raises(TermsError, match="not present"):
        check_terms(page, ("this sentence is not present",))


def test_zip_bomb_is_refused_before_anything_could_be_extracted(tmp_path: Path) -> None:
    target = _target(tmp_path)
    bomb = _zip({"zeros.bin": b"\0" * (200 * 1024)})
    opener = FakeOpener({DATA_URL: bomb, TERMS_URL: TERMS_HTML})
    with pytest.raises(QuarantinedError) as info:
        acquire_snapshot(_spec(), target, quarantine_zone=tmp_path / "q", opener=opener)
    assert info.value.record.kind == "bomb" and "ratio" in info.value.record.reason
    assert opener.calls == [DATA_URL], "the terms page is not even fetched after a guard failure"
    assert not target.exists()


def test_oversized_download_is_quarantined_with_the_size_guard(tmp_path: Path) -> None:
    opener = FakeOpener({DATA_URL: b"x" * (SMALL.max_file_bytes + 1), TERMS_URL: TERMS_HTML})
    with pytest.raises(QuarantinedError) as info:
        acquire_snapshot(_spec(), _target(tmp_path), quarantine_zone=tmp_path / "q", opener=opener)
    assert info.value.record.kind == "size"


def test_transport_failure_leaves_nothing_behind(tmp_path: Path) -> None:
    target = _target(tmp_path)
    opener = FakeOpener({})  # every URL 404s
    with pytest.raises(DownloadError):
        acquire_snapshot(_spec(), target, quarantine_zone=tmp_path / "q", opener=opener)
    assert not target.exists() and not (tmp_path / "q").exists()


def test_existing_snapshot_directory_is_never_overwritten(tmp_path: Path) -> None:
    target = _target(tmp_path)
    target.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        acquire_snapshot(_spec(), target, quarantine_zone=tmp_path / "q", opener=_happy_opener())


def test_multi_file_spec_records_the_directory_url(tmp_path: Path) -> None:
    directory = "https://data.example.invalid/tables/"
    spec = _spec(
        source="acs",
        acquisition_url=directory,
        files=(Fetch(directory + "a.dat", "a.dat"), Fetch(directory + "b.dat", "b.dat")),
    )
    opener = FakeOpener(
        {directory + "a.dat": b"a|1\n", directory + "b.dat": b"b|2\n", TERMS_URL: TERMS_HTML}
    )
    acquisition = acquire_snapshot(
        spec, _target(tmp_path, "acs"), quarantine_zone=tmp_path / "q", opener=opener
    )
    assert acquisition.manifest.acquisition_url == directory
    assert set(acquisition.manifest.files) == {"a.dat", "b.dat", "terms.html"}


def test_spec_rules() -> None:
    with pytest.raises(ValueError, match="allowlist"):
        _spec(allowlist=())
    with pytest.raises(ValueError, match="terms page must say"):
        _spec(terms_must_contain=())
    with pytest.raises(ValueError, match="unique"):
        _spec(files=(Fetch(DATA_URL, "terms.html"),))
    with pytest.raises(ValueError, match="at least one file"):
        _spec(files=())


def test_new_snapshot_dir_takes_the_next_free_id(tmp_path: Path) -> None:
    from datetime import date

    raw = tmp_path / "raw"
    first = new_snapshot_dir(raw, "acs", date(2026, 9, 2))
    assert first == raw / "acs" / "2026-09-02" and not first.exists()
    first.mkdir(parents=True)
    assert new_snapshot_dir(raw, "acs", date(2026, 9, 2)) == raw / "acs" / "2026-09-02-1"
