"""EP-8a: the site build and its dev server, on the fixture's public zone (and, since
EP-8b, on the real zone built from the committed samples).

The built site holds the public files byte for byte (the basemap among them
since EP-8b: nothing is derived at build time any more), the page sources,
and the vendored MapLibre at the digests recorded in
``site/vendor/maplibre-gl/VENDOR.md``; the build is deterministic, refuses a
zone that fails the publish gate, and replaces only a previous build. The dev
server answers with the MIME types module scripts and GeoJSON need. The
page's behaviour in a browser is ``test_site_browser.py``.
"""

from __future__ import annotations

import http.client
import json
import re
import shutil
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.fixtures.pipeline import FIXTURE_BOUNDS
from phillysim.manifest import sha256_file
from phillysim.publish import sitebuild
from phillysim.publish.export import BASEMAP_GEOJSON, PUBLIC_FILES, PUBLIC_MANIFEST

runner = CliRunner()

TOP_LEVEL = {"index.html", "main.js", "styles.css", "site.json", "data", "vendor"}
DATA_FILES = {PUBLIC_MANIFEST, *PUBLIC_FILES}


def _files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# --- layout and content --------------------------------------------------------------------


def test_built_site_layout(built_site: tuple[Path, dict]) -> None:
    out, report = built_site
    assert {p.name for p in out.iterdir()} == TOP_LEVEL
    assert {p.name for p in (out / "data").iterdir()} == DATA_FILES
    vendor = out / sitebuild.VENDOR_DIR_NAME / sitebuild.MAPLIBRE_DIR
    assert {p.name for p in vendor.iterdir()} == set(sitebuild.MAPLIBRE_FILES)
    assert report["site_schema_version"] == sitebuild.SITE_SCHEMA_VERSION == 2
    assert report["pipeline"] == "fixture" and report["public_schema_version"] == 2
    assert report["work_in_progress"] is True
    assert json.loads((out / sitebuild.SITE_MANIFEST).read_text("utf-8")) == report


def test_public_files_are_copied_verbatim(
    built_site: tuple[Path, dict], fixture_public_zone: Path
) -> None:
    out, report = built_site
    manifest = json.loads((fixture_public_zone / PUBLIC_MANIFEST).read_text("utf-8"))
    for name in (PUBLIC_MANIFEST, *PUBLIC_FILES):
        assert (out / "data" / name).read_bytes() == (fixture_public_zone / name).read_bytes()
        assert report["public_files"][name] == sha256_file(fixture_public_zone / name)
    for name in PUBLIC_FILES:
        assert report["public_files"][name] == manifest["files"][name]["sha256"]


def test_basemap_is_the_zones_file_verbatim(
    built_site: tuple[Path, dict], fixture_public_zone: Path
) -> None:
    """Nothing is derived at build time any more: the basemap is the zone's own file, and
    the site manifest records its layers from the public manifest."""
    out, report = built_site
    assert (out / "data" / BASEMAP_GEOJSON).read_bytes() == (
        fixture_public_zone / BASEMAP_GEOJSON
    ).read_bytes()
    manifest = json.loads((fixture_public_zone / PUBLIC_MANIFEST).read_text("utf-8"))
    assert report["basemap"] == {
        "file": BASEMAP_GEOJSON,
        "layers": {"county_boundary": 1},
        "sha256": manifest["files"][BASEMAP_GEOJSON]["sha256"],
    }
    assert report["basemap"]["sha256"] == sha256_file(out / "data" / BASEMAP_GEOJSON)


def test_sample_real_site_carries_the_roads(sample_built_site: tuple[Path, dict]) -> None:
    """The site built from the sample-built real zone (EP-8b): the basemap file holds the
    boundary and the roads, copied verbatim, and the report says so."""
    out, report = sample_built_site
    assert report["pipeline"] == "real" and report["license"]["bucket"] == "A"
    assert report["basemap"]["layers"] == {"county_boundary": 1, "roads": 48}
    basemap = json.loads((out / "data" / BASEMAP_GEOJSON).read_text("utf-8"))
    assert len(basemap["features"]) == 49
    assert report["basemap"]["sha256"] == sha256_file(out / "data" / BASEMAP_GEOJSON)
    assert {p.name for p in (out / "data").iterdir()} == DATA_FILES


def test_vendored_maplibre_matches_its_record(built_site: tuple[Path, dict]) -> None:
    """The vendored files are the bytes VENDOR.md records (and the same on every platform)."""
    out, report = built_site
    record = (sitebuild.site_source_dir() / "vendor" / "maplibre-gl" / "VENDOR.md").read_text(
        "utf-8"
    )
    assert f"MapLibre GL JS {sitebuild.MAPLIBRE_VERSION}" in record
    assert report["vendor"]["maplibre-gl"]["version"] == sitebuild.MAPLIBRE_VERSION
    files = report["vendor"]["maplibre-gl"]["files"]
    assert set(files) == {f"{sitebuild.MAPLIBRE_DIR}/{name}" for name in sitebuild.MAPLIBRE_FILES}
    for rel, digest in files.items():
        name = rel.split("/")[-1]
        assert re.search(rf"`{re.escape(name)}` \| `{digest}`", record), f"{name} not recorded"
        assert sha256_file(out / "vendor" / rel) == digest
    assert "BSD" in (out / "vendor" / sitebuild.MAPLIBRE_DIR / "LICENSE.txt").read_text("utf-8")


def test_page_sources_make_no_request_off_origin() -> None:
    """The page loads only relative resources: no script, stylesheet, fetch, or CSS URL points
    at another host (the links in the footer prose are ordinary hyperlinks, not loads)."""
    source = sitebuild.site_source_dir()
    html = (source / "index.html").read_text("utf-8")
    for tag, attr in (("script", "src"), ("link", "href"), ("img", "src")):
        for match in re.finditer(rf"<{tag}\b[^>]*\b{attr}=\"([^\"]+)\"", html):
            target = match.group(1)
            assert not re.match(r"^(https?:)?//", target), f"<{tag}> loads {target}"
    js = (source / "main.js").read_text("utf-8")
    assert "https://" not in js and "http://" not in js
    css = (source / "styles.css").read_text("utf-8")
    assert "url(" not in css and "@import" not in css
    assert "Work in progress" in html


# --- determinism, replacement, refusal -----------------------------------------------------


def test_build_is_deterministic(
    built_site: tuple[Path, dict], fixture_public_zone: Path, tmp_path: Path
) -> None:
    out, report = built_site
    again = sitebuild.build_site(fixture_public_zone, tmp_path / "dist", bounds=FIXTURE_BOUNDS)
    assert again == report
    assert _files(tmp_path / "dist") == _files(out)


def test_rebuild_replaces_a_previous_build_only(fixture_public_zone: Path, tmp_path: Path) -> None:
    other = tmp_path / "not-a-site"
    other.mkdir()
    (other / "keep.txt").write_text("mine", "utf-8")
    with pytest.raises(sitebuild.SiteBuildError, match="refusing to replace"):
        sitebuild.build_site(fixture_public_zone, other, bounds=FIXTURE_BOUNDS)
    assert (other / "keep.txt").read_text("utf-8") == "mine"

    out = tmp_path / "dist"
    sitebuild.build_site(fixture_public_zone, out, bounds=FIXTURE_BOUNDS)
    (out / "stray.txt").write_text("left over", "utf-8")
    sitebuild.build_site(fixture_public_zone, out, bounds=FIXTURE_BOUNDS)
    assert not (out / "stray.txt").exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".dist-")]  # staging gone


def test_refuses_a_zone_that_fails_the_gate(fixture_public_zone: Path, tmp_path: Path) -> None:
    zone = tmp_path / "public"
    shutil.copytree(fixture_public_zone, zone)
    with (zone / "tracts.csv").open("ab") as handle:
        handle.write(b"x")
    with pytest.raises(sitebuild.SiteBuildError, match="fails the publish gate"):
        sitebuild.build_site(zone, tmp_path / "dist", bounds=FIXTURE_BOUNDS)
    assert not (tmp_path / "dist").exists()


def test_refuses_a_zone_with_other_bounds(fixture_public_zone: Path, tmp_path: Path) -> None:
    with pytest.raises(sitebuild.SiteBuildError, match="fails the publish gate"):
        sitebuild.build_site(fixture_public_zone, tmp_path / "dist", bounds=(0.0, 0.0, 1.0, 1.0))


def test_refuses_missing_page_sources(fixture_public_zone: Path, tmp_path: Path) -> None:
    with pytest.raises(sitebuild.SiteBuildError, match="lack"):
        sitebuild.build_site(
            fixture_public_zone, tmp_path / "dist", source=tmp_path / "nowhere", bounds=None
        )


# --- CLI and the dev server ----------------------------------------------------------------


def test_cli_site_build_from_fixture_root(fixture_public_zone: Path, tmp_path: Path) -> None:
    root = fixture_public_zone.parent
    out = tmp_path / "dist"
    result = runner.invoke(
        app, ["site", "build", "--fixture", "--data-root", str(root), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert "site build: done" in result.output
    assert "pipeline 'fixture'" in result.output
    assert "work in progress" in result.output
    assert "nothing here is deployed" in result.output
    assert (out / "index.html").is_file()


def test_cli_site_build_from_public_dir(fixture_public_zone: Path, tmp_path: Path) -> None:
    out = tmp_path / "dist"
    result = runner.invoke(
        app, ["site", "build", "--public", str(fixture_public_zone), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert (out / "data" / BASEMAP_GEOJSON).is_file()
    assert "basemap: data/basemap.geojson holds county_boundary (1)" in result.output


def test_cli_site_build_refuses_empty_or_broken_zone(
    fixture_public_zone: Path, tmp_path: Path
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(
        app, ["site", "build", "--public", str(empty), "--out", str(tmp_path / "d")]
    )
    assert result.exit_code == 1
    assert "no public zone" in result.output
    zone = tmp_path / "public"
    shutil.copytree(fixture_public_zone, zone)
    (zone / "manifest.json").write_text("{}", "utf-8")
    result = runner.invoke(
        app, ["site", "build", "--public", str(zone), "--out", str(tmp_path / "d")]
    )
    assert result.exit_code == 1
    assert "FAIL" in result.output and "gate" in result.output
    assert not (tmp_path / "d").exists()


def test_cli_site_serve_refuses_an_unbuilt_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["site", "serve", "--out", str(tmp_path)])
    assert result.exit_code == 1
    assert "build the site first" in result.output


def test_dev_server_serves_the_page_with_the_right_types(built_site: tuple[Path, dict]) -> None:
    out, _ = built_site
    server = sitebuild.serve(out, port=0)
    host, port = server.server_address[:2]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        expected = {
            "/": ("text/html", 200),
            "/main.js": ("text/javascript", 200),
            "/styles.css": ("text/css", 200),
            "/vendor/maplibre-gl/maplibre-gl.mjs": ("text/javascript", 200),
            "/data/manifest.json": ("application/json", 200),
            "/data/tracts.geojson": ("application/geo+json", 200),
            "/data/tracts.csv": ("text/csv", 200),
            "/missing.txt": (None, 404),
        }
        for path, (content_type, status) in expected.items():
            connection = http.client.HTTPConnection(host, port, timeout=10)
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read()
            connection.close()
            assert response.status == status, path
            if content_type is not None:
                assert response.getheader("Content-Type", "").startswith(content_type), path
                assert response.getheader("Cache-Control") == "no-store"
                assert body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
