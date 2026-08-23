# ADR-0003: Two-bucket output licensing; OSM-derived tables ship ODbL

Status: accepted (Planning Baseline v1.0 AM-1, 2026-08-23)

## Context
Published tables mixing OSM-network-derived travel metrics with public-domain
Census columns; ODbL share-alike applies to Derivative Databases; rendered
maps are Produced Works (attribution only). Conservative reading adopted
after Phase B analysis + red-team verification (ODbL 1.0 §4.5(b); OSMF
Produced Work guideline, accessed 2026-08-23).

## Decision
Bucket A = CC BY 4.0 (prose, cards, tables with no OSM-derived contents).
Bucket B = ODbL (any table containing OSM-derived contents) — including
**every combined export and the site's own data payloads**, by rule, with
ODbL + "© OpenStreetMap contributors" notices in-file/sidecar and in the
export UI. CI/publish gate validates labels in `data/public/` and site
payloads. SEPTA-derived aggregates carry a documented facts-not-contents
position (matrices contain no feed contents).

## Consequences
Reusers get clear rights; the project never overstates rights it lacks; a
small labeling burden lands on the publish gate rather than on judgment
calls at export time.
