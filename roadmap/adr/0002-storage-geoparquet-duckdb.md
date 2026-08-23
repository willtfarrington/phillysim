# ADR-0002: GeoParquet zone files + DuckDB spatial; no PostGIS

Status: accepted (Planning Baseline v1.0, 2026-08-23)

## Context
Real scale is small: ~408 tracts, thousands of POIs, OD matrices in the low
millions of rows; single writer; full reproducibility required.

## Decision
File-based storage: GeoParquet/Parquet across raw→intermediate→curated→public
zones; DuckDB ≥1.1 with spatial extension as the query engine. No server
database. Upgrade to PostGIS only when: concurrent writers, data beyond
memory-practical scale, or network topology operations DuckDB cannot express.

## Consequences
Snapshots are plain files (checksummable, immutable, portable); no service to
maintain; migration later is cheap because zone boundaries are the contract.
