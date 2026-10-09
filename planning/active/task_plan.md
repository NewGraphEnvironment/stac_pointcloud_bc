# Task: README.Rmd landing page served on GitHub Pages, like stac_dem_bc (#9)

**If we do it:** the collection has a landing page like its sisters, with a write-up, a working example and a figure. Someone arriving from images.a11s.one or a sister repo can see what `stac-pointcloud-bc` holds and query it in a minute. **If we never do:** the README stays a build manual, and the GitHub Pages URL does not exist, so nothing links here.

Decided at the plan gate (user, 2026-10-09): R dependencies are declared in a `Type: Project` DESCRIPTION manifest (no renv), and the build manual stays in README.Rmd as a "Build, publish, register" section.

## Phase 1: R toolchain and header reader
- [ ] `DESCRIPTION` (`Type: Project`, Imports with floors: rstac, rmarkdown, knitr, DT,
      htmlwidgets, sf, ggplot2, bcdata, bcmaps, geojsonsf, jsonlite, httr2, dplyr, purrr,
      tibble, glue), body saying it is a manifest, not a package
- [ ] `scripts/readme_functions.R` with `pc_readme_header(url)`: range-read the first 375
      bytes, refuse anything but a 206 and a `LASF` signature, parse version, point format
      (compression bits masked), point count (the 64-bit field for LAS 1.4, legacy field
      otherwise), scale, offset, min/max
- [ ] Test (`tests/readme_functions_test.R`, testthat, run by `Rscript`): header bytes
      of one LAS 1.2 `laz` and one LAS 1.4 `copc` saved to `tests/fixtures/` (375 B each);
      parsed values must equal the item JSON that laspy produced (`pc:count`, `proj:bbox`,
      `nge:las_version`, `nge:point_format`). Restore the bug (legacy count on 1.4, unmasked
      format byte) and watch it fail

## Phase 2: Query, cache and figure
- [ ] `pc_readme_fetch()`: every item of `stac-pointcloud-bc` via rstac, reduced to a slim
      sf (id, mapsheet-year, has_copc, `laz`/`copc` href, footprint); stops unless the
      fetched id count equals the API's `numberMatched` (a truncated page must not draw a
      smaller map)
- [ ] Example AOI with bcdata, as the sisters: one chosen by measurement so the result
      holds both laz-only and laz+copc items at a table-sized count; record the choice in
      findings.md
- [ ] Header read of one returned item's `laz` and `copc`; the render `stopifnot`s each
      against the item's own `pc:count` and `proj:bbox`
- [ ] `pc_readme_fig()` → `fig/footprints.png`: footprints by mapsheet-year over a BC
      outline (bcmaps), `copc` items marked, from the cached sf
- [ ] One cache, `data/readme_cache.rds` (slim; check its size before committing)

## Phase 3: README.Rmd and render
- [ ] `README.Rmd`: floodplains' YAML/params/seed/build chunk; badges md-only
- [ ] Write-up: one item per LidarBC `.laz`; footprint, count, CRS from the header; what
      is indexed, linking NEWS.md (counts computed from the cache, never typed); the `copc`
      asset and its header check (`research/canelevation_overlap.md`); `dsm/*.laz` not
      indexed
- [ ] Example: rstac search shown (`eval = params$update_query`), table of items with
      `laz`/`copc` links (kable head in md, DT in html), the header read and its check
- [ ] Figure; sister collections (`stac-elevation-bc`, `stac-floodplains-bc`,
      `stac-airphoto-bc`, `imagery-uav-bc-prod`); "Build, publish, register" section
      carrying today's README commands; licence
- [ ] Render md (`update_query = TRUE`) then html (`FALSE`); re-render both and confirm
      no diff (determinism); commit README.Rmd, README.md, index.html, fig/, cache
- [ ] CLAUDE.md: one line that README.md and index.html are generated from README.Rmd

## Phase 4: Pages and About
- [ ] Enable Pages from `main` at `/` (`gh api -X POST repos/…/pages`) — after the PR
      merges, since it serves `main`; until then, record the step in the PR body
- [ ] Confirm https://www.newgraphenvironment.com/stac_pointcloud_bc/ returns 200 with the
      page title
- [ ] `gh repo edit --homepage <url> --description <…>`

## Phase 5: stac_dem_bc sister link (PR there)
- [ ] Branch in stac_dem_bc, add `stac_pointcloud_bc` (`stac-pointcloud-bc`) to the
      sister list in README.Rmd, re-render both outputs with `update_query = FALSE`
- [ ] Diff limited to the new bullet (stac_dem_bc's DT ids are unseeded, so index.html
      may churn — note it in the PR if so rather than fixing it there); open the PR

## Validation

- [ ] Tests pass (`uv run pytest tests/ -q` and the R test)
- [ ] `/code-check` clean (once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
