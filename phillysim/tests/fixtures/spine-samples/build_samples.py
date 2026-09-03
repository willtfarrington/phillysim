"""Build the committed spine samples from an admitted real data root (EP-5a).

Run from ``phillysim/`` after ``phillysim run --stage spine`` has admitted the
pinned snapshots and built the spine (the SNAP and roads samples are cut
against it)::

    uv run python tests/fixtures/spine-samples/build_samples.py [--data-root DIR]

For each real source the script reads ``raw/<source>/<SNAPSHOT_ID>/`` and writes
a real-shaped, fixture-scale snapshot directory beside this file: the same file
names, the provider's own header and record layout, :data:`SAMPLE_TRACTS` (six
Philadelphia County tracts) plus :data:`CONTROL_TRACTS` from another county (and,
for ACS, the nation and state rows; for SNAP and the roads, rows their own
filters must drop) so each filter has something to drop, a short excerpt of the
archived terms page carrying the sentence the adapters check, and a manifest
built through the manifest engine. Everything written is a subset of
US-public-domain Census or USDA data (see README.md). The output is
deterministic: zip member timestamps are fixed and rows keep the provider's
order.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from phillysim.adapters import ADAPTERS, acs, cenpop, snap, tiger, tiger_roads
from phillysim.adapters.base import CENSUS_TERMS_FILE, CENSUS_TERMS_PHRASE
from phillysim.config import Settings
from phillysim.manifest import build_manifest, read_manifest, write_manifest
from phillysim.pipeline import SNAPSHOT_ID
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
    return root / "raw" / source / SNAPSHOT_ID


def _out(source: str) -> Path:
    target = HERE / "raw" / source / SNAPSHOT_ID
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


def _terms_excerpt(real_terms: Path) -> bytes:
    html = real_terms.read_text("utf-8", errors="replace")
    match = re.search(r"<p[^>]*>[^<]*" + re.escape(CENSUS_TERMS_PHRASE) + r"[^<]*</p>", html)
    if match is None:
        raise SystemExit(f"{real_terms}: the checked sentence was not found in the archived page")
    return (
        "<!-- Excerpt for the CI sample: one paragraph of the terms page archived beside the\n"
        f"     real {SNAPSHOT_ID} snapshot (its manifest records the URL); the full page is\n"
        "     311 KB and lives only in the gitignored raw zone. -->\n"
        f"<html><body>\n{match.group(0)}\n</body></html>\n"
    ).encode()


def _manifest(target: Path, real: Path, tracts: int) -> None:
    original = read_manifest(real)
    manifest = build_manifest(
        target,
        source=original.source,
        snapshot_id=original.snapshot_id,
        acquired_at=original.acquired_at,
        acquisition_url=original.acquisition_url,
        acquisition_url_alt=original.acquisition_url_alt,
        terms_archive=original.terms_archive,
        license_bucket=original.license_bucket,
        license_note=(
            f"{original.license_note} CI SAMPLE: {tracts} Philadelphia County tracts plus "
            f"control rows, subset from the {SNAPSHOT_ID} snapshot; terms page excerpted."
        ),
        schema_version=original.schema_version,
        synthetic=False,
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
    return (
        "<!-- Excerpt for the CI sample: the fragments of the provider's data page archived\n"
        f"     beside the real {SNAPSHOT_ID} snapshot that the adapter checks (its manifest\n"
        "     records the URL); the full page lives only in the gitignored raw zone. -->\n"
        "<html><body>\n" + "\n".join(fragments) + "\n</body></html>\n"
    ).encode("utf-8")


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
        }[source](root)
        frame = ADAPTERS[source].read(target)
        unit = {snap.SOURCE: "retailer(s)", tiger_roads.SOURCE: "road(s)"}.get(source, "tract(s)")
        print(f"{source}: {len(frame)} {unit} after the filter -> {target}")


if __name__ == "__main__":
    main()
