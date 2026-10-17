# Where a LidarBC DEM sits against its own ground returns

**Verified:** 2026-10-17 · **Issues:** #30 (found comparing DEMs for the canopy figure), stac_elevation_bc#69 ·
**Produced by:** `scripts/dem_alignment_probe.R`, which prints the measurements below (it needs
the `.laz` that `scripts/readme_chm.R` caches in `data/readme_laz/`); the file's format is from
`gdalinfo`, and the window's size from the probe's constants.

One tile measured: `bc_093l040_xli1m_utm09_2019.tif` (`stac-elevation-bc` item
`093-093l-2019-dem-bc_093l040_xli1m_utm09_2019`), against the ground returns (class 2) of the
same delivery's point clouds `bc_093l040_3_4_1` and `_3_4_2`, over the landing page's canopy
figure at the Maxan Creek delta: its 1.2 × 1.0 km window with the 30 m margin read around it,
1.26 × 1.06 km.

## The DEM is a TIN of the ground returns, and GDAL puts it half a cell south-west of them

The file is 1 m, Float32, uncompressed, strip-organised (`Block=13554x1`), nodata −32767, and
tagged `AREA_OR_POINT=Point`. GDAL reads its origin as 681700.5, 6032224.5 (it moves a
PixelIsPoint tie point half a cell up and left); with `GTIFF_POINT_GEO_IGNORE=TRUE` it reads
681701.0, 6032224.0.

A 1 m TIN of the ground returns (`lidR::rasterize_terrain(tin())`, cells with whole-metre edges)
against the DEM moved by each half-cell, land cells only (the DEM flattens the lake):

| DEM moved (x, y) | median abs diff | p95 abs diff | cells over 1 mm | max abs diff |
|---|---|---|---|---|
| −0.5, −0.5 m | 0.040 m | 0.400 m | 92.1% | 4.76 m |
| −0.5, +0.5 m | 0.030 m | 0.200 m | 90.3% | 3.79 m |
| +0.5, −0.5 m | 0.030 m | 0.310 m | 89.9% | 3.67 m |
| **+0.5, +0.5 m** | **0.000 m** | **0.000 m** | **0.21%** | 1.10 m |

(761,571 land cells in each row.) Moved 0.5 m east and 0.5 m north of where GDAL reads it, the
DEM is the TIN to the millimetre in 99.8% of land cells; the 0.21% that differ (up to 1.10 m)
were not examined.
So its true origin is 681701.0, 6032225.0. Neither GDAL reading gives that: the default is 0.71 m
south-west of it, and ignoring PixelIsPoint fixes x but moves y the wrong way. The misplacement
is invisible in a plain difference: against a TIN on the DEM's own cells as GDAL reads them, the
median difference is 0.010 m (756,048 land cells), and the error shows only as a bias that follows
the slope: TIN minus DEM ≈ −0.50 · dz/dx − 0.50 · dz/dy, r² 0.77. That is the DEM's value at each
cell belonging half a cell east and north.

Beyond the offset, the DEM departs from the TIN at the water and along its shore. The lake is
flattened to 712.54 m (40.3% of the window), where a TIN fans across it 0.12-0.28 m higher
(p1-p99). On the low ground between the lake and 712.9 m that is not the flattened lake (27,439
cells), 20.6% differ by more than 1 mm, p95 0.25 m, max 0.45 m. Why they differ there was not
examined.

**Not known:** whether other LidarBC DEMs, other deliveries or other years share the offset. One
tile is one tile.

## What the canopy figure does with it

The landing page's figure builds its ground from the point cloud (`pc_readme_ground()`), which
above the lake's shore is this DEM correctly placed, so it reads no DEM. A workflow that overlays LidarBC DEMs on
anything else should check the offset on its own tiles with the probe's method first.
