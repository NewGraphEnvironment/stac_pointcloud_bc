## Outcome

The landing page's canopy figure (`fig/maxan_chm.png`) now draws the Maxan delta's canopy over its bare ground: a TIN of the same 2019 ground returns on the CHM's own 0.5 m grid, coloured by height above the lake's surface (712.72 m, measured from the returns over the water) from 0 to 5 m with Plasma trimmed of its green end, shaded northwest-lit with relief ×4, canopy from 2 m tinted in greens growing more opaque up to 15 m, drawn one 1 m cell per pixel through `rasterImage()` because `terra::plot()` thins a 4.8 M-cell raster to 500k cells and breaks thin channels. Old channels across the delta and curving lows on the northwest block now read at page width. Our TIN was chosen over LidarBC's published DEM for this delivery, which turned out to be the same TIN misplaced: GDAL reads it 0.5 m west and 0.5 m south of its ground returns ([research/dem_alignment.md](../../../research/dem_alignment.md), filed as stac_elevation_bc#69). Three relative elevation models (local minimum, IDW of an FWA creek-bed profile, a plane) were tried and dropped for artifacts. Helpers `pc_readme_ground()`, `pc_readme_water_level()`, `pc_readme_relief()`, `pc_readme_relief_png()` are under 20 tests with a restore-the-bug table.

## Measurement

- Published DEM vs ground TIN: unshifted median difference 0.010 m hid a slope-following bias (r² 0.77); moved +0.5 m E and +0.5 m N it matches to the millimetre in 99.8% of 761,571 land cells. A wrong turn first read the 0.01 m median as "the two agree, edge differences only" and the plan review's PixelIsPoint question is what found the shift.
- The CHM water mask is one patch, the lake (40.4% of the window); the creek is too narrow to be in it, so the water cells cannot measure the creek's fall. The creek bed falls about 3 m over 0.6 km (FWA line, 110 samples).
- `scripts/readme_chm.R` end to end: 10.5 min, not the 42 min the issue's probe took (its CHM was 9 min of that). Two runs give a byte-identical PNG; every #19 number in `data/readme_chm.json` reproduced.
- PNG 397 KB → 1.6 MB; index.html 5.6 MB.

Closed by: PR #31
