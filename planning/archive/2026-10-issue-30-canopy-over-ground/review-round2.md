# Code-check round 2 (#30)

Reviewed: `git diff origin/main...HEAD` over scripts/readme_functions.R, scripts/readme_chm.R,
scripts/dem_alignment_probe.R, tests/readme_functions_test.R, README.Rmd (setup chunk, CHM
section), research/dem_alignment.md, research/README.md, scripts/DESCRIPTION.

## Round 1 fixes, checked

- research/README.md direction: correct. The shift table needs the DEM moved +0.5 E, +0.5 N to
  match, so GDAL reads it 0.5 m west and 0.5 m south. The fit's sign agrees: if DEM(x) = T(x + 0.5),
  then TIN - DEM ≈ -0.5 dz/dx; the focal kernels' signs (row 1 = north) make dzdy positive northward.
- pc_readme_relief NA-ground blanking before the water fill: correct, and the new test covers both
  water with no TIN under it and land with no ground.
- The probe now prints the unshifted median, the fit, the lake level and both GDAL origins. A copy
  run in a temp dir (data/readme_laz read-only, 2026-10-17) reproduced every printed number the
  note quotes.

## Findings

- **[fragile: published statement stronger than its evidence]** research/dem_alignment.md:29 and :37.
  "Moved 0.5 m east and 0.5 m north ..., the DEM is the TIN to the millimetre" and "Beyond the
  offset, the DEM's only departure from the TIN is the water" are stated for every cell. The probe
  prints only the median and p95 (both 0.000), so up to 5% of land cells are not covered by what it
  prints. Measured with a copy of the probe plus a few extra lines, at the +0.5, +0.5 shift:
  - land (TIN > 712.9 m): 1,574 of 761,571 cells (0.21%) differ by more than 1 mm, with a maximum of
    1.10 m; p99 0.0000, p99.9 0.010 m.
  - cells at or below 712.9 m that are not the flat 712.54 m lake: 27,439 cells, of which 20.6% differ
    by more than 1 mm, with a maximum of 0.45 m. These are excluded from the land comparison and are
    not the flattened lake either, so "only departure is the water" does not cover them. They may be
    shore or water-edge cells, but the probe does not show that.
  The conclusion (the half-cell offset) stands, since 99.8% of land cells agree exactly. What is
  wrong is the absolute wording. Either say "99.8% of land cells to the millimetre (p95 0.000 m)"
  and have the probe print that share and the max, or qualify "only". As written, a sentence in the
  research note is not printed by its Produced-by script and is false for a measurable set of cells.

- **[fragile: published statement]** research/dem_alignment.md:9-10. "over the 1.26 × 1.06 km window
  of the landing page's canopy figure". The README calls the figure's window 1.2 × 1 km plus a 30 m
  margin (`chm$window_m`). 1.26 × 1.06 km is the window with its margin (the probe's `BOX`), and the
  cells actually compared are 3 m inside that. A reader putting the two pages side by side sees two
  sizes for one window. Say "the canopy figure's 1.2 × 1.0 km window and its 30 m margin".

Nothing else found. Checked and clean:
- grid identity of `pc_readme_ground`/`pc_readme_chm` (same `b`, same crop; `compareGeom` guards it);
- the hillshade normalisation (terra `shade()` gives sin(alt) on flat ground) and the 315° sun matching "lit from the northwest";
- ramp indexing (1..256, NA passes through);
- the PNG's pixel/user-coordinate mapping and the scale bar at `scale = FIG_CELL` after a 2x `aggregate` of 2400x2000 cells, which divides exactly;
- `as.array` orientation for `rasterImage`;
- the legend ticks against the ramps;
- the setup chunk's `stopifnot` covers every new key the prose reads (`TOP` is not quoted);
- marker uniqueness for both `pc_readme_lines` spans;
- `png` in Suggests;
- stac_elevation_bc#69 and #30 resolve to this work.

Verdict: two wording defects in research/dem_alignment.md, and no code bugs.
