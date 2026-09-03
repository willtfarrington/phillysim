"""The publish gate: what must hold for a public zone before it leaves curated (ADR-0003;
architecture.md "Security"; docs/CLAIMS.md).

:func:`check_public_zone` inspects a directory that claims to be a public zone
and returns every violation it finds (an empty list means green). It reads the
files as a stranger would (bytes on disk, the manifest as JSON), never the
pipeline's own objects, so the same function gates a freshly staged zone
inside the ``publish`` stage and, through ``phillysim gate``, an installed one
in CI or before a release. The checks:

1. **Registry.** ``manifest.json`` parses; every file in the directory is
   listed with a matching SHA-256 and size; nothing listed is missing; no
   subdirectories.
2. **License labels.** Every file's bucket is valid *and equals the bucket
   derived from its sources' buckets* (Bucket B is contagious); its license
   label is the bucket's; Bucket B files carry the ODbL and OpenStreetMap
   notices; attribution is present and covers every source; every GeoJSON
   file carries the same label in-file.
3. **Geometry.** GeoJSON is a FeatureCollection with no ``crs`` member (RFC
   7946: WGS 84 only); every feature has a geometry, and every coordinate is
   a valid longitude / latitude inside the manifest's declared bounds (which,
   when the caller supplies bounds, must be those).
4. **Untrusted text.** No CSV cell starts with a formula character
   (``= + @``, tab, carriage return, or ``-`` unless the cell is a plain
   number).
5. **No path leakage.** No file mentions a pipeline zone path, the state
   file, or an absolute path (drive letters, home directories).
6. **Vocabulary.** Column and property names are lowercase slugs and carry
   none of the terms the claims matrix prohibits (no "healthy", "score",
   "rank", "index", "desert", ...); every ``qa_`` column is declared QA-only
   with a description that says so, and the manifest carries the QA note.
7. **Parity.** A table published in two formats has the same rows in both
   (same keys, same count), and the CSV header is the manifest's column list.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

from phillysim.contracts import LICENSE_BUCKETS
from phillysim.publish.bucket import BUCKET_B, OSM_NOTICE, derive_bucket, label_of
from phillysim.stages import StageError

PUBLIC_MANIFEST = "manifest.json"
PUBLIC_CRS = "EPSG:4326"
REQUIRED_MANIFEST_KEYS: tuple[str, ...] = (
    "pipeline",
    "schema_version",
    "public_schema_version",
    "methods_version",
    "license",
    "attribution",
    "crs",
    "bounds",
    "coordinate_decimals",
    "sources",
    "fields",
    "bins",
    "columns",
    "files",
)
FORMATS: frozenset[str] = frozenset({"geojson", "csv"})
GEOMETRY_TYPES: frozenset[str] = frozenset(
    {"Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"}
)
TABLE_KEYS: dict[str, str] = {"tracts": "geoid", "sites": "site_id"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
NUMBER_RE = re.compile(r"^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
QA_PREFIX = "qa_"

#: Terms the claims matrix keeps out of project-derived names (C-1, C-2, C-3): no
#: nutrition-quality adjectives, no "food desert", no scores / ranks / indices.
PROHIBITED_NAME_TERMS: tuple[str, ...] = (
    "healthy",
    "unhealthy",
    "nutritious",
    "quality",
    "desert",
    "insecur",
    "score",
    "rank",
    "index",
)

#: Text that must not appear in any public file: pipeline zone paths, the state file,
#: absolute paths. The drive-letter pattern excludes URL schemes (``https://``).
LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (label, re.compile(pattern))
    for label, pattern in (
        ("raw zone path", r"\braw/"),
        ("intermediate zone path", r"\bintermediate/"),
        ("curated zone path", r"\bcurated/"),
        ("quarantine zone path", r"\bquarantine/"),
        ("cache zone path", r"\bcache/"),
        ("state file", r"pipeline_state\.json"),
        ("drive-letter path", r"(?<![A-Za-z])[A-Za-z]:[\\/]"),
        ("home directory path", r"(?<![A-Za-z0-9])/(home|Users)/"),
        ("backslash path", r"\\\\"),
    )
)
CSV_DANGEROUS_PREFIXES: tuple[str, ...] = ("=", "+", "@", "\t", "\r")


class PublishGateError(StageError):
    """The public zone failed the gate; nothing may leave the curated zone."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        super().__init__(f"publish gate: {len(problems)} violation(s): " + "; ".join(self.problems))


def enforce_gate(problems: list[str]) -> None:
    if problems:
        raise PublishGateError(problems)


# --- helpers ---------------------------------------------------------------------------------


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _coordinates(coords: Any):
    """Every position in a GeoJSON coordinates array, however deeply nested."""
    if isinstance(coords, list) and coords and _is_number(coords[0]):
        yield coords
    elif isinstance(coords, list):
        for part in coords:
            yield from _coordinates(part)


def _check_name(name: Any, where: str) -> list[str]:
    if not isinstance(name, str) or not NAME_RE.match(name):
        return [f"{where}: name {name!r} is not a lowercase slug"]
    hits = [term for term in PROHIBITED_NAME_TERMS if term in name]
    if hits:
        return [f"{where}: name {name!r} carries prohibited term(s) {hits} (docs/CLAIMS.md)"]
    return []


def _check_cell(cell: str) -> bool:
    """True when the CSV cell is safe: no formula prefix, ``-`` only on a plain number."""
    if not cell:
        return True
    if cell[0] in CSV_DANGEROUS_PREFIXES:
        return False
    if cell[0] == "-":
        return bool(NUMBER_RE.match(cell))
    return True


def check_bounds_value(bounds: Any) -> list[str]:
    if (
        not isinstance(bounds, list)
        or len(bounds) != 4
        or not all(_is_number(b) for b in bounds)
        or not (-180 <= bounds[0] < bounds[2] <= 180 and -90 <= bounds[1] < bounds[3] <= 90)
    ):
        return [f"manifest bounds {bounds!r} are not [minx, miny, maxx, maxy] in degrees"]
    return []


# --- the gate ------------------------------------------------------------------------------


def check_public_zone(
    public: Path, *, bounds: tuple[float, float, float, float] | None = None
) -> list[str]:
    """Every violation in the public zone at ``public`` (empty list = the gate is green).

    ``bounds``: when given, the manifest's declared bounds must equal these (the pipeline's
    own bounds parameter, so a zone cannot declare bounds of its choosing).
    """
    problems: list[str] = []
    if not public.is_dir():
        return [f"public zone {public.name!r} is not a directory"]
    manifest_path = public / PUBLIC_MANIFEST
    if not manifest_path.is_file():
        return [f"public zone has no {PUBLIC_MANIFEST}"]
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{PUBLIC_MANIFEST} is not valid JSON: {type(exc).__name__}"]
    if not isinstance(manifest, dict):
        return [f"{PUBLIC_MANIFEST} is not a JSON object"]
    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        return [f"{PUBLIC_MANIFEST} lacks required key(s) {missing}"]

    # 1. Registry: the manifest and the directory agree.
    files = manifest["files"]
    if not isinstance(files, dict) or not files:
        return [f"{PUBLIC_MANIFEST} lists no files"]
    on_disk = sorted(entry.name for entry in public.iterdir())
    for entry in public.iterdir():
        if not entry.is_file():
            problems.append(f"public zone holds a non-file entry {entry.name!r}")
    listed = sorted(files)
    for name in listed:
        if not isinstance(name, str) or any(sep in name for sep in "/\\:") or name.startswith("."):
            problems.append(f"{PUBLIC_MANIFEST} lists an invalid file name {name!r}")
        elif name == PUBLIC_MANIFEST:
            problems.append(f"{PUBLIC_MANIFEST} lists itself")
    unlisted = sorted(set(on_disk) - set(listed) - {PUBLIC_MANIFEST})
    if unlisted:
        problems.append(f"unlisted file(s) in the public zone: {unlisted}")
    absent = sorted(set(listed) - set(on_disk))
    if absent:
        problems.append(f"listed file(s) missing from the public zone: {absent}")
    if problems:
        return problems

    # Manifest-level facts the file checks rely on.
    if manifest["crs"] != PUBLIC_CRS:
        problems.append(f"manifest crs is {manifest['crs']!r}, expected {PUBLIC_CRS}")
    problems += check_bounds_value(manifest["bounds"])
    declared_bounds = manifest["bounds"] if not problems else None
    if bounds is not None and declared_bounds is not None:
        if [round(float(b), 9) for b in declared_bounds] != [round(float(b), 9) for b in bounds]:
            problems.append(
                f"manifest bounds {declared_bounds} differ from the pipeline's {list(bounds)}"
            )
    sources = manifest["sources"]
    source_buckets: dict[str, str] = {}
    citations: dict[str, str] = {}
    if not isinstance(sources, list) or not sources:
        problems.append("manifest lists no sources")
        sources = []
    for record in sources:
        if not isinstance(record, dict) or not {
            "source",
            "snapshot_id",
            "license_bucket",
            "citation",
        } <= set(record):
            problems.append(f"malformed source record {record!r}")
            continue
        name = str(record["source"])
        if name in source_buckets:
            problems.append(f"source {name!r} listed twice")
        if record["license_bucket"] not in LICENSE_BUCKETS:
            problems.append(
                f"source {name!r} has invalid license bucket {record['license_bucket']!r}"
            )
            continue
        if not str(record["citation"]).strip():
            problems.append(f"source {name!r} has no citation")
        source_buckets[name] = str(record["license_bucket"])
        citations[name] = str(record["citation"])
    fields = manifest["fields"] if isinstance(manifest["fields"], list) else []
    if not isinstance(manifest["fields"], list):
        problems.append("manifest fields is not a list")
    field_columns: set[str] = set()
    for field in fields:
        if not isinstance(field, dict) or not {
            "column",
            "metric_id",
            "qa_only",
            "description",
        } <= set(field):
            problems.append(f"malformed field record {field!r}")
            continue
        column = str(field["column"])
        field_columns.add(column)
        problems += _check_name(column, "manifest field")
        problems += _check_name(str(field["metric_id"]), "manifest field metric_id")
        if not str(field["description"]).strip():
            problems.append(f"field {column!r} has no description")
        if column.startswith(QA_PREFIX) and field["qa_only"] is not True:
            problems.append(f"field {column!r} is a QA column but not declared qa_only")
        if field["qa_only"] is True and "QA" not in str(field["description"]):
            problems.append(f"QA-only field {column!r} has a description that does not say so")
    if (
        any(isinstance(f, dict) and f.get("qa_only") is True for f in fields)
        and not str(manifest.get("qa_note", "")).strip()
    ):
        problems.append("manifest publishes QA-only field(s) without the QA note")
    bins = manifest["bins"]
    if not isinstance(bins, dict):
        problems.append("manifest bins is not an object")
    else:
        for column, record in bins.items():
            if column not in field_columns:
                problems.append(f"bins for {column!r}, which is not a published field")
            edges = record.get("edges") if isinstance(record, dict) else None
            if not isinstance(edges, list) or any(not _is_number(e) for e in edges):
                problems.append(f"bins for {column!r} have no numeric edges")
            elif any(b <= a for a, b in zip(edges, edges[1:], strict=False)):
                problems.append(f"bins for {column!r} have non-increasing edges")
        for column in sorted(field_columns - set(bins)):
            problems.append(f"published field {column!r} has no bins")
    columns = manifest["columns"] if isinstance(manifest["columns"], dict) else {}
    if not isinstance(manifest["columns"], dict):
        problems.append("manifest columns is not an object")
    for table, names in columns.items():
        if not isinstance(names, list):
            problems.append(f"manifest columns for {table!r} is not a list")
            continue
        for name in names:
            problems += _check_name(name, f"manifest columns[{table!r}]")
        if table in TABLE_KEYS and TABLE_KEYS[table] not in names:
            problems.append(f"table {table!r} columns lack its key {TABLE_KEYS[table]!r}")
        for column in sorted(field_columns):
            if table == "tracts" and column not in names:
                problems.append(f"published field {column!r} is not a tracts column")

    # 5. The manifest is a public file too: it must leak no path either.
    for label, pattern in LEAK_PATTERNS:
        if pattern.search(manifest_path.read_text("utf-8")):
            problems.append(f"file {PUBLIC_MANIFEST!r}: contains a {label}")

    # 2.-7. Per file.
    keys_seen: dict[tuple[str, str], tuple[int, set[str]]] = {}
    for name in listed:
        entry = files[name]
        path = public / name
        where = f"file {name!r}"
        if not isinstance(entry, dict) or not {
            "table",
            "format",
            "rows",
            "bucket",
            "license",
            "attribution",
            "sources",
            "sha256",
            "bytes",
        } <= set(entry):
            problems.append(f"{where}: malformed manifest entry")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
            problems.append(f"{where}: content does not match its recorded digest / size")
        for label, pattern in LEAK_PATTERNS:
            if pattern.search(data.decode("utf-8", errors="replace")):
                problems.append(f"{where}: contains a {label}")
        # License labels.
        bucket = entry["bucket"]
        if bucket not in LICENSE_BUCKETS:
            problems.append(f"{where}: invalid license bucket {bucket!r}")
            continue
        file_sources = entry["sources"] if isinstance(entry["sources"], list) else []
        unknown = sorted(set(map(str, file_sources)) - set(source_buckets))
        if unknown or not file_sources:
            problems.append(
                f"{where}: sources {file_sources!r} are not (all) in the manifest's sources"
            )
        else:
            required = derive_bucket(source_buckets[str(s)] for s in file_sources)
            if bucket != required:
                problems.append(
                    f"{where}: labeled Bucket {bucket} but its sources require Bucket {required}"
                )
            expected_attribution = [citations[str(s)] for s in file_sources]
            if set(map(str, entry["attribution"])) != set(expected_attribution):
                problems.append(f"{where}: attribution does not cover exactly its sources")
        expected_label = label_of(bucket).payload()
        if entry["license"] != expected_label:
            problems.append(f"{where}: license label is not the Bucket {bucket} label")
        if bucket == BUCKET_B and OSM_NOTICE not in entry["license"].get("notices", []):
            problems.append(f"{where}: Bucket B file lacks the notice {OSM_NOTICE!r}")
        if not entry["attribution"]:
            problems.append(f"{where}: no attribution")
        # Format-specific checks.
        fmt, table = entry["format"], entry["table"]
        if fmt not in FORMATS:
            problems.append(f"{where}: unknown format {fmt!r}")
            continue
        key_column = TABLE_KEYS.get(str(table))
        if fmt == "geojson":
            rows, keys, found = _check_geojson(
                name, data, entry, manifest, declared_bounds, key_column
            )
        else:
            rows, keys, found = _check_csv(name, data, entry, columns.get(str(table)), key_column)
        problems += found
        if rows is not None and rows != entry["rows"]:
            problems.append(f"{where}: {rows} row(s) on disk, manifest says {entry['rows']}")
        if keys is not None:
            keys_seen[(str(table), name)] = (rows or 0, keys)
    # Parity between the formats of one table.
    by_table: dict[str, list[tuple[str, int, set[str]]]] = {}
    for (table, name), (rows, keys) in keys_seen.items():
        by_table.setdefault(table, []).append((name, rows, keys))
    for table, entries in by_table.items():
        first_name, first_rows, first_keys = entries[0]
        for name, rows, keys in entries[1:]:
            if rows != first_rows or keys != first_keys:
                problems.append(
                    f"table {table!r}: {name!r} and {first_name!r} do not hold the same rows"
                )
    return problems


def _check_geojson(
    name: str,
    data: bytes,
    entry: dict[str, Any],
    manifest: dict[str, Any],
    bounds: list[float] | None,
    key_column: str | None,
) -> tuple[int | None, set[str] | None, list[str]]:
    where = f"file {name!r}"
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, None, [f"{where}: not valid JSON: {type(exc).__name__}"]
    problems: list[str] = []
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        return None, None, [f"{where}: not a GeoJSON FeatureCollection"]
    if "crs" in payload:
        problems.append(f"{where}: carries a 'crs' member (RFC 7946 GeoJSON is WGS 84 only)")
    if payload.get("license") != entry["license"]:
        problems.append(f"{where}: in-file license label differs from the manifest's")
    if payload.get("attribution") != entry["attribution"]:
        problems.append(f"{where}: in-file attribution differs from the manifest's")
    if payload.get("table") != entry["table"]:
        problems.append(f"{where}: in-file table {payload.get('table')!r} != {entry['table']!r}")
    for member in ("pipeline", "schema_version", "methods_version"):
        if payload.get(member) != manifest[member]:
            problems.append(f"{where}: in-file {member} differs from the manifest's")
    features = payload.get("features")
    if not isinstance(features, list):
        return None, None, problems + [f"{where}: no features array"]
    keys: set[str] = set()
    names_checked: set[str] = set()
    bad_geometry = bad_coords = missing_key = 0
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            bad_geometry += 1
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in GEOMETRY_TYPES:
            bad_geometry += 1
        else:
            for position in _coordinates(geometry.get("coordinates")):
                if len(position) < 2 or not (
                    -180 <= position[0] <= 180 and -90 <= position[1] <= 90
                ):
                    bad_coords += 1
                elif bounds is not None and not (
                    bounds[0] <= position[0] <= bounds[2] and bounds[1] <= position[1] <= bounds[3]
                ):
                    bad_coords += 1
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            bad_geometry += 1
            continue
        for prop in properties:
            if prop not in names_checked:
                names_checked.add(prop)
                problems += _check_name(prop, f"{where} property")
        if key_column is not None:
            key = properties.get(key_column)
            if not isinstance(key, str) or not key or feature.get("id") != key:
                missing_key += 1
            else:
                keys.add(key)
    if bad_geometry:
        problems.append(f"{where}: {bad_geometry} feature(s) malformed or without a geometry")
    if bad_coords:
        problems.append(
            f"{where}: {bad_coords} position(s) outside WGS 84 range or the declared bounds"
        )
    if missing_key:
        problems.append(f"{where}: {missing_key} feature(s) without a {key_column!r} key / id")
    if key_column is not None and len(keys) != len(features) - missing_key:
        problems.append(f"{where}: duplicate {key_column!r} keys")
    return len(features), (keys if key_column is not None else None), problems


def _check_csv(
    name: str,
    data: bytes,
    entry: dict[str, Any],
    columns: list[str] | None,
    key_column: str | None,
) -> tuple[int | None, set[str] | None, list[str]]:
    where = f"file {name!r}"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, None, [f"{where}: not UTF-8"]
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows:
        return None, None, [f"{where}: empty CSV"]
    header, body = rows[0], [row for row in rows[1:] if row]
    problems: list[str] = []
    for column in header:
        problems += _check_name(column, f"{where} header")
    if columns is not None and header != list(columns):
        problems.append(
            f"{where}: header differs from the manifest's column list for {entry['table']!r}"
        )
    unsafe = sum(1 for row in body for cell in row if not _check_cell(cell))
    if unsafe:
        problems.append(f"{where}: {unsafe} cell(s) start with a spreadsheet formula character")
    ragged = sum(1 for row in body if len(row) != len(header))
    if ragged:
        problems.append(
            f"{where}: {ragged} row(s) with a different number of cells than the header"
        )
    keys: set[str] | None = None
    if key_column is not None and key_column in header:
        index = header.index(key_column)
        values = [row[index] for row in body if len(row) > index]
        keys = set(values)
        if len(keys) != len(values) or "" in keys:
            problems.append(f"{where}: {key_column!r} keys are not unique and non-empty")
    return len(body), keys, problems
