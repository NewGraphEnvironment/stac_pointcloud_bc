# Code-check round 3 (#19): claims about the data

Reviewed `git diff d1e4b2da...HEAD` (README.Rmd, scripts/readme_chm.R, scripts/readme_functions.R,
tests/readme_functions_test.R, scripts/DESCRIPTION, .gitignore, data/readme_chm.json), against
fig/maxan_chm.png, the API's two items, stac_dem_bc#47, floodplains#121 and planning/active/findings.md.

## The mechanism

Round 1's finding came from **prose that describes the data or the figure from the author's reading
of one run, typed into the page, with nothing in data/readme_chm.json to compute it from and nothing
in scripts/readme_chm.R that refuses a run where it stops being true.** The numbers in the paragraph
are all derived; the sentences that interpret them ("no copc", "covering it", "light blue is the
lake", "trees up to about 40 m") are not. A second face of the same thing: the script's guards refuse
only *too much* (more than 2 items, more than 600 MB, a CRS mismatch, a copc asset). Nothing refuses
*too little*, so a run that would make a typed sentence false passes.

## Findings

- **[bug] README.Rmd:141 (fig.alt) and :144 (prose, "Open ground reads 0 m. Light blue is ... the
  lake")** — most of the lake reads 0 m, not light blue. findings.md (the two tiles, measured) says
  so itself: lake-surface returns are class 1, flat at 712.5–712.8 m, "so the lake reads 0 m where
  they are dense enough and NA where gaps exceed 2 m". Counted on fig/maxan_chm.png by colour: in the
  east third of the plot (x 800–1195 px), 49% (north half) and 72% (south half) of pixels are the 0 m
  colour, the same colour as the NW meadow, and only 47% / 25% are light blue. So the alt text tells a
  screen-reader user "the lake on the east in light blue", and the prose pairs "Open ground reads 0 m"
  with "Light blue is ... the lake", while the figure shows most of the lake as open ground. The same
  lake cells are in the denominator of "Of the cells with a height, 25% stand at least 2 m and 8% at
  least 10 m", which a reader of the preceding sentence takes to be land; by the pixel shares above,
  lake surface is very roughly a fifth to a quarter of the cells with a height, so the share of
  *land* at ≥ 2 m is materially higher than 25%. Unchecked text, and the json has nothing (no
  water/lake cell count) to derive it from. Fix in the words (lake water with dense returns reads 0 m
  too; the light blue is the sparse part of it), or mask water before the shares if the shares are
  meant to be of land.

- **[fragile] scripts/readme_chm.R:63–72, README.Rmd:144 ("returned the N items covering it")** —
  nothing checks that the found items cover the window. "Covering it" is typed; the guards cap the
  count from above only. Today it is true (read box x 685935–687195, y 6029135–6030195 in EPSG:3156
  lies inside the union of the two items' `proj:bbox`, 685052–688355 by 6028990–6030446, checked
  against the API 2026-10-11). On a later `update_query = TRUE` render where one tile is no longer
  served under the pinned delivery (an `EXCLUDE` entry, an id change), the script runs on one tile,
  half the window comes out NA, the plot paints it light blue, and the page says "the 1 items covering
  it" and that light blue is the lake and the channel. A union-covers-read_box assertion on the items'
  `proj:bbox` (or geometry) before download closes it; `MAX_ITEMS` alone cannot.

## Every factual claim, and what stands behind it

C = computed from data/readme_chm.json at render; G = guarded by readme_chm.R (a run where it is false
stops); U = unchecked text. "Later render" = could it become false on an `update_query = TRUE` render
with the code unchanged.

### README.Rmd, the CHM paragraph (line 144)

| claim | basis | later render |
|---|---|---|
| "The Maxan Creek delta, where the creek enters Bulkley Lake" | U (MOUTH_LON/LAT constants) | no; constants |
| window "1.2 × 1 km", "30 m margin" | C (window_m, margin_m) | no |
| "One STAC search ... returned" | U; the script makes two (the point search at the mouth for the CRS, then the window) | wording only; the code shown below it has both |
| "the 2 items covering it" — count | C | no |
| "covering it" | U | **yes**, finding 2 |
| "both from the 093/093l/2019 delivery" / else-branch "from more than one delivery" | C (items_found vs items; items ⊆ items_found by the filter, so equal length means one delivery) | no |
| "None of them has a copc asset" | G (line 76, round 1) | no |
| "each laz was downloaded whole, once" | G in effect (pc_readme_laz_get, size-checked; a cached file is reused) | no |
| "532 MB holding 107.8 million points" | C (sum of `file:size`, `pc:count`; the size is also G against the download) | no |
| "23.4 million fall in the window" | C (points_window; counts after `-drop_withheld`, so it excludes withheld points while points_files includes them; 0 withheld in these tiles per findings.md) | no for these files |
| "33% ground (class 2)", "67% class 1" | C | no |
| "which is where LidarBC leaves most of its vegetation" | U, sourced (research/laz_classes.md, CLAUDE.md) | no; collection-level fact |
| "built from every return but noise and withheld points, nothing chosen by vegetation class" | U but matches code (NOISE_CLASSES, -drop_withheld, Withheld_flag filter); tested | no |
| "heights above a triangulated surface of the ground returns" | U, matches normalize_height(tin()) (classes 2 and 9; no class 9 here). 68,755 lake points fell back to nearest neighbour (findings.md) | no |
| "first returns are rasterised pit-free at 0.5 m" | cell C; "first returns" U, confirmed in lidR 4.3.3 source (`ReturnNumber == 1L`) | no |
| "Open ground reads 0 m" | U, tested on synthetic data; true but incomplete | finding 1 |
| "Light blue is ... the lake and the creek's channel, where water returned few points" | U; no NA-is-water check | finding 1 now; finding 2 on a later render |
| "25% ≥ 2 m", "8% ≥ 10 m", "tallest 1% exceed 25.5 m", "max 39.5 m" | C | no (denominator: finding 1) |
| "LidarBC publishes its own CHMs for 2023 and 2024 only" | U, from stac_dem_bc#47 (bucket walk 2026-08-28: 264 tifs, all 2023–24) | not by the render; it goes stale when LidarBC publishes another year, and nothing re-checks it. Stated undated |
| "DSM specifications differ between deliveries" | U, from stac_dem_bc#47 (rtj#229 pilot, 082f020) | no |
| "historic channels and the forest lost since 2017" | U, matches floodplains#121 (transition 2017–2023) | no |

### README.Rmd, fig.alt (line 141)

| claim | basis | later render |
|---|---|---|
| "open ground and meadow at 0 m" | U; NW is 77% class 2 (findings.md) | no |
| "the creek channel meandering through it" | U; visible | no |
| "trees up to about 40 m tall on the delta" | U; json max 39.5 and the 35–40 m stands sit on the delta in the figure. Not derived from chm$height_m$max although a chunk option can take an R expression | only if code or params change |
| "a forested slope along the south edge" | U; visible | no |
| "the lake on the east in light blue" | U | **false now**, finding 1 |

### README.Rmd, build notes (lines 37–40, 296)

"~0.5 GB" / "about 0.5 GB" (also .gitignore): U, but bounded by MAX_BYTES (600 MB, G), so it cannot
drift far. "later runs reuse it": G by pc_readme_laz_get. Both fine.

### scripts/readme_chm.R comments

| line | claim | basis |
|---|---|---|
| 3–5 | "these have no copc"; "every return but noise" | G (copc); withheld also dropped, consistent |
| 15–16 | the BC Geographical Names point for the creek, not the FWA stem end | U; not re-checked here |
| 19–20 | "only 2019 covers this reach" | U; consistent today (all items_found are 2019; floodplains#121: 093l has 2016, 2018, 2019, only 2019 reaches here). Goes stale harmlessly: the prose's else branch handles a second delivery |
| 29 | "Refused before anything is downloaded" | true: the checks precede pc_readme_laz_get |
| 53 | "every point read has to come from a found item" | true, but does not imply coverage (finding 2) |
| 74–75 | copc refusal | G |
| 82–83 | LASlib reads only the window plus margin; pitfree needs the return number | true (`-keep_xy`; lidR source) |
| 92 | "NA cells (no returns: open water)" | U; same as finding 1/2 |
| 105 | sizes and counts are the published `file:size` and `pc:count` | true |

### scripts/readme_functions.R comments (pc_readme_chm and helpers)

| claim | basis |
|---|---|
| NOISE_CLASSES 7, 18; vegetation mostly class 1 | sourced |
| lidR takes classes 2 and 9 as ground | true (findings.md, lidR default `use_class`) |
| ground returns stay in at 0, so open ground reads 0 | true, tested (first-return ground) |
| max_edge drops long triangles so a gap stays NA | true, tested |
| rasterize_canopy refuses a point outside its grid; edge cells come out NA | measured (findings.md, Errors Encountered) |
| "about 0.5 MB/s (2026-10-12)", "0.6 GB takes 20 minutes" | measured (241 MB / 9 min, 291 MB / 7 min); date is UTC, consistent with the file mtimes |

## Checked and not a finding

- withr and data.table are used by the tests but not declared in scripts/DESCRIPTION; both arrive
  transitively (testthat imports withr, lidR imports data.table), so the documented install runs the
  tests.
- The else branch's "None of them has a copc asset" refers to the used items, which is what the guard
  checks.
