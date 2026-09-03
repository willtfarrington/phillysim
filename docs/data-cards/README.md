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
| `snap_retailers` | [snap-retailers.md](snap-retailers.md) | SNAP-authorized retailers with USDA store types (the supermarket-format layer and the all-retailer variant) | EP-6 |

The remaining destination sources (farmers' markets, meal sites), transit,
and the street network get cards with their adapters (M3, M4). Method cards
are a separate set under [docs/method-cards/](../method-cards/): the
store-format classification (EP-6) and the QA-only straight-line slice
metric (EP-7; explicitly not an access measure). Every published file names
its sources' citations, taken from the adapters, in its license label
(EP-7 publish gate).
