# Review: commits 77622cc, 75e5129, c50480f (landing-page revision, #24), round 3

Reviewed 2026-10-13 against `git diff 6be1d89..c50480f -- README.Rmd`, with line numbers from
c50480f's README.Rmd. Every probe was a read, and no repo file was edited except this one. The
render ran in a scratch copy (`git archive c50480f` plus the working tree's caches). Live probes
were against `images.a11s.one` and the LidarBC objectstore, run around 13:30 PDT on 2026-10-13.
The scripts are in the session scratchpad (`page.py`, `chm.py`).

## Measured sets used

- **DEM tiles in LidarBC's 2023 and 2024 deliveries.** I paged every `stac-elevation-bc` item with
  `"lidarbc:delivery" LIKE '%/2023'` or `'%/2024'` (limit 1000, following next links). That gives
  **72,814 items in 48 deliveries**, the same 48 mapsheet-years as the 2023–24 entries of
  `data/pointcloud_groups.json` (set-equal). No elevation item carries a `chm` asset yet
  (stac_dem_bc#47 is open), so I counted CHMs on the objectstore.
- **CHM tifs.** I listed `<delivery>/chm/` live for those 48: **264 tifs in 18 deliveries**. The
  DEM items in those 18 number **23,294** (round 2 had 23,293). That is 264 / 23,294 = **1.13%,
  or 1 in 88**, inside the deliveries that have any CHM. Over all 2023–24 deliveries it is
  264 / 72,814 = **0.36%, or 1 in 276**. stac_dem_bc#47 states its 1.1% the narrow way: "~1.1% of
  DEM tiles **within the deliveries that have any**". The sister README does the same: "~1.1%
  coverage of the mapsheet-years that carry them".
- **"None earlier".** I listed `<group>/chm/` live for all 233 pointcloud mapsheet-years. 19 have a
  `chm/` (18 with tifs, plus `092f/2023`, which is empty), and all 19 are 2023 or 2024. Round 1
  found 221 DEM mapsheet-years, all among the 233, so no DEM-only delivery is missed.
- **Items without `lidarbc:delivery`.** I paged them again: **2,288, all `dem`-only**. 2,245 are
  under `gdwuts/albers10k2m/_completed_dem/` and 43 under `albers10k2m_new/_completed_dem/`
  (`map_<r>_<c>.tif`). Their bboxes together span -133.79 to -114.07 and 48.30 to 58.84, which is
  the whole province east to west. Summed, the bbox areas come to about **163,000 km², about 17% of
  BC's 945,000 km²**. That sum includes overlaps, so the true coverage is no larger.
- **LidarBC files named `.copc`.** Searching the live API (`id LIKE '%copc%'`) finds **1 of
  174,282** pointcloud items: `093c058…20230902.copc.laz`. Round 1 found its COPC info VLR. The
  other three `copc`-named files in CLAUDE.md's count are not indexed.

## Per-sentence table

| line | sentence | members walked | verdict |
|---|---|---|---|
| 123 | "LidarBC publishes DEMs for most deliveries" | unchanged since round 2: 221 of 233 | TRUE |
| 123 | "surface models for most tiles but not all" | unchanged: 95,888 of 102,460 | TRUE |
| 123 | "canopy height models for about one in a hundred tiles of its 2023 and 2024 deliveries" | Read as written, the denominator is all 2023–24 deliveries: 264 of 72,814 DEM tiles, **1 in 276**. "One in a hundred" holds only inside the 18 deliveries that carry any CHM (264 of 23,294, 1 in 88). The other 30 deliveries have none | **FALSE**, off by a factor of 2.8. The round-2 fix moved the grain from deliveries to tiles but kept the 18-delivery denominator and dropped its qualifier ("within the deliveries that have any", as #47 says) |
| 123 | "…, none earlier." | 19 `chm/` directories among the 233, all 2023–24 | TRUE |
| 125 | "A plain LAZ file, the format LidarBC publishes, has none, so reading one area of it means reading the whole file." | 174,281 of 174,282 indexed files are plain LAZ. One, `093c058…copc.laz`, is a COPC that LidarBC publishes. Round 2 settled the mechanism: the chunk table seeks by point, not by area | TRUE for the plain-LAZ claim. The appositive "the format LidarBC publishes" is FALSE at one edge (1 of 174,282). Minor: it reads as universal, and line 139 ("if LidarBC publishes cloud-optimised files itself") reads as though it has published none |
| 127 | "The index is rebuilt each month from the province's listing, …" | `update.yml` cron `17 10 6 * *`. `catalogue_build.py` walks the live listing. `gh run list --workflow update.yml` is empty, so the first run is 2026-11-06. A 40,000-item ceiling caps one month's publish | TRUE as a description of the schedule (round 2's note stands: removals stay in the bucket) |
| 127 | "…and the API at <https://images.a11s.one> serves the new records once they are registered." | The landing page answers as a STAC Catalog (item-search and filter conformance). `/collections/stac-pointcloud-bc` returns 200. Registration is manual (`update.yml:16-19`) | TRUE. The round-2 ordering gap is fixed: the API is named where it is first used |
| 127 | "…and applications can be built on the same API." | same endpoint, and `rstac::stac("https://images.a11s.one/")` appears later on the page | TRUE |
| 189 | "Every stac-elevation-bc item from a LidarBC delivery carries the same key" | All 2,288 items without the key are `albers10k2m*` mosaic tiles. Every other item, 100,172 of them, carries it | TRUE |
| 189 | "(its province-wide mosaics do not)" | The 2,288 tiles span the province but cover at most about 17% of its area | Mostly TRUE. "Province-wide" fits the product's extent and scope, not its coverage. This is a nit: the parenthetical is there to identify the exception, and it does |
| 189 | "and this collection links it as `related`" | round 2: live on the collection | TRUE |

## Findings

- **[claim]** README.Rmd:123: "canopy height models for about one in a hundred tiles of its 2023
  and 2024 deliveries" is wrong by a factor of 2.8. The live objectstore has 264 CHM tifs, and
  the live API has 72,814 DEM tiles across the 48 deliveries from 2023–24, so the share is 1 in
  276. One in a hundred (264 of 23,294, 1.1%) holds only within the 18 deliveries that have any
  CHM. This is the same mechanism as before, inside the round-2 fix: #47's qualifier "within
  the deliveries that have any" was dropped. Suggested, true at both edges: "and canopy height
  models for a few hundred tiles in 2023 and 2024, under one in a hundred of those years'
  tiles, none earlier". Alternatively: "…for about one in a hundred tiles of the 18 deliveries
  from 2023 and 2024 that have any".
- **[claim, minor]** README.Rmd:125: "A plain LAZ file, the format LidarBC publishes" is false
  for one file. LidarBC publishes one indexed file as a COPC (`093/093c/2023/pointcloud/
  bc_093c058_1_1_1_xyes_8_utm10_20230902_20230902.copc.laz`, 1 of 174,282). Suggested: "the
  format of all but one LidarBC file", or "the format LidarBC publishes nearly every file in".
  The claim that a plain LAZ needs a whole-file read for an area still holds.
- **[bug]** README.md and index.html at HEAD (c50480f) were last re-rendered from an earlier
  revision of README.Rmd, before the round-1 and round-2 fixes. `git show HEAD:README.md` line 17
  still reads "publishes DEMs, … canopy height models for 2023 and 2024 only. … its surface
  models are made to specifications…", and line 211 reads "will carry the same key once that
  catalogue publishes it". 75e5129 committed outputs with an mtime of 13:13, older than
  README.Rmd's 13:23. A scratch render of c50480f differs from both committed outputs:
  README.md at lines 17, 19, 21 and 211, and index.html at line 3415 and after. Re-render both
  targets after the line-123 fix and commit them. The Pages site serves index.html.
- **[note]** README.Rmd:189: the "province-wide mosaics" (the 2,288 `albers10k2m*` tiles) span
  the province's extent but cover about 17% of its area or less. This is acceptable as a name
  for the product. Say "provincial 2 m mosaic tiles" if exactness is wanted.

Rendering: both targets rendered from the scratch copy with `update_query = FALSE`. There were no
errors, and README.md has no "error" text. The revised sentences render as written.
