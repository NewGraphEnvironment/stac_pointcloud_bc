# Plan review for #19 (Plan agent, 2026-10-12)

## Review: plan for #19 (Maxan Creek CHM README section)

I found 2 blockers. Both make the plan state something wrong about the figure or about how it gets built, and neither needs code to see. Most other findings are cheap to fix once the two tiles have been measured. I only read files, ran `gh issue view` and fetched lidR's source; I edited nothing.

### Blocker

**B1. lidR's defaults fill the lake, so "the lake stays empty and is drawn as water" is false** (`planning/active/task_plan.md:24-26`, `:42`).
- lidR source (`R/algorithm-dsm.R`): `pitfree(thresholds = c(0,2,5,10,15), max_edge = c(0, 1), ...)` uses first returns only (`ReturnNumber == 1L`). The base layer uses `max_edge[1]`, and 0 means "no trimming". So the base TIN fills the whole convex hull, the lake included. A triangle from shoreline trees on one bank to the other can put metres of "canopy" over open water.
- `normalize_height(las, algorithm, use_class = c(2L, 9L))` treats class 9 (water) as ground. Any water returns become height 0, and the lake reads 0 rather than NA.
- Fix, chosen and stated in the plan:
  - Either use `pitfree(max_edge = c(k, 1))` with k of about 3-5 m at 0.5 m cells, or mask cells that have no first return (a per-cell count raster).
  - Decide on class 9: drop it before rasterising, or paint it as water.
- Add a test: a block with no returns in the synthetic cloud must read NA. With the default `pitfree()` that test fails, which is the point.

**B2. The download method is unspecified, and the obvious one cannot fetch these files** (`task_plan.md:40`).
- `pc_readme_laz_get()` must fetch 241 MB and 291 MB files (`file:size` 241289305 and 291068517 in the item JSON).
- `download.file()` and URL connections stop at `getOption("timeout")`, 60 s. Open issue #18 is exactly this failure on a 35 MB file, and its body prescribes `curl::curl_fetch_disk()` (no total timeout, `status_code` checked).
- CLAUDE.md:618 says never to read status from `download.file(quiet = TRUE)`.
- Fix:
  - Specify `curl::curl_fetch_disk()`, declaring `curl` in `scripts/DESCRIPTION`, or `httr2::req_perform(path =)` with no total timeout.
  - Check the status, write to `<dest>.part` in the same directory and rename. Not `tempfile()`: a rename across filesystems can fail, and CLAUDE.md:807 notes R deletes its tempdir.

### Gap

- **G1. "Bytes downloaded" reads 0 on any re-render** (`task_plan.md:55`, `:66`). With download-once, a second `update_query = TRUE` render transfers nothing. Record the on-disk sizes, checked against `file:size`, as `bytes_files`, and word the paragraph as "downloaded once: N MB". The DEM's `bytes_read` (`scripts/readme_dem.py:137`) is per run only because the DEM always re-reads.
- **G2. The search must use the buffered box, not the window** (`task_plan.md:49`). `readLAS(filter = "-keep_xy ...")` reads window plus buffer from the files downloaded. If a buffer edge crosses into a tile the search did not return, that edge has no buffer, and the TIN edge effects the buffer exists for come back.
- **G3. Overlap (class 12 or the overlap flag) is not addressed** (`task_plan.md:23`, `:55`).
  - Both tiles are LAS 1.4 point format 6 (`data/build/headers.jsonl`), so overlap and withheld are bit flags. Their `dimensions` list `withheld` and `overlap`.
  - `research/laz_classes.md` puts class 12 in 44% of sampled files.
  - The plan keeps overlap points by default but never says so. Its class shares (ground / class 1 / other) could put a large overlap share in "other", which would undercut the paragraph's claim that class 1 is where vegetation is.
  - Measure class 12 and the overlap flag on these two tiles, decide, and report overlap separately in the json.
- **G4. No filter on height outliers.**
  - `normalize_height` keeps negative heights. It does no clamping.
  - Tile `bc_093l040_3_4_2` has header min Z 200.15 m, about 500 m below the ~705 m ground. If that point is not class 7 or 18 it normalises to about -500 m.
  - Unclassified birds or power lines (Highway 16 and the rail corridor are in the valley) would read as canopy.
  - Measure the classes of the extreme points. Then either filter heights to a stated range (for example -1 to 60 m), or show that classes 7 and 18 already catch them.
- **G5. How withheld points are dropped is unstated.** lidR's `readLAS` (`R/io_readLAS.R`) says nothing about withheld points, and `normalize_height` does not exclude them. Drop them explicitly in the read (`-drop_withheld`, alongside `-drop_class 7 18`) or filter on the withheld flag. Count them before dropping if the json is to report them.
- **G6. `select` affects both memory and correctness** (`task_plan.md:22`).
  - `pitfree` stops without `ReturnNumber`, and `normalize_height` needs `Classification`.
  - Use something like `select = "xyzrcwo"` rather than `"*"`. Format 6 loads about 18 columns, roughly 100 B a point in R.
  - With `select`, memory is about a third. Measure peak RSS on the first run rather than asserting "a few GB" (CLAUDE.md:314).
- **G7. Grid alignment.**
  - `rasterize_canopy` snaps its grid to multiples of `res`, and `terra::crop()` snaps to the nearest edge.
  - If the mouth is a lon/lat constant transformed at run time (as in `readme_dem.py:115`), the window is fractional, and the plan's test claim "the grid has the window's extent" does not hold.
  - Round the box to the cell, or pass a template `SpatRaster` as `res`.
- **G8. The synthetic-tree test is fragile under pitfree** (`task_plan.md:35-37`).
  - A single 20 m point never forms a triangle in the thresholded layers (`max_edge[2] = 1`). In the base layer it makes a cone, so its cell reads 20 only if the cell centre lands on the point.
  - Use a crown of several first returns (for example 3×3 at 0.3 m spacing).
  - Give every synthetic point `ReturnNumber = 1L` and integer `Classification`.
  - Put enough class 2 points across window plus buffer to make a TIN.
- **G9. Several json numbers lack definitions** (`task_plan.md:55-56`):
  - "points read": window or buffer?
  - class shares: before or after dropping noise and withheld?
  - height percentiles: over all non-NA cells (zeros dominate) or only cells ≥ 2 m?
  - the denominator of "share ≥ 2 m / ≥ 10 m": NA cells (water) in or out?
  - Every one of these ends up as a number in the README sentence.
- **G10. What happens to a wrong-size file is ambiguous** (`task_plan.md:38-40`). A stale cached file of the wrong size could be re-fetched (the province re-delivered) or rejected with an error, and the plan doesn't say which. A wrong size after download should error and delete the `.part`. The test must make the network fail (CLAUDE.md:840), for example with an href of `http://127.0.0.1:9/x.laz`, so that a cache miss errors rather than quietly downloading.
- **G11. The delivery rule should be a pinned constant** (`task_plan.md:50`). Only `093-093l-2019` covers this area now (31 items in `data/build/items`), and the issue names `093/093l/2019`. Pin `lidarbc:delivery == "093/093l/2019"` instead of "the one at the mouth", so a delivery indexed later cannot silently change the figure. Add a guard that refuses more than 2 items or more than about 600 MB before downloading. Window tuning (G15) could otherwise pull in a 0.5-0.6 GB neighbour.
- **G12. `system2("Rscript", ...)` may run a different R** from the one rendering, whose library may lack lidR. Use `file.path(R.home("bin"), "Rscript")`.
- **G13. Smaller stale points.**
  - The header comment of `scripts/readme_functions.R:3-7` says "two caches" and needs updating.
  - The `query` chunk must also read `CHM_JSON` (`chm <- jsonlite::fromJSON(...)`), not just add it to the existence loop at `README.Rmd:84`.
- **G14. The tiles' bboxes overlap by 57 m in x** (`3_4_1` xmax 686732, `3_4_2` xmin 686675). This is probably grid convergence on lat/lon-bounded tiles (3° east of the UTM 9 meridian), not duplicated points. Count duplicate XYZ after the merge read to confirm. `readLAS` with several files also warns if scales differ.

### Ordering

- **O1. Measure the tiles before Phase 1 freezes the filter set.** Phase 1 (`task_plan.md:34-43`) fixes what `pc_readme_chm` drops before anything has been read. G3-G5 and B1 depend on the real tiles: class counts, overlap and withheld flag counts, the Z range, and whether class 9 exists. Download and profile the two tiles first, at the start of Phase 1 or as a Phase 0, then write the tests.
- **O2. Commit `data/readme_laz/` to `.gitignore` before the first download** (`task_plan.md:52` comes after the script bullet). 530 MB in the work tree is one `git add -A` away from being staged.
- **O3. Prove the script standalone before wiring it in.** The `update_query = TRUE` render does a ~19-minute API fetch (#18 body) before the CHM step, so every CHM failure inside the render costs that much. Run `Rscript scripts/readme_chm.R` standalone until it is final, then wire it into the `query` chunk. Don't edit the script while a tuning run is in flight (CLAUDE.md:825).

### Assumption

- **A1. Density: "About 39 points/m²"** (`findings.md:28`) does not hold for these tiles. Point count over header bbox gives 21.8/m² (`3_4_1`) and 22.2/m² (`3_4_2`); 39 matches the 4_1_x and 4_3_1 tiles to the east. A 1 km window with a 50 m buffer is then about 26 M points. That helps memory, but the README must not quote 39.
- **A2. Room to tune the window is limited** (`task_plan.md:57`). The search matches on item geometry, which comes from the bboxes. To stay on 2 tiles, window plus buffer must sit within about:
  - x 685109-688298 (`3_3_2` xmax, `4_3_1` xmin)
  - y 6029123-6030380 (`3_2_4` ymax, `3_4_3` ymin)

  The mouth (686665, 6029765) leaves about 640 m to the south and 615 m to the north before the buffer is counted.
- **A3. lidR availability.** lidR is not installed (`requireNamespace` is FALSE). terra 1.9.50 is present. lidR has CRAN macOS binaries, so `pak::local_install_dev_deps("scripts")` should work. `terra` in Imports is fine, since lidR already depends on it.
- **A4. PNG determinism.** An R `png()` or terra plot should not embed a timestamp, but check it: re-run on the same input and confirm `git status fig/` is clean (CLAUDE.md:630).
- **A5. `normalize_height` gives NA heights to points in its buffer** when interpolation fails. Check that `rasterize_canopy` handles them, or crop them out first.

### Scope

- **S1. The landing-page excerpt hides lidR** (`task_plan.md:42`, `:50-51`). `normalize_height(tin())` and `rasterize_canopy(pitfree())` are inside `pc_readme_chm()` in `readme_functions.R`. The excerpt (search → download → read → CHM) would therefore show a call to a helper, not the lidR calls the issue asks to demonstrate ("height above a ground TIN, pit-free rasterising"). The DEM excerpt shows its library call (`CopcReader.query`, `readme_dem.py:132`). Keep the two lidR calls between the excerpt markers, and keep only the filtering and download helpers in tested functions.
- **S2. The plan is inconsistent about where the code lives.** It puts the functions in `readme_functions.R`, which the tests source, and also gives `readme_chm.R` an "only when invoked by Rscript" guard (`task_plan.md:51`). Nothing sources `readme_chm.R`, so the guard serves no purpose. If the guard stays, `sys.nframe() == 0L` is the right test, not `!interactive()`, which is also FALSE under `Rscript -e testthat::...`. Pick one layout, either the DEM pattern (testable functions in the demo script, tests source it) or helpers in `readme_functions.R`.
- **S3. #18 is the same download problem.** The plan reports #18 rather than fixing it (`task_plan.md:27-28`). That is consistent with CLAUDE.md, but G-B2 writes the very curl-to-disk download #18 prescribes. Either fix #18 here with a shared helper (about 5 lines) or say why not. Fallback if #18 fails the md render: on 2026-10-11 it was rendered with `options(timeout = 1800)` for that run (per #18); state whether that is acceptable here.
- **S4. Paragraph wording.** "Why class 1 is read" (`task_plan.md:66`): the plan doesn't select class 1, it just doesn't filter by vegetation class. Word it that way, or the README overstates the method.

### Acceptance

- **AC1. The diffs will carry more than the new section** (`task_plan.md:71-72`). An `update_query = TRUE` render also rewrites:
  - `fetched_at` ("read from the API on ...", `README.Rmd:157`)
  - any collection or DEM numbers the API has moved
  - `fig/kanaka_dem.png`, because `readme_dem.py` re-runs

  List the expected diff set, or the check will fail on a correct render.
- **AC2. Restore-the-bug check.** Count `r$failed > 0 | r$error` (CLAUDE.md:636), since a restored defect in lidR code often raises rather than fails. "Ground-at-0 rule removed" (`findings.md:33-34`) doesn't name a code line. Name what is reverted (for example "ground points filtered before rasterising").
- **AC3. Add checks:**
  - no `README_files/` or `index_files/` appear (the figure must come from `include_graphics`, never a printed plot; `.gitignore` comment)
  - `git status` shows nothing under `data/readme_laz/`
  - the NA-over-water behaviour (B1) is visible in the png
  - growth in `index.html` (self-contained, already 3.4 MB; the DEM png is 1.3 MB) is noted
- **AC4. Missing-cache check.** The cache-only render with `data/readme_laz/` deleted (`findings.md:35`) is good. Also delete `data/readme_chm.json` and confirm the render stops with the "missing" message.

### What was checked and is fine

- The `{r chm-code, eval=FALSE, code=pc_readme_lines(...)}` chunk works. `pc_readme_lines` is defined in the `source` chunk before it, its `# ---` marker grep is fixed-string, and it dedents an indented `main()` body. The existing labels are `setup`, `source`, `build`, `example-run`, `query`, `badges`, `dem-fig`, `dem-code`, `groups`, `example`, `tab-md`, `tab-cap`, `tab-dt`, `header`, `header-tab`; the new labels (for example `chm-fig`, `chm-code`) must not reuse any (CLAUDE.md:651). No reticulate concern, since this is an R chunk.
- Writing the png from a separate Rscript process keeps the figure out of `README_files/`.
- "No keyword `legend()`" matches CLAUDE.md:1228.
- The plan follows CLAUDE.md's README rules: edit `README.Rmd` only, R dependencies in `scripts/DESCRIPTION`.
- NEWS.md covers the published catalogue only, so no NEWS entry or version bump is needed.
- Item facts confirmed:
  - both tiles are `093/093l/2019`, `EPSG:3156`, LAS 1.4 format 6, no `copc`, with `file:size` present
  - `3_4_1` xmax 686732 is 67 m east of the mouth's x
  - a ±500 m window around the mouth lies within both tiles in y

### Critical Files for Implementation
- /Users/airvine/Projects/repo/stac_pointcloud_bc/scripts/readme_functions.R
- /Users/airvine/Projects/repo/stac_pointcloud_bc/README.Rmd
- /Users/airvine/Projects/repo/stac_pointcloud_bc/tests/readme_functions_test.R
- /Users/airvine/Projects/repo/stac_pointcloud_bc/scripts/readme_dem.py
- /Users/airvine/Projects/repo/stac_pointcloud_bc/scripts/DESCRIPTION
