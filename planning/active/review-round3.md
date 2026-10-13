# Code-check round 3: branch 24-landing-page-say-why-it-is-useful-first (base 9c0a9f6, HEAD 332cd76)

Reviewed 2026-10-13. Scope: every quantified, categorical or set-summarising sentence in
README.Rmd's prose and in maintaining.md, walked member by member. Evidence: scripts/catalogue_build.py,
scripts/laz_item.py, scripts/s3_publish.py, scripts/s3_sync.sh, scripts/cache_sync.sh,
scripts/readme_functions.R, scripts/readme_chm.R, scripts/readme_dem.py, .github/workflows/update.yml,
research/filename_dates.md, data/*.json, the local 0.3.0 build (data/build/items, 174,282 item
JSONs, scanned in full), a fresh walk of every key under the eight NTS blocks (2026-10-13, 19:0xZ),
the live API (images.a11s.one), stacs' README, and gh for the linked issues.

## Mechanism

Every defect in rounds 1 and 2 is one shape: **a summary sentence written from a prose ancestor
instead of from the members of the set it summarises.** The ancestors are the issue body,
CLAUDE.md, a research file or the old README. Each is already a compression of the code, and each
plain-language rewrite compresses it again. The qualifiers are what made the summary true at the
edge members, and compression drops them first: a parenthetical ("a pair's first day"), an
"except", an "only", a third category. Each round then checked the new sentence against the same
prose, not against the member list, so the dropped edge stayed invisible until someone walked the
members. Two of this round's findings show it directly:

- research/filename_dates.md says "a delivery in which any name's date **(a pair's first day)** is
  in another year". The page kept "any file name ... carries a date that disagrees" and dropped the
  parenthetical. The parenthetical is the whole of #2's date change: 33 deliveries.
- research/filename_dates.md counts year spans as "year-only names and the untrusted deliveries".
  866 items with no date token are in neither, and the page inherited the omission. The research
  file's own total (65,166) only adds up if they are included.

The remedy is the one in code-check.md ("A guard's scope, escape hatches, and remedies"): for each
quantified sentence, name the finite set, walk it in code or data, and write the sentence from the
walk. The table below does this for every such sentence on both pages.

## Findings

- **[claim] README.Rmd:186, the trust rule.** "If any file name in a delivery carries a date that
  disagrees with its year directory, ... none of that delivery's file-name dates are used." This
  is false for 33 deliveries (8,955 items). Their two-day names end in a later year than the
  directory (`_20230921_20251001` in `093/093c/2023`, and 32 others from 2023 and 2024), and their
  file-name dates are used: `start_datetime` and `end_datetime`, `datetime_source: filename`.
  `laz_item.date_parse` tests only the single date, or a pair's first day:
  `agrees = (d1.year == path_year and d1 <= dt) if d1 else year == path_year`. Before #2 these
  were exactly the deliveries the build distrusted (80,337 files, research/filename_dates.md), so
  a reader of the page is told the old rule. Fix: "If the date in any file name of a delivery (for
  a pair, its first day) is in another year than its directory, ...".
- **[claim] README.Rmd:186, the date sources.** "An item's date comes from its file name: the day
  ...; the first and last day ...; or the whole year, where the name gives only a year." The next
  sentence covers the untrusted deliveries. Nothing covers **866 items whose names carry no date
  token**. They are in 10 trusted deliveries (`092/092g/2019` 228, `092/092c/2019` 168,
  `092/092f/2019` 149, `092/092p/2017` 127, `092/092b/2019` 91, `092/092l/2019` 70,
  `092/092k/2019` 20, `092/092i/2021` 5, `093/093c/2023` 1, and some in `092/092h/2016`). They
  carry the directory year, `datetime_source: path` and no `filename_date`. Round 2 named this
  case. Its fix list says it was handled, but the committed text has no clause for it. Fix: add
  "or, where the name carries no date, the year of its directory".
- **[claim, low] README.Rmd:186.** "`lidarbc:filename_date` keeps the file name's own date." It
  keeps the **last** date token (`date_parse` returns `filename_date: tok`, the second group).
  For the 44,744 trusted day ranges, the first day is in `start_datetime`. For **1,204 items in
  untrusted deliveries whose names carry two different days**, the first day is in neither the
  item's dates nor `filename_date`. research/filename_dates.md says "the name's last date token".
  Fix: "keeps the last date in the file name".
- **[claim] README.Rmd:188.** "`lidarbc:delivery` ..., which keeps one flight apart from another
  where several cover the same place." Within one delivery it does not: **1,211 tiles appear twice
  in one delivery**, and **278 of them, in 11 deliveries, were flown on different days**. For
  example, `094/094h/2024` has `bc_094h007_2_2_2_..._20240611_20240611.laz` and
  `..._20240627_20240627.laz`, and `092/092g/2024` has `bc_092g002_3_3_2` on 2024-01-06 and on
  2024-03-31. Both files of each pair share one `lidarbc:delivery`, and only their dates tell
  them apart. The key separates deliveries, that is mapsheet-years. Fix: "which keeps one delivery
  apart from another where several cover the same place".
- **[claim, low] README.Rmd:297 (unchanged since base, still a kept claim).** The airphoto row
  says "historic airphoto thumbnails, 1963–2019". The live `stac-airphoto-bc` temporal extent
  starts 1967-07-11, and stac_airphoto_bc's README says "10,100 photos spanning 1967–2019". Fix:
  1967–2019.
- **[claim, low] maintaining.md:15.** "A red run is the build refusing something a person should
  look at. It refuses ..." The list reads as complete and misses one refusal in the code.
  `copc_pairs` raises when a matched name is held by two files on either side ("two LidarBC files
  named …" / "two CanElevation files named …"). LidarBC has already filed one file under two
  deliveries (`bc_093c080_…` under 092B and 092N, both in EXCLUDE), so this one can happen. Also,
  a red run is not always the build. update.yml also goes red on the Tests step, on a cache pull
  that finds no cache ("not building cold"), on the 240-minute build timeout, on `stacs audit`,
  and on the publish ceiling, which the paragraph above does mention. Fix: "A red run is usually
  the build refusing ..." and add "a file name held by two files on either side of the COPC
  pairing".
- **[claim, low] README.Rmd:117.** "each delivery is a record of a watershed at a point in time".
  A delivery is a mapsheet-year (an NTS 1:250k sheet), not a watershed. 33 deliveries run into a
  later year, and `093c/2023` holds points from 2023, 2024 and 2025 (research/filename_dates.md).
  This is the round 2 rewording, and it is still literal-false at the edge. Suggest "each delivery
  records the land as it was when it was flown".
- **[claim, low] README.Rmd:156.** "Built from the point clouds, one method serves every flight".
  The method needs class-2 ground returns (the ground TIN, and the water test). Line 192 says some
  files have no ground at all: 253 of the 349 published class lists. "serves" claims it works
  everywhere, which nobody has measured flight by flight. Suggest "the same method applies to every
  flight".
- **[claim, low] README.Rmd:302.** "Each item is created by a pure function from a file's href and
  header". The item's dates also depend on every other file name in its delivery. The trust flag
  comes from `groups_with_untrusted_dates` over the whole listing and is passed as
  `trust_filename_date`. The `copc` asset and the class list come from two more pure functions
  with their own inputs (`copc_asset_add`, `classes_add`). The function is pure, but its inputs
  are understated. Suggest "from a file's href and header, and whether its delivery's file-name
  dates are trusted".
- **[unverifiable, low] maintaining.md:17.** "GitHub disables the schedule of a public repository
  after 60 days without a commit". GitHub's documentation says "when no repository activity has
  occurred in 60 days". The ledger in findings.md says "activity". The text was moved verbatim, so
  this is low. Suggest "without activity".

Not in the branch diff, but from the same ancestor (no action needed on this branch):

- CLAUDE.md: "Only `092p/2017` mixes a day token with no token". `093/093c/2023` also does: 2,968
  two-day names and 1 with no token.
- research/filename_dates.md, "Counts": "65,166 a year (year-only names and the untrusted
  deliveries)". The two named sets hold 55,538 + 8,762 = 64,300 items. The other 866 have no token.

Render: nothing changed in inline R or chunk conditions between da58572 and 332cd76. The committed
`data/readme_cache.rds` carries `version = "0.3.0"`, so the `is.na(cached$version)` branch
evaluates on a cache-only render.

## Enumeration record

Verdict per sentence. "Members" is the set walked. Build = the local 0.3.0 build, 174,282 items,
which matches research/filename_dates.md's counts.

### README.Rmd

| line | claim | members walked / evidence | verdict |
|---|---|---|---|
| 115 | a searchable catalogue of BC's lidar point clouds | scope at 196–203 | TRUE |
| 117 | LidarBC publishes lidar flown since 2012 | live temporal extent 2012-01-01; earliest items `102i/2012`; groups 2012–2026 | TRUE |
| 117 | each delivery is a record of a watershed at a point in time | deliveries are mapsheet-years; 33 span into a later year | FALSE (low), finding |
| 119–120 | what a DEM, DSM and CHM show | definitions | TRUE |
| 121 | products LidarBC does not publish: HAND-type height, vegetation density and layering | LidarBC products: DEM, DSM, CHM (stac_dem_bc#47), point cloud | TRUE |
| 122 | flights differ in density and classification | research/laz_classes.md (classes 3–5 in ~9% of files) | TRUE |
| 124 | search returns the files that cover a place, with when flown and CRS | every item has `datetime` or a range, and `proj:code` or `proj:wkt2` (2,911 wkt2) | TRUE |
| 124 | the files stay where the province publishes them | `laz` hrefs: 174,282/174,282 on nrs.objectstore.gov.bc.ca | TRUE |
| 124 | files with a cloud-optimised copy can be read by window | 13,970 `copc` assets, COPC | TRUE |
| 126 | readable with rstac, pystac-client, QGIS 3.42+ | ledger; readme_dem.py uses pystac-client | TRUE |
| 126 | each item is one point-cloud file | one `laz` per item, ids from keys | TRUE |
| 126 | footprint, point count, point format, CRS from the file's header | `item_create`: geometry from mins/maxs, `pc:count`, `las:point_format`, `proj:*` from `crs_wkt` | TRUE |
| 126 | DEM/DSM of the same deliveries are `stac-elevation-bc` on the same endpoint | live `/collections` | TRUE |
| 134 | Kanaka: light blue is where no ground was returned (water) | readme_dem.py: NaN after the 3-neighbour fill | TRUE |
| 136 | "all flown in YEAR" / "flown more than once; the N flown in YEAR were used" | readme_dem.json: 8 found, 4 from the 2016 delivery used (`flight_year` from `lidarbc:delivery`) | TRUE |
| 136 | a `laz` has no spatial index, so a window means the whole file | plain LAZ, no LAX sidecar in pointcloud/ (walk: only .laz, .bin under one EPT temp dir, 3 .prj, 1 .dbf) | TRUE |
| 136 | ground-only items in the window | readme_dem.json `ground_only_items` (1), conditional text | TRUE |
| 154 | Maxan: the meadow reads 0 m, trees on the delta and south slope, light blue = lake and channel | fig/maxan_chm.png inspected; `cells_na` 41% | TRUE |
| 156 | LidarBC CHMs for 2023 and 2024 only | stac_dem_bc#47: 264 tifs, 19 mapsheet-years, all 2023–24 | TRUE |
| 156 | DSM specs differ between deliveries | stac_dem_bc#47 (082f020, 2017 vs 2022) | TRUE |
| 156 | one method serves every flight | method needs class-2 ground; 253 published lists have none | UNVERIFIABLE (low), finding |
| 156 | floodplains#121 covers historic channels and forest lost since 2017 | issue title and body: `transition_2017_2023` | TRUE |
| 158 | "the N items covering it, both/all from DELIVERY" | readme_chm.json: 2 found, 2 used, `093/093l/2019` | TRUE |
| 158 | "None of them has a copc asset" (literal text) | readme_chm.R:85 stops if any does | TRUE (guarded) |
| 158 | only noise and withheld points left out; nothing chosen by class | `NOISE_CLASSES` 7, 18 + `Withheld_flag`; no other class filter | TRUE |
| 158 | heights above a TIN of ground returns; first returns pit-free | `normalize_height(tin())`, `pitfree()` | TRUE |
| 158 | a cell with no ground within G m, or no return, is empty | focal mask on class 2; `max_edge` | TRUE |
| 158 | class 1 is where LidarBC leaves most vegetation; the lake's returns are class 1 | research/laz_classes.md; readme_chm.json classes {1, 2, 7} | TRUE |
| 179 | every item has a `laz` on nrs.objectstore; source of record | 174,282/174,282 | TRUE |
| 180 | a minority have a `copc`, from four CanElevation projects | 13,970; project paths: VISC_2018 7,847, Riverine UTM10 3,866, UTM11 682, Lower_Mainland_2016 1,575; no other | TRUE |
| 182 | `copc` linked only after count, horizontal CRS and box within 0.05 m | `copc_asset_add` (three checks) | TRUE |
| 182 | the test cannot see a reclassified re-delivery | header-only checks | TRUE |
| 182 | a COPC can differ in LAS version and format | 1,575 pairs 1.2/1 → 1.4/6; 12,395 1.4/6 → 1.4/6 | TRUE |
| 182 | `pc:schemas` describe the `laz`; `copc` carries its own `las:*` | `item_create` / `copc_asset_add` extra_fields | TRUE |
| 184 | items carry pointcloud, projection, file; `las:`, `lidarbc:` fields | `stac_extensions`: 5 schemas on all 174,282 | TRUE |
| 184 | an item with a class list carries classification | 349 lists, 349 classification ext, 0 either way without the other | TRUE |
| 186 | date from the file name: day / first and last day / whole year for a year-only name | build: day 64,372; range 44,744; year from a `yyyy` token 55,538; **no token 866 (path)** | FALSE, finding |
| 186 | a two-day name gives first and last day | same-day pairs give `datetime` (63k), which is the same day; different-day pairs give a range | TRUE |
| 186 | a delivery with any name's date disagreeing with its directory → no file-name dates used | `date_parse` tests the single date or a pair's **first** day; 33 trusted deliveries (8,955 items) have a last day in a later year | FALSE, finding |
| 186 | often a processing date | research/filename_dates.md: 082k/2017, 092g/h/j 2016 (4 of 9) | TRUE ("often") |
| 186 | untrusted delivery → items span the directory year | year/path items: 1,063 (yyyy) + 1,976 (yymmdd) + 5,723 (yyyymmdd) = 8,762 | TRUE |
| 186 | `datetime_source` says which | `filename`/`path` on all 174,282 | TRUE |
| 186 | `filename_date` keeps the name's own date | keeps the last token; 1,204 untrusted two-day names lose the first day | FALSE (low), finding |
| 188 | `lidarbc:delivery` is `<block>/<sheet>/<year>`, e.g. `092/092g/2016` | `DELIVERY` regex; on all items | TRUE |
| 188 | it keeps one flight apart from another where several cover the same place | 1,211 tiles twice in one delivery; 278 flown on different days | FALSE, finding |
| 188 | stac-elevation-bc will carry it once stac_dem_bc publishes it (stac_dem_bc#61) | #61 open, titled for exactly this | TRUE |
| 188 | this collection links it as `related` | live collection `related` link | TRUE |
| 192 | a header does not say which classes | LAS spec | TRUE |
| 192 | some files have no ground, some only ground | 253 / 12 of the published lists (CLAUDE.md, 0.3.0) | TRUE |
| 192 | the build samples the least dense files per mapsheet-year | `density_screen` at `SCREEN_PERCENTILE` | TRUE |
| 192 | reads in full each one the sample flags; those items list every class with counts | `classes_published` ⊇ inside ∩ flagged; `classes_add` | TRUE |
| 192 | an item without a list was not read in full | `classes_check` refuses a good whole read outside `classes_published`; local reads (349 + 73 no-ETag) all in the 349 listed | TRUE |
| 192 | the screen misses a few | 5% audit: 2 in 7,834 | TRUE |
| 196 | every `pointcloud/` point-cloud file, with two exceptions | walk 2026-10-13: 175,278 .laz under pointcloud/, no .las; 175,278 − 11 − 985 = 174,282 | TRUE |
| 198 | a few files with a faulty header, or outside their filed mapsheet | the 11 EXCLUDE entries: 8 faulty header (092h003, 082j025, 092g010, 092g020, 092h011, 092k005, 092k043, 093n052 CRS), 3 outside the sheet (082m081, 093c080 ×2) | TRUE |
| 199 | eight 2017 deliveries with no CRS; #15 | `EXCLUDE_DELIVERIES` 8 entries, all 2017; #15 title | TRUE |
| 201 | each exception named with its reason | every entry has `reason` | TRUE |
| 203 | dsm/*.laz not indexed; in every tile compared an RGB copy | `pointcloud_select` keeps product `pointcloud` only; research/laz_header_read.md | TRUE |
| 205 | rebuilt monthly; new files published; served once registered | update.yml | TRUE |
| 205 | NEWS.md says what each release published | NEWS | TRUE |
| 207 | "rendered from catalogue version X" / "as published" | `pc_readme_version`; cache version 0.3.0 | TRUE |
| 211 | every indexed point cloud in the Similkameen River watershed group | `items_fetch` follows `next`; SIML | TRUE |
| 233 | every item returned, with links for both assets | the query chunk asserts both kinds exist | TRUE |
| 256 | public header at most 375 bytes; version, format, count, box | LAS 1.4 R15 | TRUE |
| 256 | one range request reads it from either asset, any size | `pc_readme_header`: one 0–374 range, 206 required | TRUE |
| 256 | httr2 and base R, no LAS library; checked against the item | `pc_readme_header_parse`, `pc_readme_header_check` | TRUE |
| 289 | same version and format → "copy"; else "differ in version and format" | both combinations in the build differ in both or neither | TRUE |
| 293–298 | four sister collections on the endpoint | live `/collections`: all four ids present | TRUE |
| 297 | airphoto 1963–2019 | live extent 1967-07-11; its README "1967–2019" | FALSE (low), finding |
| 302 | built in Python; pure function from href and header | `item_create(url, header, collection_href, trust_filename_date)`, with the trust flag from the delivery | FALSE (low, inputs understated), finding |
| 302 | published to s3://stac-pointcloud-bc; stacs registers and verifies | s3_sync.sh, stacs.toml | TRUE |
| 304–314 | command block (verify before register) | stacs README: verify "changes nothing", a drift preview | TRUE |
| 316 | monthly on the 6th, publishes what changed; registration by hand | cron `17 10 6 * *`; no register step | TRUE |
| 316 | maintaining.md covers refusals, caches, re-render | its three sections | TRUE |
| 320 | MIT; CC-BY-4.0; Province producer and licensor, NRCan host, NGE processor | LICENSE; live providers (the Province is also host, which is not denied) | TRUE |
| 320 | each `copc` under OGL–Canada as its description says | `copc_asset_add` description | TRUE |

### maintaining.md

| line | claim | evidence | verdict |
|---|---|---|---|
| 7 | `--limit N` writes to data/build-limit/, never data/build/ | `main()`: `out = "data/build-limit" if args.limit else OUT` | TRUE |
| 9 | uploads only items whose digest the bucket lacks; collection.json only when an item goes or the collection changed | `publish_plan` | TRUE |
| 9 | unchanged build sends nothing (9 min, 2026-10-11) | CLAUDE.md measurement | TRUE |
| 9 | deletes nothing; unbuilt objects reported and left | s3_sync.sh / s3_publish `items_unbuilt` | TRUE |
| 13 | runs on the 6th and on dispatch | cron + `workflow_dispatch` | TRUE |
| 13 | pulls caches (headers and class samples, ~20 MB), rebuilds, saves back, publishes | cache_sync.sh FILES: headers, copc_headers, classes, classes_full; step order | TRUE |
| 13 | nothing new → nothing published, version kept; added items → unversioned collection | `collection_differs`, `_unstamped` | TRUE |
| 13 | > 40,000 refused; `dryrun` plans | `MAX_UPLOAD=40000`; input | TRUE |
| 13 | register then verify from a tailnet machine; summary gives commands | Summary step | TRUE |
| 15 | a red run is the build refusing | tests, cache pull, build timeout, audit and publish also go red | FALSE (low), finding |
| 15 | the refusal list (11 cases) | each matched to code: `groups_check`, `blocks_list`, `pointcloud_select`, `groups_with_untrusted_dates`, duplicate ids, header/item_create, `exclusions_check`, `copc_listing`, `copc_pairs_check`/`copc_not_copy_check`, `validate_all`, `classes_check`/`classes_attach`; **missing: `copc_pairs` duplicate name** | FALSE (incomplete, low), finding |
| 15 | the class refusal can follow growth; `--classes-record` | a previously listed file leaving the screen becomes "read whole, but neither screened and flagged nor recorded" | TRUE |
| 15 | a network error → re-run reads only what is missing | header and class caches | TRUE |
| 15 | a new mapsheet-year is built unless it pairs with CanElevation | `groups_check` logs; `copc_pairs_check` refuses unrecorded pairing groups | TRUE |
| 17 | pull before, push after; push refuses a cache the monthly run wrote since | cache_sync.sh ETag check | TRUE |
| 17 | HEADER_VERSION change re-reads every header (~2.5 h, Oct 2026) | `item_create` refuses old versions; CLAUDE.md timing | TRUE |
| 17 | schedule disabled after 60 days without a commit | GitHub docs: "no repository activity" | UNVERIFIABLE (low), finding |
| 21 | README.md and index.html from README.Rmd; scripts/DESCRIPTION lists packages | DESCRIPTION Imports | TRUE |
| 28 | DEM demo Python in group `readme`; CHM demo R | pyproject `readme` group | TRUE |
| 28 | update_query=TRUE refreshes the five files; index.html reads them | the `query` chunk | TRUE |
| 28 | CHM demo downloads ~0.5 GB to data/readme_laz/, not committed, reused | `bytes_files` 532 MB; .gitignore; `pc_readme_laz_get` | TRUE |
| 30 | the page prints no count of the collection | the remaining numbers are demo numbers and code constants (accepted) | TRUE |
