# Review: #30 part 2 (valley-floor figure), round 2

Reviewed HEAD 5fdbb97: `diff2.patch`, the round 1 fix commit (`git show 5fdbb97`), `scripts/readme_rem.R`,
the valley-floor section of `scripts/readme_functions.R`, `pc_readme_relief()`, `pc_readme_relief_png()`, the
valley-floor tests, README.Rmd (setup chunk, canopy caption, valley-floor section), `maintaining.md`,
`data/readme_rem.json`, and `fig/maxan_rem.png`.

Method: I copied the tracked tree to scratch `r2.*` and ran a copy of `scripts/readme_rem.R` that also wrote
`dem`, `rem` and `water` (FLT8S) and the bed samples and streams. The copy reproduced `data/readme_rem.json`
exactly and `fig/maxan_rem.png` byte for byte (`cmp`). I rebuilt `pc_readme_rem()`'s internals from its own
deparsed body, checked that the result equals the published `rem`, and kept `base`, `over`, `l` and `from_far`.
"Nearest-sample REM" below is ground minus the z of the nearest bed sample (FNN). Pixel positions are
(col, row) of the 1000 x 575 map, from the top left. Tests: 29 run, 0 failed, 0 errors (copy).

## The mechanism

Round 1's defects 1 and 2 share one cause. The bed is a surface interpolated between streams that lie at
different levels (a TIN, or IDW beyond the hull). Where such a surface spans a tributary and a lower creek, it
departs from every real bed near the cell, and it can be off in either direction. The captions were written
from the intended method ("the nearest stream bed"), not measured from that surface.

The fix tests one symptom of that cause: the surface standing more than 2 m **above** the ground. It replaces
the surface there with a different estimate, and does not compare the result with the beds near the cell.
That leaves three places the mechanism still reaches: findings 1 and 2, and the 0 to 2 m ring inside
finding 1.

## Findings

- **[bug: published figure and caption]** scripts/readme_functions.R:465-468 (`over`, `b[over] <- l[over]`),
  README.Rmd:202, alt text at :196. **The replacement bed overshoots, and on flat floodplain it draws a
  straight-edged yellow band.**
  - The lowest sample within 1 km is, on a valley that falls, the sample about 1 km downstream. The sample
    used lies a median 986 m from the cell (max 1,042 m, from a 1-in-7 sample of the 2,968 replaced cells).
  - So the replaced cells read 5.3 to 16.4 m (median 7.8), drawn full yellow. Yet 94% of them are less than
    3 m above their nearest bed sample:

    | group | cells | drawn REM (median) | nearest-sample REM (median) | slope (median) |
    |---|---|---|---|---|
    | Crow Creek's north bank, cols 340-400, rows < 300 | 435 | 12.6 m | 2.2 m | 3.9° |
    | bottom edge, cols 400+, rows 540+ | 777 | 8.1 m | 1.2 m | 0.8° |
    | bottom left, cols < 340, rows 450+ | 1,728 | 6.6 m | 1.0 m | 1.4° |

    1,340 of the bottom-left cells sit under the scale bar's white box.
  - The bottom-edge wedge (cols 420-525, rows 560-575) is flat floodplain at the same height as the ground
    beside it: replaced cells 726.1-727.6 m (median 726.55), unreplaced neighbours median 727.09. Up column
    470, the ground and the drawn height are:

    | row | ground | drawn |
    |---|---|---|
    | 565 | 726.61 m | -1.65 m (bed 728.26) |
    | 570 | 726.63 m | +8.02 m (bed 718.61) |

    That is 20 m apart on level ground. The figure shows a straight-edged yellow sliver across the
    floodplain at the bottom edge, and the same staircase seam on Crow Creek's north bank (crops at scratch
    `r2.*/crop_bot.png` and `crop_crow.png`, with replaced cells in green).
  - **The 0 to 2 m ring.** The other side of the threshold keeps the old artefact. Unreplaced land within 4 m
    of a replaced cell reads a median of -1.73 m (89% below 0, so dark blue "at the bed"), while its
    nearest-sample REM is 1.6 m. The interpolation error is continuous, and the rule cuts it at its 2 m
    contour into dark blue on one side and yellow on the other.
  - **Claims this makes false:**
    - The How-it-was-made clause "as on a slope between a tributary high in its own valley and the creek below
      it" does not describe where the rule fired: 2,505 of the 2,968 cells are on ground with a median slope
      of 0.8-1.4°.
    - The alt text's "Hills and terraces are yellow" fails for the bottom-edge wedge.
    - "The colour is height above the nearest stream bed" is off by about 7 m there.
  - **Fix direction.** The README states "(0.5% of the window)" correctly, but not that those cells read 5 to
    16 m. Two options:
    - Bound the bed by the samples near the cell, for example clamp the TIN/IDW bed to [min, max] of the k
      nearest samples' z. This removes both signs of the error (it also handles finding 2).
    - Take the minimum over the few nearest samples in place of the lowest within 1 km.

- **[bug: published figure and alt text]** scripts/readme_functions.R:449-468, README.Rmd:196 and :200.
  **The same mechanism with the opposite sign is not reached: about 9 ha of flat ground at Wiggins Lake's
  level is drawn as 3 m and more above the bed.**
  - East of Wiggins Lake (cols 80-210, rows 140-215; scratch `r2.*/patch.png`), 5,564 land cells (8.9 ha) lie
    within 0.5 m of the lake's flattened level, 748.55 m. Their 7 x 7 range is about 0.08 m, so the ground is
    flat to a few centimetres.
  - Their nearest bed sample is a median 0.28 m below them, mostly the lake's own samples.
  - The TIN under them, though, runs down to the outlet stream's and Crow Creek's lower samples (741.6-742 m
    in the same box), so the bed beneath them is a median 745.42 m.
  - So they are drawn a median 3.43 m above the bed, and 61% are full yellow. That is the smooth, unshaded
    yellow patch south-east of the left-hand lake.
  - The `above` rule cannot reach this case: the bed is *below* the ground.
  - Across the window, 1.15% of land is drawn at 3 m or more while lying within 1 m of the lowest of its three
    nearest bed samples. This patch is most of it.
  - **Claims this makes false:**
    - The alt text's "Hills and terraces are yellow": a reader will take a lakeside flat for a terrace.
    - "coloured by height above the nearest stream bed": off by about 3 m here.
  - The How-it-was-made text names only the bed-above-ground failure, so this one is undisclosed. The
    clamp-to-nearby-samples fix above covers it.

No security issues. Other code checked and sound:

- `rast(ext, resolution = 40 m)` keeps the extent: 58 x 100 cells, y res 39.66.
- `resample(lowest, dem, "near")` leaves no NA.
- The `focal()` fallback exists because terra refuses `nrow(w) > 2 * nrow(x)` (reproduced).
- The empty-water guard works.
- The marker excerpts resolve.
- `maintaining.md` matches the render chunk (README.Rmd:79).

Not a finding: every `pc_readme_rem()` test grid is small enough to take the global-minimum fallback, so no
test exercises the `focal()` branch the published run uses. That branch measures correctly here: `l` equals
the lowest sample within 1,000 m in 58% of cells and is lower by at most 0.48 m in 26%, because the 40 m
cells reach past 1 km.

## Claim table (new section, alt text, How it was made, canopy-caption sentence)

| claim | source | verdict |
|---|---|---|
| "this 4 × 2.3 km view" | `window_m` [4000, 2300]; map 1000 × 575 px at 4 m | holds |
| "the right-hand quarter of this view" (the delta in the canopy figure) | CHM window falls on map cols 675-975 of 1000 | holds approximately (30% band ending 2.5% short of the edge) |
| "Maxan Creek's floodplain (bottom centre)", Crow Creek "(left)", Bulkley "along the top" | FWA geometry (round 1), unchanged | holds |
| alt: "around the west end of Bulkley Lake", "a smaller lake on the left", lakes light blue | water mask: Wiggins Lake and Bulkley Lake only | holds |
| "The colour is height above the nearest stream bed, from 0 to 3 m" / alt "coloured by height above the nearest stream bed" | `relief_m` 3; drawn REM vs nearest-sample REM | false over the replaced cells (about 7 m too high, finding 1), the lakeside flat (about 3 m too high, finding 2) and the 0-2 m ring; otherwise a stated heuristic |
| alt: "dark blue at or just below the bed ... yellow at 3 m and above" | ramp clamps; land min -1.9999 | holds as a description of the ramp |
| alt: "Hills and terraces are yellow" | finding 1 (flat floodplain wedge, slope 0.8°) and finding 2 (8.9 ha lakeside flat) | false in two places |
| "41% of the land here lies less than 3 m above a stream bed" | `share_floor` 0.413 = mean(r < 3) over land; under nearest-sample REM 42.1% | holds; robust to the bed definition (spread 0.8 points) |
| "Only the window's rows were read, over HTTP, from the 638 MB file" | `bytes_file` 637,566,318; -projwin read (round 1: strip-organised, full-width rows) | holds |
| "its 1 m cells are averaged to 4 m" | `dem_cell_m` 1, `aggregate(dem, 4, mean)` | holds |
| streams list "and unnamed streams of Strahler order 2 and up" | `streams`, `min_order` 2; filter `STREAM_ORDER >= 2` | holds |
| "Every 10 m along each, the lowest ground within 15 m" | `st_line_sample(density = 1/10)`; focalMat(15, circle) on 4 m = 7 × 7 minus corners, cell centres ≤ 14.4 m from the cell holding the point | holds to within a cell (≤ about 17 m from the point) |
| "open water ... (found as level ground over 1 ha or more), counts as bed at its own level" | `pc_readme_flat_water(min_area = 1e4)`; every 10th water cell at DEM z | holds |
| "5,597 samples" | `nrow(bed)`, reproduced | holds |
| "A triangulated surface ... the bed under 89% of the window" | `share_bed_tin` 0.893 (TIN not NA and not replaced; includes lidR's own knnidw band about 0.45% beyond the hull) | holds at rounding |
| "outside the samples, at its corners (10%), ... inverse-distance mean of the three nearest samples" | `share_bed_nearest` 0.102; `interpIDW(maxPoints = 3, power = 1)` on 40 m, bilinear back | holds |
| "Where either stands more than 2 m above the ground ... the bed is the lowest sample within 1 km instead (0.5% of the window)" | `above_m` 2, `near_m` 1000, `share_bed_lowest` 0.005; sample used up to 1,042 m away | number holds; "within 1 km" holds to about 4% |
| "as on a slope between a tributary high in its own valley and the creek below it" | slope under replaced cells: median 0.8° (bottom), 1.4° (bottom left), 3.9° (Crow) | does not describe where the rule fires (finding 1) |
| "4.9% of the land lies up to 2 m below it and is drawn with the bed" | `share_below` 0.049, `min_m` -2 (-1.99988) | holds |
| "shading is the elevation model's own, relief exaggerated 4 times" | `shape = dem`, `exaggeration` 4 | holds |
| half-metre offset not corrected | accepted | not re-checked |
| canopy: "Two rough roads in BC's Digital Road Atlas cross the forest on the slope to the south: the straight line, and a curve along the forest's upper edge" | DRA query 2026-10-17 in the CHM window: 3 segments, all `rough`; two meet at (646, 909) m, one continues south-east out of the window | holds |
| canopy: "The curved lows running down that slope are gullies" | visual; FWA has no order-1 line there (only order 2 and Maxan) | interpretation, not measured; not contradicted |
