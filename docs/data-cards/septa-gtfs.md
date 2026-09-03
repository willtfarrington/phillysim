# Data card: SEPTA GTFS, release v202609060 (`gtfs`)

**Contributes.** The transit schedules the routing engine (R5 through r5py,
M3) rides: SEPTA's bus and Metro feed and its Regional Rail feed, both, for
the walk+transit mode on the pinned Wednesday and Saturday. Like the
street network it contributes nothing until the routing spike runs (EP-13
onward); no metric reads it and nothing published is derived from it yet.
Computed travel times are **facts** and carry no feed contents; the feed
itself is never republished, and nothing unwrapped from it is ever copied
under `public/` or `site/` ([roadmap/sources.md](../../roadmap/sources.md),
[docs/DATA-LICENSES.md](../DATA-LICENSES.md)).

**Provider and file.** Southeastern Pennsylvania Transportation Authority
(SEPTA), as published by SEPTA on GitHub (`septadev/GTFS`), release tag
**`v202609060`** ("Summer RR, Fall Bus-Metro, Sept Adjustments", published
2026-09-02): the asset `gtfs_public.zip`, 21,555,258 bytes, SHA-256
`4d3fa20ea094937a9bb6389ad52017e1ac90a564aee497f318797e1b1e4f07ab` as
GitHub records it, holding `google_bus.zip` (20,797,660 bytes, 19 members)
and `google_rail.zip` (757,262 bytes, 20 members). The download follows
GitHub's release-asset redirect to its content host, which the adapter
allowlists (`objects.githubusercontent.com` as the packet recorded it and
`release-assets.githubusercontent.com` as observed on 2026-09-03). Guard
limits: 128 MiB per file, 1 GiB extracted, ratio 50, 50 members, applied to
the outer zip at acquisition and to each inner zip in place before anything
is read out of it and again as a file once unwrapped.

**Vintage.** Bus and Metro authoritative 2026-09-06 through 2027-02-20;
Regional Rail authoritative 2026-09-06 through 2026-10-17 (each feed's
`feed_info.txt`; the release notes agree). The pinned analysis dates,
**Wednesday 2026-09-23** and **Saturday 2026-09-26**
([ADR-0008](../../roadmap/adr/0008-routing-toolchain-pins.md)), lie inside
both windows: 20 bus/Metro and 1 rail service run on the Wednesday, 11 and
2 on the Saturday. Pinned snapshot **`2026-09-03`**
(`phillysim.pipeline.SNAPSHOT_IDS["gtfs"]`). SEPTA publishes a new release
several times a year; a controlled refresh pins a new tag with the owner,
re-reads and re-archives the terms, moves the pinned dates if the windows
move, and is a methods-version change (ADR-0006).

**Terms and license.** SEPTA's developer license agreement, the text on
`https://www3.septa.org/developer/` ("Agreement updated: Tue, 18 Mar 2014"
by its own text), archived beside the snapshot as `terms.html` at every
acquisition and checked for two sentences, verbatim: "SEPTA reserves the
right to alter and/or no longer provide the Trip Planning Data at any time
without prior notice." and "SEPTA reserves the right to institute a license
fee at any time in the future without prior notice." A change stops
acquisition. The agreement is revocable, charges no fee today but reserves
one, and forbids altering the data and commercial use of SEPTA's marks; the
project accepts those terms as archived (the release download bypasses the
page's click-through form, so the archived agreement text is what is
accepted). **Bucket A** for the feed itself: nothing OSM-derived comes from
it, and the ODbL never attaches through it; a travel time computed over
the OSM network *and* this feed is Bucket B because of the network, not
the feed. Citation: "Southeastern Pennsylvania Transportation Authority
(SEPTA), GTFS release v202609060".

**Coverage and filter.** Stored as delivered; **no county filter**:
SEPTA's whole network is routing input, and a trip that starts in the
county may use a suburban stop. The `validate` read counts, per feed, the
stops outside the routing box (the county bounds buffered by 5 km) as
information, never a failure: the pinned snapshot has **14,054 bus/Metro
stops** (2,800 outside the box; 8,080 inside the county's tracts) and
**156 rail stops** (39 outside; 53 inside the tracts), 168 bus/Metro and 13
rail routes, 35,142 and 2,193 trips. The `network` stage **unwraps without
expanding**: the two inner zips are copied out of the release asset as
files (R5 reads GTFS zips directly), and nothing inside them is ever
extracted.

**CRS.** Stop coordinates are WGS 84 (EPSG:4326) as GTFS requires and stay
so. The routing box is computed in the analysis CRS and expressed in WGS 84
for the stop check.

**Where it lands.** `intermediate/network/google_bus.zip` and
`intermediate/network/google_rail.zip` (the feed zips as delivered inside
the asset) and the counts above in `intermediate/network.json`.

**Known limits.**
- A GTFS feed is the published schedule, not observed service: the travel
  times computed over it are scheduled times under the feed's calendar, and
  real-time detours, delays, and cancellations are absent by construction.
- The Regional Rail window ends 2026-10-17; the pinned dates stay valid
  because the feed is pinned, but a refresh after that date must move them.
- SEPTA's New Bus Network first phase (2026-08-23/24) is in this feed; the
  pinned Wednesday is after Labor Day week with schools in session, chosen
  as a typical weekday, but any single day is one day.
- The feed carries fares (`fare_*`) and pathways that the spike does not
  use; nothing about cost enters any metric.
- The CI sample of this source is synthetic (a feed in SEPTA's layout over
  the six sample tracts), so the suite exercises the layout, the guards, and
  the contract, never SEPTA's contents.

**Claims matrix.** Nothing in this card or in any output derived from the
feed states or implies simulation, prediction, or clinical guidance (C-1
through C-4 in [docs/CLAIMS.md](../CLAIMS.md)): a walk+transit time is a
descriptive measurement of the published schedule under stated assumptions.
No accessibility statement rests on it until M5 publishes the routing
outputs with their method cards.

**Checks that bind it.** Source contract (`phillysim.adapters.septa_gtfs`:
exactly the two feeds, the required GTFS files and columns present,
`feed_info.txt` dates covering both pinned days, at least one service on
each, the agency time zone, stop, route, and trip counts, Bucket A), the
pinned SHA-256 at acquisition (a mismatch quarantines with kind `digest`),
the terms sentences, the nested zip guards (an inner zip that fails a guard
is refused before anything is read out of it), and the snapshot manifest
(`phillysim verify`).
