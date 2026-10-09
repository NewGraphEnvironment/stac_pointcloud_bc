# Findings — Index LidarBC point clouds as stac-pointcloud-bc (#1)

## Issue context

## Problem

LidarBC point clouds sit in the same objectstore as the DEMs and nothing indexes them.
Measured on a full bucket walk 2026-08-28 (575,411 keys):

| product | files | indexed |
|---|---|---|
| `pointcloud/` `.laz` | **175,172** | no |
| `dem/` `.tif` | 100,081 | yes |
| `dsm/` `.tif` | 95,889 | yes (as of v1.0.0, NewGraphEnvironment/stac_dem_bc#31) |
| `dsm/` `.laz` | 6,391 | no |
| `chm/` `.tif` | 264 | no, now NewGraphEnvironment/stac_dem_bc#47 |

Point cloud is the **largest product in the bucket**, with more files than DEM.

## Decided 2026-09-30

- **Its own collection, `stac-pointcloud-bc`, one item per `.laz` tile and year.** The
  `.laz` tiles have different, smaller footprints than the raster tiles, so as assets of
  the raster item they would misstate their geometry (rtj#229). This rules out option 1
  below.
- **Its own repo, `stac_pointcloud_bc`,** reversing rtj#229's "one repo". That argument
  rested on shared machinery that was never packaged. Once NewGraphEnvironment/stacs#1 packages registration and
  verification, the new repo holds only discovery and item creation, and each repo stays
  one collection, one CI role, one release history. **This issue transfers there once the
  repo exists.**
- **Its own bucket, `stac-pointcloud-bc`** (rtj#362). Sharing `stac-dem-bc` would let two
  repos' roles overwrite each other's catalogues, would put a co-tenant beside a catalogue
  that lives at the bucket root, and would be refused by NewGraphEnvironment/stac_dem_bc#42's registration test.
- **Blocked on NewGraphEnvironment/stacs#1.** Without it the new repo starts life with a third copy of the
  registration scripts.

## The concrete gap, not just completeness

**11 mapsheet-years publish their surface model as `.laz` only**, stranding
**1,211 DEM tiles** that v1.0.0 records as `no_raster_dsm` in
`data/dsm_pairing_report.md`:

```
082/082e/2018  082/082e/2019  082/082f/2018  082/082g/2018  082/082j/2018
082/082k/2017  082/082l/2018  082/082l/2019  092/092g/2016  092/092h/2016
092/092j/2016
```

Those deliveries *did* ship a surface model. We report it as absent because we only
index rasters.

## Item granularity

From NewGraphEnvironment/stac_dem_bc#29, point cloud is subdivided roughly **20x finer than the raster grid**
(`082f/2022`: 51 raster tiles against 999+ `.laz`, mean 595 MB). One item per file
gives a collection larger than the elevation one, with footprints that do not align to
the raster tiling. That is the honest shape; the elevation item can link to its covering
point cloud items rather than carry them as assets.

Options as originally costed:

1. ~~A `pointcloud` asset on the existing DEM item~~: rejected, footprints differ.
2. **A separate collection** with its own finer tiling: chosen, above.
3. **Index only the `.laz` that closes the 1,211-tile gap** (the 11 laz-only
   mapsheet-years) and defer the rest. **Still the right first increment**, now inside
   the new collection: bounded, it closes a gap we have already published, and it forces
   the granularity and metadata questions on a small set.

## Open before building

- **What an item's geometry and properties come from.** Filenames only, or a PDAL read of
  each `.laz` header (real extent, point count, density, CRS, classification presence).
  rtj#229's pilot found DEM footprints are mapsheet-sized containers, not where the data
  is (082f037: 13.8% and 2.2% valid), which argues for the header read. But reading
  175k files of ~600 MB over the network is the same bottleneck as the DEM build. Header
  reads are range requests, so measure the per-file cost on the first increment before
  choosing.
- Whether `dsm/*.laz` (6,391) belongs in this collection or is a surface-model product
  of its own.
- The link from an elevation item to its covering point cloud items (`rel` type, and
  which side owns it).
- **Does PDAL read a remote plain `.laz` header by range request, or download the whole
  file?** [stactools-canelevation](https://github.com/stactools-packages/canelevation)
  and [stactools-pointcloud](https://github.com/stactools-packages/pointcloud) build items
  from a header-only PDAL read (`quickinfo`), but their source is NRCan **COPC**, where
  that is cheap by design. LidarBC ships plain `.laz` (~595 MB mean). Measure on one file
  (bytes transferred, wall time) before choosing between header-read and filename-only items.
- **Does NRCan CanElevation already publish these?** CanElevation is the national point
  cloud series, distributed as COPC with its own STAC. If it already carries BC LidarBC
  projects, part of this collection duplicates it. Check their index for BC projects and
  overlap with the 11 first-increment mapsheet-years before building.
- **Write item creation stactools-shaped:** a pure `create_item(href) -> pystac.Item`
  with nothing about our bucket, host or CI in it, using the `pointcloud` and `proj`
  extensions as those packages do. It is the same boundary as `stacs` (#37), and it
  keeps a later `stactools-lidarbc` contribution a lift rather than a rewrite. Copy the
  pattern rather than depend on either package: both were last pushed 2023-09.

Relates to NewGraphEnvironment/stac_dem_bc#29, NewGraphEnvironment/stac_dem_bc#31, NewGraphEnvironment/stacs#1, NewGraphEnvironment/stac_dem_bc#42, NewGraphEnvironment/stac_dem_bc#47, NewGraphEnvironment/rtj#229, NewGraphEnvironment/rtj#362

## Exploration 2026-10-06/07

- Live walk (575,438 keys, 2026-10-06): 181,708 `.laz`, of which 175,317 are `pointcloud/`
  and 6,391 are `dsm/`. 4 have `copc` in the name.
- The 11 laz-only mapsheet-years hold 6,067 `dsm/*.laz` and 9,650 `pointcloud/*.laz`.
  The user chose `dsm/*.laz` as the first increment.
- Filenames: `pointcloud/bc_082e003_1_4_4_xyes_8_utm11_170603.laz` and
  `dsm/bc_082e004_1_1_1_cyes_12_utm11_2018.laz`. The tile id has the same shape as the
  raster tiles; the date is a 6-digit `yymmdd` or a 4-digit year.
- `s3://stac-pointcloud-bc` exists (us-west-2) and is empty; local `airvine` credentials
  can write to it.
- The repo layout follows `stac_airphoto_bc`: uv, `stacs.toml`, `tests/test_stacs_config.py`.

## Phase 1 probes (2026-10-07), full write-up in `research/laz_header_read.md`

- Header read = one 64 KB range request, 0.11–0.22 s, 0 EVLRs (10 files). Rule passed:
  items take their geometry from the header.
- **`dsm/*.laz` is an RGB-colourised copy of the same-tile `pointcloud/*.laz`, not a
  surface model.** Same bounds, point counts within the noise class, point format 3/7 vs 1.
  So the 11 groups delivered no DSM. The user re-chose the increment: `pointcloud/*.laz`,
  9,650 files.
- CanElevation overlap is unresolved: NRCan STAC has no point cloud collection, and the
  FTP listing returns 403.

## Errors Encountered

| Error | Resolution |
|-------|------------|
| The probe refused every file: `server does not advertise byte ranges` | The objectstore answers a Range GET with 206 but sends no `Accept-Ranges` on HEAD. Dropped that check; the 206 check on each read is the real guard |
