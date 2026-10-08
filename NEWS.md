# stac_pointcloud_bc

Versions describe the **published catalogue**: the state of `s3://stac-pointcloud-bc`
and the `stac-pointcloud-bc` collection at <https://images.a11s.one>. A tag means "the
catalogue is in this state". Same convention as
[`stac_dem_bc`](https://github.com/NewGraphEnvironment/stac_dem_bc).

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
