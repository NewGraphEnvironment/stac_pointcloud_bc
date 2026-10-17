# Code-check round 1: branch 30-draw-the-canopy-height-figure-over-the-d

Reviewer read the diff, the changed files in full, the rendered README.md/index.html excerpts,
`data/readme_chm.json` and `fig/maxan_chm.png` (by its pixels). Nothing in the repo was modified.

## Findings

- **[bug, published statement false] research/README.md:13** — the index row says the DEM "sits
  0.5 m south-west of where GDAL reads it". The direction is reversed. `dem_alignment.md` and
  the probe show the DEM matches the TIN only when it is moved **+0.5 m east and +0.5 m north** of
  where GDAL reads it. So the DEM's true position is north-east of where GDAL reads it, and GDAL
  reads it south-west of the points, which is how README.Rmd puts it ("read as published it sits
  half a metre south-west of the points"). The magnitude is also off. The offset is 0.5 m on
  each axis, and the note itself calls the default reading "0.71 m south-west of it". Suggested
  wording: "GDAL reads it 0.5 m west and 0.5 m south of where it belongs". The same reversed
  wording is in the title of stac_elevation_bc#69 ("A LidarBC DEM sits half a cell south-west of
  where GDAL reads it"). That title is outside this diff but has the same fault.

- **[bug, small, visible in the published PNG] scripts/readme_functions.R:359** (`pc_readme_relief`)
  — `rgb[is.na(z), ] <- NA` runs after the water fill (`rgb[wet, ] <- WATER_COL`), so a water
  cell the ground TIN does not reach is painted NA, and `pc_readme_relief_png` draws NA as white.
  The docstring says water is `WATER_COL`, and the test is named "water wins", but here the
  water does not win. Reproduced: a cell with `chm` NA and `ground` NA comes back
  `red/green/blue = NA`. In `fig/maxan_chm.png` this is a white wedge of 532 px in the lake at the
  map's bottom-right corner (rows 854-1000, columns 1194-1200). It runs into the white legend
  margin, so the lake's east edge looks cut on a slant. The cause is the TIN's extrapolation
  limit: lidR `tin()` extrapolates only about 50 m from a ground point, and that corner is open
  lake. The share is small (about 0.05% of the window), but it grows with any window that puts
  more open water far from shore. The fix is to apply the NA blanking before the water fill, or
  to blank only `is.na(z) & !is.na(h)`.

- **[fragile, provenance] research/dem_alignment.md:3-4, 30-33** — the header says the note is
  "Produced by: `scripts/dem_alignment_probe.R`". The probe produces only the four-row table and
  the GDAL-read origin. Several numbers in the prose have no producer in the repo:
  - "unshifted, the median is 0.01 m". An unshifted comparison needs a resampling across the
    half-cell, and the probe does none.
  - the aspect regression "difference ≈ 0.5 · dz/dx + 0.5 · dz/dy, r² 0.76"
  - "the lake is flattened to 712.54 m, where a TIN fans across it 0.12-0.29 m higher"
  - the `GTIFF_POINT_GEO_IGNORE=TRUE` origin, 681701.0, 6032224.0

  These may all be right, but someone re-running the stated producer cannot re-derive them.
  Either extend the probe or narrow the "Produced by" line to the table.

## Checked and found sound

- Grid alignment. `ground` and `chm` are built and cropped identically. `box` sits on the 0.5 m
  lattice of `b`, so the crop is exact (2400 × 2000), and `aggregate(2)` divides it evenly.
- Hillshade normalisation. With terra's `shade()`, flat ground gives `sin(alt)`, so `f == 1` on
  flat ground. The `angle` and `direction` positional arguments are correct, and so is the sun
  at azimuth 315 (northwest, as the caption says).
- The PNG maps one unit to one pixel (`xaxs/yaxs = "i"`, `mai = 0`, `interpolate = FALSE`), and
  the 500 m bar is 500 px at 1 m.
- Legend ticks match the linear ramps: 0-5+ for the ground, and 2/10/20/30+ for the canopy at
  `(ct - tree) / (top - tree)`.
- `water_level_m` is written to the JSON from the same `level` the figure uses. The README's
  `stopifnot` covers every new key the prose reads. The rendered README and index.html carry
  712.72, the exaggeration of 4 and the 0.5/1 m cells.
- The `pc_readme_lines` markers are unique. The `is.na(level)` stop sits outside the excerpt.
- The alt text and caption claims match the PNG: the plasma ramp from dark blue to yellow,
  channels as dark threads, dark green stands on the delta, the south slope green over yellow,
  and curving lows in the NW.
- Direction in README.Rmd ("read as published it sits half a metre south-west of the points") is
  correct; only the research index reverses it.

## Pre-existing, not introduced here (no action asked)

- The tests use `withr` and `data.table`, which `scripts/DESCRIPTION` does not declare. The new
  PNG test adds another `withr::` call, but the gap predates this branch.
