# What a LidarBC `.laz` costs to describe, and what `dsm/*.laz` actually is

**Verified:** 2026-10-07 (a field name revised 2026-10-10, #12) · **Issues:** #1 (from
NewGraphEnvironment/stac_dem_bc#35), #12 · **Produced by:** `scripts/laz_header_probe.py`
over `scripts/laz_remote.py`; logs
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
- **What differs is the point format.** In the tiles compared, the `dsm/` copy is format 3
  (LAS 1.2) or 7 (LAS 1.4), which add RGB, where the `pointcloud/` file is format 1.
  Across all 9,650 `pointcloud/` files in the increment, 6,363 are format 1, but 3,275
  are format 6 and 12 are format 7 (RGB), so colour is not unique to `dsm/` (review read,
  2026-10-07).
- 5,710 of the 6,067 `dsm/*.laz` in the 11 groups have a `pointcloud/` file with the
  same tile id. The other 357 were not compared.

**How far this was measured:** two tile pairs compared point for point and header for header,
and a 5-file sample of returns and classes, all inside the 11 groups. The 324 `dsm/*.laz`
outside them were not examined. Every file compared says the same thing, so as far as was
measured those 11 mapsheet-years delivered **no DSM**. The 1,211 DEM tiles stac_dem_bc reports
as `no_raster_dsm` lack a surface model, and indexing `dsm/*.laz` would not supply one.
The first increment here is therefore `pointcloud/*.laz` (9,650 files in those groups).
`dsm/*.laz` is a colourised variant, left to a follow-up.

## CanElevation overlap

Moved to [canelevation_overlap.md](canelevation_overlap.md). The FTP tree that refused
listing here had moved to a listable S3 bucket, and #6 measured the overlap there.

## What a full read of the increment's headers found (review, 2026-10-07)

All 9,650 `pointcloud/` headers read without error. Three things the item code now handles:

- **One faulty header.** `092h/2016/.../bc_092h003_2_3_1_xyes_7_utm10_20160913.laz` has
  `mins = [0, 0, 0]` and real maxs, so its box starts at the UTM origin. The build excludes it by
  name (`EXCLUDE` in `scripts/catalogue_build.py`). `item_create` refuses a box with a side of
  zero or over 5 km, or whose centre is not in the NTS sheet its key names (below), so a new
  fault fails the build rather than publishing a footprint that reaches the equator.
- **BoundCRS.** 1,678 files carry a compound CRS whose horizontal part is a `BOUNDCRS` (with a
  TOWGS84 binding). Its EPSG code (2955) appears only once the binding is unwrapped. The 197 Esri-WKT
  files in `082k` cannot be identified at all, so they publish `proj:wkt2` with no code.
- **Filename dates are not reliably acquisition dates.** 266 `082k/2017` files are named
  `_180827`, but GPS time (adjusted standard time) puts them in October 2017. 2,008 files in
  `092g/092h/092j 2016` are named with a 2017 date equal to the header creation date, which is a
  processing date. Trust is per delivery: `082k/2017` also has a `_171015` file whose year agrees
  but whose GPS times do not fall on the 15th. So in any mapsheet-year where some filename date
  disagrees with the directory year, no file's filename date is used. Every item there carries
  the directory year as a range and keeps the token in `lidarbc:filename_date`
  (`nge:filename_date` until #12).
- **GPS time is not a general oracle.** It settled `082k/2017`, but in `082g/2018` the first-chunk
  GPS dates scatter across 2010–2018. Use it only where it is internally consistent.
- **Footprints are checked against the map sheet named in the key.** All but the excluded file
  have their centre in the NTS 1:250k sheet their key names. That catches a wrong-zone label,
  which a BC-wide box would not. There is no lower bound on tile size: 104 files have a side
  under 100 m, the smallest 1 x 1 m with 14 points, and they are real.

The 15 ` (2).laz` files are not copies of their namesakes: they have different extents and point
counts. Both are indexed.

## What a header cannot say: some deliveries are ground-only (2026-10-09, #9)

Class counts are not in the LAS header, so nothing the build reads says whether a file carries
vegetation and buildings. Reading points for the landing page's DEM demo (`scripts/readme_dem.py`)
found `092g/2016/.../bc_092g028_1_1_1_xyes_8_utm10_20170714` returning **only class 2** in a
1.6 × 1.2 km window (748,497 points), while its three neighbours carry classes 1 and 2. A coarse
sample of the whole tile's COPC (octree levels 0–2, 296,120 points; code-check round 3) was also
100% ground. The COPC's point count equals the LidarBC file's (the #6 pairing), so this is how the
province delivered it. How common it is was measured in #10:
[laz_classes.md](laz_classes.md) (one ground-only tile in the increment; 57 with no ground at all).
