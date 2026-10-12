# Code-check round 4 (#19): the round-3 fixes (commit 7674fd7) first

Reviewed `git diff main...HEAD` (README.Rmd, scripts/readme_chm.R, scripts/readme_functions.R,
tests/readme_functions_test.R, scripts/DESCRIPTION, .gitignore, data/readme_chm.json) against
fig/maxan_chm.png, the rendered README.md / index.html and the cached tiles in data/readme_laz/.
Probes ran in a scratchpad copy; nothing in the repo was edited except this file.

## Findings

- **[bug] README.Rmd:144 ("where no ground return lies within `r chm$ground_gap_m` m"), with the
  same claim at scripts/readme_functions.R:272 ("within about `ground_gap` m") and
  scripts/readme_chm.R:29 ("no ground return this near")**. The focal window is about
  `ground_gap` m **wide**, not about `ground_gap` m in **radius**.
  `w <- 2L * ceiling(ground_gap / (2 * res)) + 1L` is 11 cells at res 0.5, a 5.5 m square centred
  on the cell, so it reaches only about 2.5–2.75 m each way. Measured on a 0.5 m grid with
  `ground_gap = 5`: the farthest cell centres the window counts are 2.65 m from a single ground
  return in x and in y, and a cell whose only ground return is 3 m east has `near = 0` and is
  masked. The test fixes the narrow reach too. In "water ... is NA rather than 0 m"
  (tests/readme_functions_test.R:118), the nearest ground to (13.5, 10.5) is 3.6 m away, at
  y = 14.125. Under the documented rule ("no ground within 5 m") that cell would keep its 0 m, but
  the test expects NA, and it passes only because the window at res 1 (w = 7) stops at y = 14.
  So the page tells readers that a cell is light blue when it has no ground within 5 m, while the
  code masks any cell with no ground within about 2.5 m. That is the round-3 mechanism again: the
  number comes from the json (`ground_gap_m`), but the sentence around it says something the code
  does not do. There are two fixes, and they need opposite test changes. One fixes the words:
  "no ground return in the 5 m square around it", or within about `ground_gap_m / 2` m. The other
  fixes the code to match the words, `w <- 2L * ceiling(ground_gap / res) + 1L`, and then needs a
  test cell with ground between gap/2 and gap away that must stay 0. The figure and the json
  shares would then change slightly, so the data needs a re-run. The current choice is safe on
  land (next section), so fixing the words is the cheaper option.

## The round-3 fixes, checked

- **Focal edges.** `n` comes from `tabulate()` and has no NA, and `focal(na.rm = TRUE)` sums
  whatever part of the window lies inside the grid. So edge cells are counted over a truncated
  window, not set to NA. The grid is `b` (the box plus 2 cells), and the ground returns are
  filtered to `b` before tabulating, which means the 30 m read margin does not feed the mask. A
  land cell within about 1.75 m of the window edge sees a truncated window. In principle it could
  be masked if its only nearby ground lies just outside `b`. On real data it did not happen (next
  point). Not a finding.
- **Can the mask remove land under dense canopy?** I tested this on real data. I read the
  south-west strip of the window (700 × 200 m, the forested slope, 8.26 M returns, with the
  window's west and south edges) from the cached tiles with `-keep_xy` plus the 30 m margin. Then
  I ran `pc_readme_chm()` with `ground_gap = 5` and with `ground_gap = 60` (effectively no
  mask). Of 560,000 cells, the 5 m mask set **0** to NA that had a height, so none under canopy
  and none at the two edges. The south slope has ground returns within 2.5 m everywhere at this
  density.
- **cellFromXY/tabulate against the grid.** `grid` is the same template passed to
  `rasterize_canopy()`, and `terra::mask()` would error on a geometry mismatch. The real run
  completed, and the json has 4,800,000 cells = 2400 × 2000, so the grid matches. The points are
  filtered strictly inside `b` (`X > b[1] & X < b[3]`), so `cellFromXY` returns no NA there and
  `tabulate(nbins = ncell)` lines up cell for cell.
- **The coverage guard (readme_chm.R:76–81).** `st_union` merges touching or overlapping
  rectangles into one polygon, so `st_covers` behaves as intended. A sliver gap between two
  bboxes would make the union a MULTIPOLYGON and refuse the run, which fails safe. The two tiles'
  header boxes are x 685052.5–686731.9 and 686675.3–688355.2, which overlap by 57 m. That is
  because BCGS tiles are lat/lon cells, skewed by about 2.4° of grid convergence in UTM 9 here.
  As a result, `proj:bbox` overstates a tile's real footprint by a wedge up to about 60 m wide,
  and a missing neighbour could go undetected only inside that wedge. A missing tile here would
  open a hole hundreds of metres wide, which the guard catches. Not a finding: the catalogue has
  no finer footprint to test against.
- **The alt text and the water share** are computed from `chm$height_m$max` and
  `chm$cells_na / chm$cells`. README.md and index.html both carry 41%, 37%, 12%, 27.8 m and
  39.5 m, matching data/readme_chm.json. In the figure, the lake is now entirely light blue,
  so "the lake on the east in light blue" is true.

## Checked and not a finding

- "The lake's surface returns are class 1 and level with the ground at its shore": not checked
  by the render, but matches findings.md (class 1, 712.5–712.8 m, no class 9). It explains a
  method; it is not a figure that can drift.
- "Of the cells on land": the denominator is the non-NA cells. These include lake cells within
  about 2.5 m of shore and exclude any land gap wider than `max_edge`. Both are small at this
  density. The south strip had 0 NA cells.
- Class 9 would be ground to `normalize_height()` and not to the mask, so it would also be masked,
  which is correct for water. These tiles have no class 9.
- `.gitignore` covers `data/readme_laz/`, and with it any leftover `.part` file.
