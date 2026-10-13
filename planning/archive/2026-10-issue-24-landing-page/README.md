## Outcome

Rewrote the landing page (`README.Rmd` → `README.md`, `index.html`) to open with a plain-language case for why the catalogue is useful. DEMs, DSMs and canopy height models, and change between flights, matter for understanding, conserving and restoring watersheds, and the catalogue lets people and software find that data without downloading it first. The rewrite dropped every collection count the monthly update makes stale (badge, intro, copc share, per-mapsheet-year table, class-list totals, sync timing), moved maintainer detail to `maintaining.md`, and collapsed code and the header read into `<details>`. The render no longer fetches the whole collection: `pc_readme_fetch()` existed for the counts, and its version check would have failed every render after a monthly run that adds items. `pc_readme_version()` replaces it.

The audit found three claims wrong before the rewrite:
- `lidarbc:delivery` "matches stac_dem_bc's items" (not yet published there, NewGraphEnvironment/stac_dem_bc#61)
- the extension list was incomplete
- "one item per `.laz`" overstated what is indexed

The review then found more claims, mostly ones the rewrite itself introduced. Every one had the same cause: a summary sentence written from earlier prose (issue body, CLAUDE.md, a research file, the old page) rather than from the members of the set it summarises, so the qualifiers that made it true for the edge members were dropped. Rounds 2–5 of `/code-check` each found a defect inside the previous round's fix, in the item-date sentence above all. What ended it was enumerating that set from every built item and writing the sentence from the table, not another round. The review also surfaced a date-parser gap (#25) and fixed two stale sentences outside the page, in CLAUDE.md and `research/filename_dates.md`.

## Measurement

Item dates in the 0.3.0 build (174,282 items, scanned 2026-10-13):

| shape | source | items |
|---|---|---|
| day | file name | 64,372 |
| range of days (two-day names) | file name | 44,744 |
| year (year-only names) | file name | 55,538 |
| year | directory, in the 9 untrusted deliveries | 8,762 |
| year | directory, token the parser cannot read (#25) | 866 |

This replaced the page's earlier rule twice over. It also corrected `research/filename_dates.md`, whose year total had silently included the 866.

The claim ledger (`findings.md`) lists every kept claim with its source and verdict. The per-member enumeration of every summarising sentence is `review-round3.md`.

Closed by: PR #26

## Revision after review (2026-10-13)

Feedback on the PR:
- link the repo name at the top, as the sibling repos do
- cut the Maxan "Why from the point clouds" paragraph and the issue links
- say plainly why the point clouds matter: LidarBC's ready-made products are uneven, and from the points you choose the product and its resolution
- say that NRCan's CanElevation COPC copies are the second source
- say that the catalogue is a light index, rebuilt monthly, that applications can use and others can reproduce
- say that the DEM demo's windowed read depends on those COPC copies

A review of the rewrite (`review-rev-round1.md`) found six overstatements:
- DEMs are missing for 12 of 233 mapsheet-years
- CHMs exist in 19 of 48 mapsheet-years from 2023–24
- a plain LAZ can be range-read by chunk, just not by area
- the monthly run publishes but does not register
- one method across flights is necessary for comparing years, not sufficient
- a DSM-specification claim had lost its source

Live stac-elevation-bc items now carry `lidarbc:delivery`, and a filter on `092/092g/2016` returns items from both collections, so the page says "carry" and NewGraphEnvironment/stac_dem_bc#61 is resolved.
