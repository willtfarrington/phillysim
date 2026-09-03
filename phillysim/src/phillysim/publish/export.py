"""The public-zone export: analytic table -> license-labeled, binned, escaped GeoJSON + CSV.

Public schema version 1 (docs/data-dictionary.md, "Public zone"). One call,
:func:`build_public_zone`, writes the whole zone into a directory:

- ``tracts.geojson`` / ``tracts.csv``: one row per spine tract (``geoid``,
  ``name``, ``population``) plus, for every metric the analytic table holds,
  the wide column ``<metric_id>[__<category>][__<mode>]`` and its companions
  ``_moe``, ``_cv_tier``, ``_reliability_action``, ``_bin`` (the build-time
  class, :mod:`phillysim.publish.bins`);
- ``sites.geojson`` / ``sites.csv``: the facility points the metrics were
  computed against (already public upstream), keyed by site ID;
- ``manifest.json``: the label registry the gate checks: every file's bucket
  (derived from its sources' manifests, :mod:`phillysim.publish.bucket`),
  license, attribution, digest, and row count; the sources with their snapshot
  IDs; the published fields with descriptions; the bin edges; the bounds.

Every GeoJSON file also carries the label in-file (top-level ``license`` and
``attribution`` members; RFC 7946 permits foreign members) so the label travels
with the file; CSV has no such slot, so the manifest is its sidecar. Geometry is
WGS 84 (the publication boundary, ADR-0007) with coordinates rounded to a fixed
number of decimals and polygon rings oriented per RFC 7946; string cells in CSV
are escaped against spreadsheet formula injection (architecture.md "Security":
source-derived names are the untrusted vector). Every file is written
deterministically (sorted keys, fixed separators, ``\\n`` line ends) so a rebuilt
zone is byte-identical. The gate runs on the finished directory before the
caller installs it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon
from shapely.geometry.polygon import orient

from phillysim.contracts import ANALYTIC_TABLE, check_frame
from phillysim.manifest import read_manifest, sha256_file
from phillysim.publish import bins as binning
from phillysim.publish.bucket import derive_bucket, label_of
from phillysim.publish.gate import PublishGateError, check_public_zone
from phillysim.stages import StageContext

PUBLIC_ZONE = "public"
PUBLIC_CRS = "EPSG:4326"
PUBLIC_SCHEMA_VERSION = 1
PUBLIC_MANIFEST = "manifest.json"
TRACTS_GEOJSON = "tracts.geojson"
TRACTS_CSV = "tracts.csv"
SITES_GEOJSON = "sites.geojson"
SITES_CSV = "sites.csv"
PUBLIC_FILES: tuple[str, ...] = (TRACTS_GEOJSON, TRACTS_CSV, SITES_GEOJSON, SITES_CSV)

TRACT_BASE_COLUMNS: tuple[str, ...] = ("geoid", "name", "population")
SITE_COLUMNS: tuple[str, ...] = ("site_id", "source", "category", "name", "geoid")
SITE_CSV_COLUMNS: tuple[str, ...] = (*SITE_COLUMNS, "longitude", "latitude")
FIELD_COMPANIONS: tuple[str, ...] = ("moe", "cv_tier", "reliability_action", "bin")
COORDINATE_DECIMALS = 6

#: Columns whose metric ID starts with this are quality-assurance columns, never access
#: measures (methodology.md "Travel model"); the manifest says so and the gate checks it.
QA_PREFIX = "qa_"
QA_NOTE = (
    "Columns whose name starts with 'qa_' are quality-assurance (QA) columns that check the "
    "publication plumbing; they are not access measures and must not be presented as such "
    "(roadmap/methodology.md)."
)

#: A CSV cell starting with one of these could be executed as a formula by a spreadsheet.
CSV_DANGEROUS_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


class PublishError(ValueError):
    """The inputs cannot be published as they are (shape, provenance, or description gap)."""


# --- CSV escaping -------------------------------------------------------------------------


def escape_cell(value: Any) -> Any:
    """Neutralize a string cell a spreadsheet would treat as a formula, by prefixing ``'``.

    Only strings are touched: numeric columns are written by pandas as numbers and a
    negative number is not a formula. The gate accepts a cell starting with ``-`` only when
    the whole cell is a plain number.
    """
    if isinstance(value, str) and value and value[0] in CSV_DANGEROUS_PREFIXES:
        return "'" + value
    return value


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """The table as UTF-8 CSV with ``\\n`` line ends, every string cell escaped."""
    safe = frame.copy()
    for column in safe.columns:
        if safe[column].dtype == object or pd.api.types.is_string_dtype(safe[column]):
            safe[column] = safe[column].map(escape_cell)
    return safe.to_csv(index=False, lineterminator="\n").encode("utf-8")


# --- GeoJSON writing ----------------------------------------------------------------------


def _round_coordinates(coords: Any, decimals: int) -> Any:
    if isinstance(coords, (int, float)):
        return round(float(coords), decimals)
    return [_round_coordinates(part, decimals) for part in coords]


def geometry_member(geometry: Any, decimals: int) -> dict[str, Any]:
    """A shapely geometry as a GeoJSON geometry object: rings oriented per RFC 7946
    (exterior counter-clockwise), coordinates rounded to ``decimals``."""
    if geometry.geom_type == "Polygon":
        geometry = orient(geometry, 1.0)
    elif geometry.geom_type == "MultiPolygon":
        geometry = MultiPolygon([orient(part, 1.0) for part in geometry.geoms])
    mapping = geometry.__geo_interface__
    return {
        "type": mapping["type"],
        "coordinates": _round_coordinates(mapping["coordinates"], decimals),
    }


def _plain(value: Any) -> Any:
    """A cell as a JSON-serializable Python scalar (pandas / numpy missing values -> null)."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def feature_collection(
    frame: gpd.GeoDataFrame,
    *,
    key: str,
    decimals: int,
    members: Mapping[str, Any],
) -> dict[str, Any]:
    """A FeatureCollection over ``frame`` (already in WGS 84), one feature per row, with the
    row's non-geometry columns as properties, ``key`` as the feature ID, and ``members`` as
    top-level foreign members (the license label among them)."""
    columns = [column for column in frame.columns if column != frame.geometry.name]
    features = []
    for _, row in frame.iterrows():
        geometry = row[frame.geometry.name]
        features.append(
            {
                "type": "Feature",
                "id": _plain(row[key]),
                "geometry": None if geometry is None else geometry_member(geometry, decimals),
                "properties": {column: _plain(row[column]) for column in columns},
            }
        )
    return {"type": "FeatureCollection", **dict(members), "features": features}


def json_bytes(payload: Any) -> bytes:
    """Canonical JSON for public files: sorted keys, compact separators, UTF-8, no NaN."""
    text = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    return (text + "\n").encode("utf-8")


# --- widening the analytic table --------------------------------------------------------


def column_name(metric_id: str, category: str | None, mode: str | None) -> str:
    """The public column for a tract-metric: ``<metric_id>[__<category>][__<mode>]``."""
    return "__".join(part for part in (metric_id, category, mode) if part)


def _optional(value: Any) -> str | None:
    return None if value is None or (isinstance(value, float) and np.isnan(value)) else str(value)


def widen(
    metrics: pd.DataFrame, descriptions: Mapping[str, str]
) -> tuple[pd.DataFrame, list[dict]]:
    """The analytic table (long: one row per tract x metric) as one wide row per tract, plus the
    field records the manifest publishes (column, metric, category, mode, description, QA flag).

    Every metric ID must have a description (a published field without one is a
    :class:`PublishError`), and a tract may carry each tract-metric at most once.
    """
    violations = check_frame(ANALYTIC_TABLE, metrics)
    if violations:
        raise PublishError(
            f"analytic table breaks its contract: {'; '.join(str(v) for v in violations)}"
        )
    keys = sorted(
        {
            (str(row.metric_id), _optional(row.category), _optional(row.mode))
            for row in metrics.itertuples(index=False)
        },
        key=lambda k: (k[0], k[1] or "", k[2] or ""),
    )
    missing = sorted({k[0] for k in keys} - set(descriptions))
    if missing:
        raise PublishError(f"no description for published metric(s) {missing}")
    wide = pd.DataFrame(index=pd.Index(sorted(metrics["geoid"].astype(str).unique()), name="geoid"))
    fields: list[dict[str, Any]] = []
    category_col = metrics["category"].map(_optional)
    mode_col = metrics["mode"].map(_optional)

    def _matches(column: pd.Series, value: str | None) -> pd.Series:
        # A null key must match null cells; `== None` is all-false in pandas.
        return column.isna() if value is None else column == value

    for metric_id, category, mode in keys:
        mask = (
            (metrics["metric_id"].astype(str) == metric_id)
            & _matches(category_col, category)
            & _matches(mode_col, mode)
        )
        subset = metrics[mask].copy()
        subset["geoid"] = subset["geoid"].astype(str)
        if subset["geoid"].duplicated().any():
            raise PublishError(
                f"tract-metric {(metric_id, category, mode)} occurs twice for a tract"
            )
        subset = subset.set_index("geoid")
        column = column_name(metric_id, category, mode)
        wide[column] = subset["estimate"].astype("float64").reindex(wide.index)
        wide[f"{column}_moe"] = subset["moe"].astype("float64").reindex(wide.index)
        wide[f"{column}_cv_tier"] = subset["cv_tier"].astype("Int64").reindex(wide.index)
        wide[f"{column}_reliability_action"] = (
            subset["reliability_action"].astype("string").reindex(wide.index)
        )
        fields.append(
            {
                "column": column,
                "metric_id": metric_id,
                "category": category,
                "mode": mode,
                "qa_only": metric_id.startswith(QA_PREFIX),
                "description": str(descriptions[metric_id]),
            }
        )
    return wide, fields


# --- provenance -----------------------------------------------------------------------------


def source_records(
    snapshots: Mapping[str, Path], citations: Mapping[str, str]
) -> list[dict[str, Any]]:
    """What the public manifest records per source: read from each raw snapshot's manifest,
    plus the citation the adapter (or the fixture) declares. Never a path."""
    records = []
    for source in sorted(snapshots):
        manifest = read_manifest(snapshots[source]).to_dict()
        citation = str(citations.get(source, "")).strip()
        if not citation:
            raise PublishError(f"source {source!r} has no citation to publish")
        records.append(
            {
                "source": manifest["source"],
                "snapshot_id": manifest["snapshot_id"],
                "license_bucket": manifest["license_bucket"],
                "license_note": manifest["license_note"],
                "synthetic": bool(manifest["synthetic"]),
                "citation": citation,
            }
        )
    return records


# --- the zone ------------------------------------------------------------------------------


def _unique(metrics: pd.DataFrame, column: str) -> Any:
    values = sorted(set(metrics[column].tolist()))
    if len(values) != 1:
        raise PublishError(
            f"analytic table carries {len(values)} distinct {column} values: {values[:3]}"
        )
    return values[0]


def build_public_zone(
    out: Path,
    *,
    pipeline: str,
    metrics: pd.DataFrame,
    spine: gpd.GeoDataFrame,
    sites: gpd.GeoDataFrame,
    sources: list[dict[str, Any]],
    descriptions: Mapping[str, str],
    bounds: tuple[float, float, float, float],
    decimals: int = COORDINATE_DECIMALS,
    classes: int = binning.BIN_CLASSES,
    method: str = binning.BIN_METHOD,
) -> dict[str, Any]:
    """Write the whole public zone into ``out`` (an existing, empty directory) and gate it.

    Returns the public manifest. Raises :class:`PublishError` for inputs that cannot be
    published and :class:`~phillysim.publish.gate.PublishGateError` if the written zone
    fails the gate (in which case the caller must not install it).
    """
    if not sources:
        raise PublishError("a public zone needs at least one source to derive its bucket from")
    methods_version = str(_unique(metrics, "methods_version"))
    schema_version = int(_unique(metrics, "schema_version"))
    wide, fields = widen(metrics, descriptions)

    # Tracts: the spine's public columns, the wide metrics, then the build-time bins.
    missing = [column for column in TRACT_BASE_COLUMNS if column not in spine.columns]
    if missing:
        raise PublishError(f"spine lacks public column(s) {missing}")
    stray = sorted(set(wide.index) - set(spine["geoid"].astype(str)))
    if stray:
        raise PublishError(f"{len(stray)} metric tract(s) not in the spine: {stray[:5]}")
    tracts = pd.DataFrame(spine[list(TRACT_BASE_COLUMNS)]).copy()
    tracts["geoid"] = tracts["geoid"].astype(str)
    tracts = gpd.GeoDataFrame(tracts, geometry=spine.geometry.to_numpy(), crs=spine.crs).to_crs(
        PUBLIC_CRS
    )
    tracts = tracts.sort_values("geoid").reset_index(drop=True)
    bins: dict[str, Any] = {}
    columns: list[str] = list(TRACT_BASE_COLUMNS)
    for field in fields:
        column = field["column"]
        for companion in ("", *FIELD_COMPANIONS[:-1]):
            name = column if not companion else f"{column}_{companion}"
            tracts[name] = wide[name].reindex(tracts["geoid"]).to_numpy()
            columns.append(name)
        edges = binning.bin_edges(tracts[column], classes, method)
        tracts[f"{column}_bin"] = binning.assign_bins(tracts[column], edges).to_numpy()
        columns.append(f"{column}_bin")
        bins[column] = binning.bin_record(edges, classes, method)
    tracts = tracts[[*columns, "geometry"]]

    # Sites: the facility points, keyed by site ID, coordinates in WGS 84.
    missing = [column for column in SITE_COLUMNS if column not in sites.columns]
    if missing:
        raise PublishError(f"sites lack public column(s) {missing}")
    if sites["site_id"].duplicated().any():
        raise PublishError("duplicate site IDs in the public sites")
    points = gpd.GeoDataFrame(
        pd.DataFrame(sites[list(SITE_COLUMNS)]).copy(),
        geometry=sites.geometry.to_numpy(),
        crs=sites.crs,
    ).to_crs(PUBLIC_CRS)
    for column in SITE_COLUMNS:
        points[column] = points[column].astype("string")
    points = points.sort_values("site_id").reset_index(drop=True)
    points["longitude"] = points.geometry.x.round(decimals)
    points["latitude"] = points.geometry.y.round(decimals)
    points = points[[*SITE_CSV_COLUMNS, "geometry"]]

    # Labels: derived from the sources, identical for every file of the zone.
    bucket = derive_bucket(record["license_bucket"] for record in sources)
    label = label_of(bucket).payload()
    attribution = list(dict.fromkeys(record["citation"] for record in sources))
    source_names = [record["source"] for record in sources]
    members = {
        "license": label,
        "attribution": attribution,
        "pipeline": pipeline,
        "schema_version": schema_version,
        "public_schema_version": PUBLIC_SCHEMA_VERSION,
        "methods_version": methods_version,
    }

    payloads: dict[str, tuple[str, str, int, bytes]] = {}  # name -> (table, format, rows, bytes)
    payloads[TRACTS_GEOJSON] = (
        "tracts",
        "geojson",
        len(tracts),
        json_bytes(
            feature_collection(
                tracts, key="geoid", decimals=decimals, members={**members, "table": "tracts"}
            )
        ),
    )
    payloads[TRACTS_CSV] = (
        "tracts",
        "csv",
        len(tracts),
        csv_bytes(tracts.drop(columns=["geometry"])),
    )
    payloads[SITES_GEOJSON] = (
        "sites",
        "geojson",
        len(points),
        json_bytes(
            feature_collection(
                points.drop(columns=["longitude", "latitude"]),
                key="site_id",
                decimals=decimals,
                members={**members, "table": "sites"},
            )
        ),
    )
    payloads[SITES_CSV] = (
        "sites",
        "csv",
        len(points),
        csv_bytes(points.drop(columns=["geometry"])),
    )

    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {}
    for name, (table, fmt, rows, data) in payloads.items():
        (out / name).write_bytes(data)
        files[name] = {
            "table": table,
            "format": fmt,
            "rows": rows,
            "bucket": bucket,
            "license": label,
            "attribution": attribution,
            "sources": source_names,
            "sha256": sha256_file(out / name),
            "bytes": len(data),
        }
    manifest: dict[str, Any] = {
        **members,
        "crs": PUBLIC_CRS,
        "bounds": [float(b) for b in bounds],
        "coordinate_decimals": int(decimals),
        "sources": sources,
        "fields": fields,
        "bins": bins,
        "columns": {"tracts": columns, "sites": list(SITE_CSV_COLUMNS)},
        "files": files,
    }
    if any(field["qa_only"] for field in fields):
        manifest["qa_note"] = QA_NOTE
    (out / PUBLIC_MANIFEST).write_bytes(json_bytes(manifest))

    problems = check_public_zone(out, bounds=bounds)
    if problems:
        raise PublishGateError(problems)
    return manifest


def publish_zone(
    ctx: StageContext,
    *,
    pipeline: str,
    metrics: pd.DataFrame,
    spine: gpd.GeoDataFrame,
    sites: gpd.GeoDataFrame,
    raw_snapshots: Mapping[str, str],
    citations: Mapping[str, str],
    descriptions: Mapping[str, str],
) -> dict[str, Any]:
    """The ``publish`` stage body shared by both pipelines: provenance from the declared raw
    snapshot inputs, parameters from the stage, the zone written to the stage's single
    output (the ``public`` directory, installed atomically by the runner)."""
    if int(ctx.params["public_schema_version"]) != PUBLIC_SCHEMA_VERSION:
        raise PublishError(
            f"stage parameter public_schema_version {ctx.params['public_schema_version']!r} != "
            f"this exporter's {PUBLIC_SCHEMA_VERSION}"
        )
    sources = source_records(
        {source: ctx.input(rel) for source, rel in raw_snapshots.items()}, citations
    )
    ctx.checkpoint()
    out = ctx.output(PUBLIC_ZONE)
    out.mkdir(parents=True, exist_ok=True)
    return build_public_zone(
        out,
        pipeline=pipeline,
        metrics=metrics,
        spine=spine,
        sites=sites,
        sources=sources,
        descriptions=descriptions,
        bounds=tuple(float(b) for b in ctx.params["bounds"]),  # type: ignore[arg-type]
        decimals=int(ctx.params["coordinate_decimals"]),
        classes=int(ctx.params["bin_classes"]),
        method=str(ctx.params["bin_method"]),
    )
