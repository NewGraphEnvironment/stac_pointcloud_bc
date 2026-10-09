# stac_pointcloud_bc

Versions describe the **published catalogue**: the state of `s3://stac-pointcloud-bc`
and the `stac-pointcloud-bc` collection at <https://images.a11s.one>. A tag means "the
catalogue is in this state". Same convention as
[`stac_dem_bc`](https://github.com/NewGraphEnvironment/stac_dem_bc).

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
