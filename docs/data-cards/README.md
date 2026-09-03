# Data cards

One card per source the pipeline ingests: what the source contributes, its
vintage and provider file, the terms in force and the license bucket
([docs/DATA-LICENSES.md](../DATA-LICENSES.md), ADR-0003), the coordinate
reference system it arrives in and the one it is analysed in
([ADR-0007](../../roadmap/adr/0007-analysis-crs.md)), the filter applied,
known limits, and the claims-matrix rows ([docs/CLAIMS.md](../CLAIMS.md))
that bind how the source may be described. Cards restate facts the code and
the data dictionary already pin; they never relax a charter row, and the site
(M6) will render them beside the results as the charter's "data cards per
source" success evidence.

| Source | Card | Contributes | Since |
|---|---|---|---|
| `tiger_tracts` | [tiger-tracts.md](tiger-tracts.md) | Tract boundaries and names (the spine's geometry) | EP-5a / EP-5b |
| `cenpop` | [cenpop.md](cenpop.md) | 2020 Census population and population-weighted centers (the routing origins) | EP-5a / EP-5b |
| `acs` | [acs.md](acs.md) | ACS 5-year estimates with margins of error (denominators and context) | EP-5a / EP-5b |

Destination sources (SNAP retailers, farmers' markets, meal sites), transit,
and the street network get cards with their adapters (EP-6, M3, M4). Method
cards, per metric, are a separate set (methodology.md) and start with EP-7.
