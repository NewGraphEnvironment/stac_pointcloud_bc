# Review: commit 0a50c62 (landing-page revision, #24), round 1

Reviewed 2026-10-13 against `git show 0a50c62:README.Rmd`. Line numbers are that commit's
(the working tree's README.Rmd changed while this review ran, at line 115; not reviewed).
Every probe was a read: no repo file was edited, and the render ran in a scratch copy.

## Per-sentence table

| line | sentence / fact | set it summarises, and what was checked | verdict |
|---|---|---|---|
| 115 | repo link at the top | rendered README.md and index.html in a scratch copy, both `update_query = FALSE`; both byte-identical to the working-tree outputs; link present at README.md:9 and index.html:3391 | TRUE |
| 117 | "a searchable index of BC's lidar point clouds" | - | TRUE |
| 123 | bullet on comparing flights (sentence "Each new delivery adds another point in time" dropped) | - | TRUE |
| 125 | "LidarBC publishes DEMs" | pointcloud mapsheet-years (`data/pointcloud_groups.json`, 233) against DEM mapsheet-years (stac_dem_bc `data/urls_list.txt` on origin/main, 221). 12 have point clouds and no DEM; 4 checked in the live listing (`093i/2018`, `092a/2016`, `082k/2021`, `093o/2017`), each holding only `pointcloud/`. 2,361 indexed files sit in those 12 | FALSE by omission: set beside "surface models for most tiles but not all", it reads as DEMs everywhere. 12 of 233 deliveries have none |
| 125 | "surface models for most tiles but not all" | stac_dem_bc README: 95,888 of 102,460 DEM items carry a `dsm` | TRUE |
| 125 | "canopy height models for 2023 and 2024 only" | stac_dem_bc#47 and #29: 264 CHM tifs in 19 mapsheet-years, all 2023–24, about 1.1% of the DEM tiles in those deliveries (`093a/2024`: 398 DEM, 2 CHM). Live listing today: 19 of the 48 mapsheet-years from 2023–24 have a `chm/`, and none from 2025 | FALSE by omission: the years are right, but the sentence reads as CHMs covering 2023–24. Elsewhere this coverage is called "a sample, not a product" |
| 125 | "Each comes at the resolution and by the method LidarBC chose" | - | TRUE (says little) |
| 125 | "its surface models are made to specifications that differ between deliveries" | stac_dem_bc#47 cites rtj#229's pilot: one tile, `082f020`, CHM median 4.05 m in 2017 against 0.52 m in 2022 | UNVERIFIABLE beyond one tile pair. The old text cited #47; the citation is gone, so the claim now has no visible source |
| 125 | "you can apply one method to every flight, so that years compare" | line 123 says flights differ in density and in classification; the CHM section says vegetation is mostly class 1 | Overstated: one method is necessary for comparison, not sufficient. The removed text said "comparing change over time needs exactly that", which was the necessary form |
| 125 | "They also give products LidarBC does not publish, …" | - | TRUE |
| 127 | "Every file is LidarBC's, on the province's objectstore." | every item's `laz` href is `nrs.objectstore.gov.bc.ca/gdwuts/…` (live item and samples) | TRUE |
| 127 | "For a minority of them, CanElevation publishes a COPC" | 13,970 of 174,282 items (8.0%) carry `copc`. The link resolves to "LiDAR Point Clouds - CanElevation Series" (CKAN `package_show`) | TRUE |
| 127 | "A program can read one area of a COPC over the internet" | `readme_dem.py`, `CopcReader` over `HttpRangeFile` | TRUE |
| 127 | "any other file has to be downloaded whole before its points can be used" | (a) `scripts/laz_classes_probe.py:9,75`: "LAZ is chunked, so a seek fetches one chunk, not the file". The build itself reads points from plain LAZ over HTTP ranges, which is how classes are sampled. (b) One indexed LidarBC file is itself a COPC: `093/093c/2023/pointcloud/bc_093c058_1_1_1_xyes_8_utm10_20230902_20230902.copc.laz` carries a `copc` / "COPC info VLR" at byte 377 (range read). Its item has only a `laz` asset | FALSE, two counter-examples. What is true is narrower: a plain LAZ has no spatial index, so reading one *area* means reading the whole file. The commit deleted the sentence that said exactly that ("A `laz` asset has no spatial index, so the same window from it means downloading the whole file") |
| 127 | "Each item links the LidarBC file and, where there is one, its COPC." | 26 name-matched non-copies are left unlinked by design; the one LidarBC COPC above is linked as `laz` | TRUE (the LidarBC COPC is linked, though not labelled as one) |
| 129 | "one small record per file: where the file is, the area it covers, when it was flown, its coordinate system and its point count" | live item `094o/2026`: `laz` href, geometry and `proj:bbox`, `datetime`, `proj:code`, `pc:count`. `research/filename_dates.md`: 65,166 items carry a year only. Some items carry `proj:wkt2` | TRUE (not given as an exhaustive list; "when it was flown" is to the year for 37% of items; the "area" is the header box) |
| 129 | "No point data is copied" | - | TRUE |
| 129 | "the index is rebuilt each month from the province's listing" | `.github/workflows/update.yml`: cron on the 6th; it publishes the digest diff to the bucket under a 40,000-item ceiling and **does not register**, and its summary asks a person to run `stacs register` from a tailnet machine. The workflow was added 2026-10-12 and has never run (`gh run list --workflow update.yml` is empty), so the first run is 2026-11-06 | Partly FALSE in context: the bucket's records are rebuilt monthly, but the API that the next sentence tells people to search is not updated until someone registers. Line 208 keeps that qualifier ("the API serves them once they are registered"); this sentence drops it |
| 129 | "search … from R (rstac), Python (pystac-client), QGIS 3.42+ …; applications can be built on its API at https://images.a11s.one" | unchanged facts, reworded | TRUE |
| 129 | "the bucket's collection.json links every one" | collection.json (35 MB): 174,282 `item` links = the item count; 4 random hrefs returned 200 without credentials | TRUE |
| 129 | "stacs, the tool that loads them into this API's PostgreSQL database (pgstac), can load them into anyone else's" | stacs is public and MIT; its README says the host, database, API and bucket "are always the caller's", with no defaults pointing at any deployment. It reads items from `bucket_url` | TRUE (it needs ssh to a host running pypgstac ≥ 0.9.6 and a STAC API; "pre-release") |
| 129 | "sister collection on the same API" | the section heading at line 296 still says "on the same endpoint" | TRUE; terminology nit |
| 131 | heading "a DEM read from the cloud-optimised copies" | `readme_dem.py:118-121` exits if any used item lacks `copc` | TRUE |
| 139 | "Only the area shown was read, not the whole files" | 74 of 434 MB transferred; `CopcReader` fetches the octree nodes that meet the window, which extend past it | TRUE in substance |
| 139 | "every tile here has a CanElevation COPC" | `data/readme_dem.json`: 4 items, 4 `copc` hrefs on `canelevation-lidar-point-clouds`; guarded at `readme_dem.py:118` | TRUE |
| 139 | "Most tiles do not have one" | 160,312 of 174,282 items have no `copc` | TRUE |
| 139 | "for those a workflow has to download each file whole" | read in context (reading an area): a plain LAZ has no spatial index | TRUE in context, though see line 127 |
| 139 | "as the canopy height model below does" | `readme_chm.R:85` stops if any item gains `copc`; `readme_chm.json`: 2 items, 532 MB downloaded | TRUE |
| 139 | "That may change if LidarBC publishes cloud-optimised files itself." | LidarBC already publishes at least one COPC (`093c058`, above) | Mostly TRUE; the edge member says "already, once" |
| 141 | the removed sentence "A `laz` asset has no spatial index …" | - | removing it drops the only accurate statement of the limit (see line 127) |
| 191 | "once that catalogue publishes it" (replacing the stac_dem_bc#61 link) | stac_dem_bc README on main already says every item carries `lidarbc:delivery` (#55) | Possibly stale (pre-existing claim): the sister README says the key is already carried. Not introduced by this commit; worth a check |
| 202, 206 | issue links removed | grep for `/issues/`, `/pull/`, "Why from", anchors: only `#which-classes-a-file-holds` remains, and it resolves | TRUE, nothing left dangling |

## Findings

- **[claim]** README.Rmd:127: "any other file has to be downloaded whole before its points can
  be used" is false. The build itself reads points from plain LAZ by HTTP range, one 50,000-point
  chunk per seek (`scripts/laz_classes_probe.py:9,75`). One indexed LidarBC file is a real COPC
  (`093/093c/2023/pointcloud/bc_093c058_1_1_1_xyes_8_utm10_20230902_20230902.copc.laz`, COPC
  info VLR in its header), and its item carries only `laz`. Restore the qualifier this commit
  deleted at line 141: a plain LAZ has no spatial index, so reading one area means reading the
  whole file. Also say "nearly every other file", or name the one LidarBC COPC.
- **[claim]** README.Rmd:125: "canopy height models for 2023 and 2024 only" drops the qualifier
  that makes it true. There are 264 CHM tiles, in 19 of the 48 mapsheet-years from 2023–24,
  about 1.1% of the DEM tiles in those deliveries (stac_dem_bc#47 and #29; the live listing
  matches today). Suggested: "canopy height models for a few hundred tiles flown in 2023 and 2024".
- **[claim]** README.Rmd:125: "LidarBC publishes DEMs" reads as universal next to "surface
  models for most tiles but not all". 12 of the 233 pointcloud mapsheet-years have no DEM
  (2,361 indexed files; for example `093/093i/2018`, `092/092a/2016`, `082/082k/2021`,
  `093/093o/2017`, all checked live). Suggested: "DEMs for most deliveries".
- **[claim]** README.Rmd:129: "the index is rebuilt each month" sits in the paragraph that sends
  readers to the API. The workflow publishes to the bucket only and does not register (its
  summary asks for a manual `stacs register`). It has never run either: it was added on
  2026-10-12, and its first scheduled run is 2026-11-06. Line 208 keeps the qualifier ("the API
  serves them once they are registered"). Here it is dropped. Say "the records are rebuilt each
  month", or carry the registration clause.
- **[claim]** README.Rmd:125: "apply one method to every flight, so that years compare" turns a
  necessary condition into a sufficient one, and line 123 of the same page contradicts it
  (flights differ in density and classification). The removed text had the right form. Suggested:
  "which is what comparing years needs".
- **[claim]** README.Rmd:125: "surface models are made to specifications that differ between
  deliveries" rests on one tile pair (082f020, 2017 against 2022; rtj#229 via stac_dem_bc#47). With
  the #47 link removed, nothing on the page supports it. Either soften it ("can differ") or link
  the research.
- **[claim, minor]** README.Rmd:296: the heading says "on the same endpoint", while line 129 now
  says "on the same API".
- **[note, pre-existing]** README.Rmd:191: "once that catalogue publishes it". The stac_dem_bc
  README on main already says every LidarBC item carries `lidarbc:delivery` (#55). If so, the
  future tense is stale. This commit did not introduce it; it only removed the #61 link.
- **[note]** The commit holds only README.Rmd. The re-rendered README.md and index.html are
  uncommitted in the working tree. They match a scratch render of 0a50c62's Rmd byte for byte.

Rendering: both targets rendered cleanly from a scratch copy with `update_query = FALSE`, and the
repo link appears in both outputs.
