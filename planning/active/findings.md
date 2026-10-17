# Findings — Draw the canopy height figure over the delta's ground (#30)

## Issue context

## Problem

The landing page's canopy height figure (`fig/maxan_chm.png`, #19) shows the Maxan Creek delta as trees on a flat 0 m meadow. The ground under it is not flat: a quick draft of the ground returns from the same two 2019 tiles shows a looped low in the northwest that looks like an old meander, narrow channels under the forest on the south edge, and faint threads between the stands on the delta. The figure could show the forest *and* the old channels it grows among, which is what a floodplain reader comes for.

The draft (ground hillshade, ground below its ~100 m median in blues clamped at −1.5 m, canopy 2 m and up on top) came out washed out, for reasons in how it was drawn, not in the data:

- Only the low ground was coloured, over a grey hillshade, under a 60%-opaque canopy layer, so every colour was diluted twice.
- The elevations' 1st–99th percentiles span 712.7–743.4 m, but the floodplain sits within about a metre of its median (713.7 m); the south slope takes most of any min–max stretch.
- The lake has no ground returns, so the triangulation fills it with flat grey and fans of artifacts.

A turbo-type ramp stretched over the floodplain's own range is known to bring these channels out in QGIS on the overlapping LidarBC DEM.

## Explore first

1. **Which DEM.** Our 1 m TIN from the ground returns vs. LidarBC's published DEM for the same delivery (`stac-elevation-bc`). Both come from the same 2019 ground returns, so expect them to match; difference the two over the window and say whether either shows the channels better. Using our own keeps the page's point (products from the points), the published one is a STAC read instead of a computation.
2. **Which surface.** Elevation stretched over the floodplain's range, vs. a relative elevation model (height above the creek's water surface), which takes out the valley's slope so one scale covers the whole delta.
3. **The stretch and the blend.** A colour ramp (blues, or turbo as in QGIS) stretched to the floodplain's percentiles, not the window's; hillshade multiplied in rather than under a transparent layer; the canopy drawn so it does not wash the ground out; the lake masked with the canopy figure's existing water mask (no ground return within `GROUND_GAP`).

Straight lows in the hayfield-like block in the northwest and under the south forest may be ditches or a road, not old channels: the caption says only what the figure shows.

## Done when

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


## Errors Encountered

| Error | Resolution |
|-------|------------|
