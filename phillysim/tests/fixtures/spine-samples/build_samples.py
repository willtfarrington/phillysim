"""Build the committed spine samples from an admitted real data root (EP-5a).

Run from ``phillysim/`` after ``phillysim run --stage spine`` has admitted the
pinned snapshots and built the spine (the SNAP, roads, OSM, and GTFS samples
are cut or placed against it)::

    uv run python tests/fixtures/spine-samples/build_samples.py [--data-root DIR]

For each real source the script reads ``raw/<source>/<snapshot id>/`` (the
per-source IDs in ``phillysim.pipeline.SNAPSHOT_IDS``) and writes a
real-shaped, fixture-scale snapshot directory beside this file: the same file
names, the provider's own header and record layout, :data:`SAMPLE_TRACTS` (six
Philadelphia County tracts) plus :data:`CONTROL_TRACTS` from another county (and,
for ACS, the nation and state rows; for SNAP and the roads, rows their own
filters must drop) so each filter has something to drop, a short excerpt of the
archived terms page carrying the sentence the adapters check, and a manifest
built through the manifest engine. The Census and USDA samples are subsets of
US-public-domain data; the OSM sample (EP-12) is real OpenStreetMap data
under ODbL, clipped to the six tracts' bounds with the same way-complete clip
the ``network`` stage runs, committed with the ODbL notice (see README.md);
the GTFS sample (EP-12) is **synthetic** in SEPTA's layout, because
committing any subset of the real feed would republish feed contents. The
output is deterministic: zip member timestamps are fixed and rows keep the
provider's order.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from phillysim.adapters import ADAPTERS, acs, cenpop, osm, septa_gtfs, snap, tiger, tiger_roads
from phillysim.adapters.base import CENSUS_TERMS_FILE, CENSUS_TERMS_PHRASE, WGS84
from phillysim.config import Settings
from phillysim.download import visible_text
from phillysim.manifest import build_manifest, read_manifest, write_manifest
from phillysim.pipeline import SNAPSHOT_IDS
from phillysim.spine import SPINE

HERE = Path(__file__).resolve().parent
SAMPLE_TRACTS: tuple[str, ...] = (
    "42101000101",
    "42101000102",
    "42101000200",
    "42101000300",
    "42101000401",
    "42101000403",
)
#: Two Adams County tracts: present in every state-level file, outside Philadelphia.
CONTROL_TRACTS: tuple[str, ...] = ("42001030101", "42001030103")
#: ACS summary rows that are not tracts at all (nation, Pennsylvania).
CONTROL_GEO_IDS: tuple[str, ...] = ("0100000US", "0400000US42")
KEEP = frozenset(SAMPLE_TRACTS + CONTROL_TRACTS)
ZIP_TIME = (2026, 9, 2, 0, 0, 0)


def _real(root: Path, source: str) -> Path:
    return root / "raw" / source / SNAPSHOT_IDS[source]


def _out(source: str) -> Path:
    target = HERE / "raw" / source / SNAPSHOT_IDS[source]
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


def _terms_excerpt(real_terms: Path) -> bytes:
    html = real_terms.read_text("utf-8", errors="replace")
    match = re.search(r"<p[^>]*>[^<]*" + re.escape(CENSUS_TERMS_PHRASE) + r"[^<]*</p>", html)
    if match is None:
        raise SystemExit(f"{real_terms}: the checked sentence was not found in the archived page")
    snapshot_id = real_terms.parent.name
    return (
        "<!-- Excerpt for the CI sample: one paragraph of the terms page archived beside the\n"
        f"     real {snapshot_id} snapshot (its manifest records the URL); the full page is\n"
        "     311 KB and lives only in the gitignored raw zone. -->\n"
        f"<html><body>\n{match.group(0)}\n</body></html>\n"
    ).encode()


def _manifest(target: Path, real: Path, tracts: int, *, note: str | None = None) -> None:
    original = read_manifest(real)
    snapshot_id = original.snapshot_id
    if note is None:
        note = (
            f"CI SAMPLE: {tracts} Philadelphia County tracts plus control rows, subset from "
            f"the {snapshot_id} snapshot; terms page excerpted."
        )
    manifest = build_manifest(
        target,
        source=original.source,
        snapshot_id=original.snapshot_id,
        acquired_at=original.acquired_at,
        acquisition_url=original.acquisition_url,
        acquisition_url_alt=original.acquisition_url_alt,
        terms_archive=original.terms_archive,
        license_bucket=original.license_bucket,
        license_note=f"{original.license_note} {note}",
        schema_version=original.schema_version,
        synthetic=note.startswith("CI SAMPLE (synthetic)"),
    )
    write_manifest(target, manifest)


def _write_shapefile_zip(subset: gpd.GeoDataFrame, archive: Path) -> None:
    """``subset`` as a zipped shapefile with the provider's member names, fixed member
    timestamps, and the dBASE header's write date pinned, so the sample is byte-identical
    on any day."""
    stem = archive.stem
    with tempfile.TemporaryDirectory() as scratch:
        subset.to_file(Path(scratch) / f"{stem}.shp", driver="ESRI Shapefile")
        members = sorted(Path(scratch).iterdir())
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for member in members:
                info = zipfile.ZipInfo(member.name, date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                data = member.read_bytes()
                if member.suffix == ".dbf":
                    # The dBASE header stamps the day of writing in bytes 1-3 (YY MM DD,
                    # year minus 1900); pin it so the sample is byte-identical on any day.
                    year, month, day = ZIP_TIME[:3]
                    data = data[:1] + bytes((year - 1900, month, day)) + data[4:]
                zf.writestr(info, data)


def build_tiger(root: Path) -> Path:
    real, target = _real(root, tiger.SOURCE), _out(tiger.SOURCE)
    frame = gpd.read_file(f"zip://{(real / tiger.FILE_NAME).as_posix()}")
    subset = frame[frame["GEOID"].isin(KEEP)].sort_values("GEOID").reset_index(drop=True)
    if len(subset) != len(KEEP):
        raise SystemExit(f"tiger: expected {len(KEEP)} tracts, found {len(subset)}")
    _write_shapefile_zip(subset, target / tiger.FILE_NAME)
    (target / CENSUS_TERMS_FILE).write_bytes(_terms_excerpt(real / CENSUS_TERMS_FILE))
    _manifest(target, real, len(SAMPLE_TRACTS))
    return target


#: Local-road control rows (EP-8b): features of another MTFCC class inside the sample
#: tracts, so the adapter's feature-class filter demonstrably drops something.
ROADS_CONTROLS = 4


def build_roads(root: Path) -> Path:
    """The primary and secondary roads crossing the six sample tracts, plus control rows.

    Needs the curated spine in the data root (``phillysim run --stage spine``) to find the
    sample tracts; features keep the provider's attributes and geometry unchanged.
    """
    real, target = _real(root, tiger_roads.SOURCE), _out(tiger_roads.SOURCE)
    everything = tiger_roads.read_all(real)
    spine = gpd.read_parquet(root / SPINE)
    area = spine[spine["geoid"].isin(SAMPLE_TRACTS)].union_all()
    crossing = everything[everything.to_crs(spine.crs).intersects(area)]
    major = crossing[crossing["MTFCC"].isin(tiger_roads.MAJOR_ROAD_CLASSES)]
    local = crossing[~crossing["MTFCC"].isin(tiger_roads.MAJOR_ROAD_CLASSES)]
    if len(major) < 10 or len(local) < ROADS_CONTROLS:
        raise SystemExit(f"roads: {len(major)} major and {len(local)} local roads in the tracts")
    controls = local.sort_values("LINEARID").head(ROADS_CONTROLS)
    subset = pd.concat([major, controls]).sort_values("LINEARID").reset_index(drop=True)
    subset = gpd.GeoDataFrame(subset, geometry="geometry", crs=everything.crs)
    _write_shapefile_zip(subset, target / tiger_roads.FILE_NAME)
    (target / CENSUS_TERMS_FILE).write_bytes(_terms_excerpt(real / CENSUS_TERMS_FILE))
    _manifest(target, real, len(SAMPLE_TRACTS))
    return target


def build_cenpop(root: Path) -> Path:
    real, target = _real(root, cenpop.SOURCE), _out(cenpop.SOURCE)
    lines = (real / cenpop.FILE_NAME).read_bytes().split(b"\n")
    kept = [lines[0]]
    for line in lines[1:]:
        fields = line.decode("utf-8").split(",")
        if len(fields) >= 3 and "".join(fields[:3]) in KEEP:
            kept.append(line)
    if len(kept) != len(KEEP) + 1:
        raise SystemExit(f"cenpop: expected {len(KEEP)} rows, found {len(kept) - 1}")
    (target / cenpop.FILE_NAME).write_bytes(b"\n".join(kept) + b"\n")
    (target / CENSUS_TERMS_FILE).write_bytes(_terms_excerpt(real / CENSUS_TERMS_FILE))
    _manifest(target, real, len(SAMPLE_TRACTS))
    return target


def build_acs(root: Path) -> Path:
    real, target = _real(root, acs.SOURCE), _out(acs.SOURCE)
    wanted = {f"1400000US{geoid}" for geoid in KEEP} | set(CONTROL_GEO_IDS)
    for table in acs.TABLES:
        name = acs.file_name(table)
        kept: list[bytes] = []
        with (real / name).open("rb") as handle:
            kept.append(next(handle).rstrip(b"\r\n"))
            for line in handle:
                geo_id = line.split(b"|", 1)[0].decode("ascii")
                if geo_id in wanted:
                    kept.append(line.rstrip(b"\r\n"))
        if len(kept) != len(wanted) + 1:
            raise SystemExit(f"acs {table}: expected {len(wanted)} rows, found {len(kept) - 1}")
        (target / name).write_bytes(b"\n".join(kept) + b"\n")
    (target / CENSUS_TERMS_FILE).write_bytes(_terms_excerpt(real / CENSUS_TERMS_FILE))
    _manifest(target, real, len(SAMPLE_TRACTS))
    return target


#: SNAP control rows (EP-6): closed Philadelphia spells, another county, another state.
SNAP_CLOSED_PHILADELPHIA = 2
SNAP_OTHER_COUNTY = 2
SNAP_OTHER_STATE = 1


def build_snap(root: Path) -> Path:
    """Current Philadelphia retailers inside the sample tracts, plus control rows.

    Needs the curated spine in the data root (``phillysim run --stage spine``) to find
    which retailers fall inside :data:`SAMPLE_TRACTS`; rows are written in the
    provider's column order and quoting, the member name and header unchanged.
    """
    real, target = _real(root, snap.SOURCE), _out(snap.SOURCE)
    everything = snap.read_all(real)
    spine = gpd.read_parquet(root / SPINE)
    spine = spine[spine["geoid"].isin(SAMPLE_TRACTS)]
    current = snap.read(real)
    points = gpd.GeoDataFrame(geometry=current.geometry.to_crs(spine.crs))
    inside = gpd.sjoin(points, spine[["geometry"]], how="inner", predicate="within")
    keep_ids = set(current.loc[inside.index.unique(), "Record ID"])
    if len(keep_ids) < 10:
        raise SystemExit(f"snap: only {len(keep_ids)} current retailers in the sample tracts")

    def first(mask, n: int):
        rows = everything[mask]
        return rows.iloc[rows["Record ID"].astype("int64").argsort(kind="stable").to_numpy()[:n]]

    philadelphia = (everything["State"] == "PA") & (everything["County"] == "PHILADELPHIA")
    controls = [
        first(philadelphia & everything["End Date"].notna(), SNAP_CLOSED_PHILADELPHIA),
        first(
            (everything["State"] == "PA")
            & (everything["County"] == "ADAMS")
            & everything["End Date"].isna(),
            SNAP_OTHER_COUNTY,
        ),
        first((everything["State"] == "DE") & everything["End Date"].isna(), SNAP_OTHER_STATE),
    ]
    control_keys = {
        (row["Record ID"], row["Authorization Date"])
        for part in controls
        for _, row in part.iterrows()
    }
    is_control = pd.Series(
        [
            (r, a) in control_keys
            for r, a in zip(everything["Record ID"], everything["Authorization Date"], strict=True)
        ],
        index=everything.index,
    )
    wanted = everything[
        (everything["Record ID"].isin(keep_ids) & everything["End Date"].isna()) | is_control
    ]
    expected = len(keep_ids) + sum(len(part) for part in controls)
    if len(wanted) != expected:
        raise SystemExit(f"snap: expected {expected} rows, selected {len(wanted)}")

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(snap.COLUMNS)
    for _, row in wanted.iterrows():
        writer.writerow(["" if value is None or value != value else value for value in row])
    with zipfile.ZipFile(target / snap.FILE_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(snap.MEMBER, date_time=ZIP_TIME)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, ("﻿" + buffer.getvalue()).encode("utf-8"))
    (target / snap.PAGE_FILE).write_bytes(_page_excerpt(real / snap.PAGE_FILE))
    _manifest(target, real, len(keep_ids))
    return target


def _page_excerpt(real_page: Path) -> bytes:
    html = real_page.read_text("utf-8", errors="replace")
    fragments = []
    for phrase in snap.PAGE_PHRASES:
        match = re.search(r"<(p|span|div)[^>]*>[^<]*" + re.escape(phrase) + r".{0,80}?</\1>", html)
        fragments.append(match.group(0) if match else f"<p>{phrase}</p>")
    snapshot_id = real_page.parent.name
    return (
        "<!-- Excerpt for the CI sample: the fragments of the provider's data page archived\n"
        f"     beside the real {snapshot_id} snapshot that the adapter checks (its manifest\n"
        "     records the URL); the full page lives only in the gitignored raw zone. -->\n"
        "<html><body>\n" + "\n".join(fragments) + "\n</body></html>\n"
    ).encode("utf-8")


# --- the routing sources (EP-12) --------------------------------------------------------


def _fragment_excerpt(real_page: Path, phrases: tuple[str, ...], what: str) -> bytes:
    """The smallest HTML fragments of the archived page whose visible text carries each
    checked phrase (a phrase may span an inline element, as Geofabrik's footer does)."""
    html = real_page.read_text("utf-8", errors="replace")
    fragments = []
    for phrase in phrases:
        match = re.search(
            r"<p[^>]*>(?:(?!</p>).)*?" + re.escape(phrase) + r"(?:(?!</p>).)*?</p>", html, re.S
        )
        if match is None:
            # The phrase spans inline elements: cut from the nearest anchor start before
            # its first word to the end of the anchor closing after its last word.
            words = phrase.split()
            first, last = html.find(words[0]), html.find(words[-1])
            if first < 0 or last < first:
                raise SystemExit(f"{real_page}: {phrase!r} not found in the archived page")
            anchor = html.rfind("<a", max(0, first - 200), first)
            start = anchor if anchor >= 0 else first
            end = html.find("</a>", last)
            end = last + len(words[-1]) if end < 0 else end + len("</a>")
            fragment = html[start:end]
            if phrase not in visible_text(fragment):
                raise SystemExit(f"{real_page}: could not excerpt {phrase!r}")
            # Trailing whitespace stripped per line: the committed excerpt must survive the
            # repository's whitespace hooks byte for byte (its digest is in the manifest).
            fragment = "\n".join(line.rstrip() for line in fragment.splitlines())
            fragments.append(f"<p>{fragment}</p>")
        else:
            fragments.append(match.group(0))
    snapshot_id = real_page.parent.name
    return (
        f"<!-- Excerpt for the CI sample: the fragments of {what} archived beside the real\n"
        f"     {snapshot_id} snapshot that the adapter checks in their visible text (its\n"
        "     manifest records the URL); the full page lives only in the gitignored raw\n"
        "     zone. -->\n<html><body>\n" + "\n".join(fragments) + "\n</body></html>\n"
    ).encode("utf-8")


def _sample_box(root: Path) -> tuple[float, float, float, float]:
    """The six sample tracts' bounds in WGS 84 (no buffer: the sample stays small)."""
    spine = gpd.read_parquet(root / SPINE)
    tracts = spine[spine["geoid"].isin(SAMPLE_TRACTS)].to_crs(WGS84)
    minx, miny, maxx, maxy = (round(float(v), 6) for v in tracts.total_bounds)
    return (minx, miny, maxx, maxy)


def build_osm(root: Path) -> Path:
    """The real extract clipped to the six sample tracts' bounds, way-complete, with the
    provider's header (generator, timestamp, and the state's bounding box) carried over so
    the sample passes the same header contract as the real file; the MD5 sidecar
    regenerated for the sample's bytes. Real OpenStreetMap data under ODbL (README.md)."""
    real, target = _real(root, osm.SOURCE), _out(osm.SOURCE)
    box = _sample_box(root)
    source_header = osm.read_header(real / osm.FILE_NAME)
    report = osm.clip(
        real / osm.FILE_NAME, target / osm.FILE_NAME, box, header_box=source_header["bbox"]
    )
    if report.highway_ways < 50:
        raise SystemExit(f"osm: only {report.highway_ways} highway ways in the sample box")
    md5 = hashlib.md5((target / osm.FILE_NAME).read_bytes()).hexdigest()  # noqa: S324
    (target / osm.MD5_FILE).write_bytes(f"{md5}  {osm.FILE_NAME}\n".encode())
    (target / osm.TERMS_FILE).write_bytes(
        _fragment_excerpt(real / osm.TERMS_FILE, osm.TERMS_PHRASES, "the Geofabrik region page")
    )
    _manifest(
        target,
        real,
        len(SAMPLE_TRACTS),
        note=(
            f"CI SAMPLE: the extract clipped to the bounds of {len(SAMPLE_TRACTS)} Philadelphia "
            f"County tracts ({report.nodes} nodes, {report.ways} ways, {report.relations} "
            f"relations; way-complete) from the {SNAPSHOT_IDS[osm.SOURCE]} snapshot, the "
            "provider's header carried over, the MD5 sidecar regenerated for the sample; "
            f"real OpenStreetMap data, ODbL 1.0, {osm.OSM_ATTRIBUTION}; terms page "
            "excerpted."
        ),
    )
    return target


#: The synthetic feed's shape: one bus route through the six sample tracts' centers, one
#: rail line between two of them, both running the pinned Wednesday and Saturday services,
#: and one control stop in Adams County (outside the routing box; counted, never dropped).
GTFS_CONTROL_STOP = ("adams_ctl", "Gettysburg Control Stop", 39.8309, -77.2311)
GTFS_WINDOWS = {
    "google_bus.zip": ("20260906", "20270220"),
    "google_rail.zip": ("20260906", "20261017"),
}


def _csv_bytes(header: tuple[str, ...], rows: list[tuple]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return buffer.getvalue()


def _synthetic_feed(feed: str, stops: list[tuple[str, str, float, float]]) -> bytes:
    """One inner feed zip in SEPTA's layout with synthetic contents: the stops given, one
    route, weekday and Saturday services covering the feed window, one trip per service
    visiting every stop in order, and ``feed_info.txt`` with the pinned release's dates."""
    start, end = GTFS_WINDOWS[feed]
    label = "bus" if feed == "google_bus.zip" else "rail"
    route_type = "3" if label == "bus" else "2"
    services = [("wk", "1,1,1,1,1,0,0"), ("sat", "0,0,0,0,0,1,0")]
    trips = [(f"{label}_route", sid, f"{label}_{sid}_1", "Synthetic", "0") for sid, _ in services]
    stop_times = []
    for _, _sid, trip_id, _, _ in trips:
        for seq, (stop_id, _, _, _) in enumerate(stops, start=1):
            clock = f"{8 + seq // 60:02d}:{(10 + seq) % 60:02d}:00"
            stop_times.append((trip_id, clock, clock, stop_id, str(seq)))
    members = {
        "agency.txt": _csv_bytes(
            ("agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"),
            [
                (
                    "SYN",
                    "Synthetic Transit (CI sample)",
                    "https://example.invalid/",
                    "America/New_York",
                    "en",
                )
            ],
        ),
        "stops.txt": _csv_bytes(("stop_id", "stop_name", "stop_lat", "stop_lon"), stops),
        "routes.txt": _csv_bytes(
            ("route_id", "agency_id", "route_short_name", "route_long_name", "route_type"),
            [(f"{label}_route", "SYN", label.upper(), f"Synthetic {label} route", route_type)],
        ),
        "trips.txt": _csv_bytes(
            ("route_id", "service_id", "trip_id", "trip_headsign", "direction_id"), trips
        ),
        "stop_times.txt": _csv_bytes(
            ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"), stop_times
        ),
        "calendar.txt": _csv_bytes(
            (
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ),
            [(sid, *days.split(","), start, end) for sid, days in services],
        ),
        "calendar_dates.txt": _csv_bytes(
            ("service_id", "date", "exception_type"), [("wk", "20261126", "2")]
        ),
        "feed_info.txt": _csv_bytes(
            (
                "feed_publisher_name",
                "feed_publisher_url",
                "feed_lang",
                "feed_start_date",
                "feed_end_date",
                "feed_version",
            ),
            [("SEPTA", "https://septa.org/", "en", start, end, septa_gtfs.RELEASE)],
        ),
    }
    return _zip_bytes(members)


def build_gtfs(root: Path) -> Path:
    """A synthetic feed in SEPTA's layout over the six sample tracts (their population-
    weighted centers as stops), plus the terms excerpt and a ``synthetic: true`` manifest.
    No byte of SEPTA's feed is copied."""
    real, target = _real(root, septa_gtfs.SOURCE), _out(septa_gtfs.SOURCE)
    spine = gpd.read_parquet(root / SPINE)
    tracts = spine[spine["geoid"].isin(SAMPLE_TRACTS)].sort_values("geoid")
    bus_stops = [
        (f"bus_{geoid}", f"Synthetic stop {name}", round(float(lat), 6), round(float(lon), 6))
        for geoid, name, lat, lon in zip(
            tracts["geoid"],
            tracts["name"],
            tracts["centroid_lat"],
            tracts["centroid_lon"],
            strict=True,
        )
    ] + [GTFS_CONTROL_STOP]
    rail_stops = [
        ("rail_" + s[0][4:], s[1].replace("stop", "station"), s[2], s[3]) for s in bus_stops[:2]
    ]
    outer = _zip_bytes(
        {
            "google_bus.zip": _synthetic_feed("google_bus.zip", bus_stops),
            "google_rail.zip": _synthetic_feed("google_rail.zip", rail_stops),
        }
    )
    (target / septa_gtfs.FILE_NAME).write_bytes(outer)
    (target / septa_gtfs.TERMS_FILE).write_bytes(
        _fragment_excerpt(
            real / septa_gtfs.TERMS_FILE, septa_gtfs.TERMS_PHRASES, "SEPTA's developer page"
        )
    )
    _manifest(
        target,
        real,
        len(SAMPLE_TRACTS),
        note=(
            f"CI SAMPLE (synthetic): a feed in SEPTA's layout ({', '.join(septa_gtfs.FEEDS)} "
            f"inside {septa_gtfs.FILE_NAME}) with {len(bus_stops)} bus and {len(rail_stops)} "
            f"rail stops placed on the {len(SAMPLE_TRACTS)} sample tracts' centers plus one "
            "control stop outside the routing box, one route and two services each, and the "
            f"pinned release's feed_info dates; no SEPTA feed contents (the real "
            f"{SNAPSHOT_IDS[septa_gtfs.SOURCE]} snapshot is never copied); terms page excerpted."
        ),
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()
    root = args.data_root or Settings.load().data_root
    for source in sorted(ADAPTERS):
        target = {
            tiger.SOURCE: build_tiger,
            cenpop.SOURCE: build_cenpop,
            acs.SOURCE: build_acs,
            snap.SOURCE: build_snap,
            tiger_roads.SOURCE: build_roads,
            osm.SOURCE: build_osm,
            septa_gtfs.SOURCE: build_gtfs,
        }[source](root)
        frame = ADAPTERS[source].read(target)
        unit = {
            snap.SOURCE: "retailer(s)",
            tiger_roads.SOURCE: "road(s)",
            osm.SOURCE: "summary row(s)",
            septa_gtfs.SOURCE: "feed(s)",
        }.get(source, "tract(s)")
        print(f"{source}: {len(frame)} {unit} after the filter -> {target}")


if __name__ == "__main__":
    main()
