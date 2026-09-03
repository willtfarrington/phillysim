# Method card: store-format classification of SNAP retailers

> **Status: stub (EP-6, 2026-09-02).** This card documents one method: how
> the project turns USDA's own store-type labels into the format classes its
> destination layers use. It is the first method card; the second, the
> QA-only slice metric of EP-7, is [qa-straight-line.md](qa-straight-line.md),
> and the cards for the access metrics themselves are drafted at M5. Method
> cards restate what the code pins and never relax a claims row
> ([docs/CLAIMS.md](../CLAIMS.md)).

## What this method does

USDA's SNAP Retailer Locator file ([data card](../data-cards/snap-retailers.md))
types every authorized retailer with one **store type**, defined by USDA on
its [SNAP Store Type Definitions](https://www.fna.usda.gov/snap/store-definitions)
page by what the store sells and how it operates (variety of staple foods,
checkout lanes, primary line of business). The project maps each of those
labels to one of seven **format classes** and marks one class,
`supermarket`, as the **supermarket-format** destination layer that the
flagship nutrition-access measures use (Planning Baseline amendment AM-4;
[methodology.md](../../roadmap/methodology.md) "Destination layers"). The
whole classified table, all format classes together, is the
**all-SNAP-retailer** variant kept for the like-for-like comparison with
USDA's SNAP Retailer Access Map at M5.

The mapping is **format-based only**. Class names describe a retail format
(what kind of store it is), never what the store stocks, how affordable it
is, or whether its food is "healthy" (C-2). The project does not verify any
store's inventory; a `supermarket` row means "USDA typed this authorized
retailer as a Supermarket or Super Store on the file's as-of date", nothing
more.

## The mapping table

The table below is rendered from the packaged mapping
(`phillysim.classify.store_format`) and a test fails if the two drift; to
re-render after a change, run `uv run python -m phillysim.classify.store_format`
from `phillysim/`. Any change to the table bumps `MAPPING_VERSION` (the
methods axis of [ADR-0006](../../roadmap/adr/0006-versioning-axes.md)),
which the `snap_retailers` stage records as a parameter and the changelog
notes.

<!-- store-formats:begin -->
Mapping version `store-formats-1` (17 provider store types, 7 format classes; rendered from `phillysim/src/phillysim/classify/store_formats.csv`).

| USDA store type | Code | Format class | Supermarket-format | Basis (USDA definition, abridged) |
|---|---|---|---|---|
| Supermarket | SM | `supermarket` | yes | Establishments commonly known as supermarkets, food stores, grocery stores and food warehouses primarily engaged in the retail sale of an extensive variety of grocery and other store merchandise; typically ten or more checkout lanes. |
| Super Store | SS | `supermarket` | yes | USDA name "Super Store/Chain Store": very large supermarkets, big-box stores, super stores and food warehouses; includes large food/drug combination stores, mass merchandisers, and membership retail/wholesale hybrids. |
| Large Grocery Store | LG | `grocery` | no | A store that carries a wide selection of all four staple food categories; primary stock is food. |
| Medium Grocery Store | MG | `grocery` | no | A store that carries a moderate selection of all four staple food categories; primary stock is food. |
| Small Grocery Store | SG | `grocery` | no | A store that carries a small selection of all four staple food categories; primary stock is food. |
| Combination Grocery/Other | CO | `combination` | no | Primary business is the sale of general merchandise with a variety of food products: independent drug stores, dollar stores, general stores. |
| Convenience Store | CS | `convenience` | no | Self-service stores offering a limited line of convenience items, typically open long hours; grocery items in limited amounts. |
| Meat/Poultry Specialty | ME | `specialty` | no | USDA name "Specialty Food Store - Meat/Poultry Products": specializing in meat products. |
| Seafood Specialty | SE | `specialty` | no | USDA name "Specialty Food Store - Seafood Products": specializing in seafood products. |
| Fruits/Veg Specialty | FV | `specialty` | no | USDA name "Specialty Food Store - Fruits/Vegetables": specializing in fruits and/or vegetables at a fixed or semi-permanent location, including produce stands not affiliated with a farmers' market. |
| Bakery Specialty | BB | `specialty` | no | USDA name "Specialty Food Store - Bakery/Bread": specializing in bread/cereal products. |
| Farmers' Market | FM | `farmers_market` | no | A single- or multi-stall market selling agricultural products, particularly fresh fruit and vegetables, to the general public; the organization operating the market location. |
| Delivery Route | DR | `other` | no | No permanent store location: delivery routes and rolling routes; not a destination a person travels to. |
| Food Buying Co-op | BC | `other` | no | USDA name "Non-Profit Food Buying Cooperative": any store that operates as a cooperative; membership-based. |
| Military Commissary | MC | `other` | no | Retail food entities on military installations; only authorized shoppers with military ID may shop. |
| Wholesaler | — | `other` | no | Label present in the historical file but absent from the USDA store-type definitions page; not a retail destination. |
| Unknown | — | `other` | no | Label present in the historical file but absent from the USDA store-type definitions page; no format information. |
<!-- store-formats:end -->

## Choices and their basis

- **`supermarket` = USDA `Supermarket` + `Super Store`.** These are the two
  USDA types defined by an *extensive* or *wide* variety of grocery and
  other merchandise at scale (ten or more checkout lanes; very large,
  big-box, food/drug combination, and membership warehouse formats). The
  three `Grocery Store` sizes are defined by a *wide / moderate / small
  selection of all four staple food categories* with food as the primary
  stock; they form their own class, `grocery`, so that the supermarket-format
  layer stays the USDA definition rather than a project judgement about
  which grocery stores are "big enough". Whether `Large Grocery Store`
  belongs with supermarkets is a sensitivity question for M5, not a
  reclassification here.
- **`combination`** (drug stores, dollar stores, general stores) and
  **`convenience`** are kept apart from `grocery` because USDA defines them
  by a *limited* line of food and a primary business other than food; they
  are in the all-retailer variant and in no flagship layer.
- **`specialty`** groups the four specialty food stores (meat/poultry,
  seafood, fruits/vegetables, bakery/bread); **`farmers_market`** is USDA's
  authorized-market organization record, which the City's farmers'-market
  layer (M4) will be conflated with, not replaced by.
- **`other`** holds formats that are not fixed retail destinations a
  resident travels to (delivery routes), are access-restricted (military
  commissaries), are membership cooperatives, or carry a label the USDA
  definitions page does not define (`Wholesaler`, `Unknown`). They stay in
  the all-retailer table because USDA counts them; they enter no flagship
  layer.
- **Labels versus definitions.** The file's labels abbreviate the
  definitions page's names (`Super Store` for "Super Store/Chain Store",
  `Meat/Poultry Specialty` for "Specialty Food Store – Meat/Poultry
  Products", `Food Buying Co-op` for "Non-Profit Food Buying Cooperative");
  the table keeps the file's spelling as the key and the USDA code as the
  crosswalk. Two defined types, `Direct Marketing Farmer` and `Internet
  Retailer`, do not occur in the historical file at all (which is also why
  the file's national totals sit a few percent below USDA's year-end firm
  counts; see the data card). A label the table does not know is a
  **contract violation and a stop condition**: the pipeline fails rather than
  classifying it, and the mapping is extended only after its USDA definition
  has been read, with a version bump.

## What it does not do

- It does not rate, score, or rank stores or tracts (C-3).
- It does not say anything about food quality, price, or suitability (C-1,
  C-2); the class names are the only vocabulary the site may use for these
  layers.
- It does not de-duplicate against other sources (M4 conflation) or add
  opening hours (the SNAP file has none; `hours_status` will be
  `not_in_source` for these rows when the sites table is built).
- The OSM `shop=supermarket` cross-check methodology.md mentions is deferred
  to M4 conflation and is not part of this method.
