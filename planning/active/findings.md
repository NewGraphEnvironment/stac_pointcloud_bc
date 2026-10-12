# Findings — README: a canopy height model from the point clouds (Maxan Creek delta) (#19)

## Issue context

## Problem

The README demonstrates the collection with a bare-earth DEM (lower Kanaka Creek, ground returns from a
COPC window). Ground is half of what a point cloud gives. The other half, the height of what stands on
the ground, is what the DEM and DSM products do not give consistently: LidarBC's own CHMs cover 2023-24
only (NewGraphEnvironment/stac_dem_bc#47), and DSM specifications differ between deliveries.

## Proposal

A short README section: from a STAC search to a canopy height model, over a small window at the Maxan
Creek delta, Bulkley Lake (`093/093l/2019`), linking to the full article in
NewGraphEnvironment/floodplains#121 (historic channels, forest loss) for the story.

- Built with lidR or lasR (height above a ground TIN, pit-free rasterising), not hand-rolled in laspy.
  Their R dependencies go in `scripts/DESCRIPTION`.
- From all non-ground returns: LidarBC vegetation is mostly class 1 (`research/laz_classes.md`).
- These tiles have no `copc` asset, so the window's `.laz` is downloaded whole, once, under
  `update_query = TRUE`, and the figure and its numbers are cached like `fig/kanaka_dem.png` and
  `data/readme_dem.json`. A render with `update_query = FALSE` reads only the cache.
- Keep the window to one or two tiles (each 0.1-0.6 GB here).

## Data (measured 2026-10-11)

About 39 points/m²; a sample from `bc_093l040_4_1_1` is 17% class 2 and 83% class 1.

## Verification plan (from plan mode)


- Both test suites green; the CHM test goes red when the noise filter or the ground-at-0 rule is
  removed (restore-the-bug check).
- `update_query = FALSE` render with `data/readme_laz/` deleted succeeds (cache only, no network).
- Every number in the new paragraph traced to `data/readme_chm.json`.

## lidR behaviour met in Phase 1 (lidR 4.3.3, 2026-10-11)

- `rasterize_canopy()` given a template grid errors with `C++ unexpected internal error in
  'filter_with_grid': point out of raster` when any point lies outside the grid. The read
  margin has to be filtered off before rasterising.
- Pit-free rasterising leaves the outermost row/column of its grid NA (the triangulation of
  per-cell highest points does not reach those cell centres). So the grid is built two cells
  beyond the window and cropped back.
- `normalize_height()` takes classes 2 **and 9** (water) as ground by default.
- `pitfree(highest = TRUE)` (the default) keeps the highest point per pixel, of any return.

## The two tiles, measured 2026-10-12

`bc_093l040_3_4_1` and `_3_4_2` (`093/093l/2019`), read whole with lidR:

| | 3_4_1 | 3_4_2 |
|---|---|---|
| points | 53,354,535 | 54,403,776 |
| class 1 / 2 / 7 | 30,135,310 / 23,219,133 / 92 | 45,825,296 / 8,573,975 / 4,505 |
| withheld, overlap flag | 0, 0 | 0, 0 |
| first-return share | 0.72 | 0.57 |
| Z range (m) | 705.8–782.5 | 200.2–808.1 |

- No class 9, so the lake is not ground to `normalize_height()`. Lake surface returns are class 1,
  about 4.6/m², flat (712.5–712.8 m), so the lake reads 0 m where they are dense enough and NA
  where gaps exceed 2 m: the speckle in the figure.
- The 200 m low in 3_4_2 and the lowest 1e-5 of its returns are mostly class 7, dropped. The
  highest returns are class 1, at most 39.5 m above ground in the CHM: trees, not birds.
- Density in these two is about 22/m² (count over area), not the 39/m² the issue quotes for
  tiles to the east (plan review A1). Window probe: 22.5/m² over open ground in the NW.
- The open NW of the window is 77% class 2, Z 713–717: land (meadow), not lake.
- Downloads from nrs.objectstore.gov.bc.ca: 241 MB in about 9 min, then 291 MB in about 7 min.
- `Rscript scripts/readme_chm.R` on the cached tiles: 570 s, peak RSS 9.4 GB, window 1.2 × 1.0
  km plus 30 m, 23.4 M returns in the window. lidR warns that 68,755 points were too far from
  ground to interpolate (the lake) and used the nearest neighbour.
- Window kept as first drawn (mouth −700/+500 m E, −600/+400 m N): it shows the channel, the
  delta's tree stands, the forested south slope and the lake edge, and stays on two tiles.

## Plan review (planning/active/review-plan.md), dispositions

- B1 confirmed in lidR's source: `pitfree()` rasterises first returns only and needs
  `ReturnNumber`, so the first run's `select = "xyzc"` would have failed; now `"xyzrc"`.
  `max_edge = c(2, 1.5)` already trimmed the base layer; a test now pins a gap reading NA.
- B2: `pc_readme_fetch_file()` uses httr2 to a `.part` in the target directory; total timeout
  removed in favour of a low-speed abort.
- G2 search with the margin, G11 pinned delivery plus item/byte guard, G12 the render's own
  Rscript, S1 the lidR calls shown on the page through a second marker: done.
- G3/G4/G5 measured above: no overlap, withheld or water classes in these tiles.
- S3: #18 stays its own issue; this work does not touch `pc_readme_bucket()`.

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `pitfree()`: No attribute 'ReturnNumber' (from lidR source; first run killed before reaching it) | `select = "xyzrc"` |
| `filter_with_grid: point out of raster` | Filter points to the grid before `rasterize_canopy()` |
