// phillysim slice page (EP-8a): the public zone drawn as a map and tables, nothing else.
//
// Everything rendered here comes from data/manifest.json and the files it registers
// (docs/data-dictionary.md "Public zone"): the columns, the field descriptions, the
// class edges (bins are computed at build time; this page never classifies), the QA
// note, the sources' snapshot IDs (the vintage line), the license and attribution.
// The basemap is data/basemap.geojson, the county boundary derived at site-build time.
// No request leaves this origin. Vanilla ES module; MapLibre GL JS is vendored.

import * as maplibregl from "./vendor/maplibre-gl/maplibre-gl.mjs";

const DATA = "data/";
const FILES = {
  manifest: DATA + "manifest.json",
  tracts: DATA + "tracts.geojson",
  sites: DATA + "sites.geojson",
  basemap: DATA + "basemap.geojson",
};
const DOWNLOADS = ["tracts.geojson", "tracts.csv", "sites.geojson", "sites.csv", "manifest.json"];
// Five-class sequential samples of viridis (CVD-safe family named in the accessibility
// spec), light = low value, dark = high value; sampled evenly when a column has fewer
// classes. Validation against CVD simulators is an M6 release-gate item.
const PALETTE = ["#fde725", "#5ec962", "#21918c", "#3b528b", "#440154"];
const NO_VALUE = "#d9d9d9";
const MAPLIBRE_VERSION = "6.7.0";

const html = document.documentElement;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}

function isNumberColumn(column, manifest) {
  if (column === "population" || column === "longitude" || column === "latitude") return true;
  return manifest.fields.some(
    (f) =>
      column === f.column ||
      column === `${f.column}_moe` ||
      column === `${f.column}_cv_tier` ||
      column === `${f.column}_bin`,
  );
}

function formatCell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toLocaleString("en-US", { maximumFractionDigits: 3 });
  }
  return String(value);
}

function formatEdge(value) {
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function classColors(classes) {
  if (classes <= 0) return [];
  if (classes === 1) return [PALETTE[PALETTE.length - 1]];
  const colors = [];
  for (let i = 0; i < classes; i += 1) {
    const index = Math.round((i * (PALETTE.length - 1)) / (classes - 1));
    colors.push(PALETTE[index]);
  }
  return colors;
}

// --- tables ---------------------------------------------------------------------------------

function renderTable(tableId, captionText, columns, rows, manifest, keyColumn) {
  const table = $(tableId);
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");
  thead.replaceChildren();
  tbody.replaceChildren();
  table.querySelector("caption").textContent = captionText;
  const headerRow = el("tr");
  for (const column of columns) {
    headerRow.append(
      el("th", { scope: "col", class: isNumberColumn(column, manifest) ? "num" : null, text: column }),
    );
  }
  thead.append(headerRow);
  for (const row of rows) {
    const tr = el("tr", { "data-key": String(row[keyColumn]) });
    columns.forEach((column, index) => {
      const cellTag = index === 0 ? "th" : "td";
      const cell = el(cellTag, {
        scope: index === 0 ? "row" : null,
        class: isNumberColumn(column, manifest) ? "num" : null,
        text: formatCell(row[column]),
      });
      tr.append(cell);
    });
    tbody.append(tr);
  }
}

function featureRows(collection, extra = () => ({})) {
  return collection.features.map((feature) => ({ ...feature.properties, ...extra(feature) }));
}

// --- legend + field description ------------------------------------------------------------

function renderLegend(field, manifest) {
  const legend = $("legend");
  legend.replaceChildren();
  const record = manifest.bins[field.column];
  const edges = record ? record.edges : [];
  const classes = record ? record.classes : 0;
  const colors = classColors(classes);
  for (let i = 0; i < classes; i += 1) {
    const low = formatEdge(edges[i]);
    const high = formatEdge(edges[i + 1]);
    const last = i === classes - 1;
    legend.append(
      el("li", {}, [
        el("span", { class: "swatch", style: `background:${colors[i]}`, "aria-hidden": "true" }),
        el("span", { text: `Class ${i + 1}: ${low} to ${last ? "" : "below "}${high}` }),
      ]),
    );
  }
  legend.append(
    el("li", {}, [
      el("span", { class: "swatch", style: `background:${NO_VALUE}`, "aria-hidden": "true" }),
      el("span", { text: "No value" }),
    ]),
  );
  return colors;
}

function renderFieldText(field, manifest) {
  const parts = [field.column];
  if (field.category) parts.push(`category ${field.category}`);
  if (field.mode) parts.push(`mode ${field.mode}`);
  $("field-description").textContent = `${parts.join(", ")}: ${field.description}`;
  const qa = $("qa-note");
  if (field.qa_only) {
    qa.textContent = `QA only. ${manifest.qa_note || "This column is a quality-assurance check, not an access measure."}`;
    qa.hidden = false;
  } else {
    qa.textContent = "";
    qa.hidden = true;
  }
}

// --- map --------------------------------------------------------------------------------------

function webglAvailable() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

function fillColorExpression(field, colors) {
  if (colors.length === 0) return NO_VALUE;
  const expression = ["match", ["coalesce", ["get", `${field.column}_bin`], -1]];
  colors.forEach((color, index) => expression.push(index + 1, color));
  expression.push(NO_VALUE);
  return expression;
}

function attributionText(manifest) {
  const label = manifest.license;
  return `${manifest.attribution.join(" ")} Published under ${label.spdx_id}.`;
}

function initMap(manifest, basemap, tracts, sites, onSelect) {
  const map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {},
      layers: [{ id: "background", type: "background", paint: { "background-color": "#f5f5f5" } }],
    },
    bounds: manifest.bounds,
    fitBoundsOptions: { padding: 24, animate: false },
    attributionControl: { compact: false, customAttribution: attributionText(manifest) },
    fadeDuration: reducedMotion ? 0 : 300,
    maxBounds: [
      [manifest.bounds[0] - 1, manifest.bounds[1] - 1],
      [manifest.bounds[2] + 1, manifest.bounds[3] + 1],
    ],
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false, visualizePitch: false }), "top-left");

  map.on("load", () => {
    map.addSource("tracts", { type: "geojson", data: tracts });
    map.addSource("sites", { type: "geojson", data: sites });
    map.addSource("basemap", { type: "geojson", data: basemap });
    map.addLayer({
      id: "tracts-fill",
      type: "fill",
      source: "tracts",
      paint: { "fill-color": NO_VALUE, "fill-opacity": 0.8 },
    });
    map.addLayer({
      id: "tracts-outline",
      type: "line",
      source: "tracts",
      paint: { "line-color": "#555555", "line-width": 0.6 },
    });
    map.addLayer({
      id: "county-boundary",
      type: "line",
      source: "basemap",
      paint: { "line-color": "#1b1b1b", "line-width": 1.8 },
    });
    map.addLayer({
      id: "sites",
      type: "circle",
      source: "sites",
      paint: {
        "circle-radius": 4,
        "circle-color": "#1b1b1b",
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.5,
      },
    });
    map.on("click", "tracts-fill", (event) => {
      const feature = event.features && event.features[0];
      if (feature) onSelect(feature.properties);
    });
    map.on("mouseenter", "tracts-fill", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "tracts-fill", () => {
      map.getCanvas().style.cursor = "";
    });
  });
  return map;
}

// --- page ---------------------------------------------------------------------------------------

function renderVintage(manifest) {
  const list = $("vintage");
  list.replaceChildren();
  for (const source of manifest.sources) {
    const synthetic = source.synthetic ? " (synthetic fixture, not real data)" : "";
    list.append(
      el("li", {
        text: `${source.source}: snapshot ${source.snapshot_id}${synthetic}. ${source.citation}`,
      }),
    );
  }
}

function renderAttribution(manifest) {
  const label = manifest.license;
  const license = $("license");
  license.replaceChildren(
    document.createTextNode(`Published data files: license bucket ${label.bucket}, `),
    el("a", { href: label.url, rel: "noopener", text: `${label.name} (${label.spdx_id})` }),
    document.createTextNode(`. Pipeline ${manifest.pipeline}, methods version ${manifest.methods_version}, public schema version ${manifest.public_schema_version}.`),
  );
  const attribution = $("attribution");
  attribution.replaceChildren(...manifest.attribution.map((line) => el("li", { text: line })));
  const notices = $("notices");
  notices.replaceChildren(...(label.notices || []).map((line) => el("li", { text: line })));
  $("maplibre-version").textContent = `v${MAPLIBRE_VERSION}`;
  const downloads = $("downloads");
  downloads.replaceChildren(
    ...DOWNLOADS.map((name) => {
      const entry = manifest.files[name];
      const detail = entry ? ` (${entry.rows} rows, ${entry.bytes} bytes)` : "";
      return el("li", {}, [el("a", { href: DATA + name, text: name }), document.createTextNode(detail)]);
    }),
  );
}

function renderColumns(manifest) {
  const dl = $("columns");
  dl.replaceChildren();
  dl.append(el("dt", { text: "geoid, name, population" }));
  dl.append(
    el("dd", {
      text: "The tract's 2020 Census GEOID, name, and 2020 Census population (a count, no margin of error).",
    }),
  );
  for (const field of manifest.fields) {
    dl.append(el("dt", { text: field.column + (field.qa_only ? " (QA only)" : "") }));
    dl.append(el("dd", { text: field.description }));
    dl.append(
      el("dd", {
        text:
          `Companions: ${field.column}_moe (margin of error), _cv_tier (reliability tier), ` +
          "_reliability_action (interval-only or none), _bin (the build-time class shown on the map).",
      }),
    );
  }
}

function selectTract(properties) {
  const rows = $("tracts-table").querySelectorAll("tbody tr");
  for (const row of rows) row.classList.toggle("selected", row.dataset.key === String(properties.geoid));
  const field = currentField();
  const value = properties[field.column];
  const bin = properties[`${field.column}_bin`];
  $("map-status").textContent =
    `Selected tract ${properties.geoid} (${properties.name}): ${field.column} = ` +
    `${formatCell(value)}${bin === null || bin === undefined ? ", no class" : `, class ${bin}`}.`;
}

let state = { manifest: null, map: null, colors: [] };

function currentField() {
  const column = $("field").value;
  return state.manifest.fields.find((f) => f.column === column) || state.manifest.fields[0];
}

function applyField() {
  const field = currentField();
  renderFieldText(field, state.manifest);
  state.colors = renderLegend(field, state.manifest);
  if (state.map && state.map.getLayer("tracts-fill")) {
    state.map.setPaintProperty("tracts-fill", "fill-color", fillColorExpression(field, state.colors));
  }
  html.dataset.field = field.column;
}

async function main() {
  const manifest = await fetchJson(FILES.manifest);
  state.manifest = manifest;
  const [tracts, sites, basemap] = await Promise.all([
    fetchJson(FILES.tracts),
    fetchJson(FILES.sites),
    fetchJson(FILES.basemap),
  ]);

  const select = $("field");
  select.replaceChildren(
    ...manifest.fields.map((field) =>
      el("option", { value: field.column, text: field.column + (field.qa_only ? " (QA only)" : "") }),
    ),
  );
  select.addEventListener("change", applyField);

  const tractColumns = manifest.columns.tracts;
  const tractRows = featureRows(tracts);
  renderTable(
    "tracts-table",
    `Tracts: ${tractRows.length} rows, ${tractColumns.length} columns (data/tracts.csv)`,
    tractColumns,
    tractRows,
    manifest,
    "geoid",
  );
  $("tracts-summary").textContent =
    `${tractRows.length} tracts. Every column of the published file, in the file's order; ` +
    "the map shows the selected column's build-time class.";
  const siteColumns = manifest.columns.sites;
  const siteRows = featureRows(sites, (feature) => ({
    longitude: feature.geometry ? feature.geometry.coordinates[0] : null,
    latitude: feature.geometry ? feature.geometry.coordinates[1] : null,
  }));
  renderTable(
    "sites-table",
    `Sites: ${siteRows.length} rows, ${siteColumns.length} columns (data/sites.csv)`,
    siteColumns,
    siteRows,
    manifest,
    "site_id",
  );
  $("sites-summary").textContent =
    `${siteRows.length} facility points the tract columns were computed against (already public upstream).`;
  renderColumns(manifest);
  renderVintage(manifest);
  renderAttribution(manifest);
  applyField();

  const status = $("map-status");
  if (!webglAvailable()) {
    html.dataset.map = "unavailable";
    status.textContent = "The map needs WebGL, which this browser does not provide. The tables below carry every value.";
    html.dataset.state = "ready";
    return;
  }
  try {
    state.map = initMap(manifest, basemap, tracts, sites, selectTract);
  } catch (error) {
    html.dataset.map = "unavailable";
    status.textContent = `The map could not start (${error.message}). The tables below carry every value.`;
    html.dataset.state = "ready";
    return;
  }
  state.map.once("idle", () => {
    applyField();
    html.dataset.map = "ready";
    status.textContent =
      `Map of ${tractRows.length} tracts and ${siteRows.length} sites. Use the zoom buttons or, with the map focused, ` +
      "the arrow keys and plus and minus keys; click a tract to name it here. Every value is in the table below.";
    html.dataset.state = "ready";
  });
  state.map.on("error", (event) => {
    if (html.dataset.state !== "ready") {
      html.dataset.map = "unavailable";
      status.textContent = `The map could not draw (${event.error ? event.error.message : "unknown error"}). The tables below carry every value.`;
      html.dataset.state = "ready";
    }
  });
}

main().catch((error) => {
  html.dataset.state = "error";
  html.dataset.map = "unavailable";
  $("map-status").textContent = `The public files could not be loaded: ${error.message}`;
});
