# Findings — Draw the canopy height figure over the delta's ground (#30)

## Issue context

### Problem

The landing page's canopy height figure (`fig/maxan_chm.png`, #19) shows the Maxan Creek delta as trees on a flat 0 m meadow. The ground under it is not flat: a quick draft of the ground returns from the same two 2019 tiles shows a looped low in the northwest that looks like an old meander, narrow channels under the forest on the south edge, and faint threads between the stands on the delta. The figure could show the forest *and* the old channels it grows among, which is what a floodplain reader comes for.

The draft (ground hillshade, ground below its ~100 m median in blues clamped at −1.5 m, canopy 2 m and up on top) came out washed out, for reasons in how it was drawn, not in the data:

- Only the low ground was coloured, over a grey hillshade, under a 60%-opaque canopy layer, so every colour was diluted twice.
- The elevations' 1st–99th percentiles span 712.7–743.4 m, but the floodplain sits within about a metre of its median (713.7 m); the south slope takes most of any min–max stretch.
- The lake has no ground returns, so the triangulation fills it with flat grey and fans of artifacts.

A turbo-type ramp stretched over the floodplain's own range is known to bring these channels out in QGIS on the overlapping LidarBC DEM.

### Explore first

1. **Which DEM.** Our 1 m TIN from the ground returns vs. LidarBC's published DEM for the same delivery (`stac-elevation-bc`). Both come from the same 2019 ground returns, so expect them to match; difference the two over the window and say whether either shows the channels better. Using our own keeps the page's point (products from the points), the published one is a STAC read instead of a computation.
2. **Which surface.** Elevation stretched over the floodplain's range, vs. a relative elevation model (height above the creek's water surface), which takes out the valley's slope so one scale covers the whole delta.
3. **The stretch and the blend.** A colour ramp (blues, or turbo as in QGIS) stretched to the floodplain's percentiles, not the window's; hillshade multiplied in rather than under a transparent layer; the canopy drawn so it does not wash the ground out; the lake masked with the canopy figure's existing water mask (no ground return within `GROUND_GAP`).

Straight lows in the hayfield-like block in the northwest and under the south forest may be ditches or a road, not old channels: the caption says only what the figure shows.

### Done when

- `fig/maxan_chm.png` (or a second figure beside it) shows canopy height over the floodplain's ground, with the old channels legible at page width.
- `scripts/readme_chm.R` builds it from the same pinned delivery and window; `data/readme_chm.json` carries any number the caption quotes.
- The README caption and alt text describe what is shown, and README.md / index.html are re-rendered from README.Rmd.



<details><summary>The draft probe (2026-10-17), run from the repo root against the cached data/readme_laz/: 42 min, most of it the CHM height normalisation</summary>

```r
# Probe: does the Maxan delta's bare earth show old channels? Ground DEM, relative to a
# smoothed valley surface, blues for low, hillshade, CHM over it. Reads the cached .laz.
setwd("/Users/airvine/Projects/repo/stac_pointcloud_bc")
source("scripts/readme_functions.R")
out <- commandArgs(TRUE)[1]
crs <- "EPSG:3156"  # placeholder, replaced from the file
laz <- list.files("data/readme_laz", full.names = TRUE)
xy <- sf::st_coordinates(sf::st_transform(sf::st_sfc(sf::st_point(c(-126.1256, 54.3814)), crs = 4326),
                                          lidR::st_crs(lidR::readLASheader(laz[1]))))
box <- c(xy[1] - 700, xy[2] - 600, xy[1] + 500, xy[2] + 400)
rb <- box + 30 * c(-1, -1, 1, 1)
las <- lidR::readLAS(laz, select = "xyzrc",
                     filter = paste("-drop_withheld -keep_xy", paste(rb, collapse = " ")))
chm <- pc_readme_chm(las, box, res = 0.5, ground_gap = 5)
g <- lidR::filter_ground(las)
grid <- terra::rast(terra::ext(rb[1], rb[3], rb[2], rb[4]), resolution = 1, crs = lidR::st_crs(las)$wkt)
dem <- lidR::rasterize_terrain(g, grid, lidR::tin())
dem <- terra::crop(dem, terra::ext(box[1], box[3], box[2], box[4]))
# Relative elevation: the DEM minus a broad (~101 m) median, so the valley's slope drops out.
base <- terra::focal(dem, w = 101, fun = "median", na.rm = TRUE)
rel <- dem - base
water <- terra::resample(is.na(chm), dem, method = "near")
hs <- terra::shade(terra::terrain(dem, "slope", unit = "radians"),
                   terra::terrain(dem, "aspect", unit = "radians"), 35, 315)
print(terra::global(dem, quantile, probs = c(.01, .5, .99), na.rm = TRUE))
print(terra::global(rel, quantile, probs = c(.01, .05, .5, .95, .99), na.rm = TRUE))
sh <- \(r) terra::shift(r, dx = -box[1], dy = -box[2])
png(out, width = 1350, height = 1125, res = 150)
terra::plot(sh(hs), col = grey.colors(100, 0.15, 0.95), legend = FALSE, axes = FALSE, box = FALSE, mar = c(1, 1, 1, 5))
# Low ground in blues, deepest darkest; above the base surface left clear.
lo <- terra::clamp(rel, -1.5, 0, values = TRUE); lo[rel >= -0.1] <- NA
terra::plot(sh(lo), col = rev(hcl.colors(50, "Blues 3"))[10:50] |> rev(), alpha = 0.75, add = TRUE,
            legend = TRUE, plg = list(title = "below\nvalley (m)", cex = 0.8))
ch <- chm; ch[chm < 2] <- NA
terra::plot(sh(ch), col = hcl.colors(50, "YlGn", rev = TRUE), alpha = 0.6, add = TRUE, legend = FALSE)
dev.off()
```

</details>


## Plan-mode exploration (2026-10-17)

- `scripts/readme_chm.R` reads 2 cached `.laz` (`data/readme_laz/`, 532 MB), calls
  `pc_readme_chm()` (`scripts/readme_functions.R`), plots with `plot_chm()`, writes
  `data/readme_chm.json`. The issue's probe took 42 min, mostly `normalize_height()`.
- **The published DEM exists for this delivery:** `stac-elevation-bc` item
  `093-093l-2019-dem-bc_093l040_xli1m_utm09_2019`, 1 m, EPSG:3156, 638 MB, **uncompressed and
  strip-organised (`Block=13554x1`)**, nodata −32767, `AREA_OR_POINT=Point` with corners on .5 m.
  So a window read is ~1,060 contiguous rows (~57 MB), and our grid must be aligned to its cells
  for a difference without resampling.
- Water is already defined: `pc_readme_chm()` masks cells with no ground return within
  `GROUND_GAP` m. Those cells' class 1 returns are the water surface (lake 712.5–712.8 m,
  `research/laz_classes.md`), which gives a data-derived water surface for an REM with no new
  dependency.
- Tests are synthetic-LAS testthat in `tests/readme_functions_test.R`; README.Rmd excerpts code
  between `# --- … : begin/end` markers (`pc_readme_lines()`); figures render at `out.width = "100%"`.


## Phase 1: our ground TIN vs LidarBC's published DEM (2026-10-17)

Published: `stac-elevation-bc` item `093-093l-2019-dem-bc_093l040_xli1m_utm09_2019`, window read
with `gdal_translate -projwin` over `/vsicurl/` in 12 s (1262 x 1062 cells, as requested, no
nodata in the window). Ours: `lidR::rasterize_terrain(filter_ground(las), grid, tin())` at 1 m on
cells aligned to the published grid (corners on .5 m), from the cached 2019 `.laz`. Both EPSG:3156,
but `terra::same.crs()` is FALSE between lidR's WKT and GDAL's: set one CRS from the other before
comparing. Probe scripts: scratchpad `p30_probe.R`, `p30_diff.R` (not committed).

TIN minus published, 787,028 land cells (published > 712.55 m):

| p1 | p5 | p25 | p50 | p75 | p95 | p99 |
|---|---|---|---|---|---|---|
| -0.25 | -0.10 | -0.02 | 0.01 | 0.04 | 0.17 | 0.33 m |

15.5% of land cells differ by more than 0.1 m, 0.23% by more than 0.5 m. The differences sit on
bank edges and on the forested south slope (where the ground returns are sparse and the two
interpolations differ); the open delta is within noise. **The published DEM is hydro-flattened:**
40% of the window is exactly 712.54 m (the lake), where our TIN fans across the water 0.12-0.29 m
higher. That is the only systematic difference.

Drawn with the same turbo stretch (712.6-718 m) and hillshade, the two show the same channels:
the NW loop, the threads across the delta, the low along the lakeshore. Neither is better for the
channels. **Verdict: our TIN**, with the lake masked by the CHM's existing water mask, which
removes the one place it is worse. It keeps "products from the points" and adds no second STAC
read of a 638 MB strip-organised file.

Land elevations (published, lake excluded): p1 712.74, p5 713.19, p25 714.23, p50 715.24,
p75 717.06, p90 734.23 m. The issue's "within about a metre of its median (713.7 m)" was taken over
a window that included the lake; the delta itself rises about 5 m from the lakeshore westward.

### Correction (same day): the 0.01 m median hid a half-cell shift (review G10)

Regressing the difference on the published DEM's gradient gave difference = 0.50·(−dz/dy) +
0.50·(−dz/dx), r² 0.76 (783,878 land cells): an aspect-dependent bias, not noise. Probe
`p30_shift.R`: a 1 m TIN on cells with integer corners, against the published DEM shifted by each
half-cell combination:

| shift (x, y) | median abs | p95 abs |
|---|---|---|
| −0.5, −0.5 | 0.040 | 0.400 m |
| −0.5, +0.5 | 0.030 | 0.200 m |
| +0.5, −0.5 | 0.030 | 0.310 m |
| **+0.5, +0.5** | **0.000** | **0.000 m** |

(761,571 land cells.) **Shifted 0.5 m east and 0.5 m north, the published DEM equals a TIN of the
ground returns to the millimetre.** Read as GDAL reads it by default (`AREA_OR_POINT=Point`, origin
681700.5, 6032224.5), every value sits half a cell south-west of the ground it describes. Neither
GDAL reading is right: `GTIFF_POINT_GEO_IGNORE=TRUE` gives origin 681701.0, 6032224.0, which is
(+0.5, −0.5) and still wrong in y; the match needs 681701.0, 6032225.0. One tile measured
(`bc_093l040_xli1m_utm09_2019`); how many LidarBC DEMs share it is not known.

So the earlier table (bank edges and the south slope differing) was this shift, and the hydro-
flattened lake is the only real difference. The verdict stands — our TIN, which is the same surface
correctly placed — for a stronger reason: the published tile, as read, is misplaced by 0.71 m.

## Phase 2: surface, stretch, blend (2026-10-17)

**The water mask is the lake only.** `pc_readme_chm()`'s mask (no ground return within 5 m) is one
8-connected patch of 1,947,056 cells (40.4% of the window); the creek is narrower than 10 m and is
not in it. Its returns' per-cell medians: p1 712.65, p50 712.72, p99 712.78 m, so the lake surface
is 712.72 m, level, and the water cells cannot measure the creek's fall (review G4).

**The creek's fall**, measured instead from the FWA Maxan Creek line (EDGE_TYPE 1000) sampled every
10 m, lowest TIN ground within 6 m (110 points, probe `p30_rem.R`): 715.9 m at the window's west
edge to 712.9 m near the mouth, about 3 m over 0.6 km. Land rises ~5 m from the lake westward.

Three REMs tried (renders `remA/B/C_turbo.png`, scratch):
- A: lowest ground within ~100 m (5 m min, focal 41 min, 21 mean): halos and blotches; the delta
  turns red against its own channels.
- B: IDW of the creek-bed samples and lake-edge points: wedge and band artifacts from the IDW.
- C: plane fitted to the creek-bed samples (resid sd 0.19 m), floored at the lake: the NW block
  falls below the plane, so the trend is not planar there.

None showed the channels better than elevation stretched over the floodplain's range, and each
added either artifacts or a network read (FWA). **Choice: elevation, coloured as height above the
lake's surface** (712.72 m measured from the water cells' returns), 0 to 5 m. Land elevations
(published, lake excluded): p1 712.74, p50 715.24, p75 717.06, p90 734.23 m; 0-5 m above the lake
(712.7-717.7 m) holds the delta's bulk, the south slope runs past it.

**Canopy.** On a quick stand-in CHM (max z per 0.5 m cell minus the TIN) the delta is largely
shrub 2-5 m, so an opaque canopy hides most of the delta's ground. Drawn instead with opacity
growing with height (shrubs a light tint, trees ≥ 15 m nearly opaque) and the ground's hillshade
multiplied through both, the threads stay legible under the shrubs. Ground ramp: plasma (no green,
dark = low, so channels read as dark threads); canopy greens; water light blue. Turbo collides with
green canopy (review G8).

## Phase 3-4: the shipped figure (2026-10-17)

- `scripts/readme_chm.R` end to end: 10.5 min (10:12:40-10:23:11Z), downloads cached. Every #19
  number in `data/readme_chm.json` reproduced exactly; new keys `water_level_m` 712.72,
  `relief_m` 5, `tree_m` 2, `exaggeration` 4, `figure_cell_m` 1.
- `fig/maxan_chm.png`: 1530 x 1000 px (1200 x 1000 map at 1 m, 330 px of scales), 1.6 MB, up
  from 397 KB; index.html embeds it as base64 (~2.2 MB).
- At 880 px (GitHub's column), the threads across the delta, the creek and the curving lows on the
  northwest block read; the straight lines under the south forest are left unnamed in the caption.
- Defaults chosen by eye, at page scale, from scratch renders through the shipping helpers (`p30_fig.R`): shrub opacity
  0.15 (0.25 greyed the delta), exaggeration 4 (3 left the NW scars faint), relief 5 m (4 m put
  the NW block's top into the ramp's end).

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `[mask] CRS do not match` (lidR WKT vs GDAL's for EPSG:3156; `same.crs()` FALSE) | Set one raster's CRS from the other, or compare values |
| `color intensity -1, not in 0:255` from `as.raster()` | `terra::shade()` goes negative facing away from the sun: clamp the shade factor at 0 |
| Pixel test compared integer to double with `identical()` | Compare by `==` |
