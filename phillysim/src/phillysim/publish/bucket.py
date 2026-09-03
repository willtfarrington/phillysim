"""License buckets for published files (ADR-0003, Planning Baseline AM-1).

Two buckets, fixed by the ADR: **A**, CC BY 4.0, for prose, cards, and derived
tables containing no OSM-derived contents; **B**, ODbL, for any table containing
OSM-derived contents, every combined export included, with the ODbL notice and
"(c) OpenStreetMap contributors" carried in-file or in the sidecar. A published
file's bucket is never a judgement call at export time: it is *derived* from the
buckets its sources' manifests record (:func:`derive_bucket`), the label the file
carries must equal that derivation, and the gate checks both.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from phillysim.contracts import LICENSE_BUCKETS

BUCKET_A = "A"
BUCKET_B = "B"

#: The notice every Bucket B file must carry (ADR-0003; OSMF attribution guideline).
OSM_NOTICE = "© OpenStreetMap contributors"


@dataclass(frozen=True)
class LicenseLabel:
    """What a bucket means for a published file: the license and the notices it must carry."""

    bucket: str
    spdx_id: str
    name: str
    url: str
    notices: tuple[str, ...]

    def payload(self) -> dict[str, Any]:
        """The label as it is written into a file (GeoJSON top-level member) and the manifest."""
        return {
            "bucket": self.bucket,
            "spdx_id": self.spdx_id,
            "name": self.name,
            "url": self.url,
            "notices": list(self.notices),
        }


LABELS: dict[str, LicenseLabel] = {
    BUCKET_A: LicenseLabel(
        bucket=BUCKET_A,
        spdx_id="CC-BY-4.0",
        name="Creative Commons Attribution 4.0 International",
        url="https://creativecommons.org/licenses/by/4.0/",
        notices=(),
    ),
    BUCKET_B: LicenseLabel(
        bucket=BUCKET_B,
        spdx_id="ODbL-1.0",
        name="Open Data Commons Open Database License v1.0",
        url="https://opendatacommons.org/licenses/odbl/1-0/",
        notices=(
            "This file is made available under the Open Database License (ODbL) 1.0. Any "
            "rights in individual contents are licensed under the Database Contents License.",
            OSM_NOTICE,
        ),
    ),
}


def check_bucket(bucket: Any) -> str:
    if bucket not in LICENSE_BUCKETS:
        raise ValueError(
            f"unknown license bucket {bucket!r}; expected one of {sorted(LICENSE_BUCKETS)}"
        )
    return str(bucket)


def derive_bucket(source_buckets: Iterable[str]) -> str:
    """The bucket a file derived from sources with these buckets must carry.

    Bucket B is contagious (ADR-0003: any table containing OSM-derived contents, every
    combined export included); a file derived only from Bucket A sources is Bucket A.
    """
    buckets = {check_bucket(b) for b in source_buckets}
    return BUCKET_B if BUCKET_B in buckets else BUCKET_A


def label_of(bucket: str) -> LicenseLabel:
    return LABELS[check_bucket(bucket)]
