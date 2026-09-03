"""EP-8a: the slice page in a real browser (Playwright + axe), against the fixture-built site.

The page renders the map and both tables from the public-zone files, fully
offline (every request stays on the dev server's origin); axe-core reports no
violation; the keyboard reaches every control and escapes the map; the page
reflows to 320 CSS px without horizontal scroll; without WebGL the tables still
carry every value. The browser is the machine's own Chrome or Edge (Playwright's
``channel``), so nothing is downloaded: on GitHub-hosted runners both are
preinstalled, and CI fails rather than skips when neither can be launched.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from axe_playwright_python.sync_playwright import Axe  # noqa: E402

from phillysim.publish.export import PUBLIC_MANIFEST  # noqa: E402

CHANNELS: tuple[str, ...] = ("chrome", "msedge")
#: Software WebGL for headless runs (GitHub-hosted runners have no GPU).
BROWSER_ARGS: tuple[str, ...] = ("--use-angle=swiftshader", "--enable-unsafe-swiftshader")
REQUIRE_BROWSER = os.environ.get("CI", "").lower() in {"1", "true", "yes"}
READY = "document.documentElement.dataset.state === 'ready'"
READY_TIMEOUT_MS = 60_000


@pytest.fixture(scope="module")
def site_url(built_site: tuple[Path, dict]) -> Iterator[str]:
    from phillysim.publish import sitebuild

    out, _ = built_site
    server = sitebuild.serve(out, port=0)
    host, port = server.server_address[:2]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def manifest(built_site: tuple[Path, dict]) -> dict:
    out, _ = built_site
    return json.loads((out / "data" / PUBLIC_MANIFEST).read_text("utf-8"))


@pytest.fixture(scope="module")
def browser() -> Iterator[playwright.Browser]:
    with playwright.sync_playwright() as pw:
        failures: list[str] = []
        launched = None
        for channel in CHANNELS:
            try:
                launched = pw.chromium.launch(
                    channel=channel, headless=True, args=list(BROWSER_ARGS)
                )
                break
            except Exception as exc:  # noqa: BLE001 (any launch failure means "try the next")
                failures.append(f"{channel}: {type(exc).__name__}")
        if launched is None:
            message = f"no browser among {CHANNELS} could be launched ({'; '.join(failures)})"
            if REQUIRE_BROWSER:
                pytest.fail(message)
            pytest.skip(message)
        try:
            yield launched
        finally:
            launched.close()


@pytest.fixture
def loaded(browser: playwright.Browser, site_url: str) -> Iterator[tuple[playwright.Page, dict]]:
    """A fresh page at the site, waited for ``data-state="ready"``; with the requests it made
    and the console errors it raised (``record``)."""
    context = browser.new_context(viewport={"width": 1200, "height": 900})
    page = context.new_page()
    record: dict[str, list[str]] = {"requests": [], "errors": []}
    page.on("request", lambda request: record["requests"].append(request.url))
    page.on("pageerror", lambda error: record["errors"].append(str(error)))
    page.on(
        "console",
        lambda message: record["errors"].append(message.text) if message.type == "error" else None,
    )
    page.goto(site_url)
    page.wait_for_function(READY, timeout=READY_TIMEOUT_MS)
    try:
        yield page, record
    finally:
        context.close()


def _rows(page: playwright.Page, table: str) -> int:
    return page.locator(f"#{table} tbody tr").count()


def test_renders_map_and_tables_offline(
    loaded: tuple[playwright.Page, dict], manifest: dict, site_url: str
) -> None:
    page, record = loaded
    assert page.evaluate("document.documentElement.dataset.map") == "ready"
    assert record["errors"] == []
    off_origin = [url for url in record["requests"] if not url.startswith(site_url)]
    assert off_origin == [], off_origin
    assert page.locator("#map canvas.maplibregl-canvas").count() == 1

    tracts_rows = manifest["files"]["tracts.geojson"]["rows"]
    sites_rows = manifest["files"]["sites.geojson"]["rows"]
    assert _rows(page, "tracts-table") == tracts_rows
    assert _rows(page, "sites-table") == sites_rows
    headers = page.locator("#tracts-table thead th").all_inner_texts()
    assert headers == manifest["columns"]["tracts"]
    assert page.locator("#sites-table thead th").all_inner_texts() == manifest["columns"]["sites"]
    keys = [row.get_attribute("data-key") for row in page.locator("#tracts-table tbody tr").all()]
    assert keys == sorted(keys) and len(set(keys)) == tracts_rows

    options = page.locator("#field option").all_inner_texts()
    assert options == [
        f["column"] + (" (QA only)" if f["qa_only"] else "") for f in manifest["fields"]
    ]
    field = manifest["fields"][0]
    assert field["description"] in page.locator("#field-description").inner_text()
    assert page.locator("#qa-note").evaluate("e => e.hidden") is (not field["qa_only"])
    classes = manifest["bins"][field["column"]]["classes"]
    assert page.locator("#legend li").count() == classes + 1  # + "No value"
    assert "Map of" in page.locator("#map-status").inner_text()
    assert "Work in progress" in page.locator("#wip-note").inner_text()


def test_vintage_and_attribution_come_from_the_manifest(
    loaded: tuple[playwright.Page, dict], manifest: dict
) -> None:
    page, _ = loaded
    vintage = page.locator("#vintage li").all_inner_texts()
    assert len(vintage) == len(manifest["sources"])
    for source, line in zip(manifest["sources"], vintage, strict=True):
        assert source["source"] in line and source["snapshot_id"] in line
        assert source["citation"] in line
        assert ("synthetic" in line) is bool(source["synthetic"])
    attribution = page.locator("#attribution li").all_inner_texts()
    assert attribution == manifest["attribution"]
    license_text = page.locator("#license").inner_text()
    assert manifest["license"]["spdx_id"] in license_text
    assert manifest["license"]["name"] in license_text
    assert manifest["methods_version"] in license_text
    notices = page.locator("#notices li").all_inner_texts()
    assert notices == manifest["license"]["notices"]  # the fixture is Bucket B: ODbL + OSM
    assert page.locator("#downloads a").count() == 5
    map_attribution = page.locator(".maplibregl-ctrl-attrib").inner_text()
    for line in manifest["attribution"]:
        assert line in map_attribution


def test_changing_the_column_updates_legend_and_description(
    loaded: tuple[playwright.Page, dict], manifest: dict
) -> None:
    page, _ = loaded
    assert len(manifest["fields"]) > 1
    field = manifest["fields"][-1]
    page.select_option("#field", field["column"])
    page.wait_for_function(f"document.documentElement.dataset.field === {field['column']!r}")
    assert field["description"] in page.locator("#field-description").inner_text()
    classes = manifest["bins"][field["column"]]["classes"]
    assert page.locator("#legend li").count() == classes + 1
    legend = page.locator("#legend li").all_inner_texts()
    assert legend[0].startswith("Class 1:") and legend[-1] == "No value"


def test_axe_reports_no_violation(loaded: tuple[playwright.Page, dict]) -> None:
    page, _ = loaded
    results = Axe().run(page)
    violations = results.response.get("violations", [])
    summary = [(v["id"], v["impact"], [n["target"] for n in v["nodes"]][:3]) for v in violations]
    assert results.violations_count == 0, summary


def test_keyboard_reaches_every_control_and_escapes_the_map(
    loaded: tuple[playwright.Page, dict],
) -> None:
    page, _ = loaded
    describe = (
        "(() => { const e = document.activeElement; "
        "return e.tagName + (e.id ? '#' + e.id : '') + "
        "(e.className ? '.' + String(e.className).split(' ').join('.') : ''); })()"
    )
    page.locator("body").focus()
    order: list[str] = []
    for _ in range(60):
        page.keyboard.press("Tab")
        current = page.evaluate(describe)
        if current.startswith("BODY"):
            break
        order.append(current)
    wanted = [
        "A.skip-link",
        "SELECT#field",
        "CANVAS.maplibregl-canvas",
        "BUTTON.maplibregl-ctrl-zoom-in",
        "BUTTON.maplibregl-ctrl-zoom-out",
        "A.skip-link.skip-link-after",
        "DIV.table-scroll",
    ]
    positions = [next((i for i, o in enumerate(order) if o == w), None) for w in wanted]
    assert None not in positions, (wanted, order)
    assert positions == sorted(positions), order  # in document order, no trap
    assert order.count("DIV.table-scroll") == 2
    # Every control is at least 24 x 24 CSS px (WCAG 2.5.8).
    for selector in ("#field", ".maplibregl-ctrl-zoom-in", ".maplibregl-ctrl-zoom-out"):
        box = page.locator(selector).bounding_box()
        assert box is not None and box["width"] >= 24 and box["height"] >= 24, (selector, box)


def test_reflows_to_320_px_without_horizontal_scroll(
    browser: playwright.Browser, site_url: str
) -> None:
    context = browser.new_context(viewport={"width": 320, "height": 640})
    page = context.new_page()
    try:
        page.goto(site_url)
        page.wait_for_function(READY, timeout=READY_TIMEOUT_MS)
        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
        )
        assert scroll_width <= client_width, (scroll_width, client_width)
    finally:
        context.close()


def test_reduced_motion_still_reaches_ready(browser: playwright.Browser, site_url: str) -> None:
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    try:
        page.goto(site_url)
        page.wait_for_function(READY, timeout=READY_TIMEOUT_MS)
        assert page.evaluate("document.documentElement.dataset.map") == "ready"
    finally:
        context.close()


def test_without_webgl_the_tables_still_carry_every_value(
    browser: playwright.Browser, site_url: str, manifest: dict
) -> None:
    context = browser.new_context()
    page = context.new_page()
    page.add_init_script(
        "const original = HTMLCanvasElement.prototype.getContext;"
        "HTMLCanvasElement.prototype.getContext = function (type, ...rest) {"
        "  if (String(type).startsWith('webgl')) return null;"
        "  return original.call(this, type, ...rest);"
        "};"
    )
    try:
        page.goto(site_url)
        page.wait_for_function(READY, timeout=READY_TIMEOUT_MS)
        assert page.evaluate("document.documentElement.dataset.map") == "unavailable"
        assert "WebGL" in page.locator("#map-status").inner_text()
        assert _rows(page, "tracts-table") == manifest["files"]["tracts.geojson"]["rows"]
        assert page.locator("#legend li").count() >= 2
    finally:
        context.close()
