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

## Errors Encountered

| Error | Resolution |
|-------|------------|
