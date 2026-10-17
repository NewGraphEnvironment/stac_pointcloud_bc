# Review: #30 part 2 (valley-floor figure), round 1

Reviewed `diff2.patch` (README.Rmd, data/readme_rem.json, maintaining.md, scripts/readme_functions.R,
scripts/readme_rem.R, tests/readme_functions_test.R) and the committed `fig/maxan_rem.png`.

Method: copied the tracked tree to a scratch dir and ran a copy of `scripts/readme_rem.R` that also
wrote `dem`, `rem` and `water` (Float64), the FWA streams and the bed samples. The copy reproduced
`data/readme_rem.json` exactly and `fig/maxan_rem.png` byte for byte (`cmp`). All numbers below come
from those objects, from FWA/DRA WFS queries (bcdata, 2026-10-17), or from the source DEM's gdalinfo.
(An earlier probe wrote the diagnostics as Int32 by terra's default and gave nonsense; it was
discarded. The numbers here are from the Float64 rerun, which matches the JSON's 0.37.)

## Findings

- **[bug: published figure and number]** scripts/readme_rem.R:116 and scripts/readme_functions.R:428-441:
  **4.5% of the land (38.8 ha) lies below the modelled bed surface, and the figure draws it in the
  bed's colour.** `share_floor` is `mean(r >= 0 & r < RELIEF)`, so those cells are left out of
  the numerator. The colour ramp clamps them to dark blue, the colour the alt text calls "at the
  bed". 1.2% of the land is more than 1 m below the bed, and the minimum is -8.94 m. Consequences:
  - The README's "37% of the land here lies within 3 m of a stream bed" leaves out cells it draws
    as within 3 m. Counting them gives `r < 3` 41.5%, or `-3 < r < 3` 41.4%. The published
    number is low by about 4 points.
  - The worst cells are an artefact, not real ground. In the bottom left, the bed surface runs
    between Crow Creek's upstream end, with a bed sample at z = 745.38 at pixel (1,434), and Maxan
    Creek near the bottom edge, at z = 728.02 at pixel (324,574). Inside the samples' hull the
    TIN's long triangles do it, and outside the hull the IDW fallback does. Three cells:
    - Pixel (114,570): ground 735.74 m, bed 744.68 m, so REM -8.94 m and drawn dark blue. That
      ground is about 7.7 m above Maxan's bed, so it should be yellow.
    - Pixel (220,500): ground 730.00, bed 732.73, REM -2.74. It is about 2.7 m above Maxan.
    - Pixel (250,540): REM -0.70.
    Other negative patches sit in the central field (pixels 480-570 x 150-300) and east of Maxan
    (530-610 x 455-540). A mask is at scratchpad `rev.*/neg.png`.
  - So the alt text ("dark blue at the bed") and "the colour is height above the nearest stream
    bed" do not hold over those patches. The quantity drawn is height above a surface
    interpolated between streams at different levels. Between a high and a low stream, that
    surface sits above the low stream's bed.

  Fix options: count `r < RELIEF` (or `abs(r) < RELIEF`) in `share_floor` and state the negative
  share; and/or build the bed so it never interpolates across a divide. For example, take the
  per-cell minimum over a few nearest samples, or the bed of the nearest sample alone (the
  "nearest stream bed" the caption names) instead of a TIN.

- **[published claim false]** README.Rmd:201 ("How it was made"): **"A triangulated surface through
  them is the bed under every cell."** `pc_readme_rem()` falls back to inverse-distance weighting
  on a 40 m grid wherever lidR's TIN is NA. Its own roxygen says so, and lidR 4.3.3's `tin()` also
  extrapolates by `knnidw(3, 1, 50)` within 50 m of the hull. Measured on this window:
  - 10.25% of cells are NA after `rasterize_terrain(..., tin())` and take the coarse IDW bed.
  - 10.7% of the window is outside the bed samples' convex hull, mostly the bottom-left, top-left
    and bottom-right corners.
  - The -8.94 m cell above is one of the IDW cells.

  The sentence holds for about 89% of cells, not every one.

- **[published claim wider than the code]** README.Rmd:201 ("Every 10 m along each, the lowest ground within 15 m stands in for its
  bed"), scripts/readme_functions.R:395. The window is a square,
  `w = 2 * ceiling(15 / 4) + 1 = 9` cells of 4 m, centred on the cell that holds the sample point.
  Its cell centres reach ±16 m from that cell's centre, so they are up to 18 m from the point
  along an axis and about 25 m along a diagonal, not "within 15 m". `ceiling()` makes the window
  wider than `reach` at any cell size that does not divide it. Same wording in the roxygen at
  :386 and the comment at readme_rem.R:26. Either use a circular `terra::focalMat(dem, reach,
  "circle")`-shaped weight, or state the square.

- **[published claim incomplete, could mislead]** README.Rmd:167 (canopy caption addition):
  **"The straight line across the forest on the slope to the south is a road (it is in BC's
  Digital Road Atlas), and the curved lows down that slope are gullies."** DRA
  (`WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP`) has **two** roads across that slope in the CHM
  window, both surface "rough". Positions are m from the window's top-left:
  - The straight one, (0,920) to (646,909), matches the straight line in the figure. That half
    of the sentence holds.
  - A curving one, (0,874) via (103,842), (214,833) and (400,864) to (646,909), follows the top
    edge of the forest. Overlaid on `fig/maxan_chm.png`, it coincides with the most visible
    curved dark line on that slope, at about (0-330, 830-880).

  A reader told "the curved lows ... are gullies" will take that road for a gully. The downslope
  lows between the two roads look like gullies; the curved cut along the forest edge is the
  second DRA road. Name both roads, or say which curved lows are meant. The overlay is at
  scratchpad `rev.*/chm_south.png`.

- **[fragile]** scripts/readme_functions.R:401: `k[seq(1, length(k), by = spacing)]` errors with
  "wrong sign in 'by' argument" when `water` is given but holds no TRUE cell (reproduced). Not
  reached by this window (it has two lakes). It is reached if the window or `WATER_AREA` changes
  so that no flat patch qualifies: `readme_rem.R` always passes `water`, so the README render
  would stop with an error that names nothing about water. Guard with `if (length(k))`.

## Claim table (new README section, alt text, canopy-caption addition)

| claim | source | verdict |
|---|---|---|
| "this 4 × 2.3 km view" | `window_m` [4000, 2300]; PNG is 1000×575 px at 4 m | holds |
| "The delta in the canopy figure is the right-hand edge of this view" | CHM window maps to REM pixels x 675-975, y 87-337 (of 1000×575); its east edge is 100 m short of the REM's, and the delta's land is at x 675-850 | holds loosely: the right quarter, not the edge itself |
| "Maxan Creek's floodplain (bottom centre)" / alt "at the bottom centre" | FWA Maxan Creek runs from the lake at px (885,141) via (649,277) and (633,384) to (325,575) | holds |
| "Crow Creek winds along a narrower valley floor (left)" | FWA Crow Creek runs from (0,432) via (160,338) and (335,291) to (523,32) | holds |
| "the Bulkley River runs along the top" | FWA Bulkley River runs from (506,0) to (742,80), then through the lake | holds (top centre-right) |
| alt "around the west end of Bulkley Lake" | FWA Bulkley Lake spans px x 777-1862, so it extends 3.4 km east of the window | holds |
| alt "a smaller lake on the left" | FWA Wiggins Lake, 12 ha, px x -67..92 | holds |
| alt "Bulkley Lake on the right ... light blue" | flat-water mask: two patches only, Wiggins Lake and Bulkley Lake | holds |
| "Curving old channels also cross the cleared field west of the delta" | visual; no canopy over the field in the CHM | plausible, not measured |
| "The colour is height above the nearest stream bed, from 0 to 3 m" | `relief_m` 3; but the bed is a TIN/IDW surface, and 4.5% of land is below it | partly false (finding 1) |
| alt "dark blue at the bed ... yellow at 3 m and above" | ramp clamps; negatives to -8.94 m are dark blue | partly false (finding 1) |
| "37% of the land here lies within 3 m of a stream bed" | `share_floor` = mean(0 ≤ r < 3) = 0.370004 | the number is right for its code but omits r < 0; 41.5% with them (finding 1) |
| "Only the window's rows were read, over HTTP, from the 638 MB file" | gdalinfo: Float32, `Block=13554x1` (one row per strip), uncompressed; `file:size` 637,566,318 | holds; each strip is full width, so about 125 MB is read |
| "its 1 m cells are averaged to 4 m" | `dem_cell_m` 1 = abs(tf[1]); `aggregate(dem, 4, mean)` | holds |
| "(Bulkley River, Crow Creek, Maxan Creek, Wiggins Creek and unnamed streams of Strahler order 2 and up)" | after filter: Bulkley 5-6, Crow 4, Maxan 5, Wiggins 2, 12 unnamed rows at order 2; no NA order | holds |
| "Every 10 m along each, the lowest ground within 15 m" | 9×9 square of 4 m cells | wider than stated (finding 3) |
| "open water ... (found as level ground over 1 ha or more), counts as bed at its own level" | `pc_readme_flat_water(min_area = 1e4)`; every 10th water cell added at DEM z | holds |
| "5,597 samples" | `nrow(bed)` | holds (reproduced) |
| "A triangulated surface through them is the bed under every cell" | 10.25% of cells take the IDW fallback | false for about 11% (finding 2) |
| "shading is the elevation model's own, relief exaggerated 4 times" | `shape = dem`, `exaggeration = 4` | holds |
| "model sits half a metre west and half a metre south ... not corrected" | accepted | not re-checked |
| canopy: "straight line ... on the slope to the south is a road (it is in BC's Digital Road Atlas)" | DRA straight segment at y ≈ 915 m matches the visible line | holds |
| canopy: "the curved lows down that slope are gullies" | a second, curving DRA road coincides with the most visible curved low | misleading (finding 4) |

No security issues. The code excerpt markers resolve: the fixed-string grep for `# --- shown on the
landing page: begin` does not match `# --- the valley floor, shown on ...`.
