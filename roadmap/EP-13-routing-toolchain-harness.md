# EP-13 — Routing toolchain and harness: pinned JDK 21 and R5 jar, r5py behind the wheel-only rule, the RSS sampler, run records, the smoke route

**Status:** [~] work complete 2026-09-03 (the smoke green on the amended ADR-0008 jar pin); the status commit marks it done · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

## Outcome & value
The routing engine exists on the machine under the project's control and
nothing else's: the exact Temurin JDK 21 build and the exact R5 jar of
ADR-0008, downloaded once through the guarded path, verified against the
recorded checksums, installed project-local (never on `PATH`, never in the
system), with `JAVA_HOME` set per invocation; r5py and its Java bridge in
the locked stack as an optional dependency group, installed from wheels,
imported by nothing CI runs. Around it, the harness the spike's numbers
come from: a process-tree RSS sampler at ≥ 1 Hz that kills the tree at
22 GB, a wall clock, and a run record in a fixed shape scrubbed of machine
identifiers. The packet ends with the first JVM run of the project, a
smoke route on the clipped network EP-12 built (one tract center to one
supermarket-format retailer, walk and walk+transit), three times, with the
first peak-RSS number the project has ever measured and the first
determinism observation. The CI performance-smoke test quality.md deferred
to this milestone lands here, measuring the fixture stages with the same
sampler (CI never runs the JVM).

## Scope
- in:
  1. **`phillysim toolchain install` / `check`.** Installs into
     `<repo>/phillysim/.jdk/jdk-21.0.12.1+1/` (from
     `OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip`, 205,073,461
     bytes, SHA-256
     `f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e`;
     on Linux the `…_linux_hotspot_21.0.12.1_1.tar.gz`, 207,473,347 bytes,
     `ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94`)
     and `<repo>/phillysim/.r5/r5-v7.6-r5py-all.jar` (65,104,016 bytes,
     SHA-256
     `bb3935be2edd2fc5a20726600440bb4561f5ab2ce5d9d64c6b9cc6ca19260eb5`,
     the jar r5py 1.1.7 itself pins). Both through `phillysim.download`
     (allowlist `github.com`, `objects.githubusercontent.com`; caps 256 MiB
     file / 1 GiB extracted / ratio 10 / 2,000 members for the JDK archive,
     which **is** extracted, under the zip-slip and bomb guards, into the
     project-local directory; 128 MiB for the jar, not an archive to the
     guards), digest verified before installation, a mismatch deleting the
     download. A `toolchain.json` beside them records what was installed
     and its digests. `check` reports the JDK's `java -version` string (must
     contain `21.0.12.1`), the jar's digest, and the r5py / JPype1 / psutil
     versions; the real-run preflight gains the same check when a routing
     verb is invoked. Both directories are already gitignored (`.jdk/`,
     `*.jar`); `.r5/` is added.
  2. **r5py in the locked stack as the `routing` dependency group**
     (`r5py==1.1.7`, `jpype1==1.7.1`, `psutil==7.2.2`, and what they pull:
     `rasterio`, `scikit-learn`, `geohexgrid`, `simplification`, `joblib`,
     `requests`, `filelock`, `configargparse`; all wheels on Windows and
     Linux for Python 3.13, resolved 2026-09-03 with `uv pip compile
     --only-binary :all:`; none of them is `GDAL` or `fiona`, so the
     dependency policy test stays green on the new lock). Installed
     locally with `uv sync --locked --group routing`; **CI does not install
     the group and no module CI imports imports r5py** (importing r5py
     starts the JVM and, without the jar, downloads it: verified in
     r5py's source, `r5/transport_network.py` calls `start_jvm()` at import).
     `psutil` (the sampler's dependency) goes into the core dependencies so
     the CI performance-smoke test can use it.
  3. **The routing subprocess and its environment.** Every JVM run happens
     in a child process (`phillysim.routing.harness`), never in the CLI
     process, with an environment built per invocation: `JAVA_HOME` = the
     project-local JDK; `JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=8` (the
     architecture.md parallelism cap; R5 sizes its thread pool from the
     processor count); r5py's arguments `--max-memory 12G`
     (the 12 GB heap), `--r5-classpath <the jar>`,
     `--temporary-directory <data root>/cache/r5py/tmp`; and r5py's cache
     directory pointed under the data root (`<data root>/cache/r5py`; r5py
     resolves it from `LOCALAPPDATA` on Windows and `XDG_CACHE_HOME` on
     Linux, so the child's environment sets those; r5py writes the built
     network there as `<digest>.mapdb` and expires cache files older than
     two weeks). r5py copies its inputs to working copies, so the raw
     zone is never written beside. `PATH` is untouched. The child's
     stdout / stderr go to the run record's log.
  4. **The process-tree RSS sampler and the wall clock.** A thread in the
     parent samples the child and all its descendants with psutil at
     ≥ 1 Hz (1 Hz default, 4 Hz around start-up), records the peak sum of
     RSS, the time series (`rss.csv`: UTC second, bytes), and kills the
     whole tree (children first) when the sum reaches **22 GB** (the
     architecture.md kill; the budget line at 20 GB is recorded when
     crossed). Wall time from the child's start to exit. Unit-tested with a
     scripted child that allocates memory in steps and with a fake sampler
     clock.
  5. **The run record.** `<data root>/runs/routing/<run-id>/` with
     `plan.json` (what was asked: mode, speed, window, dates, origin and
     destination sets and counts, percentiles), `record.json` (outcome:
     `completed` / `killed-rss` / `failed` / `cancelled`; wall seconds;
     peak RSS bytes and the second it occurred; whether the 20 GB budget
     was crossed; the toolchain digests; r5py and jar versions; the
     inputs' digests; the output's byte digest and canonicalized-value
     digest), `rss.csv`, `log.txt`, and the output table. Paths inside are
     relative to the data root; the data root is scrubbed like the state
     file; `data/runs/` is gitignored. `<run-id>` =
     `<UTC timestamp>-<plan slug>`.
  6. **The smoke route** (`phillysim route smoke`): `TransportNetwork` on
     EP-12's clipped PBF and the two GTFS zips; one origin (the spine
     center of the tract containing City Hall, `42101000500` or the
     tract the session confirms) to one supermarket-format retailer (the
     nearest by the QA slice); `TravelTimeMatrix` for walk at 4.8 km/h and
     for walk+transit at 4.8 km/h on the pinned Wednesday with a
     60-minute window and percentiles 50 and 85; `max_time` 120 min. Run
     three times in a row; record each run; assert the three outputs'
     canonicalized-value digests are equal (the first determinism
     observation, recorded whichever way it goes) and that every RSS
     sample is under 22 GB. Also a single-departure mode of the same call
     (window one minute) that EP-15's hand check uses.
  7. **CI performance smoke** (`tests/test_performance_smoke.py`): runs
     `phillysim run --fixture` under the sampler and asserts wall under
     60 s and peak process-tree RSS under 2 GiB (generous bounds; the
     purpose is that the measurement exists and the machinery runs on both
     platforms), writing the numbers to the test log; the quality.md test
     matrix row flips to "yes".
- out (explicit non-scope): the run matrix and any run over the full
  origin set (EP-14); the verdict (EP-15); replacing the fixture's
  `network` / `travel_times` stubs (owner decision at EP-11, question 6:
  they stay stubs; CI never runs the JVM); a Docker or WSL path; a
  Linux-side smoke run.

## Prerequisites & locked decisions
- prerequisites: EP-12 (the clipped network and the feed exist).
- locked decisions honored: ADR-0001 (project-local pinned JVM;
  everything Python from wheels; the `GDAL` / `fiona` ban); ADR-0008 (the
  exact JDK build, the jar, the locations, `JAVA_HOME` per invocation, the
  heap, the processor cap, the cache under the data root);
  architecture.md "Resource budgets" (20 GB budget, 22 GB kill, sampled
  ≥ 1 Hz, ≤ 8 of 16 processors) and "Security" (allowlist, caps, guards on
  the JDK archive); methodology.md "Travel model" (r5py, 12 GB heap, CPU
  only, 4.8 km/h, the departure convention; note r5py's default walking
  speed is 3.6 km/h and must be set explicitly on every call); quality.md
  ("Performance smoke" lands here; CI offline); the state-file scrub rule
  for the run record.
- dependencies: `github.com` / `objects.githubusercontent.com` for the JDK
  (205 MB) and the jar (65 MB); PyPI for the routing group.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the JDK and the jar are
downloaded once, verified against the recorded checksums before anything
is installed, and installed project-local (never on `PATH`, never in the
system, never in the repository: `.jdk/`, `.r5/`, and `*.jar` are
gitignored and the diff is checked for them); the JDK archive is
extracted only under the zip-slip and bomb guards; the RSS sampler kills
the process tree at 22 GB and is tested to; the routing child writes only
under the data root (`cache/r5py`, `runs/routing`) and its own working
copies, never beside a raw file; CI stays offline and never runs the JVM
(the routing group is not installed in CI and a test asserts that no
module under `phillysim` imports r5py at module level outside
`phillysim.routing`); no machine identifier, user name, or absolute path
enters a tracked file or a run record (the record scrubs the data root
and the repository root); no secret; r5py's own jar download path is never
exercised (the classpath argument always names the installed jar and a
test asserts the argument is passed).

## Likely components & contracts (proposed)
`src/phillysim/routing/{__init__,toolchain,harness,sampler,records,smoke}.py`
(only `harness` and `smoke` import r5py, inside functions run in the
child), `cli.py` (`toolchain install|check`, `route smoke`),
`preflight.py` (toolchain check for routing verbs), `pyproject.toml` +
`uv.lock` (`routing` group; `psutil` core), `.gitignore` (`.r5/`,
`data/runs/`), `tests/test_toolchain.py` (crafted archives and digests, no
network), `tests/test_sampler.py`, `tests/test_records.py`,
`tests/test_performance_smoke.py`, `tests/test_no_jvm_in_ci.py`,
`docs/data-dictionary.md` (the run record shape; `runs/` as a data-root
directory), `phillysim/README.md` (toolchain, routing verbs, the
"Resource baselines" first peak-RSS line), `roadmap/quality.md` (test
matrix), `CHANGELOG.md`, this file.

## Implementation notes
Order of work: the toolchain verb and its tests first (crafted zip with a
slip entry, a bomb, a wrong digest), then the group and the lock (run the
dependency policy test), then the sampler with a scripted child, then the
record, then the smoke run. Set `JAVA_HOME` and the r5py arguments in the
child only; r5py reads its arguments through `configargparse`, so pass
them as `sys.argv` of the child or as an `r5py.yml` written under
`<data root>/cache/r5py/` per invocation (the latter is easier to
record; write it into the run record). The first `TransportNetwork` build
on the clipped extract is the first real timing: record build wall and
RSS separately from routing wall and RSS. If r5py's two-week cache
expiry would rebuild the network between EP-14's nights, EP-14 must
account for it (record the build time here so EP-14 can). Keep the
smoke's three outputs; their digests are the first OQ-C evidence. Add
the peak-RSS line to `phillysim/README.md` "Resource baselines" (the
EP-10 table said "deferred to the M3 spike harness").

## Acceptance criteria & evidence
- [x] `phillysim toolchain install` from a clean state installs the JDK
      and the jar with the recorded digests; `toolchain check` reports
      `21.0.12.1` and the jar digest; a wrong digest is refused (tested on
      crafted bytes); nothing lands on `PATH` or outside the two
      directories.
- [x] `uv sync --locked --group routing` installs r5py 1.1.7 and JPype1
      1.7.1 from wheels on Windows; `uv run pytest` green with and without
      the group installed; the dependency policy test green; the
      no-JVM-in-CI test green; CI green on both platforms without the
      group.
- [x] The sampler kills a scripted child tree at the threshold and records
      a peak within one sample of the true peak (tested).
- [x] `phillysim route smoke` completes three runs; each record has wall,
      peak RSS, digests, and outcome `completed`; the three
      canonicalized-value digests are recorded (equal or not); no sample
      reached 22 GB.
- [x] The CI performance-smoke test runs on both platforms and records
      fixture wall and peak RSS.
- Evidence: CI run; the three smoke records' numbers in the handoff; the
  "Resource baselines" line.

## Tests / validation
`uv run pytest` (with and without the routing group); `pre-commit run
--all-files`; `phillysim toolchain install`, `toolchain check`, `route
smoke` by hand with the console output kept; a scan of the diff for
`.jdk/`, `.r5/`, `*.jar`, machine identifiers, and absolute paths.

## Resource budget
Network: about 270 MB once (JDK 205 MB, jar 65 MB) plus the routing
group's wheels. Disk: the JDK unpacked (about 300 MB) and the jar under
`phillysim/`; r5py's cache under the data root (the built network, tens
to hundreds of megabytes). RAM: the JVM at 12 GB heap plus Python; the
sampler reports the real number (budget 20 GB, kill 22 GB). Runtime: the
network build plus three short routes, minutes. Session: one, attended.

## Risks, rollback, stop condition
JPype cannot find or start the pinned JVM → **stop**; do not install any
other JDK; record the error. The smoke route's RSS reaches 22 GB on the
clipped extract → the sampler kills it → **stop**: that is a spike
finding (KILLED-BY-EVIDENCE territory if it holds on a re-check with the
build and the route separated), surfaced to the owner before EP-14. The
three smoke outputs differ → not a stop: record the differences; EP-15
measures the band on the matrix. The routing group fails to resolve as
wheels on Linux → the group is Windows-only in the lock markers and the
Linux fallback is documented, not a stop (CI never installs it). r5py
1.1.7 rejects the pinned jar or the JDK → **stop**; the pins are
ADR-0008's and change only with the owner. Rollback: the group is one
lock change; the toolchain directories are deleted by hand; the code
reverts cleanly.

## Documentation / ADR updates
`phillysim/README.md` (toolchain, routing verbs, baselines),
`docs/data-dictionary.md` (run record, `runs/`), `roadmap/quality.md`
(performance-smoke row), `roadmap/architecture.md` (stage table row 9's
note: the real body arrives with EP-15 on go), CHANGELOG, the packet row.
ADR-0008 is referenced, not changed; a pin that must change goes back to
the owner as an amendment.

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-13 — done at commit `<work-commit>` (+ the status commit),
  2026-09-03, one session, at the S estimate (the stop condition below cost
  about ten minutes: a diagnosis, an owner decision, a jar reinstall, and a
  re-run of the smoke); Planning Baseline v1.0. CI run: recorded in the
  status commit. Owner review at the end of this payload.
- **Files changed.** New: `phillysim/src/phillysim/routing/{__init__,
  toolchain,sampler,records,harness,smoke}.py`, `tests/test_toolchain.py`,
  `tests/test_sampler.py`, `tests/test_records.py`,
  `tests/test_routing_harness.py` (the brief's `test_harness.py` name is
  taken by `tests/contracts/test_harness.py`; pytest refuses two modules
  with one basename), `tests/test_no_jvm_in_ci.py`,
  `tests/test_performance_smoke.py`. Changed: `guards.py`
  (`safe_link_target`, `inspect_tar`, `extract_tar`), `preflight.py`
  (`psutil` in the locked packages; `run_preflight(extra=…)`), `cli.py`
  (`toolchain install|check`, `route smoke`, a `__main__` guard),
  `pyproject.toml` + `uv.lock` (`psutil` core; the `routing` group),
  `.gitignore` (`.r5/`, `data/runs/`, `phillysim/toolchain.json`),
  `roadmap/adr/0008-routing-toolchain-pins.md` (the jar amendment),
  `phillysim/README.md`, `docs/data-dictionary.md`, `roadmap/quality.md`,
  `roadmap/architecture.md`, `CHANGELOG.md`, `roadmap/README.md`, this
  file.
- **Commands/tests run + results.** `uv lock` then `uv sync --locked
  --group routing`: 18 packages added from wheels (affine, attrs, click,
  cloudpickle, configargparse, geohexgrid, joblib, jpype1 1.7.1, narwhals,
  psutil 7.2.2, pyparsing, r5py 1.1.7, rasterio 1.5.1, scikit-learn 1.9.0,
  scipy 1.18.1, simplification 1.0.0, threadpoolctl 3.6.0; `.venv` 480 MB →
  738 MB); `uv pip compile --only-binary :all:` for `windows` and `linux` on
  Python 3.13 resolves the group to the same 31 packages (Windows adds
  `tzdata`), so the lock carries no Linux marker and the Linux fallback
  needs no documenting; `uv lock --check` clean; `uv run pytest` → **583
  passed, 3 skipped** in 43 s (516 before; the three skips are the
  real-data-root tests), with the routing group installed and no r5py
  imported by the suite (asserted); the dependency policy test green on the
  new lock (none of the 18 is `GDAL` or `fiona`); the no-JVM-in-CI test
  green; `ruff check` / `ruff format --check` clean; `pre-commit run
  --all-files` all hooks passed; the diff scanned for user names, machine
  identifiers, and absolute paths → none; `git ls-files` shows nothing
  under `.jdk/`, `.r5/`, no `*.jar`, no `toolchain.json`, nothing under
  `data/`. Without the group the suite also passes: every routing test runs
  on crafted archives, scripted children, and fake probes (CI proves it on
  both platforms).
- **The toolchain install (console kept).** First install, against the
  gate's pins: the JDK zip **205,073,461 B in 14.8 s**, sha256
  `f9d6e191…8b4e` = the pin; 490 archive members extracted under the
  guards (256 MiB / 1 GiB / ratio 10 / 2,000); `java -version` → `openjdk
  version "21.0.12.1" 2026-08-18 LTS` (ADR-0008 says published 2026-08-19;
  the build's own date string is the 18th); the jar `r5-v7.6-r5py-all.jar`
  **65,104,016 B in 4.8 s**, sha256 `bb3935be…0eb5` = the gate's pin;
  `.jdk/` 329 MB, `.r5/` 63 MB; about 20 s in all; `toolchain check` all
  four checks ok. After the amendment (below): `.r5/` deleted by hand,
  `toolchain install` re-run → the JDK found installed and verified (no
  download), the jar `r5-v7.5.1-r5py-all.jar` **64,437,972 B in 1.5 s**,
  sha256 `d50be106…9be7` = the amended pin, `.r5/` 62 MB; `check` ok.
  Both downloads redirected from `github.com` to
  `release-assets.githubusercontent.com` (the host EP-12 observed).
- **The group's wheel list:** above (18 wheels; the routing three plus
  what r5py pulls: rasterio, scikit-learn, scipy, geohexgrid,
  simplification, joblib, configargparse, cloudpickle, affine, attrs,
  click, narwhals, pyparsing, threadpoolctl; `requests` and `filelock`
  were already in the tree through `osmium`).
- **The smoke route on the gate's jar (the stop condition).** `phillysim
  route smoke` → preflight green (the real-run thresholds plus the four
  toolchain checks), the plan: origin the spine center of tract
  `42101000500` (contains City Hall, confirmed against the spine),
  destination `snap_retailers:1298051` (MOM's Organic Market, 239.9 m
  straight-line by the QA rule), walk and walk+transit at 4.8 km/h,
  2026-09-23 08:00 America/New_York, 60-minute window, percentiles 50 and
  85, `max_time` 120 min, on `intermediate/network/` (the clip
  49,968,756 B sha256 `1f87cacb…`, the two feed zips). Run
  `20260903T212734Z-smoke` → **`failed` at 8.5 s**, peak RSS 0.33 GB, 31
  samples: `TypeError: Java class has no constructors` at
  `com.conveyal.osmlib.OSM(...)` in r5py's `TransportNetwork.__init__`.
  Diagnosis (`javap` on the installed jar): R5 7.6's `OSM` has one
  **private** constructor and static factories; r5py **1.1.7 calls the
  public constructor**, and its own `util/classpath.py` pins
  `r5-v7.5.1-r5py-all.jar` (SHA-256 `d50be106cadd7b636cfc0e209052767d7df5
  70629f79fdf98ecd5cf5d2d89be7`, release `v7.5.1-r5py`, 2026-05-08,
  64,437,972 B); r5py's unreleased `main` pins v7.6; PyPI's latest r5py is
  1.1.7. The gate's sentence "the jar r5py 1.1.7 itself pins" was wrong for
  the file it named; every other pin held (the JDK's digest and version, the
  jar's digest and size, JPype starting the JVM from the project-local JDK
  with the pinned classpath honored: the constructor error proves the v7.6
  classes were loaded). The record is kept under `data/runs/routing/`.
- **The diagnostic before the decision (not the pinned toolchain).** The
  v7.5.1 jar fetched through the guarded path (digest verified) into a
  scratch toolchain home under the session scratchpad (the JDK reached
  through a directory junction; the project's `.r5/` untouched), the smoke
  plan run through the real harness; records under
  `data/runs/routing-diagnostic/` (slug `smoke-diag-v751`; kept by owner
  decision). Cold: 45.3 s, peak RSS 4.81 GB; cached network: 8.0 / 6.3 /
  6.4 s, 2.36 / 2.45 / 2.54 GB; four completed runs with identical
  canonicalized-value digests. **Honest note:** in the diagnostic the
  child's `--r5-classpath` named a file that did not exist (the session's
  rename of the jar constant lived only in the parent process) and r5py
  **silently fell back to its own download** of the same v7.5.1 jar
  (checksum-verified by r5py; identical bytes) into `data/cache/r5py/`, so
  the safety precondition "r5py's own jar download path is never
  exercised" was breached once, in the diagnostic only; the copy was
  deleted and the harness child now **refuses to import r5py unless the
  installed jar exists and refuses to route unless r5py resolved exactly
  that path** (`ClasspathError`, tested; `phases.json` records the
  resolved classpath's name), so it cannot recur. One diagnostic run failed
  in 0.3 s with a `SyntaxError` because the harness module was being edited
  at that moment; unrelated to routing.
- **The smoke route on the pinned toolchain (after the amendment; r5py's
  network cache cleared first so run 1 builds cold).** Three runs, every
  record `completed`, the three canonicalized-value digests **equal**
  (`cab6893edad3bb3aefda1671fc4f9280c1bb131bc796a3127675ece9e52d007a`) and
  the three byte digests equal (`0298735475b2…`): the first determinism
  observation (OQ-C), on one pair, two modes, 60-minute window.
  | run | wall | peak RSS (when) | phases |
  |---|---|---|---|
  | `20260903T214412Z-smoke` (cold) | 45.1 s | **4.94 GB** at 36.9 s, 160 samples | import 1 s at 0.33 GB; **network build 43 s at 4.94 GB**; walk route under 1 s and walk+transit route under 1 s at 4.72 GB |
  | `20260903T214458Z-smoke` (cached network) | 6.2 s | 2.52 GB at 5.9 s, 22 samples | import 2 s; build from cache 2 s at 2.19 GB; routes about 1 s |
  | `20260903T214504Z-smoke` (cached network) | 6.2 s | 2.43 GB at 5.7 s, 22 samples | import 2 s; build from cache 2 s at 2.40 GB; routes about 1 s |
  | `20260903T214511Z-smoke-single` (`--single-departure`, a one-minute window) | 5.8 s | 2.43 GB, 21 samples | the same values; r5py's below-five-minutes warning in `log.txt` |
  Output: walk p50 = p85 = **4 min**, walk+transit p50 = p85 = **4 min**
  (a 240 m pair; transit never wins it). No sample reached the 22 GB line
  or the 20 GB budget. r5py's cache after the build:
  `<digest>.transport_network` 397 MiB, `.mapdb.p` 101 MiB, `.mapdb` 4 MiB;
  the three inputs are symlinks into `intermediate/network/` (Windows
  Developer Mode allows them); nothing written beside the raw or
  intermediate files; the harness now removes the temporary directories
  R5 leaves behind after a killed or failed child.
- **CI performance smoke:** `phillysim run --fixture` under the sampler:
  **1.3 s wall, peak RSS 140 MiB** (146,747,392 B), 10 samples at 10 Hz on
  Windows; the Linux numbers are printed in the CI log (recorded in the
  status commit).
- **Resource observations:** one session, at the S estimate. Network:
  270 MB for the gate's toolchain, 64 MB more for the amended jar (and 64 MB
  for the diagnostic's copy), about 260 MB of wheels; under a minute in all.
  Disk: `.jdk/` 329 MB, `.r5/` 62 MB, `.venv` +258 MB, r5py's cache about
  500 MB under the data root, run records about 12 KB each. RAM: **peak
  process-tree RSS 4.94 GB** for a cold network build on the 50 MB clip
  with a 12 GB heap; **2.4–2.5 GB** with the cached network; against the
  20 GB budget and the 22 GB kill there is room for the state-extract
  fallback several times over. Time: the network build is 43 s cold and 2 s
  from cache; one pair routes in about a second per mode; the sampler ran
  at 4 Hz for the first minute (160 samples over 45 s). Suite +67 tests,
  +6 s.
- **Decisions made (routine, agent's call, logged):** `toolchain.json` at
  `phillysim/toolchain.json` (beside `.jdk/` and `.r5/`; one more ignore
  line); `runs/` is a data-root directory like `fixture/`, not a zone
  (`phillysim paths` unchanged); the run's output table is CSV in canonical
  row order (byte-deterministic), not Parquet, and the byte digest is of
  that file; the roots scrubbed are `<data-root>`, `<toolchain-home>` (the
  project directory, which also holds `.venv`), and `<repo-root>`; r5py's
  arguments go on the child's `sys.argv` rather than into an `r5py.yml`
  (recorded in `child.json`); `APPDATA` / `XDG_CONFIG_HOME` point under the
  cache so no user-level `r5py.yml` is read or written; the sampler's `GB`
  is decimal (`10**9`, as `preflight.GB`), so the lines are 20,000,000,000
  and 22,000,000,000 bytes; phase peaks come from the series and the
  child's UTC phase stamps; `guards.extract_tar` allows only files,
  directories, and in-root relative symlinks (Temurin's Linux tarball ships
  `lib/server/libjsig.so -> ../libjsig.so`), copies where the platform
  refuses symlinks, and writes Windows-style link targets on Windows; the
  child writes `phases.json` even on failure; the classpath guards; the
  temporary-directory cleanup; the test module's name. **Owner-level
  decisions** below.
- **Unresolved risks / questions:** r5py's cache expiry is two weeks from
  a file's access or modification time: EP-14 should expect at most one
  43 s rebuild per night (`phases.json` says whether a run built or loaded,
  `network_cached_before`). `JAVA_TOOL_OPTIONS` makes the JVM print
  `Picked up JAVA_TOOL_OPTIONS: …` to stderr (in `log.txt`; harmless).
  r5py adds `-Xcheck:jni` to every JVM (slower JNI; r5py's choice). The
  walk+transit result equals walk for the smoke pair by construction
  (240 m); EP-15's hand check needs farther pairs. The Linux toolchain
  path is tested on crafted archives only; no Linux JVM run exists (out of
  scope). R5 7.6 stays available for a later amendment once an r5py release
  targets it. For the third checkpoint: the estimate-accuracy row for EP-13
  (one session, S).
- **No-go areas touched:** none (nothing on `PATH` or in the system; the
  JDK and jar only under `phillysim/.jdk/` and `phillysim/.r5/`, both
  ignored and asserted untracked; nothing under `data/` committed; CI stays
  offline and installs no routing group; no PHI, no secret, nothing
  deployed; no machine identifier or absolute path in a tracked file or a
  run record; the routing child wrote only under `data/cache/r5py/` and
  `data/runs/`). The one precondition breached is the diagnostic's r5py
  fallback download, disclosed above and closed by code.
- `roadmap/README.md` packet row updated to `[x] <work-commit>` in the
  status commit; the M3 heading stays open (EP-14, EP-15 remain).
- **Exact next packet: EP-14** (`roadmap/EP-14-routing-run-matrix.md`: the
  pre-scripted run matrix over the 408 CenPop centers and the 1,609 SNAP
  retailers through this harness, launched as the first unattended night;
  expect one cold network build of about 43 s and 4.9 GB, then routing
  RSS on top of the 2.4 GB cached-network floor).

### Owner review (2026-09-03)

Four decisions put to the owner interactively at the stop condition; **the
recommended option was accepted for every one**:
- **The jar pin (ADR-0008 amendment):** amend to the jar r5py 1.1.7 pins
  itself, `r5-v7.5.1-r5py-all.jar` (release `v7.5.1-r5py`, 2026-05-08;
  64,437,972 B; SHA-256 `d50be106…9be7`), every other pin kept; finish the
  packet in this session. Applied: ADR-0008 amended with a dated note, the
  constants and tests changed, `.r5/` deleted by hand and the jar
  reinstalled through the guarded path, the smoke green three times.
- **The diagnostic records:** keep under `data/runs/routing-diagnostic/`,
  labeled (gitignored; never committed).
- **The allowlist:** `release-assets.githubusercontent.com` confirmed
  beside the brief's two hosts, as at EP-12.
- **Commit, push, CI, handoff:** yes, once green. Work commit
  `<work-commit>`, CI run recorded in the status commit, then the status
  commit.
