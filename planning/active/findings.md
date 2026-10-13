# Findings — Landing page rewrite (#24)

## Issue context

## Problem

The landing page (`README.Rmd` → `README.md` and `index.html`) is accurate in most places but reads as a build log. It opens with what the catalogue is made of, not why anyone would want it. It prints counts that the monthly update (#4) will make stale. It also carries maintainer detail that a reader looking for data has to scroll past.

### 1. Counts that go stale

The monthly run publishes new items without a re-render of the page, so every exact count is wrong after the first month that adds files:

- the `items-174282` badge
- the intro's "174,282 items in 225 mapsheet-years"
- "13,970 of 174,282 items" in the asset table
- "9 minutes to check 174,282 items" (`s3_sync.sh`)
- "In 0.3.0, 253 of them hold no ground … about 38 more" (class lists)
- the per-mapsheet-year table and its summary line

The API does not report a total (`/search` returns no `numberMatched`; checked 2026-10-13), so the page cannot hand off to a live count. It should describe the scope in words ("every LidarBC point cloud file, less a few named exceptions") instead. Numbers that describe one dated demo (MB read for the Kanaka window, the Similkameen search result) are a different case, because they describe the figure next to them.

### 2. Claims checked (2026-10-13)

**Wrong or incomplete**

- *"`lidarbc:delivery` … the same key stac_dem_bc writes on the DEM and DSM items of that delivery."* NewGraphEnvironment/stac_dem_bc#55 is closed by stac_dem_bc PR #58, but the live stac-elevation-bc items do not carry the key yet: `094-094o-2026-dem-bc_…` has only `datetime` and `proj:*`. The collection's `related` link title ("match items on lidarbc:delivery") says the same thing and is also not yet true. Both become true when stac_dem_bc republishes.
- *"Items carry the pointcloud, projection and file extensions."* They also carry the `lidarbc` and `las` schemas, and items with a class list carry `classification`.
- *"one item per `.laz` file on the province's objectstore."* It is one item per `pointcloud/*.laz`, less the exclusions. The `dsm/*.laz` are not indexed.

**Verified**

- The exclusions are 11 files (4 with 0 or 1 points, 3 with impossible boxes, 3 outside their mapsheet, 1 contradicting CRS) plus 985 files in 8 deliveries from 2017 (`catalogue_build.py` `EXCLUDE`, `EXCLUDE_DELIVERIES`).
- The COPC pairing check is real: point count, horizontal CRS, box within 0.05 m.
- A LAS public header is at most 375 bytes.
- QGIS 3.42 added STAC search to the Data Source Manager.
- LidarBC publishes CHMs for 2023–24 only (stac_dem_bc#47: 19 mapsheet-years).
- The API-versus-bucket id check is done in both directions (`readme_functions.R:182`).
- The monthly run is on the 6th, has a `dryrun` input and a 40,000-item ceiling; `s3_sync.sh` deletes nothing; the group floor is 90%.
- Licence and providers match `collection.json`.
- The landing page answers 200.
- floodplains is public, so the floodplains#121 link works for outside readers.

**Not re-measured:** the timings for maintainers (2.5 h header re-read, ~20 MB of caches, 9 min sync check). Item 4 below asks whether they belong on this page at all.

### 3. "So a client can find the files"

"Client" reads as a paying customer. The point is that **people and software** can both find the lidar that covers a place, by searching, without knowing how the province lays out its folders and without downloading tiles to find out.

### 4. Too much detail for a reader

The paragraphs a reader has to get through include:

- why 11 files were not loaded
- the `nge:` → `lidarbc:` rename history
- the class-sampling method, which sits in the DEM section although it is about items
- the full list of what makes the monthly build refuse
- cache handling and a schedule-disable warning

These belong in `NEWS.md`, `research/`, the code, or a maintainer document, linked once.

## Proposed shape

1. **Why it is useful, in plain language, first.** Lidar shows the shape of the ground and the vegetation on it, flight by flight, across BC.
   - A **DEM** (bare earth) shows floodplains, side and historic channels, terraces, and the roads and embankments that cut a river off from its floodplain: where water goes and where it used to.
   - A **canopy height model** shows riparian forest: where streams are shaded, where cover has been lost, how tall stands are, and where planting or protection would matter.
   - A **digital surface model** (the top of whatever is there: canopy, buildings, bridges) is the other half of that picture.
   - The point clouds can also become products nobody has made yet: height above the channel to map floodplain extent, vegetation density and layering, terrain derivatives that show where water flows and pools.
   - **Now and over time.** Many places have been flown more than once. Comparing flights shows change that affects watershed health, such as channels migrating, riparian forest cleared or regrowing, and floodplains filled or reconnected. That makes the change something we can measure and show to others, not just describe. Each new LidarBC delivery adds another point in time.
   - The catalogue removes the friction between those questions and the data. Search a place from R, Python or QGIS, get the files that cover it, and read only the part you need, with the province's data left where it is published. That helps people who are understanding, conserving and restoring watersheds, and lets the work be repeated and shared.
2. **Then the two demos**, each led by what the figure shows and why it matters, with the method after.
3. **What an item holds, and how to query it**, kept short, with the class-list caveat moved here and trimmed to what a user needs to know.
4. **Technical detail last**, for maintainers: build, publish, register, the monthly update.

## Done when

- [ ] No count of items, mapsheet-years or files that the monthly run can change appears in the page's prose or badges.
- [ ] The page opens with a plain-language case for why the catalogue is useful, without the word "client" meaning a user.
- [ ] Each claim the page keeps has been checked against its source, and the PR lists them.
- [ ] The `lidarbc:delivery` sentence says what is true today.
- [ ] Detail moved off the page is linked from it.
- [ ] `README.md` and `index.html` are re-rendered from `README.Rmd`, and the served page matches after the push.


## Claim ledger (checked 2026-10-13)

Claims the rewritten page keeps or adds. Live = `images.a11s.one` / `stac-pointcloud-bc.s3` read 2026-10-13.

| claim | source | verdict |
|---|---|---|
| LidarBC lidar flown from 2012 on | collection temporal extent starts 2012-01-01 (live); `data/pointcloud_groups.json` years 2012-2026 | true |
| Places flown more than once (tile level) | `data/readme_dem.json`: the same four Kanaka tiles (092g018_3_3_3/4, 092g028_1_1_1/2) are in the 2016 delivery and again in 2024/2025 | true; Maxan's CHM window has only 093l/2019 |
| LidarBC publishes DSMs | stac_dem_bc PR #32 (dsm as a second asset on stac-elevation-bc) | true |
| LidarBC publishes CHMs for 2023-24 only | stac_dem_bc#47: 264 tifs, 19 mapsheet-years, all 2023-24 | true |
| Items give dates and CRS | live item properties `datetime`/`start_datetime`, `proj:code` | true |
| Search from R, Python, QGIS 3.42+ | rstac, pystac-client (readme_dem.py uses it); QGIS changelog: 3.42 added STAC search in the Data Source Manager | true |
| Read only the window from a `copc` | `data/readme_dem.json` bytes_read vs bytes_files | true |
| `laz` stays on the province's objectstore; nothing copied | live item `laz` href on `nrs.objectstore.gov.bc.ca` | true |
| `copc` linked only after point count, horizontal CRS and box within 0.05 m match | `catalogue_build.py` `COPC_BOX_TOLERANCE_M`, collection description | true |
| COPC from four CanElevation projects | collection description (`catalogue_build.py:241`) | true |
| `copc` carries its own `las:version`/`las:point_format`; `pc:schemas` describe the `laz` | `laz_item.py` | true (unchanged text) |
| Extensions: pointcloud, projection, file, plus `lidarbc` and `las` schemas; `classification` where a class list is published | live item `stac_extensions`; `laz_item.py:27` | **page listed only three: fix** |
| `lidarbc:delivery` matches stac_dem_bc's items | live stac-elevation-bc item `094-094o-2026-dem-bc_…` has only `datetime`, `proj:*`; stac_dem_bc#55 closed by PR #58 (code merged, not republished) | **not yet true: say "from its next full rebuild"** |
| One item per `pointcloud/*.laz`, less named exceptions; `dsm/*.laz` not indexed | `catalogue_build.py` `EXCLUDE` (11), `EXCLUDE_DELIVERIES` (8 deliveries, 985 files) | true; "one item per .laz" overstated: fix |
| Exclusion breakdown 4/3/3/1 | `EXCLUDE` reasons | true, but cut from the page |
| LAS public header at most 375 bytes | LAS 1.4 spec header size 375 | true |
| Header read with httr2 + base R, no LAS library | `readme_functions.R` `pc_readme_header` | true |
| API serves exactly the ids collection.json links | was `readme_functions.R:182-186`; the check went with `pc_readme_fetch()` on this branch | claim removed from the page |
| Monthly run on the 6th, dispatch with `dryrun`, 40,000 ceiling, no registration | `update.yml:30-33,131` | true |
| `s3_sync.sh` uploads changed items only, deletes nothing | `s3_sync.sh:9` | true |
| Group listed under 90% of its count is refused | `catalogue_build.py:91` `GROUP_FLOOR = 0.9` | true |
| Public repo schedule disabled after 60 days without activity | GitHub Actions docs | true |
| Licence CC-BY-4.0; providers BC (producer, licensor, host), NRCan (host), NGE (processor) | live collection.json | true |
| Landing page served | `https://www.newgraphenvironment.com/stac_pointcloud_bc/` HTTP 200 | true |
| floodplains#121 link readable outside | `floodplains` is public | true |
| Not re-measured: 2.5 h header re-read, ~20 MB caches, 9 min sync check | CLAUDE.md, 2026-10-11 measurements | moved to `maintaining.md` with their dates |

Counts on the old page that the monthly run makes stale: the `items-` badge, "N items in M mapsheet-years", "N of M items" with copc, "9 minutes to check N items", "253 … 38" (0.3.0 class lists), the per-mapsheet-year table and its summary, and the Similkameen search count. The API reports no `numberMatched` (`/search?limit=1`, 2026-10-13), so no live count can replace them.
