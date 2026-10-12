# Task: README: a canopy height model from the point clouds (Maxan Creek delta) (#19)

The README demonstrates the collection with a bare-earth DEM (lower Kanaka Creek, ground returns from a
COPC window). Ground is half of what a point cloud gives. The other half, the height of what stands on
the ground, is what the DEM and DSM products do not give consistently: LidarBC's own CHMs cover 2023-24
only (NewGraphEnvironment/stac_dem_bc#47), and DSM specifications differ between deliveries.

## What exploration found

- **Mouth:** BCGNIS point for Maxan Creek, `-126.1256, 54.3814` → EPSG:3156 `686665, 6029765`. Used
  instead of the FWA stem end, which the atlas routes to the receiving water's centreline
  (code-check-spatial).
- **Tiles:** the mouth sits ~70 m from the boundary between `bc_093l040_3_4_1` (241 MB, 53 M pts) and
  `bc_093l040_3_4_2` (291 MB, 54 M pts). A ~1 × 1 km window around it takes those two: ~530 MB
  downloaded once. No `copc` on any of the 20 nearby items; `laz` assets carry `file:size` only (no
  checksum), so "downloaded once" is checked by size.
- **Pattern to mirror:** `readme_dem.py` + `data/readme_dem.json` + `fig/kanaka_dem.png`, run from the
  `query` chunk under `update_query = TRUE`, shown via `pc_readme_lines(path, "shown on the landing
  page")`, and the cache-existence loop stops a render with a missing cache.
- **lidR vs lasR:** lidR (CRAN 4.3.3; lasR is r-universe only, a harder install from
  `scripts/DESCRIPTION`). Neither is installed here; `pak::local_install_dev_deps("scripts")` will.
  Reading with `filter = "-keep_xy …"` loads only the window (+ buffer), so memory stays at a few GB.
- **"All non-ground returns":** classes 7 and 18 (noise) and withheld points dropped; nothing filtered
  by vegetation class (class 1 is where vegetation is, `research/laz_classes.md`). Ground returns stay
  in at height 0 so open ground reads 0 m rather than empty; the lake, with few returns, stays empty
  and is drawn as water like the DEM.
- **#18 (open):** an `update_query = TRUE` render reads the 35 MB collection.json through R's 60 s URL
  timeout. If it fails the render, that is #18, reported, not worked around here.

## Phase 1: CHM functions and tests

- [ ] `scripts/DESCRIPTION`: add `lidR` and `terra` to Imports; install with
      `pak::local_install_dev_deps("scripts")`
- [ ] Failing tests in `tests/readme_functions_test.R`:
  - CHM from a synthetic `lidR::LAS` (flat ground + a 20 m "tree" + a class 7 point at 80 m): the
    tree's cell reads ~20 m, open ground reads 0, the noise point does not appear, the grid has the
    window's extent and resolution
  - download-once: a cached file of the item's `file:size` is not fetched again; a wrong-size file
    is refused (no network in the test)
- [ ] `scripts/readme_functions.R`: `pc_readme_laz_get(href, size, dir)` (download to a temp name,
      check size, rename; skip when present at the right size) and `pc_readme_chm(las, box, res)`
      (`normalize_height(tin())` on the buffered read, drop noise/withheld, `rasterize_canopy(res,
      pitfree(...))`, crop to the window); `CHM_JSON` constant
- [ ] Tests pass

## Phase 2: the CHM script, cache and figure

- [ ] `scripts/readme_chm.R`, shaped like `readme_dem.py`: constants (mouth, window offsets, 0.5 m
      cell, buffer), an rstac search for the window, keep the one delivery at the mouth
      (`lidarbc:delivery`), refuse items with mixed CRS; `# --- shown on the landing page` markers
      around search → download → read → CHM; runs `main()` only when invoked by Rscript
- [ ] Download dir `data/readme_laz/`, gitignored
- [ ] Writes `fig/maxan_chm.png` (terra plot to a fixed-size png, water light blue, scale bar, no
      keyword `legend()`) and `data/readme_chm.json`: items found / used, hrefs, CRS, window, cell,
      bytes downloaded, points read, class shares (ground / class 1 / other), CHM height percentiles,
      share of cells ≥ 2 m and ≥ 10 m
- [ ] Tune the window on the first run so it shows the delta, the channel and forest edge; record
      the measured numbers in `findings.md`

## Phase 3: README section

- [ ] `README.Rmd` `query` chunk: run `Rscript scripts/readme_chm.R` beside the DEM demo; add
      `CHM_JSON` to the cache-existence loop
- [ ] New section after the DEM one ("From a search to a canopy height model"): figure with alt text,
      a paragraph whose numbers all come from `readme_chm.json` (tiles, MB downloaded, points, class
      shares, cell size, heights), why the `laz` is downloaded whole (no `copc` here), why class 1 is
      read, the floodplains#121 link; the script excerpt via `pc_readme_lines()` in an `{r}` chunk
      with `eval=FALSE`, and a link to the whole script
- [ ] Update the `build` chunk comment and the "Build, publish, register" paragraph (new outputs,
      the CHM step, `data/readme_laz/`)
- [ ] Render both targets per the `build` chunk; check README.md and index.html diffs carry only the
      new section and expected numbers, and that `fig/maxan_chm.png` looks right

## Validation

- [ ] Tests pass (`uv run pytest tests/ -q`, `testthat::test_file("tests/readme_functions_test.R")`)
- [ ] `/code-check` clean (once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion

