# tinycity — synthetic pipeline fixture

**Wholly synthetic.** Every file in this directory is produced by
`phillysim gen-tinycity` from hand-chosen constants in
`src/phillysim/fixtures/tinycity.py`. Nothing is derived from real data: the
tracts sit in the open Atlantic (longitude −70.00 to −69.97, latitude 38.00 to
38.02), the GEOIDs use state FIPS 99 and county FIPS 999 (neither exists), the
"sources" point at `https://example.invalid/…`, and every name is invented.
The fixture is therefore permissively licensed by construction: it is code
output and ships under the repository's MIT license. No source terms apply.

Do not hand-edit anything here except this README. Regenerate instead:

```
cd phillysim
uv run phillysim gen-tinycity --out tests/fixtures/tinycity
uv run phillysim gen-tinycity --out tests/fixtures/tinycity-invalid --variant invalid
uv run pytest
```

`tests/test_tinycity_fixture.py` fails if the committed files drift from a
fresh generation. Text files are compared byte-for-byte (and against
`CHECKSUMS.txt`); Parquet files are compared by content, because their bytes
legitimately change when the pinned pyarrow / geopandas writers change.
`tests/fixtures/.gitattributes` disables line-ending conversion so the
checksums survive a Windows checkout.

## What it stands in for

| Pipeline stage (architecture.md "Data flow") | Fixture files | Notes |
|---|---|---|
| Source adapters → raw snapshots | `raw/<source>/2026-01-01/` — data file, `manifest.json`, `TERMS.txt` | Eight fake sources mirroring the v1 matrix: `tiger_tracts`, `cenpop`, `acs`, `snap_retailers`, `farmers_markets`, `meal_sites`, `gtfs`, `osm_network`. The manifest shape (URL + alt URL, terms archive, license bucket, schema version, per-file SHA-256) is a proposal for EP-4a. |
| Schema + license validation | `src/phillysim/fixtures/tinycity_contracts.py` + `tests/contracts/` | One `SourceContract` per fake source; the invalid variant (below) proves each check fires. |
| Normalization to the tract spine | `expected/tracts_spine.parquet` | GeoParquet, EPSG:4326, six polygons with population-weighted centroids that are deliberately off-centre. |
| Conflation + hours parsing | `expected/sites.parquet` | Thirteen sites with source-scoped IDs, containing tract, and the hand-derived Tier 2 answers for the hours edge cases. |
| Travel-time matrices (M3) | `expected/travel_times.parquet` | **Precomputed stand-in**, not routing: Manhattan distance at 4.8 km/h plus a fixed access minute, a 15 % slower 85th percentile, and a stub transit line along the bottom row of tracts. Until M3, downstream stages consume this file. |
| Metrics + MOE + analytic tables | `expected/tract_metrics.parquet` | The locked schema `{estimate, moe, cv_tier, reliability_action}` with all three CV tiers present, plus `time_to_nearest_min` per tract × category × mode derived from the matrix. |
| Public-safe aggregates / site | — | Not seeded here; the analytic table is the input those stages will read. |

`fixture.json` records every parameter (bounds, analysis weeks, travel-model
constants, CV tier edges) so tests never hard-code them.

## Hours edge cases (methodology.md, Tier 2)

The pinned analysis weeks are the first full Monday-to-Sunday weeks of June
2026 (in-season, starting 2026-06-01) and February 2026 (off-season, starting
2026-02-02).

| Site | Source hours | Status | Weekday | Weekend | In-season week | Off-season week |
|---|---|---|---|---|---|---|
| M1 Weekend Green Market | "Saturday 9:00 AM - 1:00 PM", year-round | parsed | no | yes | yes | yes |
| M2 Seasonal Square Market | "Tuesdays 2:00 PM - 6:00 PM", "May - November" | parsed | yes | no | yes | **no** |
| M3 Quiet Corner Market | null | missing | — | — | — | — |
| M4 Riverside Stand | "9-1 sat&sun / call ahead ###", "??" | malformed | — | — | — | — |
| M5 Midweek Market | "Wednesday 10:00 AM - 2:00 PM", year-round | parsed | yes | no | yes | yes |
| S1 Central Kitchen | structured Mon–Fri 11:30–13:00 | parsed | yes | no | yes | yes |
| S2 Weekend Breakfast | structured Sat–Sun 08:00–10:00 | parsed | no | yes | yes | yes |
| S3 Unlisted Pantry | all fourteen hour fields null | missing | — | — | — | — |
| S4 Typo Table | `mon_open = "25:00"` | malformed | — | — | — | — |
| R1–R4 (SNAP-like retailers) | source has no hours field | not_in_source | — | — | — | — |

"—" is stored as null in `expected/sites.parquet`: the parser must say "cannot
determine", never guess. A market counts as open in a week if it is open on at
least one day of that week (category-aware rule).

## The invalid variant

`tests/fixtures/tinycity-invalid/` is the same generator with faults injected
(listed in its `fixture.json` under `injected_faults`): a self-intersecting
tract polygon, a ten-character GEOID, a dropped `store_type` column, a retailer
outside the bounds, a manifest license bucket of `Z`, a duplicated market ID, a
negative ACS margin of error, and an emptied meal-site layer. The contract
suite requires every one to be caught by the check kind it targets, and the
untouched sources to still pass.

## What this fixture does not exercise (on purpose)

Real routing, the 120-minute censoring branch (all trips are short), POI
de-duplication across sources (each site appears once), CSV formula-injection
cases, ACS ratio-MOE propagation, and license-bucket labeling of published
outputs. Each belongs to the packet that builds that stage; the brief's stop
condition is "exercises every stage, not realism."
