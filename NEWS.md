# stac_pointcloud_bc

Versions describe the **published catalogue**: the state of `s3://stac-pointcloud-bc`
and the `stac-pointcloud-bc` collection at <https://images.a11s.one>. A tag means "the
catalogue is in this state". Same convention as
[`stac_dem_bc`](https://github.com/NewGraphEnvironment/stac_dem_bc).

## 0.3.0

Every `pointcloud/*.laz` (#2): **174,282 items in 225 mapsheet-years**, up from 9,649 in 11.
This is also the full re-registration that publishes three changes merged since 0.2.0: renamed
fields (#12), class lists (#10) and the delivery key (#5). Unpublished as of this entry.

- **What is listed.** The build walks the objectstore's eight NTS blocks and keeps every
  `<block>/<sheet>/<year>/pointcloud/*.laz`: 175,278 files in 233 mapsheet-years on
  2026-10-10, recorded per group in `data/pointcloud_groups.json`. A later listing that falls
  under 90% of a group's recorded count stops the build; a new group is logged.
- **Held out, each by a named entry with its reason.** 11 files whose header no item can be
  built from: four hold 0 or 1 points, three have a box no tile could have, three sit outside
  the mapsheet their path names, and one declares a CRS its file name contradicts. And 985
  files in eight 2017 deliveries (`093e`, `103b`, `103c`, `103f`, `103g`, `103h`, `103j`,
  `103k`) that state no CRS at all; indexing them from the CRS their delivery's DEM declares is
  #15. If a file in either set is re-delivered without its fault, the build stops and asks for
  its entry to be reviewed.
- **Fields renamed (#12)**, on the item and on a `copc` asset: `nge:product` →
  `lidarbc:product`, `nge:datetime_source` → `lidarbc:datetime_source`, `nge:filename_date` →
  `lidarbc:filename_date`, `nge:las_version` → `las:version`, `nge:point_format` →
  `las:point_format`. Each item lists the two schemas that define them,
  `https://newgraphenvironment.github.io/crate/stac/lidarbc/v1.0.0/schema.json` and
  `.../las/v1.0.0/schema.json` (crate#23), and every item is validated against them.
- **`lidarbc:delivery` (#5).** Each item names its delivery, `<block>/<sheet>/<year>`, the key
  stac-elevation-bc writes on the DEM and DSM items of the same delivery, and the collection
  links stac-elevation-bc as `related`.
- **Class lists (#10).** A LAS header cannot say which classes a file holds, so the build
  samples points from every file at or below the 10th density percentile of its mapsheet-year
  (17,552) and reads whole each one a sample calls ground-only or groundless. **349 items**
  carry `classification:classes` on the `laz` asset, every class with its point count: 12
  ground-only, most of them near-empty or noise tiles, and 253 with no ground at all. A random
  5% of the other files (7,834 sampled) found 2 more, one denser than 96% of its
  mapsheet-year, so about 38 of the 148,894 items neither screened nor audited (95% interval
  5 to 137) hold no ground or only ground but carry no list (`research/laz_classes.md`). Vegetation is mostly class 1: classes 3 to 5 are in
  9% of the randomly sampled files.
- **Dates.** 76 of the 77 deliveries since 2023 (109,327 files) name each file with two days,
  the first and last day flown over that tile; the year directory is the year of the first, and the last can be a later
  year. Such an item carries them as `start_datetime` / `end_datetime` (44,744 items), or as
  its `datetime` when the two are the same day; with names of one day, 64,372 items carry a
  day. In 30 two-day files from 15 deliveries every sampled point's GPS time fell between the
  two days, and in 12 same-day files on that day. 9 deliveries name files with a date whose
  year disagrees with the directory (the first increment's 4 among them), so all their items
  carry the directory year, as do names with a year only: 65,166 items span a year.
  `092p/2017` mixes a day token with no token, so each of its items keeps its own precision,
  as `lidarbc:datetime_source` says. The first increment's day tokens were all in its four
  untrusted deliveries, so 0.2.0 had only years.
- **A compound CRS written vertical-first.** 2,008 files in seven 2021 deliveries write
  `COMPD_CS[VERT_CS, PROJCS]`, which PROJ refuses. They are read with the two parts swapped.
- **COPC.** 13,970 items carry a `copc` asset, in 28 mapsheet-years (0.2.0: 1,964 in 4). 26
  more CanElevation files share a LidarBC file name but are not copies: each has fewer points
  than the LAZ (all `Vancouver_Island_Sunshine_Coast_2018`). They are recorded in
  `data/copc_not_copies.json` and left unlinked. Of the 13,970 linked, the largest box offset
  is 0.01 m and the horizontal EPSG agrees in every pair (`scripts/copc_pairs_measure.py`).
- **Checked against 0.2.0.** Every one of 0.2.0's 9,649 items is still built, and none differs
  from its published body beyond this release's changes: the renamed fields, the new schemas in
  `stac_extensions`, `lidarbc:delivery`, class lists and new `copc` assets
  (`scripts/catalogue_compare.py`). 164,633 items are new. Every item validates against core
  STAC and each schema it lists.

## 0.2.0

CanElevation's COPC linked (#6). **1,964 of the 9,649 items gain a `copc` asset**: the Cloud
Optimized Point Cloud that NRCan's CanElevation series publishes under the same file name. No
item was added or removed, and nothing else in any item changed: before upload, every
published body was compared with its build (`links` removed, as stacs digests them), and the
changed ids were exactly the 1,964 with a `copc` asset, differing by that asset alone
(`scripts/copc_pairs_measure.py --published`). Published 2026-10-09 and verified `IN SYNC`
(9,649 ids equal in both directions, every body digest-equal).

- **Which items.** `092g/2016` 1,155, `092h/2016` 420, `082e/2019` 332, `082l/2019` 57;
  the other seven mapsheet-years have no copy. 13,996 LidarBC file names recur in four
  CanElevation projects, so later increments are likely to link more
  (`research/canelevation_overlap.md`).
- **Checked per item, not by name alone.** A COPC is linked only when its header has the
  same point count, the same horizontal CRS, and a box within 0.05 m of the LidarBC file's.
  All 1,964 passed, with the largest offset 0.01 m (`scripts/copc_pairs_measure.py`). That
  test cannot see a reclassified re-delivery under the same name.
- **The COPC can be a different format.** 1,575 (`Lower_Mainland_2016`) are LAS 1.4
  format 6 where the source is 1.2 format 1. The item's `pc:schemas` describe the `laz`
  asset; the `copc` asset carries its own `nge:las_version` and `nge:point_format`.
- **Collection.** The description names the four CanElevation projects, and Natural
  Resources Canada is added as a `host` provider.

## 0.1.0

First increment (#1, from stac_dem_bc#35): **9,649 items**, one per `pointcloud/*.laz`
in the 11 mapsheet-years whose `dsm/` directory holds no raster. Published 2026-10-07
and verified `IN SYNC` (id sets equal in both directions, every body digest-equal).

- **What an item holds.** Footprint, point count, point format and CRS come from the
  file's LAS header, read with one 64 KB range request (`research/laz_header_read.md`).
  Items carry the `pointcloud`, `projection` and `file` extensions. The `laz` asset
  points at the province's file; nothing is copied.
- **One file excluded:** `092h/2016/.../bc_092h003_2_3_1_xyes_7_utm10_20160913.laz`.
  Its header box starts at the UTM origin (`mins = [0, 0, 0]`). Every other footprint's
  centre is in the NTS 1:250k sheet its key names.
- **Dates are years, not days, in this release.** Four deliveries (`082k/2017`,
  `092g/092h/092j 2016`) name files with dates that are not acquisition dates: a 2018
  date in a 2017 flight, or a 2017 processing date. Every other delivery names only the
  year. So every item carries its directory year as `start_datetime` / `end_datetime`,
  and the filename's token is kept in `nge:filename_date`.
- **`dsm/*.laz` is not indexed.** In every tile compared, it was an RGB-colourised copy
  of the same-tile `pointcloud/*.laz`, not a surface model: two tile pairs compared point
  for point, and a 5-file sample of returns and classes, all in these 11 groups. 357 of the
  groups' 6,067 have no same-id `pointcloud/` tile, and the 324 outside the groups were not
  examined. So, as far as was measured, these groups delivered no DSM, and the gap
  stac_dem_bc reports for them is real (stac_dem_bc#53). Whether to index them is #3.
