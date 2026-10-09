# Task: README.Rmd landing page served on GitHub Pages, like stac_dem_bc (#9)

**If we do it:** the collection has a landing page like its sisters, with a write-up, a working example and a figure. Someone arriving from images.a11s.one or a sister repo can see what `stac-pointcloud-bc` holds and query it in a minute. **If we never do:** the README stays a build manual, and the GitHub Pages URL does not exist, so nothing links here.

Decided at the plan gate (user, 2026-10-09): R dependencies are declared in a `Type: Project` DESCRIPTION manifest (no renv), and the build manual stays in README.Rmd as a "Build, publish, register" section.

## Phase 1: R toolchain and header reader
- [x] `DESCRIPTION` (`Type: Project`, Imports with floors: rstac, rmarkdown, knitr, DT,
      htmlwidgets, sf, ggplot2, bcdata, bcmaps, geojsonsf, jsonlite, httr2, dplyr, purrr,
      tibble, glue), body saying it is a manifest, not a package
- [x] `scripts/readme_functions.R` with `pc_readme_header(url)`: range-read the first 375
      bytes, refuse anything but a 206 and a `LASF` signature, parse version, point format
      (compression bits masked), point count (the 64-bit field for LAS 1.4, legacy field
      otherwise), scale, offset, min/max
- [x] Test (`tests/readme_functions_test.R`, testthat, run by `Rscript`): header bytes
      of one LAS 1.2 `laz` and one LAS 1.4 `copc` saved to `tests/fixtures/` (375 B each);
      parsed values must equal the item JSON that laspy produced (`pc:count`, `proj:bbox`,
      `nge:las_version`, `nge:point_format`). Restore the bug (legacy count on 1.4, unmasked
      format byte) and watch it fail

## Phase 2: Query, cache and figure
- [x] `pc_readme_fetch()`: every item of `stac-pointcloud-bc` via rstac, reduced to a slim
      sf (id, mapsheet-year, has_copc, `laz`/`copc` href, footprint); stops unless the
      fetched id count equals the API's `numberMatched` (a truncated page must not draw a
      smaller map)
- [x] Example AOI with bcdata, as the sisters: one chosen by measurement so the result
      holds both laz-only and laz+copc items at a table-sized count; record the choice in
      findings.md
- [x] Header read of one returned item's `laz` and `copc`; the render `stopifnot`s each
      against the item's own `pc:count` and `proj:bbox`
- [x] `pc_readme_fig()` → `fig/footprints.png`: footprints by mapsheet-year over a BC
      outline (bcmaps), `copc` items marked, from the cached sf
- [x] One cache, `data/readme_cache.rds` (slim; check its size before committing)

## Phase 3: README.Rmd and render
- [x] `README.Rmd`: floodplains' YAML/params/seed/build chunk; badges md-only
- [x] Write-up: one item per LidarBC `.laz`; footprint, count, CRS from the header; what
      is indexed, linking NEWS.md (counts computed from the cache, never typed); the `copc`
      asset and its header check (`research/canelevation_overlap.md`); `dsm/*.laz` not
      indexed
- [x] Example: rstac search shown (`eval = params$update_query`), table of items with
      `laz`/`copc` links (kable head in md, DT in html), the header read and its check
- [x] Figure; sister collections (`stac-elevation-bc`, `stac-floodplains-bc`,
      `stac-airphoto-bc`, `imagery-uav-bc-prod`); "Build, publish, register" section
      carrying today's README commands; licence
- [x] Render md (`update_query = TRUE`) then html (`FALSE`); re-render both and confirm
      no diff (determinism); commit README.Rmd, README.md, index.html, fig/, cache
- [x] CLAUDE.md: one line that README.md and index.html are generated from README.Rmd

## Phase 4: Pages and About
- [x] Enable Pages from `main` at `/` (`gh api -X POST repos/…/pages`) — enabled before
      the merge (review O1): it serves main's README until then, index.html after
- [x] Confirm https://www.newgraphenvironment.com/stac_pointcloud_bc/ returns 200 with the
      page title
- [x] `gh repo edit --homepage <url> --description <…>`

## Phase 5: stac_dem_bc sister link (PR there)
- [x] Branch in stac_dem_bc, add `stac_pointcloud_bc` (`stac-pointcloud-bc`) to the
      sister list in README.Rmd, re-render both outputs with `update_query = FALSE`
- [x] Diff limited to the new bullet (stac_dem_bc's DT ids are unseeded, so index.html
      may churn — note it in the PR if so rather than fixing it there); open the PR

## Phase 6: From a search to a DEM (added 2026-10-09, user direction)

The user redirected the lead figure: show what the collection is for (find by place, get a
point cloud, make something) rather than a coverage map. Houston (093l) was asked for first
but is not indexed yet (#2) and has no COPC; Kanaka Creek at the Fraser was chosen from the
stream mouths that fall in COPC-linked items. The coverage map was then dropped ("we will
register all very soon").

- [x] `scripts/readme_dem.py`: pystac-client search for a window, windowed COPC read through
      `HttpRangeFile` (bytes counted), ground returns gridded at 2 m, hillshaded DEM →
      `fig/kanaka_dem.png`, numbers → `data/readme_dem.json`
- [x] `readme` dependency group (matplotlib, pystac-client)
- [x] Tests for `grid()` and `fill_small_gaps()`; two restored bugs each fail them
- [x] README.Rmd: the demo leads the page; its code is the script's own lines between markers
      (`pc_readme_lines()`); coverage map, `pc_readme_fig()`, bcmaps and ggplot2 removed
- [x] Renders: live md == cached md; cached renders byte-identical

## Validation

- [x] Tests pass (`uv run pytest tests/ -q` and the R test)
- [x] `/code-check` clean (once over the branch with `/code-check branch`)
- [x] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
