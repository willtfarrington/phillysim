# ADR-0008: Routing toolchain pins, extents, dates, and the spike's decision numbers

Status: accepted (EP-11, 2026-09-03; owner-reviewed: every value below was put to the owner as a numbered question and the recommended option accepted; the review is recorded in the EP-11 handoff). **Amended 2026-09-03 (EP-13, owner decision): the R5 jar pin** moved from `r5-v7.6-r5py-all.jar` to `r5-v7.5.1-r5py-all.jar`; see the jar entry and the amendment note below.

## Context
ADR-0001 and architecture.md say the routing engine is r5py on a
"project-local pinned Temurin JDK 21 (exact build)" with "R5 jar pinned by
checksum", and methodology.md fixes the travel model's parameters, but no
document names a build, a jar, a checksum, a street-network extent, a
transit feed release, the calendar dates behind "pinned typical Wednesday",
the determinism band AM-2 allows, or the tolerance behind "≥ 80 % of
hand-checked OD times within tolerance". The M3 refinement gate (EP-11)
must fix them so the spike's packets (EP-12 to EP-15) run against written
numbers. Each is hard to reverse once the spike has measured against it,
so they are recorded here rather than in a packet handoff. Values were
looked up on 2026-09-03 from the providers' own release records; none was
downloaded or installed by the gate.

## Decision

### Toolchain (EP-13 installs; EP-12 adds the Python side)
- **JDK:** Eclipse Temurin **21.0.12.1+1** (release `jdk-21.0.12.1+1`,
  published 2026-08-19; the current JDK 21 LTS build on the decision
  date). Windows x64: `OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip`,
  205,073,461 bytes, SHA-256
  `f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e`.
  Linux x64 (the documented WSL2 fallback; CI never runs the JVM):
  `OpenJDK21U-jdk_x64_linux_hotspot_21.0.12.1_1.tar.gz`, 207,473,347
  bytes, SHA-256
  `ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94`.
  Installed under `<repo>/phillysim/.jdk/jdk-21.0.12.1+1/` (gitignored),
  never on `PATH` or in the system; `JAVA_HOME` is set in the routing
  child's environment per invocation and nowhere else.
- **R5 jar (amended 2026-09-03, EP-13):** `r5-v7.5.1-r5py-all.jar` from the
  r5py project's R5 build (release `v7.5.1-r5py`, 2026-05-08, R5 7.5.1 with
  the r5py patches; **the jar r5py 1.1.7 pins in its own source**,
  `r5py/util/classpath.py`), 64,437,972 bytes, SHA-256
  `d50be106cadd7b636cfc0e209052767d7df570629f79fdf98ecd5cf5d2d89be7`.
  Installed at `<repo>/phillysim/.r5/r5-v7.5.1-r5py-all.jar` (gitignored)
  and always passed to r5py as its classpath, so r5py's own download path
  is never exercised (the harness refuses to import r5py unless that file
  exists and refuses to route unless r5py resolved exactly that path).
  *Amendment note.* The gate recorded `r5-v7.6-r5py-all.jar` (release
  `v7.6-r5py`, 2026-08-03; 65,104,016 bytes; SHA-256 `bb3935be…0eb5`) as
  "the jar r5py 1.1.7 itself pins"; that was wrong: r5py 1.1.7 (PyPI's
  latest on the amendment date) pins v7.5.1, and only r5py's unreleased
  `main` branch pins v7.6. EP-13's first smoke run on the v7.6 jar failed
  inside r5py's `TransportNetwork` build (`com.conveyal.osmlib.OSM` has
  only a private constructor in R5 7.6; r5py 1.1.7 calls the public one),
  the packet's stop condition. The owner chose the jar r5py 1.1.7 pins
  over waiting for an r5py release that targets v7.6; every other pin is
  unchanged. Moving to R5 7.6 later is a new amendment with a matching
  r5py release and a methods-version bump (ADR-0006).
- **Python side:** `r5py==1.1.7` (2026-06-29) with `jpype1==1.7.1` and
  `psutil==7.2.2`, in an optional `routing` dependency group of the
  locked stack; all wheels on Windows and Linux for Python 3.13
  (resolved wheel-only on the decision date). CI does not install the
  group; nothing CI imports imports r5py (importing it starts the JVM).
  `psutil` is a core dependency (the RSS sampler). `osmium` (pyosmium
  4.3.1, wheels on both platforms) is a core dependency for the extract
  clip. `osmnx` 2.1.1 and `scipy` 1.18.1 join the routing group at EP-15
  for the concordance check and the fallback.
- **JVM settings per invocation:** heap 12 GB (`--max-memory 12G`),
  `JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=8` (architecture.md's ≤ 8
  of 16 logical processors), r5py's cache and temporary directory under
  `<data root>/cache/r5py/`, CPU only.

### Street network (EP-12)
- **Source:** the Geofabrik **dated** Pennsylvania extract
  `pennsylvania-260831.osm.pbf` (generated 2026-09-01, data current to
  2026-09-02T20:20:51Z; 345,912,530 bytes; provider MD5
  `a779d2ef14c8addce6eac207ab9cd851`), ODbL 1.0, Bucket B; stored as
  delivered; never the `-latest` file. Geofabrik defines no sub-region
  for Pennsylvania.
- **Extent used for routing:** the county bounds
  (`adapters.base.COUNTY_BOUNDS`) buffered by **5 km**, clipped from the
  stored extract with pyosmium at first read (way-complete), written to
  `intermediate/network/`, Bucket B by derivation. Rationale: R5 builds a
  street layer for the whole file it is given; the state is 345 MB of PBF
  against a 12 GB heap and a 20 GB budget, and the spike should measure
  routing, not the state's build; 5 km covers walking access to every
  stop a Philadelphia trip can use. **Recorded fallback:** feed R5 the
  whole state extract if the clip tool cannot be installed from wheels
  (decided with the owner at that point).

### Transit feed (EP-12)
- **Source:** SEPTA's GTFS as published by SEPTA on GitHub, release tag
  **`v202609060`** (2026-09-02; "Summer RR, Fall Bus-Metro, Sept
  Adjustments"), asset `gtfs_public.zip`, 21,555,258 bytes, SHA-256
  `4d3fa20ea094937a9bb6389ad52017e1ac90a564aee497f318797e1b1e4f07ab`,
  holding `google_bus.zip` (Bus/Metro; authoritative 2026-09-06 to
  2027-02-20) and `google_rail.zip` (Regional Rail; authoritative
  2026-09-06 to 2026-10-17). **Both feeds** are used. Terms: SEPTA's
  developer license agreement (revocable, no fee today but reservable,
  no alteration or commercial use of SEPTA's marks), archived and
  sentence-checked at every acquisition; the raw feed is never
  republished; computed travel times are facts and carry no feed
  contents (ADR-0003, DATA-LICENSES). The feed's own bucket is A.

### Calendar (EP-14)
- **Pinned typical Wednesday: 2026-09-23**, departures 08:00–20:00 local,
  one per minute (720). **Saturday window: 2026-09-26**, same hours. Both
  lie inside both feeds' authoritative windows, after Labor Day week and
  the New Bus Network's first phase (2026-08-23/24), with schools in
  session. Time zone America/New_York. A later feed release moves these
  dates only with a new snapshot and a methods-version bump (ADR-0006).

### Snapshot IDs (EP-12)
- Snapshot IDs are **per source** (`pipeline.SNAPSHOT_IDS`), as
  architecture.md and quality.md already state; the five sources acquired
  on 2026-09-02 keep that ID, and a source acquired later takes its own
  acquisition date. A controlled refresh changes one source's entry and
  is recorded in the changelog.

### The spike's decision numbers (EP-14, EP-15)
- **Run matrix and the wall criterion:** origins = the 408 CenPop
  centers; destinations = all 1,609 SNAP retailers (the 164
  supermarket-format ones are a subset); the **≤ 8 h wall** applies to
  the two core runs together (walk 4.8 km/h; walk+transit 4.8 km/h on
  the Wednesday window); the slow-walk (3.0 km/h) and Saturday runs and
  the determinism repeats run the same night and are timed and reported,
  not judged.
- **Determinism band (OQ-C):** measured as the pair-by-pair comparison of
  a core run and its repeat on the pinned Windows environment (integer
  minutes; canonicalized-value digest and byte digest both recorded).
  **Within band** = every pair identical, or at least 99.9 % of pairs
  identical with no difference above 1 minute; the measured numbers
  become the documented variance band of AM-2 / quality.md. Wider goes to
  the owner (widen with a claims-wording change, or kill). *Measured
  2026-09-03 (EP-15, not an amendment):* on the first night both core runs
  were identical to their repeats pair for pair (656,472 of 656,472 each,
  both columns; byte and value digests equal); the band as written stands
  and OQ-C is closed with it.
- **Hand-check tolerance:** ten OD pairs by rule (EP-15), two departures
  (08:30, 17:30) on the pinned Wednesday, both modes, forty checks
  against a public trip planner by hand (never a data source); walk
  within 3 minutes or 15 % (the larger), walk+transit within 10 minutes
  or 25 % (the larger); the gate is 32 of 40.
- **Outputs and publication:** run records under `<data root>/runs/
  routing/`; on go the matrix becomes `curated/travel_times.parquet` in
  the data dictionary's shape through a `travel_times` stage; the spike
  publishes nothing and the public zone stays Bucket A until M5.
- **Time box:** three attended spike sessions (EP-13, EP-14, EP-15) after
  the sources packet (EP-12) and this gate (EP-11), plus unattended
  nights; one owner-approved extension = one further attended packet and
  one more night; the verdict session calls TIMEBOX-EXHAUSTED and the
  owner confirms; the fallback packet follows the verdict.

## Alternatives considered
- **A newer or older JDK 21 build**: any 21.x would run R5 7.5.1 (or 7.6); the
  current LTS build was chosen because it is what Adoptium serves today
  and its checksum is published beside it. A JDK 17 or 25 is not
  supported by R5 7.x.
- **Conveyal's own R5 jar** instead of the r5py build: r5py pins its
  patched build and verifies it by checksum at start-up; using another jar
  would fight the library.
- **The whole state extract without a clip**: kept as the recorded
  fallback; rejected as the default for the reasons above.
- **A third-party city-level extract** (BBBike, Protomaps): a different
  provider with its own terms and no dated, checksummed file; rejected.
- **Bus feed only**: Regional Rail carries Philadelphia trips too and the
  cost of the second feed is small; rejected.
- **A single `SNAPSHOT_ID` bumped for every source**: would re-acquire
  five byte-identical files under a new ID for no information; rejected.
- **A looser band from the start** (for example 5 % of pairs, 5 minutes):
  would pre-empt what the spike is for; the band is set at the
  granularity of the method and widened only on evidence.

## Consequences
The spike's packets carry these values verbatim and their tests pin them;
changing any of them is an amendment to this ADR with a date. The
toolchain is a dependency axis (ADR-0006) recorded in `toolchain.json`
and the lock, not in the repository's tracked files beyond this ADR. The
first Bucket B source enters the real pipeline; every file computed over
the clipped network is ODbL by derivation. The calendar dates are methods
parameters. The M5 gate inherits the sensitivity runs' timings and the
second-night verification as carry-ins.
