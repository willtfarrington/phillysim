"""OpenStreetMap extract for Pennsylvania from Geofabrik (source ``osm_network``; EP-12).

**Stored as delivered, clipped at the ``network`` stage.** Geofabrik publishes
a daily extract per region as a PBF file; ADR-0008 pins the **dated** file
``pennsylvania-260831.osm.pbf`` (generated 2026-09-01, data current to the
replication timestamp its header records) rather than the ``-latest`` file,
whose bytes change every day. Geofabrik defines no sub-region for
Pennsylvania, so the state file is what exists. The file is kept
byte-for-byte in the raw zone beside Geofabrik's own MD5 sidecar
(``<file>.md5``, fetched through the same guarded path and compared against
the file before admission; the adapter also pins that MD5, so a replaced
file under the same name is a stop), and the region page in force is
archived as ``terms.html`` and checked for the two phrases its footer
carries: "created by OpenStreetMap Contributors" and "License: ODbL".

A PBF is not an archive: the download path applies the file cap only and
never opens it as a zip. :func:`read` (what ``validate`` checks) opens the
file's header only and returns a one-row summary: size, the pinned and the
sidecar MD5, the writing program, the replication timestamp, the header
bounding box (which must enclose the county bounds), and the sorting. The
county filter is the **clip** (:func:`clip`): every way with at least one
node inside the routing box (the county bounds buffered by 5 km in the
analysis CRS, ADR-0008) is kept with all of its nodes (R5 needs complete
ways), turn-restriction relations whose members are all kept are kept, and
the result is written in the source file's order with the box in its
header. Every file computed over the clip is **Bucket B** by derivation
(ADR-0003); the state extract itself never leaves the raw zone.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import osmium
import osmium.filter
import osmium.io
import osmium.osm
import pandas as pd

from phillysim.adapters.base import COUNTY_BOUNDS, Adapter
from phillysim.contracts import ColumnSpec, SourceContract
from phillysim.download import Fetch, SnapshotSpec, digest_file, read_md5_sidecar
from phillysim.guards import Limits

SOURCE = "osm_network"
REGION = "pennsylvania"
#: The dated extract (YYMMDD of the OSM data date) pinned by ADR-0008.
EXTRACT_DATE = "260831"
STEM = f"{REGION}-{EXTRACT_DATE}"
#: The extract's OSM data date as an ISO date.
OSM_DATA_DATE = f"20{EXTRACT_DATE[:2]}-{EXTRACT_DATE[2:4]}-{EXTRACT_DATE[4:]}"
FILE_NAME = f"{STEM}.osm.pbf"
MD5_FILE = f"{FILE_NAME}.md5"
BASE_URL = "https://download.geofabrik.de/north-america/us/"
URL = BASE_URL + FILE_NAME
MD5_URL = BASE_URL + MD5_FILE
#: The provider's MD5 of the pinned file, from its sidecar on 2026-09-03 (ADR-0008).
PROVIDER_MD5 = "a779d2ef14c8addce6eac207ab9cd851"
PROVIDER_BYTES = 345_912_530
TERMS_URL = BASE_URL + f"{REGION}.html"
TERMS_FILE = "terms.html"
#: The region page's footer, verbatim in its visible text.
TERMS_PHRASES: tuple[str, ...] = ("created by OpenStreetMap Contributors", "License: ODbL")
ALLOWLIST: tuple[str, ...] = ("download.geofabrik.de",)
#: The state extract is about 346 MB and not an archive: the file cap is the only guard
#: that applies to it (the archive limits are declared, never exercised on a PBF).
LIMITS = Limits(
    max_file_bytes=1024**3,
    max_extracted_bytes=1024**3,
    max_compression_ratio=50.0,
    max_members=50,
)
#: What the OSM data date and the clip are described as in every note and card.
OSM_ATTRIBUTION = "© OpenStreetMap contributors"
ODBL = (
    "Open Database License (ODbL) 1.0 (https://opendatacommons.org/licenses/odbl/1-0/); "
    "data © OpenStreetMap contributors; extract processed and published by Geofabrik GmbH"
)
#: The header's sorting field for a Geofabrik extract (the clip keeps that order).
SORTING = "Type_then_ID"
#: The tag that makes a way part of the street network (R5 reads highway ways).
HIGHWAY = "highway"
RESTRICTION = "restriction"

SPEC = SnapshotSpec(
    source=SOURCE,
    acquisition_url=URL,
    files=(
        Fetch(URL, FILE_NAME, digest=f"md5:{PROVIDER_MD5}"),
        Fetch(MD5_URL, MD5_FILE, md5_of=FILE_NAME),
    ),
    terms=Fetch(TERMS_URL, TERMS_FILE),
    terms_must_contain=TERMS_PHRASES,
    allowlist=ALLOWLIST,
    limits=LIMITS,
    license_bucket="B",
    license_note=(
        f"{ODBL}. Geofabrik dated Pennsylvania extract {FILE_NAME} (OSM data of "
        f"{OSM_DATA_DATE}, provider MD5 {PROVIDER_MD5}), stored as delivered; every output "
        "computed over it is Bucket B by derivation (ADR-0003) and carries the ODbL notice "
        f'and "{OSM_ATTRIBUTION}".'
    ),
)

#: What :func:`read` returns: one row describing the delivered file and its header.
SUMMARY_COLUMNS: tuple[str, ...] = (
    "file",
    "bytes",
    "md5",
    "md5_pinned",
    "md5_sidecar",
    "sidecar_match",
    "generator",
    "replication_timestamp",
    "sorting",
    "bbox_min_lon",
    "bbox_min_lat",
    "bbox_max_lon",
    "bbox_max_lat",
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("file", "str", nullable=False, allowed=frozenset({FILE_NAME})),
        ColumnSpec("bytes", "int", nullable=False, minimum=1, maximum=LIMITS.max_file_bytes),
        ColumnSpec("md5", "str", nullable=False, pattern=r"[0-9a-f]{32}"),
        ColumnSpec("md5_pinned", "str", nullable=False, pattern=r"[0-9a-f]{32}"),
        ColumnSpec("md5_sidecar", "str", nullable=False, pattern=r"[0-9a-f]{32}"),
        # 1 when the file's MD5 equals the provider's sidecar (the second check, at read).
        ColumnSpec("sidecar_match", "int", nullable=False, minimum=1, maximum=1),
        ColumnSpec("generator", "str", nullable=False),
        ColumnSpec(
            "replication_timestamp",
            "str",
            nullable=False,
            pattern=r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        ),
        ColumnSpec("sorting", "str", nullable=False, allowed=frozenset({SORTING})),
        # The header box must enclose the county bounds: the right region, whole.
        ColumnSpec("bbox_min_lon", "float", nullable=False, maximum=COUNTY_BOUNDS[0]),
        ColumnSpec("bbox_min_lat", "float", nullable=False, maximum=COUNTY_BOUNDS[1]),
        ColumnSpec("bbox_max_lon", "float", nullable=False, minimum=COUNTY_BOUNDS[2]),
        ColumnSpec("bbox_max_lat", "float", nullable=False, minimum=COUNTY_BOUNDS[3]),
    ),
    key="file",
    license_buckets=frozenset({"B"}),
    min_rows=1,
    max_rows=1,
)


def read_header(path: Path) -> dict[str, Any]:
    """The PBF header: generator, replication timestamp, sorting, and bounding box."""
    reader = osmium.io.Reader(str(path), osmium.osm.NOTHING)
    try:
        header = reader.header()
        box = header.box()
        return {
            "generator": header.get("generator"),
            "replication_timestamp": header.get("osmosis_replication_timestamp"),
            "sorting": header.get("sorting"),
            "box_valid": bool(box.valid()),
            "bbox": (
                box.bottom_left.lon,
                box.bottom_left.lat,
                box.top_right.lon,
                box.top_right.lat,
            )
            if box.valid()
            else None,
        }
    finally:
        reader.close()


def read(snapshot_dir: Path) -> pd.DataFrame:
    """One row: the delivered file, its MD5 against the pin and the provider's sidecar, and
    its header. Opens the header only; the extract is never scanned here."""
    path = snapshot_dir / FILE_NAME
    header = read_header(path)
    md5 = digest_file(path, "md5")
    sidecar = read_md5_sidecar(snapshot_dir / MD5_FILE, FILE_NAME)
    bbox = header["bbox"] or (float("nan"),) * 4
    row = {
        "file": FILE_NAME,
        "bytes": int(path.stat().st_size),
        "md5": md5,
        "md5_pinned": PROVIDER_MD5,
        "md5_sidecar": sidecar,
        "sidecar_match": int(md5 == sidecar),
        "generator": header["generator"],
        "replication_timestamp": header["replication_timestamp"],
        "sorting": header["sorting"],
        "bbox_min_lon": float(bbox[0]),
        "bbox_min_lat": float(bbox[1]),
        "bbox_max_lon": float(bbox[2]),
        "bbox_max_lat": float(bbox[3]),
    }
    frame = pd.DataFrame([row], columns=list(SUMMARY_COLUMNS))
    for column in ("bytes", "sidecar_match"):
        frame[column] = frame[column].astype("int64")
    return frame


# --- the clip -----------------------------------------------------------------------------


Box = tuple[float, float, float, float]


def _inside(box: Box, lon: float, lat: float) -> bool:
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


@dataclass(frozen=True)
class ClipReport:
    """What :func:`clip` wrote: counts the ``network`` stage records."""

    file_name: str
    bytes: int
    box: Box
    nodes: int
    nodes_in_box: int
    ways: int
    highway_ways: int
    relations: int
    source_nodes: int
    source_ways: int
    source_relations: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file_name,
            "bytes": self.bytes,
            "box": list(self.box),
            "nodes": self.nodes,
            "nodes_in_box": self.nodes_in_box,
            "ways": self.ways,
            "highway_ways": self.highway_ways,
            "relations": self.relations,
            "source": {
                "nodes": self.source_nodes,
                "ways": self.source_ways,
                "relations": self.source_relations,
            },
        }


def clip(
    source: Path,
    target: Path,
    box: Box,
    *,
    header_from: Path | None = None,
    header_box: Box | None = None,
) -> ClipReport:
    """Write the way-complete clip of ``source`` to ``target``.

    Three streaming passes over the source: the nodes inside ``box`` (lon/lat, WGS 84);
    the ways touching one of them, with every node they reference; the
    ``type=restriction`` relations whose members are all kept. Then one pass writes the
    kept objects in the source's order (pyosmium's ID filter, so the output stays sorted
    ``Type_then_ID``) with the box in the header, the generator recorded, and the
    source's replication timestamp carried over. Metadata (version, timestamp, user)
    is kept as delivered; the output is a function of the pinned input and the box.
    ``header_from``: take the generator and timestamp from another file's header;
    ``header_box``: write this box into the header instead of the clip box (the samples
    builder keeps the provider's header, box included, on the CI sample, which is a raw
    snapshot in the suite and must pass the same header contract as the real file).
    """
    src = str(source)
    inside: set[int] = set()
    source_nodes = source_ways = source_relations = 0
    for node in osmium.FileProcessor(src, osmium.osm.NODE):
        source_nodes += 1
        location = node.location
        if location.valid() and _inside(box, location.lon, location.lat):
            inside.add(node.id)
    keep_ways: set[int] = set()
    keep_nodes: set[int] = set()
    for way in osmium.FileProcessor(src, osmium.osm.WAY):
        source_ways += 1
        refs = [ref.ref for ref in way.nodes]
        if any(ref in inside for ref in refs):
            keep_ways.add(way.id)
            keep_nodes.update(refs)
    keep_nodes |= inside  # a node inside the box with no way (a POI) is kept too
    keep_relations: set[int] = set()
    for relation in osmium.FileProcessor(src, osmium.osm.RELATION):
        source_relations += 1
        if relation.tags.get("type") != RESTRICTION:
            continue
        members = list(relation.members)
        if not members:
            continue
        if all(
            (m.type == "w" and m.ref in keep_ways) or (m.type == "n" and m.ref in keep_nodes)
            for m in members
        ):
            keep_relations.add(relation.id)

    source_header = read_header(header_from or source)
    header = osmium.io.Header()
    written_box = box if header_box is None else header_box
    header.add_box(osmium.osm.Box(*written_box))
    header.set("generator", f"phillysim clip of {source.name} ({source_header['generator']})")
    if source_header["replication_timestamp"]:
        header.set("osmosis_replication_timestamp", source_header["replication_timestamp"])
    header.set("sorting", SORTING)

    nodes = ways = highway_ways = relations = 0
    if target.exists():
        target.unlink()
    with osmium.SimpleWriter(str(target), header=header) as writer:
        processor = (
            osmium.FileProcessor(src, osmium.osm.NODE | osmium.osm.WAY | osmium.osm.RELATION)
            .with_filter(osmium.filter.IdFilter(keep_nodes).enable_for(osmium.osm.NODE))
            .with_filter(osmium.filter.IdFilter(keep_ways).enable_for(osmium.osm.WAY))
            .with_filter(osmium.filter.IdFilter(keep_relations).enable_for(osmium.osm.RELATION))
        )
        for obj in processor:
            if obj.is_node():
                nodes += 1
            elif obj.is_way():
                ways += 1
                if HIGHWAY in obj.tags:
                    highway_ways += 1
            else:
                relations += 1
            writer.add(obj)
    return ClipReport(
        file_name=target.name,
        bytes=int(target.stat().st_size),
        box=box,
        nodes=nodes,
        nodes_in_box=len(inside),
        ways=ways,
        highway_ways=highway_ways,
        relations=relations,
        source_nodes=source_nodes,
        source_ways=source_ways,
        source_relations=source_relations,
    )


def check_clip(
    path: Path,
    box: Box,
    *,
    node_band: tuple[int, int],
    way_band: tuple[int, int],
) -> list[str]:
    """The clipped file's contract, as a list of violations (empty when sound): a readable
    PBF whose header carries the box; node and way counts within the recorded bands;
    every node inside the box or referenced by a kept way (the way-complete invariant);
    ``highway`` ways present."""
    problems: list[str] = []
    try:
        header = read_header(path)
    except Exception as exc:  # noqa: BLE001 - any unreadable file is one violation
        return [f"{path.name}: not a readable PBF ({type(exc).__name__}: {exc})"]
    if not header["box_valid"]:
        problems.append(f"{path.name}: header carries no bounding box")
    else:
        recorded = tuple(round(v, 6) for v in header["bbox"])
        if recorded != tuple(round(v, 6) for v in box):
            problems.append(f"{path.name}: header box {recorded} is not the clip box {box}")
    outside: set[int] = set()
    nodes = ways = highway_ways = 0
    for node in osmium.FileProcessor(str(path), osmium.osm.NODE):
        nodes += 1
        location = node.location
        if not (location.valid() and _inside(box, location.lon, location.lat)):
            outside.add(node.id)
    for way in osmium.FileProcessor(str(path), osmium.osm.WAY):
        ways += 1
        if HIGHWAY in way.tags:
            highway_ways += 1
        if outside:
            outside.difference_update(ref.ref for ref in way.nodes)
    if outside:
        problems.append(
            f"{len(outside)} node(s) outside the box are referenced by no way: "
            f"{sorted(outside)[:5]}"
        )
    if not node_band[0] <= nodes <= node_band[1]:
        problems.append(f"{nodes} nodes outside the recorded band {list(node_band)}")
    if not way_band[0] <= ways <= way_band[1]:
        problems.append(f"{ways} ways outside the recorded band {list(way_band)}")
    if highway_ways == 0:
        problems.append("no highway ways: not a street network")
    return problems


def count_objects(path: Path) -> dict[str, int]:
    """Node, way, and relation counts of a PBF (one streaming pass)."""
    counts = {"nodes": 0, "ways": 0, "relations": 0}
    for obj in osmium.FileProcessor(str(path)):
        if obj.is_node():
            counts["nodes"] += 1
        elif obj.is_way():
            counts["ways"] += 1
        elif obj.is_relation():
            counts["relations"] += 1
    return counts


def clip_file_name(buffer_m: float) -> str:
    """``pennsylvania-260831-philadelphia-5km.osm.pbf`` for the pinned extent."""
    km = buffer_m / 1000.0
    label = f"{km:g}km"
    return f"{STEM}-philadelphia-{label}.osm.pbf"


#: Node and way counts of the pinned clip (county bounds + 5 km), measured at EP-12 on
#: 2026-09-03 (5,803,119 nodes, 921,869 ways, 224,252 of them highways, 3,693 restriction
#: relations, 49,968,756 bytes) and given a band of roughly plus or minus a third; the
#: ``network`` stage checks its output against them (its ``node_band`` / ``way_band``
#: parameters; the CI sample overrides them). A count outside the band means the extract
#: or the box changed: a stop, not a value to widen.
CLIP_NODE_BAND: tuple[int, int] = (4_000_000, 8_000_000)
CLIP_WAY_BAND: tuple[int, int] = (600_000, 1_300_000)


def band(values: Iterable[int]) -> tuple[int, int]:
    """A tuple band from a JSON list (stage parameters arrive as lists)."""
    lo, hi = (int(v) for v in values)
    if lo < 0 or hi < lo:
        raise ValueError(f"band {list(values)!r} must be 0 <= low <= high")
    return lo, hi


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "stored as delivered (the dated state extract, verifiable against the provider's "
        "MD5 sidecar, which is fetched and stored beside it); the county filter is the clip "
        "the network stage writes: every way touching the county bounds buffered by 5 km "
        "(ADR-0008) with all of its nodes, restriction relations whose members are all kept, "
        "in the source order; the PBF is never opened as an archive"
    ),
    citation=(
        f"OpenStreetMap contributors, Pennsylvania extract {FILE_NAME} via Geofabrik (ODbL 1.0)."
    ),
)
