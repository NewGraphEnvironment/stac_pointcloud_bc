# Task: Draw the canopy height figure over the delta's ground, so its old channels show (#30), part 2

Part 1 (archived in `planning/archive/2026-10-issue-30-canopy-over-ground/`) redrew the delta's
canopy over its ground. A look outside that window (2026-10-17) found the old channels are clearest
upstream on Maxan Creek, 1-2.5 km south-west, and on the Bulkley River's floodplain. The user chose
(2026-10-17): keep the delta figure, add a second, ground-only figure of height above the stream bed
over ~4 x 2.5 km from LidarBC's published DEM through `stac-elevation-bc`, the stream-bed surface
rebuilt so it has no blotches; and name in the delta caption what the straight lines are.

## Phase 5: The stream-bed surface (tests first)
- [ ] Helpers: stream-bed samples (lowest ground near each FWA stream line, plus the lake's level),
      and the surface through them as a TIN, not nearest-sample (the scratch render's blotches)
- [ ] Tests on a synthetic valley: a channel reads 0, its floodplain its height above the bed

## Phase 6: The figure
- [ ] `scripts/readme_rem.R`: STAC search of `stac-elevation-bc` pinned to `093/093l/2019`, window
      read over HTTP, refused if any of it is nodata; FWA streams; REM; `fig/maxan_rem.png`,
      `data/readme_rem.json`
- [ ] `pc_readme_relief_png()` takes the ground scale's label and can omit the canopy scale

## Phase 7: The page
- [ ] README.Rmd: the new figure, caption, alt text, How it was made, code; the build chunk runs
      the script; the delta caption names the road (BC Digital Road Atlas) and the gullies
- [ ] Render README.md and index.html; check the figure at page width

## Validation
- [ ] Tests pass
- [ ] `/code-check branch` clean
- [ ] PWF checkboxes match landed work; archive
