"""SEPTA's GTFS feed pinned to a release tag (source ``gtfs``; EP-12).

**Stored as delivered, unwrapped without expanding.** SEPTA publishes its
General Transit Feed Specification data on GitHub (``septadev/GTFS``) as one
release asset per release, ``gtfs_public.zip``, holding two feeds as zips:
``google_bus.zip`` (bus and Metro) and ``google_rail.zip`` (Regional Rail).
ADR-0008 pins release **v202609060** (published 2026-09-02; bus and Metro
authoritative 2026-09-06 to 2027-02-20, Regional Rail 2026-09-06 to
2026-10-17; the pinned analysis dates, Wednesday 2026-09-23 and Saturday
2026-09-26, lie inside both windows) and the asset's SHA-256 as GitHub
records it: a different digest is a replaced asset and a stop. The outer zip
is inspected (slip, bomb) at acquisition before anything is read out of it;
each inner zip is inspected in place by the reader and again as a file once
unwrapped. The download follows GitHub's release-asset redirect, so its
target host is allowlisted beside ``github.com``.

**Terms.** The developer license agreement on SEPTA's developer page
(``https://www3.septa.org/developer/``; "Agreement updated: Tue, 18 Mar 2014"
by its own text) is archived as ``terms.html`` at every acquisition and
checked for the two sentences that make the feed revocable and its fee
reservable; a change is the stop condition (quarantine kind ``terms``). The
project's position (roadmap/sources.md, docs/DATA-LICENSES.md): the raw feed
is never republished, nothing unwrapped from it is ever copied under
``public/`` or ``site/``, computed travel times are facts and carry no feed
contents, and the feed is Bucket A (nothing OSM-derived comes from it).

:func:`read` (what ``validate`` checks) returns one row per inner feed:
the required GTFS files and columns present, ``feed_info.txt``'s dates
covering the pinned Wednesday and Saturday, services running on both, the
agency time zone, the stop count and how many stops lie outside the routing
box (information, not a failure: SEPTA serves the suburbs), route and trip
counts. :func:`unwrap` (the ``network`` stage) copies the two inner zips as
files into the caller's directory; R5 reads GTFS zips directly, so nothing
inside them is ever extracted.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from phillysim.adapters.base import (
    ANALYSIS_CRS,
    COUNTY_BOUNDS,
    ROUTING_BUFFER_M,
    Adapter,
    buffered_bounds,
)
from phillysim.contracts import ColumnSpec, SourceContract
from phillysim.download import Fetch, SnapshotSpec
from phillysim.guards import Limits, check_file_size, extract_zip, inspect_nested_zip, inspect_zip

SOURCE = "gtfs"
RELEASE = "v202609060"
FILE_NAME = "gtfs_public.zip"
URL = f"https://github.com/septadev/GTFS/releases/download/{RELEASE}/{FILE_NAME}"
#: The asset's SHA-256 as GitHub records it (ADR-0008); pinned at acquisition.
SHA256 = "4d3fa20ea094937a9bb6389ad52017e1ac90a564aee497f318797e1b1e4f07ab"
PROVIDER_BYTES = 21_555_258
TERMS_URL = "https://www3.septa.org/developer/"
TERMS_FILE = "terms.html"
#: The two sentences of the license agreement, verbatim (the stop condition).
TERMS_PHRASES: tuple[str, ...] = (
    "SEPTA reserves the right to alter and/or no longer provide the Trip Planning Data at "
    "any time without prior notice.",
    "SEPTA reserves the right to institute a license fee at any time in the future without "
    "prior notice.",
)
#: GitHub and the release-asset hosts its download redirects to (``objects.…`` as the
#: packet recorded it, ``release-assets.…`` as observed on 2026-09-03), plus the terms host.
ALLOWLIST: tuple[str, ...] = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "www3.septa.org",
)
#: The outer zip is about 21.6 MB holding two zips (about 21.6 MB stored); the bus feed's
#: ``stop_times.txt`` alone is about 100 MB uncompressed, hence the extracted cap.
LIMITS = Limits(
    max_file_bytes=128 * 1024**2,
    max_extracted_bytes=1024**3,
    max_compression_ratio=50.0,
    max_members=50,
)
#: The inner feeds, in the order they are reported.
FEEDS: tuple[str, ...] = ("google_bus.zip", "google_rail.zip")
FEED_LABELS: Mapping[str, str] = {"google_bus.zip": "bus_metro", "google_rail.zip": "rail"}
#: The pinned analysis dates (ADR-0008) and the feed's time zone.
PINNED_WEDNESDAY = "2026-09-23"
PINNED_SATURDAY = "2026-09-26"
TIMEZONE = "America/New_York"
PUBLISHER = "SEPTA"
#: The GTFS files and columns the routing engine needs, checked per inner feed.
REQUIRED_FILES: Mapping[str, tuple[str, ...]] = {
    "agency.txt": ("agency_name", "agency_url", "agency_timezone"),
    "stops.txt": ("stop_id", "stop_name", "stop_lat", "stop_lon"),
    "routes.txt": ("route_id", "route_type"),
    "trips.txt": ("route_id", "service_id", "trip_id"),
    "stop_times.txt": ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"),
    "calendar.txt": (
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
    "feed_info.txt": ("feed_publisher_name", "feed_start_date", "feed_end_date", "feed_version"),
}
CALENDAR_DATES = "calendar_dates.txt"
LICENSE_POSITION = (
    "SEPTA developer license agreement (custom terms, agreement text of 2014-03-18 archived "
    "beside the data): revocable, no license fee today but one reservable without notice, "
    "no alteration of the data and no commercial use of SEPTA's marks. Project position "
    "(roadmap/sources.md, docs/DATA-LICENSES.md): the raw feed is never redistributed, no "
    "feed contents are ever published, computed travel times are facts; Bucket A (nothing "
    "OSM-derived comes from the feed)."
)

SPEC = SnapshotSpec(
    source=SOURCE,
    acquisition_url=URL,
    files=(Fetch(URL, FILE_NAME, digest=f"sha256:{SHA256}"),),
    terms=Fetch(TERMS_URL, TERMS_FILE),
    terms_must_contain=TERMS_PHRASES,
    allowlist=ALLOWLIST,
    limits=LIMITS,
    license_bucket="A",
    license_note=(
        f"{LICENSE_POSITION} SEPTA GTFS release {RELEASE} ({FILE_NAME} holding "
        f"{' and '.join(FEEDS)}; bus/Metro authoritative 2026-09-06 to 2027-02-20, Regional "
        "Rail to 2026-10-17), stored as delivered; SHA-256 pinned."
    ),
)

SUMMARY_COLUMNS: tuple[str, ...] = (
    "feed",
    "label",
    "bytes",
    "members",
    "missing_required",
    "missing_names",
    "feed_publisher",
    "feed_version",
    "feed_start_date",
    "feed_end_date",
    "covers_wednesday",
    "covers_saturday",
    "services_wednesday",
    "services_saturday",
    "agency_timezone",
    "stops",
    "stops_outside_box",
    "routes",
    "trips",
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("feed", "str", nullable=False, allowed=frozenset(FEEDS)),
        ColumnSpec("label", "str", nullable=False, allowed=frozenset(FEED_LABELS.values())),
        ColumnSpec("bytes", "int", nullable=False, minimum=1, maximum=LIMITS.max_file_bytes),
        ColumnSpec("members", "int", nullable=False, minimum=len(REQUIRED_FILES)),
        ColumnSpec("missing_required", "int", nullable=False, maximum=0),
        ColumnSpec("missing_names", "str", nullable=True),
        ColumnSpec("feed_publisher", "str", nullable=False, allowed=frozenset({PUBLISHER})),
        ColumnSpec("feed_version", "str", nullable=False, allowed=frozenset({RELEASE})),
        ColumnSpec("feed_start_date", "str", nullable=False, pattern=r"\d{8}"),
        ColumnSpec("feed_end_date", "str", nullable=False, pattern=r"\d{8}"),
        ColumnSpec("covers_wednesday", "int", nullable=False, minimum=1, maximum=1),
        ColumnSpec("covers_saturday", "int", nullable=False, minimum=1, maximum=1),
        ColumnSpec("services_wednesday", "int", nullable=False, minimum=1),
        ColumnSpec("services_saturday", "int", nullable=False, minimum=1),
        ColumnSpec("agency_timezone", "str", nullable=False, allowed=frozenset({TIMEZONE})),
        ColumnSpec("stops", "int", nullable=False, minimum=1),
        ColumnSpec("stops_outside_box", "int", nullable=False, minimum=0),
        ColumnSpec("routes", "int", nullable=False, minimum=1),
        ColumnSpec("trips", "int", nullable=False, minimum=1),
    ),
    key="feed",
    license_buckets=frozenset({"A"}),
    min_rows=len(FEEDS),
    max_rows=len(FEEDS),
)


def routing_box(
    buffer_m: float = ROUTING_BUFFER_M, crs: str = ANALYSIS_CRS
) -> tuple[float, float, float, float]:
    """The routing extent in WGS 84: the county bounds buffered in the analysis CRS."""
    return buffered_bounds(COUNTY_BOUNDS, buffer_m, crs)


# --- reading the nested feeds in place ---------------------------------------------------


def _open_feed(outer: zipfile.ZipFile, feed: str) -> zipfile.ZipFile:
    """The inner feed zip, read through the outer archive after the nested guards."""
    inspect_nested_zip(outer, feed, LIMITS)
    return zipfile.ZipFile(outer.open(feed))


def _rows(inner: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    with inner.open(member) as handle:
        text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
        return list(csv.DictReader(text))


def _header(inner: zipfile.ZipFile, member: str) -> list[str]:
    with inner.open(member) as handle:
        text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
        return next(csv.reader(text), [])


def _missing_required(inner: zipfile.ZipFile) -> list[str]:
    names = set(inner.namelist())
    missing: list[str] = []
    for member, columns in REQUIRED_FILES.items():
        if member not in names:
            missing.append(member)
            continue
        header = set(_header(inner, member))
        missing.extend(f"{member}:{column}" for column in columns if column not in header)
    return missing


def _gtfs_date(value: str) -> str:
    return date.fromisoformat(value).strftime("%Y%m%d")


def services_on(inner: zipfile.ZipFile, day: str) -> int:
    """How many ``service_id`` values run on ``day`` (ISO date) per ``calendar.txt`` and
    the exceptions in ``calendar_dates.txt``."""
    when = _gtfs_date(day)
    weekday = date.fromisoformat(day).strftime("%A").lower()
    active: set[str] = set()
    for row in _rows(inner, "calendar.txt"):
        if row.get(weekday) == "1" and row["start_date"] <= when <= row["end_date"]:
            active.add(row["service_id"])
    if CALENDAR_DATES in inner.namelist():
        for row in _rows(inner, CALENDAR_DATES):
            if row["date"] != when:
                continue
            if row["exception_type"] == "1":
                active.add(row["service_id"])
            elif row["exception_type"] == "2":
                active.discard(row["service_id"])
    return len(active)


def _stops_frame(inner: zipfile.ZipFile) -> pd.DataFrame:
    rows = _rows(inner, "stops.txt")
    frame = pd.DataFrame(
        {
            "stop_id": [r.get("stop_id") for r in rows],
            "stop_name": [r.get("stop_name") for r in rows],
            "stop_lat": pd.to_numeric([r.get("stop_lat") for r in rows], errors="coerce"),
            "stop_lon": pd.to_numeric([r.get("stop_lon") for r in rows], errors="coerce"),
        }
    )
    return frame


def read_stops(snapshot_dir: Path, feed: str) -> pd.DataFrame:
    """The feed's stops (``stop_id``, ``stop_name``, ``stop_lat``, ``stop_lon``; WGS 84
    degrees), read from the inner zip in place. Never published."""
    with zipfile.ZipFile(snapshot_dir / FILE_NAME) as outer, _open_feed(outer, feed) as inner:
        return _stops_frame(inner)


def outside_box(stops: pd.DataFrame, box: tuple[float, float, float, float]) -> int:
    inside = (
        stops["stop_lon"].between(box[0], box[2]) & stops["stop_lat"].between(box[1], box[3])
    ).fillna(False)
    return int((~inside).sum())


def read(snapshot_dir: Path, box: tuple[float, float, float, float] | None = None) -> pd.DataFrame:
    """One row per inner feed (see the module docstring); ``box`` is the routing extent the
    stops are counted against (the pinned one when omitted)."""
    box = routing_box() if box is None else box
    archive = snapshot_dir / FILE_NAME
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive) as outer:
        names = tuple(outer.namelist())
        if tuple(sorted(names)) != tuple(sorted(FEEDS)):
            raise ValueError(f"{FILE_NAME}: members {names} != expected {FEEDS}")
        for feed in FEEDS:
            info = outer.getinfo(feed)
            with _open_feed(outer, feed) as inner:
                names = set(inner.namelist())
                missing = _missing_required(inner)
                feed_info = _rows(inner, "feed_info.txt")[0] if "feed_info.txt" in names else {}
                agency = _rows(inner, "agency.txt")[0] if "agency.txt" in names else {}
                start = feed_info.get("feed_start_date", "")
                end = feed_info.get("feed_end_date", "")
                stops = _stops_frame(inner) if "stops.txt" in names else pd.DataFrame()
                wednesday, saturday = _gtfs_date(PINNED_WEDNESDAY), _gtfs_date(PINNED_SATURDAY)
                has_calendar = "calendar.txt" in names
                rows.append(
                    {
                        "feed": feed,
                        "label": FEED_LABELS[feed],
                        "bytes": int(info.file_size),
                        "members": len([m for m in inner.infolist() if not m.is_dir()]),
                        "missing_required": len(missing),
                        "missing_names": "; ".join(missing) if missing else None,
                        "feed_publisher": feed_info.get("feed_publisher_name"),
                        "feed_version": feed_info.get("feed_version"),
                        "feed_start_date": start,
                        "feed_end_date": end,
                        "covers_wednesday": int(bool(start) and start <= wednesday <= end),
                        "covers_saturday": int(bool(start) and start <= saturday <= end),
                        "services_wednesday": (
                            services_on(inner, PINNED_WEDNESDAY) if has_calendar else 0
                        ),
                        "services_saturday": (
                            services_on(inner, PINNED_SATURDAY) if has_calendar else 0
                        ),
                        "agency_timezone": agency.get("agency_timezone"),
                        "stops": int(len(stops)),
                        "stops_outside_box": outside_box(stops, box) if len(stops) else 0,
                        "routes": len(_rows(inner, "routes.txt")) if "routes.txt" in names else 0,
                        "trips": len(_rows(inner, "trips.txt")) if "trips.txt" in names else 0,
                    }
                )
    frame = pd.DataFrame(rows, columns=list(SUMMARY_COLUMNS))
    for column in (
        "bytes",
        "members",
        "missing_required",
        "covers_wednesday",
        "covers_saturday",
        "services_wednesday",
        "services_saturday",
        "stops",
        "stops_outside_box",
        "routes",
        "trips",
    ):
        frame[column] = frame[column].astype("int64")
    for column in ("missing_names", "feed_publisher", "feed_version", "agency_timezone"):
        frame[column] = frame[column].astype("string")
    return frame


def unwrap(snapshot_dir: Path, target_dir: Path, limits: Limits = LIMITS) -> dict[str, int]:
    """Copy the inner feed zips out of the admitted outer zip into ``target_dir`` as files,
    every guard applied (the outer archive inspected, each inner zip inspected in place
    before and as a file after, the copy capped); nothing inside a feed is extracted.
    Returns ``{feed: bytes}``."""
    archive = snapshot_dir / FILE_NAME
    check_file_size(archive, limits)
    inspect_zip(archive, limits)
    with zipfile.ZipFile(archive) as outer:
        names = tuple(sorted(outer.namelist()))
        if names != tuple(sorted(FEEDS)):
            raise ValueError(f"{FILE_NAME}: members {names} != expected {FEEDS}")
        for feed in FEEDS:
            inspect_nested_zip(outer, feed, limits)
    target_dir.mkdir(parents=True, exist_ok=True)
    written = extract_zip(archive, target_dir, limits)
    out: dict[str, int] = {}
    for path in written:
        inspect_zip(path, limits)
        out[path.name] = int(path.stat().st_size)
    return out


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "stored as delivered (the release asset, verifiable against the digest GitHub "
        "records); no county filter: SEPTA's whole network is routing input and stops "
        "outside the routing box are counted, not dropped; the two inner feed zips are "
        "unwrapped as files by the network stage and never expanded"
    ),
    citation=(
        f"Southeastern Pennsylvania Transportation Authority (SEPTA), GTFS release {RELEASE}."
    ),
)
