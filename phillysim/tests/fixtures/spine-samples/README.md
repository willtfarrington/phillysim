# spine-samples — real-shaped CI samples of the real sources

Fixture-scale subsets of the **real** snapshots acquired on 2026-09-02 (the
three spine sources, EP-5a; the USDA SNAP retailer file, EP-6), so the source
contracts (`tests/contracts/test_spine_sources.py`, `test_snap.py`) and the
real pipeline's stages (`tests/integration/test_real_pipeline.py`) run offline
in CI against the provider's own file shapes. They are not synthetic: every
byte of data is Census Bureau or USDA data, and the manifests say so
(`synthetic: false`, a `license_note` that names the subset).

## License

All four sources are works of the United States Government and therefore in
the **US public domain** (17 U.S.C. § 105). The Census Bureau "publishes its
data as open data, meaning it is freely available for use and re-use by the
public" (its Open Government page, archived as `terms.html` beside every real
Census snapshot and excerpted here), and the TIGER/Line technical documentation
(2025, section 1.2) states that copyright protection is not available for the
files and asks only that the Census Bureau be cited as the source. USDA
publishes the SNAP retailer file as public data (docs/DATA-LICENSES.md
records why no USDA terms page is archived). Committing these subsets to the
repository is therefore permitted; they carry the same Bucket A label as the
real snapshots (ADR-0003). TIGER/Line® is a registered trademark of the
Census Bureau; nothing here repackages the files under another name.

## Layout

```
raw/<source>/2026-09-02/
  <data file(s)>      same file names, header, and record layout as the provider's
  terms.html          excerpt: the one paragraph the adapters check (the real page is 311 KB)
  source-page.html    (snap_retailers) excerpt: the two fragments of the provider's data
                      page the adapter checks
  manifest.json       built through phillysim.manifest; digests match the files here
```

| Source | Provider file(s) | Sample contents | After the filter |
|---|---|---|---|
| `tiger_tracts` | `tl_2025_42_tract.zip` (TIGER/Line 2025, Pennsylvania tracts, NAD 83) | a shapefile of 8 tracts with every TIGER attribute, zipped with fixed timestamps (the dBASE header's write date pinned too) | 6 tracts |
| `cenpop` | `CenPop2020_Mean_TR42.txt` (CenPop2020, Pennsylvania tract centers) | the provider's header (with its byte-order mark) and 8 rows, verbatim | 6 tracts |
| `acs` | `acsdt5y2024-b01003.dat`, `acsdt5y2024-b08201.dat` (ACS 5-year 2020–2024 table-based summary file) | the header, the nation and Pennsylvania rows, and 8 tract rows, verbatim | 6 tracts |
| `snap_retailers` | `snap-retailer-locator-data2005-2025.zip` (USDA SNAP Retailer Locator historical data, one CSV member) | the provider's header and 31 rows: the 26 retailers authorized as of 2025-12-31 whose points fall inside the six sample tracts, 2 closed Philadelphia spells, 2 open Adams County rows, 1 open Delaware row | 26 retailers (5 of them supermarket-format) |

The six Philadelphia County tracts are `42101000101`, `42101000102`,
`42101000200`, `42101000300`, `42101000401`, and `42101000403`; the two control
tracts, `42001030101` and `42001030103`, are in Adams County and exist so the
county filter demonstrably drops something. The ACS nation row carries a real
annotation value (`-555555555` as the MOE of a controlled estimate) and is
dropped as a non-tract row. The SNAP control rows exist so that each part of
that adapter's filter (state, county, open spell) demonstrably drops something.

## Regenerating

From `phillysim/`, after `phillysim run --stage spine` has admitted the pinned
snapshots into the data root and built the spine (the SNAP sample is cut by
point-in-tract against it):

```
uv run python tests/fixtures/spine-samples/build_samples.py [--data-root DIR]
uv run pytest tests/contracts tests/test_destinations.py tests/integration/test_real_pipeline.py
```

`build_samples.py` is deterministic for a given real snapshot. Regenerate only
when the pinned snapshot changes (a controlled refresh bumps
`phillysim.pipeline.SNAPSHOT_ID`) and say so in the changelog.
`tests/fixtures/.gitattributes` keeps every file here byte-exact on checkout.
