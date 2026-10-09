# Code-check round 3 — branch 9-readme-rmd-landing-page-served-on-github (base 9a9d02a)

## Findings

- **[severity: fragile]** scripts/readme_dem.py:105 (`items = [i for i in items if ...[:4] == year]`) with README.Rmd:121 ("One STAC search for a … window returned the `length(dem$items)` items covering it") — the round-2 fix changed what `items` means, and the sentence written before it did not change. `dem$items` is now the search result *after* the year filter, but the page still says that is what the search returned. Today the two agree: the window search returns only the four 092g/2016 items (probed live). They stop agreeing as soon as a second delivery over Kanaka is indexed, and one exists. `stac-elevation-bc` at the mouth point holds `092-092g-2024-dem-bc_092g018_3_3_3_xli1m_utm10_20240217_20250425` beside the 2016 tile, so indexing the rest of the province will bring 092g/2024 point clouds into this window. After that, a re-render that passes every guard prints "returned the 4 items" for a search that returned about 8. The mechanism is one fact taken from two places: the prose describes the search and the number comes from the filtered list. Fix: write the unfiltered search count to readme_dem.json too (e.g. `"items_searched"`), and make the sentence say what was kept ("returned N items; the M from the 2016 delivery were read").

## The mechanism behind R1/R2, and where it reaches

The shared assumption was that the declared environment (scripts/DESCRIPTION, the pyproject `readme` group, the README setup commands) was complete. That was inferred from the page rendering on this machine, where everything happens to be installed, and never computed. I checked it by building environments that hold only what is declared:

- **R, declared packages only.** I built a library from scripts/DESCRIPTION Imports + Suggests and their recursive Depends/Imports/LinkingTo (109 packages, with reticulate, purrr and everything else absent), plus R's base/recommended library. Under `R_LIBS_USER=<that lib>`, in a `git archive HEAD` copy:
  - the README.md render with `update_query = TRUE` (live API, bucket, bcdata, two header reads, and the DEM through a fresh `uv run --group readme` venv with 57 packages, CPython 3.12.13) succeeded. Its README.md, data/readme_dem.json and fig/kanaka_dem.png are **byte-identical** to the committed ones, and every element of data/readme_cache.rds is `identical()`;
  - both `update_query = FALSE` renders are byte-identical to the committed README.md and index.html;
  - `tests/readme_functions_test.R` passes 24/24.
- **Every `pkg::` reference** in README.Rmd, scripts/readme_functions.R and the tests (enumerated by grep: bcdata, dplyr, DT, geojsonsf, glue, htmlwidgets, httr2, jsonlite, knitr, rmarkdown, rstac, sf, tibble, testthat) is declared. The only exception is `pak::`, which is the installer itself.
- **Version floors against the APIs used:** `resp_stream_is_complete()` and the current `req_perform_connection()` arrived in httr2 1.1.0, the declared floor. `items_as_sf()` arrived in rstac 1.0.0, the declared floor. Base `%||%` needs R 4.4, which is declared. `\(x)` and `|>` need 4.1.
- **Python:** the `readme` group (matplotlib, pystac-client) plus the base dependencies was enough for the DEM run above in a venv built from scratch. `uv run pytest tests/ -q` passes 101 tests without the group, because readme_dem.py imports pystac_client and matplotlib inside functions. numpy is imported directly but declared only transitively (through laspy and matplotlib), which is guaranteed rather than accidental.
- **System tools:** `uv` and `pandoc` resolve from /opt/homebrew/bin, which /etc/paths.d/homebrew also gives to GUI-launched R. A missing uv fails loudly through the `system2()` status check.

**Verdict on the mechanism:** the declared environment is now sufficient. This was measured, not inferred.

## Round-2 fixes (9a9337a)

- `python.reticulate = FALSE`: knitr's `eng_python` routes to `eng_interpreted`, which returns `engine_output()` without running anything when `eval = FALSE`. With reticulate removed from the library path, both renders were byte-identical. Correct.
- One delivery per grid: the year filter is a stand-in for "one delivery". It is safe here because a LidarBC delivery is `<block>/<sheet>/<year>`, and the window sits about 43 km from the nearest other NTS sheet that could carry a same-year delivery. The defect the fix did introduce is the prose mismatch in the finding above.
- Stale map / purrr references: grep finds none left.

## Also probed, no defect

- The "holds ground returns only" claim was measured inside the window, but it holds for the whole item. COPC octree levels 0–1 of 092g028_1_1_1 are 97,740/97,740 class 2, against roughly 90% class 1 in the other three items.
- The DEM window (529,609–531,209 E, 5,449,509–5,450,709 N) lies entirely inside the union of the four tiles' boxes, so no NaN gap at the edge is painted as water.
