"""The site build: a gated public zone + the page sources -> one static directory.

The slice page (EP-8a; the seed of the M6 site, roadmap/architecture.md "Static
site") renders the public zone and nothing else. :func:`build_site` takes the
installed ``public/`` directory of either pipeline, re-runs the publish gate on
it (a zone that fails the gate is never built into a site), copies its files
**verbatim** into ``<out>/data/`` (digests re-checked against the manifest, so
map, table, and download are the same bytes; since EP-8b the basemap,
ADR-0005's county boundary plus major roads, is one of those public files
rather than something derived here), and lays the page sources and the
vendored MapLibre GL JS beside them. Nothing in the built site refers to any
host but its own: no tiles, fonts, scripts, or analytics are fetched at
runtime.

The build is deterministic: every byte comes from the zone, the sources, and
the vendored library, so a rebuilt site is byte-identical and ``site.json``
records the digests. :func:`serve` is the local dev server the brief asks for
(the standard library's threaded HTTP server bound to loopback, with the MIME
types ES modules and GeoJSON need); it exists so the page can be looked at and
tested through a real ``http://`` origin, which module scripts require.
"""

from __future__ import annotations

import functools
import http.server
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from phillysim.config import find_repo_root
from phillysim.manifest import sha256_file
from phillysim.publish.export import BASEMAP_GEOJSON, PUBLIC_FILES, PUBLIC_MANIFEST, json_bytes
from phillysim.publish.gate import check_public_zone

#: 1 was EP-8a's (the boundary derived at build time); 2 takes the basemap from the zone.
SITE_SCHEMA_VERSION = 2
SITE_DIR_NAME = "site"
DIST_DIR_NAME = "dist"
DATA_DIR_NAME = "data"
VENDOR_DIR_NAME = "vendor"
SITE_MANIFEST = "site.json"
#: The page sources copied from ``site/`` (everything else there is documentation).
PAGE_FILES: tuple[str, ...] = ("index.html", "main.js", "styles.css")
#: The vendored map library, pinned in ``site/vendor/maplibre-gl/VENDOR.md``.
MAPLIBRE_DIR = "maplibre-gl"
MAPLIBRE_FILES: tuple[str, ...] = (
    "maplibre-gl.mjs",
    "maplibre-gl-shared.mjs",
    "maplibre-gl-worker.mjs",
    "maplibre-gl.css",
    "LICENSE.txt",
)
MAPLIBRE_VERSION = "6.7.0"

#: MIME types the standard server does not know (or knows wrongly) that the page needs.
MIME_TYPES: dict[str, str] = {
    ".mjs": "text/javascript",
    ".js": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".geojson": "application/geo+json",
    ".html": "text/html",
    ".csv": "text/csv",
    ".png": "image/png",
}


class SiteBuildError(ValueError):
    """The site cannot be built from these inputs (gate failure, or a missing source file)."""


def site_source_dir(start: Path | None = None) -> Path:
    """The page sources: ``<repo root>/site``, found from the working directory (or ``start``)
    the way the data root is, with the checkout this module was imported from as the fallback."""
    root = find_repo_root(start)
    if root is not None and (root / SITE_DIR_NAME / PAGE_FILES[0]).is_file():
        return root / SITE_DIR_NAME
    fallback = Path(__file__).resolve().parents[3] / SITE_DIR_NAME
    if (fallback / PAGE_FILES[0]).is_file():
        return fallback
    raise SiteBuildError(f"no site sources found ({SITE_DIR_NAME}/{PAGE_FILES[0]} is missing)")


def _copy_checked(src: Path, dst: Path, expected_sha256: str) -> None:
    shutil.copyfile(src, dst)
    actual = sha256_file(dst)
    if actual != expected_sha256:
        raise SiteBuildError(
            f"{src.name}: copied digest {actual[:12]} != manifest {expected_sha256[:12]}"
        )


def build_site(
    public: Path,
    out: Path,
    *,
    source: Path | None = None,
    bounds: tuple[float, float, float, float] | None = None,
) -> dict[str, Any]:
    """Build the static site from the public zone at ``public`` into ``out`` (replaced whole).

    Runs the publish gate on the zone first (``bounds`` as for :func:`check_public_zone`)
    and refuses a zone that fails it. Returns the site manifest also written to
    ``<out>/site.json``: the schema version, the pipeline, the public files with their
    digests, the basemap record (the zone's file and its layer counts), the page and
    vendor files with their digests.
    """
    source = site_source_dir() if source is None else source
    problems = check_public_zone(public, bounds=bounds)
    if problems:
        raise SiteBuildError(
            f"public zone fails the publish gate ({len(problems)} violation(s)); "
            "nothing here may be built into a site: " + "; ".join(problems[:3])
        )
    manifest = json.loads((public / PUBLIC_MANIFEST).read_text("utf-8"))
    missing = [name for name in PAGE_FILES if not (source / name).is_file()]
    missing += [
        f"{VENDOR_DIR_NAME}/{MAPLIBRE_DIR}/{name}"
        for name in MAPLIBRE_FILES
        if not (source / VENDOR_DIR_NAME / MAPLIBRE_DIR / name).is_file()
    ]
    if missing:
        raise SiteBuildError(f"site sources under {source.name!r} lack {missing}")

    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        data_dir = staging / DATA_DIR_NAME
        data_dir.mkdir()
        public_files: dict[str, str] = {}
        for name in (PUBLIC_MANIFEST, *PUBLIC_FILES):
            src = public / name
            dst = data_dir / name
            if name == PUBLIC_MANIFEST:
                shutil.copyfile(src, dst)
            else:
                _copy_checked(src, dst, manifest["files"][name]["sha256"])
            public_files[name] = sha256_file(dst)

        page_files: dict[str, str] = {}
        for name in PAGE_FILES:
            shutil.copyfile(source / name, staging / name)
            page_files[name] = sha256_file(staging / name)
        vendor_dir = staging / VENDOR_DIR_NAME / MAPLIBRE_DIR
        vendor_dir.mkdir(parents=True)
        vendor_files: dict[str, str] = {}
        for name in MAPLIBRE_FILES:
            shutil.copyfile(source / VENDOR_DIR_NAME / MAPLIBRE_DIR / name, vendor_dir / name)
            vendor_files[f"{MAPLIBRE_DIR}/{name}"] = sha256_file(vendor_dir / name)

        site_manifest: dict[str, Any] = {
            "site_schema_version": SITE_SCHEMA_VERSION,
            "pipeline": manifest["pipeline"],
            "public_schema_version": manifest["public_schema_version"],
            "methods_version": manifest["methods_version"],
            "license": manifest["license"],
            "attribution": manifest["attribution"],
            "public_files": public_files,
            "basemap": {
                "file": manifest["basemap"]["file"],
                "layers": dict(manifest["basemap"]["layers"]),
                "sha256": public_files[BASEMAP_GEOJSON],
            },
            "page_files": page_files,
            "vendor": {"maplibre-gl": {"version": MAPLIBRE_VERSION, "files": vendor_files}},
            "work_in_progress": True,
        }
        (staging / SITE_MANIFEST).write_bytes(json_bytes(site_manifest))

        if out.exists():
            if not (out / SITE_MANIFEST).is_file():
                raise SiteBuildError(
                    f"{out} exists and is not a previous site build ({SITE_MANIFEST} missing); "
                    "refusing to replace it"
                )
            shutil.rmtree(out)
        staging.replace(out)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return site_manifest


# --- the local dev server ---------------------------------------------------------------------


class _SiteHandler(http.server.SimpleHTTPRequestHandler):
    """The standard file handler with the page's MIME types and no caching."""

    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **MIME_TYPES}

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 (stdlib signature)
        if self._log is not None:
            self._log(f"{self.address_string()} {format % args}")

    _log: Callable[[str], None] | None = None


def serve(
    directory: Path,
    *,
    port: int = 8000,
    host: str = "127.0.0.1",
    log: Callable[[str], None] | None = None,
) -> http.server.ThreadingHTTPServer:
    """A threaded HTTP server for the built site, bound (by default) to loopback only.

    Returns the server without starting it; the caller runs ``serve_forever()`` (the CLI)
    or serves on a thread (the tests). ``port=0`` picks a free port; read
    ``server.server_address``.
    """
    if not (directory / "index.html").is_file():
        raise SiteBuildError(f"{directory} holds no index.html (build the site first)")
    handler = functools.partial(_SiteHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer((host, port), handler)
    _SiteHandler._log = log
    server.daemon_threads = True
    return server
