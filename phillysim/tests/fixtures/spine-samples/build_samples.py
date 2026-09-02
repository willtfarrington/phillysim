"""Build the committed spine samples from an admitted real data root (EP-5a).

Run from ``phillysim/`` after ``phillysim run --stage validate`` has admitted the
pinned snapshots::

    uv run python tests/fixtures/spine-samples/build_samples.py [--data-root DIR]

For each spine source the script reads ``raw/<source>/<SNAPSHOT_ID>/`` and writes
a real-shaped, fixture-scale snapshot directory beside this file: the same file
names, the provider's own header and record layout, :data:`SAMPLE_TRACTS` (six
Philadelphia County tracts) plus :data:`CONTROL_TRACTS` from another county (and,
for ACS, the nation and state rows) so the county filter has something to drop,
a short excerpt of the archived terms page carrying the sentence the adapters
check, and a manifest built through the manifest engine. Everything written is a
subset of US-public-domain Census data (see README.md). The output is
deterministic: zip member timestamps are fixed and rows keep the provider's
order.
"""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd

from phillysim.adapters import ADAPTERS, acs, cenpop, tiger
from phillysim.adapters.base import CENSUS_TERMS_FILE, CENSUS_TERMS_PHRASE
from phillysim.config import Settings
from phillysim.manifest import build_manifest, read_manifest, write_manifest
from phillysim.pipeline import SNAPSHOT_ID

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


def build_tiger(root: Path) -> Path:
    real, target = _real(root, tiger.SOURCE), _out(tiger.SOURCE)
    frame = gpd.read_file(f"zip://{(real / tiger.FILE_NAME).as_posix()}")
    subset = frame[frame["GEOID"].isin(KEEP)].sort_values("GEOID").reset_index(drop=True)
    if len(subset) != len(KEEP):
        raise SystemExit(f"tiger: expected {len(KEEP)} tracts, found {len(subset)}")
    stem = Path(tiger.FILE_NAME).stem
    with tempfile.TemporaryDirectory() as scratch:
        subset.to_file(Path(scratch) / f"{stem}.shp", driver="ESRI Shapefile")
        members = sorted(Path(scratch).iterdir())
        with zipfile.ZipFile(target / tiger.FILE_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
            for member in members:
                info = zipfile.ZipInfo(member.name, date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, member.read_bytes())
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
        }[source](root)
        frame = ADAPTERS[source].read(target)
        print(f"{source}: {len(frame)} tract(s) after the county filter -> {target}")


if __name__ == "__main__":
    main()
