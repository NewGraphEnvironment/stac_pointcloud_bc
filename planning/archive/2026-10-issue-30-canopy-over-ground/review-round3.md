# Code-check round 3 (#30): findings

Reviewer: subagent, 2026-10-17. Read-only on the repo. The probes ran from a scratch copy
(`scratchpad/r3/check.R`) against the cached `data/readme_laz/` and the published DEM over
`/vsicurl/`, 11:04 to 11:15 UTC.

## The mechanism

**A sentence names the whole subject ("the DEM", "the surface", "every number", "every
delivery", "the ramp"), but the producer behind it measured only a filtered subset.** The
probe's agreement figures are for *land cells with TIN > 712.9 m*. "Prints every number" is
true only of the probe's own `cat()` lines. "Indexes every delivery" is true of the build's
groups after `EXCLUDE_DELIVERIES`. "No green" holds for the ramp's lower 93%. The prose takes
its scope from the conclusion and drops the filter that made the number true. Round 2's "to
the millimetre" and "only departure" for *every* cell came from this mechanism, and so did
"1.26 × 1.06 km" (the read box presented as the window). Round 1's direction error is a
second, separate mechanism: a relative term ("west of", the shift's sign) was resolved
without writing out the anchor (which raster moves onto which).

Wherever the mechanism reaches, the check is the same: name the producer's filter, then ask
whether the sentence's subject is wider than it.

## Findings

- **[bug] stac_elevation_bc#69 body, "Open" list, first bullet.** It says "Measuring that
  needs the ground returns, which `stac-pointcloud-bc` indexes for every delivery." This is
  false. `scripts/catalogue_build.py:224` `EXCLUDE_DELIVERIES` holds out eight 2017
  deliveries (093e and 103b/c/f/g/h/j/k), and CLAUDE.md records them as 985 files with no
  CRS. A reader scoping the "how widespread" question is told every delivery can be
  checked, and eight cannot be from this collection. Suggested wording: "for every delivery
  but eight from 2017 whose files state no CRS".

- **[bug] README.Rmd:165 ("The ground under it"), "LidarBC publishes a DEM for this
  delivery, and it is the same surface".** The page links research/dem_alignment.md, which
  says the DEM flattens the lake to 712.54 m over 40.3% of the window. That alone contradicts
  "the same surface". The agreement also holds only on land above 712.9 m, the probe's
  `LAND_ABOVE` filter. Measured on the +0.5, +0.5 grid (scratch probe):
  - Land with TIN > 712.9: 761,356 cells, 0.18% over 1 mm, max 1.10 m. **Holds.**
  - Low ground with TIN ≤ 712.9 and the DEM not at the lake level: 27,439 cells, **20.6% over
    1 mm, p95 0.25 m, max 0.45 m.** This is the dark-blue shore fringe of the figure.
  - DEM flat at 712.54: 516,549 cells, 100% over 1 mm, p95 0.23 m, max 0.75 m.

  So the claim holds only on land above 712.9 m. Suggested wording: "the same surface on
  land, but flattened over the water and the shore".

- **[bug] research/dem_alignment.md:40.** "Beyond the offset, the DEM's one systematic
  departure from the TIN is the water". "One" is unsupported, and the measurement above
  argues against it. Low ground that the DEM does *not* hold at the lake level departs in
  20.6% of 27,439 cells (p95 0.25 m). That is either a second departure or the flattening
  reaching past the flat cells onto the shore. The note's own probe never measured cells
  between 712.54 and 712.9 m, because `LAND_ABOVE` excludes them and `flat` takes only the
  modal value. The note also says the 0.21% "were not examined", which by itself rules out
  "one". These are the round-2 "only departure" words, reworded rather than removed.

- **[fragile] research/dem_alignment.md:3-4, "**Produced by:** `scripts/dem_alignment_probe.R`,
  which prints every number below".** This is false. The probe does not print the file's
  1 m cell, Float32, "uncompressed", `Block=13554x1`, nodata −32767 or `AREA_OR_POINT=Point`.
  Those come from `gdalinfo`, and I checked them against `gdalinfo` today: all hold. It does
  not print 0.71 m (derived: √(0.5²+0.5²)). It does not print 1.2 × 1.0 km, 30 m or
  1.26 × 1.06 km, which are constants of readme_chm.R and `BOX`. This is the round-1 finding
  ("numbers no script printed") fixed by widening the provenance sentence rather than
  narrowing it. Suggested wording: "prints every measured number below; the file's
  structure is from `gdalinfo`".

- **[fragile] scripts/readme_functions.R:351.** The comment says "The ground ramp has no
  green, so it cannot be read as canopy." This is false at the ramp's top. Of the 256
  colours of `hcl.colors(256, "Plasma")`, numbers 239 to 256 have G > R, ending at `#DAFF47`
  (chartreuse, Luv hue about 100°). The 5+ m end is that colour, and 16.3% of land cells sit
  at ≥ level + 5 m. 89.7% of those are on the forested south slope, under canopy greens,
  which is exactly where the comment says confusion cannot happen. The figure shows it: the
  south slope and the west edge read lime. The alt text's "yellow at 5 m and above" is
  borderline for the same colour.

- **[fragile] README.Rmd:165, "drawn over it in greens, more opaque the taller it
  stands".** `pc_readme_relief()` caps opacity at `full = 15` m (`pmin(..., 1)`), so every
  canopy from 15 m to 39.5 m is drawn at the same 0.9. That includes the 20,580 cells at
  ≥ 30 m. The function's own doc says it correctly ("`opacity[2]` from `full` m"); the
  caption does not.

## Claim table

Sources: J = `data/readme_chm.json` key; P = probe output line (cc/probe_output.txt);
R3 = scratch probe of this round; C = code path.

### README CHM section (rendered README.md)

| # | Claim | Source | Verdict |
|---|---|---|---|
| 1 | alt: ground coloured by height above the lake | C `pc_readme_relief` `ramp(z, level, level+relief)` | holds |
| 2 | alt: "dark blue at the lake's level" | C, Plasma[1] `#001889` | holds |
| 3 | alt: "through purple and orange to yellow at 5 m and above" | J relief_m 5; Plasma top `#DAFF47` is yellow-green | holds, borderline (see the ramp finding) |
| 4 | alt: "shaded to show its shape" | C `terra::shade` × f | holds |
| 5 | alt: creek meanders across the delta to the lake | figure | holds |
| 6 | alt: narrow channels dark threads, under a light green tint of shrubs | figure; C opacity 0.15 at tree m | holds |
| 7 | alt: "Stands of trees up to 40 m tall … on the delta" | J height_m.max 39.5, `round()` gives 40; R3 max 39.5 at (611, 175) m from the SW corner, in the delta stand; 74% of the ≥ 30 m cells are north of y = 250 | holds (40 is the rounded-up bound) |
| 8 | alt: forested south slope green over yellow | figure; R3 90% of the ≥ 5 m ground is at y < 250 | holds |
| 9 | alt: curving lows mark higher ground in the NW | figure | holds |
| 10 | alt: lake on the east light blue | C WATER_COL on NA chm | holds |
| 11 | caption: canopy over bare ground, coloured by height above lake, shaded | C | holds |
| 12 | caption: shrubs drawn as a light tint | C opacity[1] 0.15 | holds |
| 13 | caption: curving lows to the NW | figure | holds |
| 14 | caption: 37% ≥ 2 m, 12% ≥ 10 m "of the cells on land" | J share_2m 0.366, share_10m 0.123, over non-NA chm | holds |
| 15 | caption: tallest 1% exceed 27.8 m, max 39.5 m | J height_m p99, max | holds |
| 16 | caption: light blue 41% of the window is the lake and the channel | J cells_na/cells = 0.4104; C every NA chm cell painted WATER_COL | holds |
| 17 | How: 1.2 × 1 km window plus 30 m margin | J window_m, margin_m | holds |
| 18 | How: 2 items, both 093/093l/2019 | J items, items_found, delivery | holds |
| 19 | How: 532 MB, 107.8 M points, 23.4 M in window | J bytes_files, points_files, points_window | holds |
| 20 | How: 33% class 2, 67% class 1 | J share_ground, share_class1 | holds |
| 21 | How: only noise and withheld left out | C NOISE_CLASSES, -drop_withheld | holds |
| 22 | How: pit-free at 0.5 m; no ground within 5 m, or no return, means empty | J cell_m, ground_gap_m; C | holds |
| 23 | Ground: same TIN of the ground returns, same 0.5 m grid | C pc_readme_ground (classes 2 and 9, same b grid, crop); test compareGeom | holds |
| 24 | Ground: lake surface 712.72 m, the median of the returns over the water | J water_level_m; C pc_readme_water_level (non-ground in NA chm cells, lake plus channel) | holds |
| 25 | Ground: 0 to 5 m "holds the delta, while the slope to the south runs past it" | R3: 16.3% of land ≥ level + 5; 89.7% of that south (y < 250), 6.2% on the west edge | holds (not exclusive) |
| 26 | Ground: lit from the northwest | C sun c(35, 315) | holds |
| 27 | Ground: relief exaggerated 4 times | J exaggeration; C e = ground × 4 | holds |
| 28 | Ground: canopy of 2 m and up in greens | J tree_m; C h >= tree | holds |
| 29 | Ground: "more opaque the taller it stands" | C pmin at full = 15 | **false above 15 m** |
| 30 | Ground: shading runs through the canopy | C rgb × f after the blend | holds |
| 31 | Ground: each pixel is the average of the 0.5 m cells in its 1 m square | J figure_cell_m; C aggregate(2, mean); png one cell per pixel | holds |
| 32 | Ground: the DEM "is the same surface" | P table rows (land > 712.9 only); R3 low ground 20.6% differ; P lake flat | **false as unqualified** |
| 33 | Ground: read as published it sits 0.5 m W and 0.5 m S of the points | P "+0.5 +0.5 … 0.000"; C `terra::shift(pub, +0.5, +0.5)` matches | holds |

### research/dem_alignment.md

| # | Claim | Source | Verdict |
|---|---|---|---|
| 34 | the probe "prints every number below" | P has none of 13554, −32767, 0.71, 1.2/1.0/1.26/1.06, 30 | **false** |
| 35 | one tile measured | C one DEM URL | holds |
| 36 | window 1.2 × 1.0 km, 30 m margin, read 1.26 × 1.06 km | C BOX = (−730, −630, 530, 430) | holds |
| 37 | 1 m, Float32, uncompressed, Block=13554x1, nodata −32767, AREA_OR_POINT=Point | gdalinfo, 2026-10-17 (not the probe) | holds (wrong producer) |
| 38 | GDAL origin 681700.5, 6032224.5 | P line 1 | holds |
| 39 | GDAL moves a PixelIsPoint tie point half a cell up and left | P lines 1-2: 681701 to 681700.5 (left), 6032224 to 6032224.5 (up) | holds |
| 40 | IGNORE gives 681701.0, 6032224.0 | P line 2 | holds |
| 41 | table: four rows of median, p95, share, max | P rows | holds |
| 42 | 761,571 land cells in each row | P cells column | holds |
| 43 | moved 0.5 E and 0.5 N it is the TIN to the mm in 99.8% of land cells; 0.21% differ, up to 1.10 m | P +0.5 +0.5 row (1 − 0.0021) | holds (land = TIN > 712.9) |
| 44 | true origin 681701.0, 6032225.0 | derived: GDAL + (0.5, 0.5) | holds |
| 45 | default is 0.71 m SW of it | derived √0.5 | holds |
| 46 | ignoring fixes x, moves y the wrong way | 6032224.5 to 6032224.0, away from 6032225.0 | holds |
| 47 | unshifted median 0.010 m over 756,048 land cells | P line "unshifted" | holds |
| 48 | TIN − DEM ≈ −0.50 dz/dx − 0.50 dz/dy, r² 0.77 | P coefficients −0.495, −0.505 | holds |
| 49 | DEM's value at each cell belongs half a cell E and N | follows from 48 and the shift | holds |
| 50 | "the DEM's **one** systematic departure … is the water" | R3: low non-flat ground 20.6% differ; 0.21% "not examined" | **unsupported** (and contradicted) |
| 51 | lake flat 712.54 m, 40.3% of the window | P lake line | holds |
| 52 | TIN 0.12-0.28 m higher there (p1-p99) | P lake line | holds |
| 53 | the figure's ground "is this DEM correctly placed" | P (land only), R3 | holds on land > 712.9 only; same scope as #32 |
| 54 | heading: "GDAL puts it half a cell south-west of them" | P | holds |

### research/README.md row

| # | Claim | Source | Verdict |
|---|---|---|---|
| 55 | the DEM is a TIN of its delivery's ground returns | P land rows | holds on land; lake flattened (as the note says) |
| 56 | GDAL reads it 0.5 m W and 0.5 m S of the returns | P | holds |
| 57 | found by differencing at half-cell shifts | C probe loop | holds |

### stac_elevation_bc#69

| # | Claim | Source | Verdict |
|---|---|---|---|
| 58 | title: half a cell SW of its ground returns | P | holds |
| 59 | placed 0.5 W, 0.5 S; moved E/N it is the TIN to the mm in 99.8% of land cells (0.21%, up to 1.10 m) | P | holds |
| 60 | misplaced by 0.71 m | derived | holds |
| 61 | 1 m, AREA_OR_POINT=Point, origin 681700.5, 6032224.5 | gdalinfo; P | holds |
| 62 | matching origin 681701.0, 6032225.0 | derived | holds |
| 63 | IGNORE: right in x, 1 m south in y | P line 2 | holds |
| 64 | 761,571 land cells of a 1.26 × 1.06 km window | P; BOX | holds |
| 65 | table (median, p95) | P | holds |
| 66 | unshifted median 0.01 m | P | holds |
| 67 | −0.50·dz/dx − 0.50·dz/dy, r² 0.77 | P | holds |
| 68 | only one tile measured | C | holds |
| 69 | stac-pointcloud-bc indexes the ground returns "for every delivery" | catalogue_build.py:224 EXCLUDE_DELIVERIES (8) | **false** |
| 70 | items' proj:transform and footprints are taken from the file as GDAL reads it | published item: `proj:transform` [1, 0, 681700.5, 0, −1, 6032224.5], proj:bbox from 681700.5 | holds |

### Code comments that describe behaviour

| # | Claim | Source | Verdict |
|---|---|---|---|
| 71 | readme_chm.R header: ground from the same returns | C readLAS, then pc_readme_ground | holds |
| 72 | readme_chm.R header: "so the old channels … show" | not measured | interpretive; not a published sentence |
| 73 | readme_chm.R: RELIEF "holds the delta's land" | R3 (as #25) | holds |
| 74 | readme_chm.R: drawn at FIG_CELL m, one cell to one pixel | C aggregate and png size | holds |
| 75 | readme_chm.R plot_chm: each pixel is the mean of the cells under it | C aggregate mean | holds |
| 76 | pc_readme_ground: same grid as pc_readme_chm, cell for cell | C; test | holds |
| 77 | pc_readme_ground: TIN runs across water; the figure paints water over it | C wet painted after NA | holds |
| 78 | water_level: those cells have no ground return near them | C chm NA mask | holds |
| 79 | water_level: "their unclassified returns" | C keeps all classes but 2, 9 and noise; data has only 1, 2, 7 | holds for this data |
| 80 | water_level: NA when there is no water | C; test | holds |
| 81 | GROUND_PAL: "has no green, so it cannot be read as canopy" | Plasma 239-256 G > R, `#DAFF47`; R3 16.3% of land | **false** |
| 82 | pc_readme_relief doc: ramp ends hold; tint at tree; opacity[2] from full; flat keeps colour; water WATER_COL; one grid | C; tests | holds |
| 83 | hillshade normalised so flat = 1; unknown counts as flat | C f / sin(35°), NA to 1 | holds |
| 84 | "No ground under land is drawn blank; water is water whether or not the TIN reaches it" | C order of assignment; test | holds |
| 85 | pc_readme_relief_png: rasterImage, one cell to one pixel | C; test of dims and stripes | holds |
| 86 | probe: "Prints every number in research/dem_alignment.md" | P | **false** (same as #34) |
| 87 | probe: the DEM flattens the lake to 712.54 m | P lake line | holds |
| 88 | probe: moved half a cell, the DEM's cells land on the TIN's, so near only picks them up | C whole-metre edges vs .5 edges | holds |
| 89 | probe: cells 3 m inside the read, so the TIN has no edge in them | C e | holds |

## Code

No functional bug was found in `pc_readme_ground`, `pc_readme_water_level`,
`pc_readme_relief`, `pc_readme_relief_png`, `plot_chm` or the probe. I checked the matrix
recycling in the blend and in `rgb * f` (row-wise, correct), the order of the NA and water
assignments, the legend tick positions, the scale-bar pixel length at FIG_CELL = 1, and the
probe's `-projwin` order and focal kernels (dz/dx and dz/dy signs correct).
