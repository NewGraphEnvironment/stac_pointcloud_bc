# Code-check part 2, round 3 (#30): valley-floor figure

Reviewer: subagent, 2026-10-17. HEAD 23ae327. All measurements on a `git archive HEAD` copy
(scratchpad `r34zUz/`), `scripts/readme_rem.R` run unchanged except for a return value added at the
end of `main()`; the JSON it wrote matched `data/readme_rem.json` on every key compared
(shares, `bed_samples`, `min_m`). Figure coordinates below are map pixels of `fig/maxan_rem.png`
from its top-left corner (775 x 575 px, 4 m per px). Repo tree untouched (`git status` clean).
Valley-floor tests: `tests/readme_functions_test.R` 30 tests, 0 failed.

## Findings

- **[bug: published statement false]** README.Rmd:202 (README.md:239, index.html) — "Only the
  window's rows were read, over HTTP, from the 638 MB file". Since round 2's fix the script reads
  the window **plus 500 m on every side** (`read` in scripts/readme_rem.R:70-75; measured: `read`
  = window +/- 500 m on all four sides, nothing clipped by the tile's bbox, 4.1 x 3.3 km, 1.90x the
  window's area). The later sentence "Both are built from 500 m beyond the window too" does not
  repair it, because the first sentence says *only* the window was read. Something like "Only the
  window's rows and 500 m around it were read" fixes it. This is the doc-drift form of the
  fix-inside-a-fix pattern: the buffer changed the read, and the sentence describing the read
  stayed as it was.

- **[fragile: claim wider than method]** README.Rmd:202 — "Where either stands more than 1 m over
  the highest sample within 150 m ... it is held there (6.3% of the window)". `pc_readme_rem()`
  (scripts/readme_functions.R:463-476) takes the maximum per 40 m block, then the maximum over a
  7 x 7 block circle, then interpolates that bilinearly to 4 m. So the reach is not 150 m: a
  sample about 120 m away can be left out, and one about 200 m away can be counted. Measured
  against an exact 150 m maximum (samples rasterised at 4 m, focal circle r = 150 m):
  - the cap differs from the exact one by -12.2 to +14.0 m (IQR -0.02 to +0.04 m);
  - held status disagrees on 1.4% of window cells (6.3% implemented, 5.6% exact);
  - 3,886 window cells (0.9%) keep a bed more than 1.1 m over the highest sample within 150 m,
    up to 8.2 m over (on hills, drawn yellow anyway). Of those, 1,256 are land drawn below 3 m,
    where the excess has a median of 0.23 m, a 90th percentile of 0.58 m and a maximum of 1.34 m.
  On the drawn floor the visible effect is small, but the sentence states an exact rule that the
  code only approximates. Either word it as approximate ("about 150 m"), or say "measured on 40 m
  blocks".

No other findings rise to a bug. The mechanism review and the measurements are below. The residual
errors in the bed are real but sit inside the accepted "the bed rule is a heuristic stated in the
caption with its shares". They are recorded here so the next round does not re-derive them.

## 1. The mechanism, and where it still reaches

**Mechanism:** the bed is a surface interpolated in plan distance (TIN, or IDW beyond its hull)
between samples from streams at different heights. It cannot see the terrain between them, so a
cell's bed is set by whichever streams triangulate over it, including a stream up a hillside or
across a ridge. Each fix so far has been a one-sided, distance-based clamp on that surface:
round 1's "lowest within 1 km" and round 2's "highest within 150 m + 1". A clamp of that kind
moves the error to wherever its distance assumption fails. The current cap:

1. **Clamps only a bed that is too high.** A bed pulled *down* by a lower stream is untouched.
   Measured in the trimmed window: the small valley at px x 0-100, y 100-160, west of Wiggins
   Creek. Its stream's samples are at 743.5 m. On its north slope at px (40,120) the ground is
   745.71 and the bed is 740.9, 2.6 m below that stream's own samples 56 m away, so the cell is
   drawn at 4.8 m. In the window, 707 land cells are drawn at 3 m or more while lying less than
   1.5 m above a sample within 100 m (0.17% of land). Most are on that slope (x 0-100, y 100-150)
   and around the Crow and Wiggins confluence (x 125-200, y 125-200). This is the Wiggins Lake
   error from round 2 at a smaller scale; the trim removed the lake, not the mechanism.
2. **Is blind when a high sample lies within 150 m.** A hillside stream inside the radius raises
   the cap with it. Measured at the Crow and Wiggins confluence, px (162,190): ground 720.41, bed
   723.01, samples within 50 m 719.79-720.30, but the highest within 150 m is 733.47 (Wiggins
   Creek on the slope), so the cap is 734.5 and nothing is held. That cell **is the published
   `min_m` = -2.6**. The ground is 0.1-0.6 m *above* the nearest stream's samples and is drawn as
   2.6 m below the bed. Across the window: of the land within 50 m of a sample, 5.4% (4,099
   cells) have a bed more than 1 m above their nearest sample, and 1.2% (887) more than 2 m.
3. **Is absent on 46% of the window** (204,058 of 445,625 cells have no sample within the block
   circle, so the cap is NA). There the bed is the raw TIN, as in patches 34 and 42 below, which
   are 276-380 m from any sample. The cap's edge follows 40 m blocks, which is the seam source in
   2(a).
4. The cap's own radius is approximate (finding 2 above).

## 2. Measurements

### (a) Seams

`seam_check.R` (rem jumps > 1.5 m where ground changes < 0.3 m, not water, min < 3): **1 pair**,
not 3. Same script, `return` line added, run from the copy's root; JSON identical to the
committed one.

A wider probe: bed steps between 4 m neighbours on cells drawn below 3 m, not water:

| step | pairs |
|---|---|
| > 0.3 m | 1,635 |
| > 0.5 m | 342 |
| > 1.0 m | 50 |

Of the 342 steps over 0.5 m:

- 139 are on the cap's edge (held on one side, cap NA on the other), up to 1.48 m, on a 40 m
  staircase. The two clusters with the most steps, at px (350-365, 505-520) and (0-12, 550-575),
  are in ground drawn dark blue on both sides (rem < 0), and are not visible at 1:1 or zoomed.
- 190 are TIN to TIN, on steep stream facets: the Bulkley and Crow junction at px x 285-320,
  y 0-35; Crow Creek near Wiggins at x 150-175, y 175-200; and a diagonal at x 215-240, y 440-447
  in Maxan's floodplain. None reads as a seam in the figure.

### (b) Land more than 1 m below the bed

There are 48 patches (8-connected), 1,646 cells, 2.63 ha in all. 21,810 land cells are below 0,
1,646 below -1 and 19 below -2. Patches of 15 cells or more:

| patch | px (x,y) | area m² | min rem | ground | bed at deepest | samples ≤50 m | ≤150 m | verdict |
|---|---|---|---|---|---|---|---|---|
| 43 | 358,522 | 10,112 | -2.04 | 722.93 | 724.97 | none | none | real low: a backswamp below the nearest bed (724.44 at 145 m). It is 1.1 m above Maxan's lowest sample within 300 m. |
| 29 | 375,480 | 2,464 | -1.34 | 722.11 | 723.45 | none | none | **artifact**: ground is 0.27 m above the nearest sample (721.84 at 136 m); bed is 1.6 m above it |
| 11 | 166,86 | 2,384 | -2.20 | 714.50 | 716.70 | none | 712.95-718.51 | mixed: bed is pulled up by a high sample (718.5) within 150 m |
| 48 | 63,544 | 2,304 | -1.83 | 728.34 | 730.17 | none | 727.86-730.05 | artifact-leaning: bed is at the top of the 150 m range |
| 34 | 50,478 | 2,192 | -1.56 | 728.84 | 730.40 | none | none (nearest 276 m, 727.15) | **artifact**: raw TIN, cap NA; ground is 1.7 m above the nearest sample |
| 1 | 115,6 | 1,472 | -2.15 | 711.13 | 713.29 | 711.15-711.60 | 711.10-712.13 | **artifact**: bed is 1.16 m over the exact 150 m cap (finding 2) |
| 42 | 4,494 | 1,168 | -1.56 | 729.58 | 731.14 | none | none (nearest 358 m, 728.86) | **artifact**: raw TIN, cap NA; ground is 0.7 m above the nearest sample |
| 17 | 161,191 | 848 | -2.60 | 720.41 | 723.01 | 719.79-720.30 | 718.97-733.47 | **artifact**: mechanism 2 above; this is the published `min_m` |
| 25 | 130,251 | 560 | -1.68 | 723.56 | 725.23 | none | 721.85-724.34 | artifact-leaning: bed is 0.9 m above every sample within 150 m |
| 20 | 156,204 | 336 | -1.63 | 721.18 | 722.81 | none | 719.38-721.85 | artifact-leaning: same shape as 25 |
| 18 | 288,192 | 288 | -1.15 | 716.65 | 717.80 | none | none (nearest 265 m, 717.65) | real low: ground is below the nearest bed |
| 5 / 3 | 301,6 / 312,1 | 272 / 240 | -1.55 / -1.65 | 710.4 / 712.8 | 712.0 / 714.5 | 710.28-713.31 / none | 710.1-721.6 / 710.1-723.2 | artifact-leaning: steep facets at the Bulkley and Crow junction, top edge |

About 1.0 ha of the 2.6 ha is a real low (43, 18). The rest is a bed artifact. All of it is drawn
dark blue, "with the bed", as the caption says.

### (c) Flat floor drawn at 3 m or more, and hillside drawn under 1 m

| test | cells | share of land |
|---|---|---|
| land drawn ≥ 3 m but < 1.5 m above a sample within 100 m | 707 | 0.17% |
| the same, slope < 3°, < 1 m above a sample within 150 m | 485 | 0.12% |
| slope > 15°, drawn < 1 m, > 30 m from any sample | 533 | 0.13% |
| drawn < 1 m but > 3 m above the nearest sample, > 30 m from any sample | 647 | 0.16% |

The clusters with the most cells:

- Floor drawn at 3 m or more: the north slope of the small west valley (x 0-100, y 100-150; §1,
  item 1) and around the confluence (x 125-200, y 125-200).
- Hillside drawn under 1 m: Crow Creek's banks near Wiggins (x 150-175, y 75-100 and 175-200),
  and the steep east edge of the hill at x 250-275, y 150-250.

There is no large field of flat floodplain drawn yellow, and no large hillside drawn dark. Each
is under 0.2% of land.

## 3. Claims

The quantified and directional claims in the valley-floor section (README.Rmd:194-202, as rendered
at README.md:237-239), its alt text, and the canopy caption's new sentences (README.Rmd:168):

| claim | source | verdict |
|---|---|---|
| "the right-hand part of this 3.1 × 2.3 km view" | `window_m` [3100, 2300]. The CHM window (readme_chm.R: W700 E500 S600 N400 from the same mouth) is at px x 450-750, y 87-337 | true |
| Maxan Creek's floodplain is at the bottom left, with meander scars and cut-off loops | FWA Maxan line enters at px (110,575) and meanders to x 400; oxbows are visible at x 150-300, y 430-470 | true |
| Crow Creek winds along a narrower valley floor (left) | FWA Crow line runs px (0,345) to (298,32) along the narrow valley between the two hill masses | true |
| the Bulkley River runs along the top | FWA Bulkley line runs px x 281-775, y 0-80 (then through the lake) | true |
| curving old channels cross the cleared field west of the delta | the figure at x 300-560, y 80-280; the canopy figure shows no canopy on that field | true |
| one scale shows a valley floor that rises upstream | ground about 711-713 m at the delta and 728-730 m on Maxan's floodplain at the bottom left | true |
| 48% of the land is less than 3 m above a stream bed | `share_floor` 0.482 = mean(r < RELIEF) over land, readme_rem.R:144 | true, of the constructed bed |
| "Only the window's rows were read, over HTTP, from the 638 MB file" | `read` = window ± 500 m (readme_rem.R:70-75); `bytes_file` 637,566,318 | **false**: finding 1 |
| 1 m cells averaged to 4 m | `dem_cell_m` 1, `cell_m` 4, `aggregate(CELL, mean)` | true |
| the stream names, and unnamed streams of order 2 and up | `streams` after `STREAM_ORDER >= MIN_ORDER`; all four named streams are in the window | true |
| every 10 m, the lowest ground within 15 m | `st_line_sample(density = 1/10)`, focal min over a 15 m circle on the 4 m DEM | true (the lowest 4 m mean cell) |
| open water is level ground over 1 ha or more, counted as bed at its own level | `pc_readme_flat_water(min_area = 1e4)`; every 10th water cell is added | true |
| 8,097 samples | `bed_samples` | true |
| TIN under 93% of the window | `share_bed_tin` 0.927 (src == 1, after held cells are removed) | true |
| IDW of the three nearest "at its edges (1%)" | `share_bed_nearest` 0.010. Measured: all 4,570 such cells are in the NE corner, px x 632-775, y 0-62 | true |
| built from 500 m beyond the window | `read` minus `box` = 500 m on all four sides. The aggregated read has 464 NA cells, in its SW buffer corner only | true |
| held at 1 m over the highest sample within 150 m (6.3% of the window) | `share_bed_held` 0.063 is correct for the code, but the code's radius is approximate | **imprecise**: finding 2 |
| "as where a stream on the high ground beyond a valley wall pulls it up" | the cap does catch these cells, but misses the same case when the high stream is within 150 m (§1, item 2) | true as an example |
| 5.3% of the land lies up to 2.6 m below the bed and is drawn with the bed | `share_below` 0.053, `min_m` -2.6 over land; ramp clamps below 0 | true. The -2.6 itself is an artifact cell (patch 17) |
| shading is the DEM's own, exaggerated 4 times | `shape = dem`, `exaggeration` 4 | true |
| alt text: "dark blue at or just below the bed" | the ramp's bottom colour covers rem down to -2.6 | loose; covered by the caption |
| alt text: hills and terraces are yellow; lake is light blue on the right | the figure | true |
| canopy: "Two rough roads in BC's Digital Road Atlas cross the forest on the slope to the south: the straight line, and a curve along the forest's upper edge" | DRA (`bb060417-...`) over the CHM window. Three segments, all `ROAD_SURFACE` rough: a straight one at y 909-920 m from the top, x 0-646 (straightness 1.000); a curved one from x 0 to (646,909) along the forest's upper edge (1.015); and a stub from their junction to the south edge. Overlaid on fig/maxan_chm.png, both lines sit on the visible tracks | true |
| canopy: "The curved lows running down that slope are gullies" | dark, roughly N-S curved lows in the south forest band (CHM figure px x 100-450, y 830-1000) | plausible, not measured further |
