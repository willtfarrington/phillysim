# Data card: ACS 5-year 2020–2024 selected tables (`acs`)

**Contributes.** Survey estimates with margins of error on the spine's
tracts: the pinned variable list is `B01003_001` (total population, the
denominator for rate-type metrics and the population that CV tiers are
judged against) and `B08201_002` (households with no vehicle available, the
car-free context methodology.md states). Nothing more: adding a variable is
a methods-version bump (ADR-0006).

**Provider and files.** US Census Bureau, American Community Survey 5-Year
Estimates 2020–2024, **table-based summary file**:
`acsdt5y2024-b01003.dat` and `acsdt5y2024-b08201.dat` from
`https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/`
(pipe delimited; one row per geography at every summary level; estimate and
MOE columns interleaved). The Census data API is **not** used: it requires
a key, and the summary file carries the same numbers without one (EP-5a
decision), so reproducing the snapshot needs no secret.

**Vintage.** ACS 5-year, 2020–2024 (released December 2025), on 2020 tract
definitions. Pinned snapshot `2026-09-02`; the annual release is the
controlled-refresh cadence (roadmap/sources.md), each refresh a new snapshot
beside the old one.

**Terms and license.** US public domain (17 U.S.C. § 105); the Open
Government page in force archived as `terms.html`. The API Terms of Service
are not engaged. **Bucket A** (ADR-0003). Citation: "U.S. Census Bureau,
American Community Survey 5-Year Estimates 2020–2024, tables B01003 and
B08201".

**Coverage and filter.** Delivered nationwide; stored as delivered and
filtered at first read to the county's tract rows (`GEO_ID` prefix
`1400000US42101`), the pinned lines, and the data dictionary's
`<table>_<line>E` / `…M` column names.

**CRS.** None: attribute data joined on `geoid`.

**Where it lands.** `intermediate/acs_tracts.parquet` (one row per spine
tract; data dictionary, "Intermediate files"), consumed by the `metrics`
stage; estimates and MOEs flow into the analytic table's `estimate` / `moe`
columns with their CV tier and reliability action.

**Uncertainty.** Every estimate carries a **90 percent margin of error**
(the Bureau's default). The project propagates MOEs (methodology.md,
"Uncertainty"), classes reliability by coefficient of variation
(CV = (MOE / 1.645) / estimate; tiers below 12 %, 12–40 %, 40 % and above),
and displays interval-only views for the weakest tier. Provider annotation
values (`-999999999`, `-888888888`, `-666666666`, `-555555555`,
`-333333333`, `-222222222`) and blank cells become **null and stay null**
(ADR-0004): nothing is imputed or suppressed by the project. The pinned
snapshot has no null in any of the four columns for the 408 tracts.

**Known limits (real snapshot, 2026-09-02).**
- Five-year estimates describe the 2020–2024 period as a whole, not any one
  year, and lag the 2020 Census count they sit beside: `B01003_001E` is not
  the spine's `population` and will differ tract by tract.
- Tracts with tiny populations (the `980x` series) have estimates of zero
  or near zero with MOEs larger than the estimate; their CV tier will be 3
  wherever a rate is formed, and the reliability flag, not the project,
  decides what is shown.
- `B08201_002` counts **households** without a vehicle, not people, and is
  context for the walk and transit framing; it is not an access measure and
  is never combined into a score.
- Tract-level ACS MOEs are large in general; sorted views carry
  margin-of-error caveats by rule (C-3).

**Claims matrix.** Estimates are published with their MOE and reliability
flag, never as a ranking or composite (C-3); "households with no vehicle
available" is the Bureau's own variable label and is not turned into a
deprivation or risk label (C-2, C-4); nothing here measures food insecurity
or diet quality (C-1).

**Checks that bind it.** Source contract (`phillysim.adapters.acs`: the
pinned columns, non-negative, nullable), the join invariants (exactly one
ACS row per spine tract, none unmatched, MOE columns present), and the
snapshot manifest.
