# EP-13 — Routing toolchain and harness: pinned JDK 21 and R5 jar, r5py behind the wheel-only rule, the RSS sampler, run records, the smoke route

**Status:** [ ] planned · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

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
- [ ] `phillysim toolchain install` from a clean state installs the JDK
      and the jar with the recorded digests; `toolchain check` reports
      `21.0.12.1` and the jar digest; a wrong digest is refused (tested on
      crafted bytes); nothing lands on `PATH` or outside the two
      directories.
- [ ] `uv sync --locked --group routing` installs r5py 1.1.7 and JPype1
      1.7.1 from wheels on Windows; `uv run pytest` green with and without
      the group installed; the dependency policy test green; the
      no-JVM-in-CI test green; CI green on both platforms without the
      group.
- [ ] The sampler kills a scripted child tree at the threshold and records
      a peak within one sample of the true peak (tested).
- [ ] `phillysim route smoke` completes three runs; each record has wall,
      peak RSS, digests, and outcome `completed`; the three
      canonicalized-value digests are recorded (equal or not); no sample
      reached 22 GB.
- [ ] The CI performance-smoke test runs on both platforms and records
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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- the toolchain install (bytes, seconds, digests), the group's wheel list,
  the network build wall and RSS, the three smoke runs' wall, peak RSS,
  and digests (equal or not), the CI performance-smoke numbers on both
  platforms
- resource observations (the first peak RSS; against the 20 / 22 GB lines)
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none; nothing on `PATH`; nothing under
  `.jdk/` / `.r5/` tracked)
- `roadmap/README.md` packet row updated to `[x] <commit>`
- exact next packet: EP-14 (the run matrix and the first unattended night)
