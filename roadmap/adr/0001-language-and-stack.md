# ADR-0001: Python 3.12+/uv on native Windows; pyogrio-only geo I/O; pinned JVM for routing

Status: accepted (Planning Baseline v1.0, 2026-08-23)

## Context
Local-first geospatial pipeline on a Windows 11 laptop; the geospatial/
statistical ecosystem lives in Python; historic Windows pain concentrated in
GDAL bindings; routing engine (R5) requires a JVM.

## Decision
Python 3.12+ managed by uv (lockfile committed); native Windows primary,
WSL2 documented fallback only; GeoPandas/Shapely/pyproj with **pyogrio** I/O
and a hard ban on the `GDAL` and `fiona` PyPI packages (sdist-only on
Windows; verified 2026-08-23), enforced by a dependency-policy test;
project-local pinned Temurin JDK 21 with checksummed R5 jar for r5py; no
Docker in v1 (trigger: a reproducibility failure pinning cannot fix).

## Consequences
Everything installs from wheels on Windows; pyogrio's bundled GDAL covers
common vector drivers (DuckDB spatial's embedded GDAL covers gaps); JVM is
the single non-Python runtime and is version-pinned like any dependency.
