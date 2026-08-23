# ADR-0006: Six version axes; three release-visible, three manifest-recorded

Status: accepted (Planning Baseline v1.0 AM-6, 2026-08-23)

## Context
Reproducing any published result requires pinning code, dependencies, data,
schema, and method parameters — but a solo project should not run six
independent release streams.

## Decision
Release-visible axes: code SemVer (0.x pre-v1), per-source dataset snapshot
IDs, and the public release tag (which pins everything). Manifest-recorded
axes bumped by rule: dependency lockfile reference, integer schema version
(with migration note), and methods/parameters version (any metric definition
or pinned-parameter change bumps it — never silent).

## Consequences
Old results reproduce from a release tag + manifests; metric changes are
always visible; bookkeeping stays inside files that already exist.
