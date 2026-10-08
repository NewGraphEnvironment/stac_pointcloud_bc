# What a LidarBC `.laz` costs to describe, and what `dsm/*.laz` actually is

**Verified:** 2026-10-07 · **Issues:** #1 (from NewGraphEnvironment/stac_dem_bc#35) ·
**Produced by:** `scripts/laz_header_probe.py` over `scripts/laz_remote.py`; logs
`logs/20261007_*_header_probe.log`, `logs/20261007_*_classification_probe.log`
(gitignored; the numbers below are the record).

## A header read is one 64 KB range request

The objectstore (`nrs.objectstore.gov.bc.ca/gdwuts`) answers a `Range` GET with
`206 Partial Content`. It does **not** send `Accept-Ranges` on HEAD, so a client that
checks for that header first will wrongly conclude ranges are unsupported.

laspy, reading through an HTTP range file object, opens a plain LAZ and parses the
header and all VLRs from the first block. Measured on 10 files (5 `dsm/`, 5
`pointcloud/`) spread over the 11 laz-only mapsheet-years:

| measure | value |
|---|---|
| bytes transferred | 65,536 every file (one request) |
| wall time | 0.11–0.22 s per file |
| file size | 82–392 MB |
| EVLRs | 0 in every file (nothing to fetch from the tail) |

So item geometry and properties come from the header, not the filename: real bounds,
point count, point format, LAS version, CRS. 9,650 files is about 630 MB of range reads.

**CRS is in the header and varies by delivery.** Some files carry an EPSG GeoKey
(`EPSG:3157`, NAD83(CSRS) / UTM 10N; `EPSG:2955`, UTM 11N). Some carry an OGC WKT
compound CRS: `EPSG:2955` + CGVD2013 height (`EPSG:6647`). laspy's
`header.parse_crs()` reads both.

Decompressing points costs more but is still partial. The first 100k–200k points need
1.0–1.5 MB and 0.9–1.6 s, because LAZ is chunked.

## `dsm/*.laz` is an RGB copy of the point cloud, not a surface model

stac_dem_bc#31 recorded 11 mapsheet-years whose `dsm/` directory holds only `.laz`. It
read them as surface models "published as point cloud only". They are not:

- **Every return, not a surface.** The `dsm/` files hold multiple returns per pulse
  (return numbers up to 6), classed 1 (unclassified) and 2 (ground). A
  surface model would hold first or highest returns, not ground returns beneath canopy.
- **The same points as the `pointcloud/` file for the same tile.** For `092g026_1_4_2`,
  the two files have identical bounds and 30,202,168 vs 30,202,170 points, with an
  identical class and return distribution over the first 100k. `082e084_4_1_4` matches
  the same way (58,432,776 vs 58,466,790): the `dsm/` copy drops class 7 (noise), which
  is why its z range is narrower (814–1134 m vs 517–1280 m).
- **What differs is the point format.** `dsm/` files are format 3 (LAS 1.2) or 7 (LAS
  1.4), which add RGB to format 1's
  fields. `pointcloud/` files are format 1, with no colour.
- 5,710 of the 6,067 `dsm/*.laz` in the 11 groups have a `pointcloud/` file with the
  same tile id.

So those 11 mapsheet-years delivered **no DSM**. The 1,211 DEM tiles stac_dem_bc reports
as `no_raster_dsm` lack a surface model, and indexing `dsm/*.laz` would not supply one.
The first increment here is therefore `pointcloud/*.laz` (9,650 files in those groups).
`dsm/*.laz` is a colourised variant, left to a follow-up.

## Unresolved: CanElevation overlap

NRCan's datacube STAC (`datacube.services.geo.ca/stac/api`) has DEM/DSM collections
(`hrdem-lidar`, `cdsm`, ...) but no point cloud collection. The CanElevation point
cloud FTP tree refuses directory listing (403), and the index file name tried 404s. So
whether CanElevation republishes these LidarBC projects is still unknown, and is a
follow-up issue rather than a blocker.
