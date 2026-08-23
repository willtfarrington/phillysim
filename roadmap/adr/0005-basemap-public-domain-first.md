# ADR-0005: Minimal public-domain basemap default; PMTiles as gated enhancement

Status: accepted (Planning Baseline v1.0 AM-5, 2026-08-23)

## Context
Static site with zero third-party runtime calls. Options: self-hosted
Protomaps PMTiles extract (richer cartography; ODbL attribution; depends on
HTTP range requests, with an open bug affecting range requests on GitHub
Pages) vs minimal cartography built from public-domain TIGER/city layers.

## Decision
v1 default: minimal public-domain basemap (county boundary + roads,
grayscale, meeting the UI contrast spec). PMTiles becomes an optional
enhancement packet gated on a Pages range-request smoke test.

## Consequences
Basemap leaves the critical path with trivially clean licensing; visual
richness is a reversible later upgrade rather than a launch dependency.
