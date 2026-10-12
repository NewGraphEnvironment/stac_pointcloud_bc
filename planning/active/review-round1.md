# Code-check round 1 — branch 19-readme-a-canopy-height-model-from-the-po vs main

Reviewed: README.Rmd, scripts/readme_chm.R, scripts/readme_functions.R,
tests/readme_functions_test.R, scripts/DESCRIPTION, .gitignore, data/readme_chm.json,
and README.md's rendered prose against data/readme_chm.json.

## Findings

- **[severity: fragile]** README.Rmd:144 (prose), scripts/readme_chm.R:63-77 — the page says
  "None of them has a `copc` asset, so there is no window to read", and the shown code
  comments "No `copc` asset, so no window read", but nothing checks it and
  data/readme_chm.json does not record it. Every other number in that paragraph comes from
  the JSON; this claim is fixed text. It holds today (probed 2026-10-11: both
  093l040_3_4_{1,2} items carry only `laz`), but the build adds a `copc` asset wherever a
  CanElevation COPC of the same name passes the header check, so a later release that pairs
  this tile would leave a re-render (update_query = TRUE) succeeding and publishing a false
  statement. Fix: `stopifnot(all(vapply(items, \(f) is.null(f$assets$copc), logical(1))))`
  before the download in readme_chm.R (or write a `copc` count to the JSON and branch the
  prose on it).

## Checked and not a defect

- `pc_readme_laz_get`: `.part` is removed by `on.exit` on every exit path, renamed only at
  the item's `file:size`; a wrong-size cached file is refused, not overwritten.
- `pc_readme_fetch_file`: httr2 `req_perform()` raises on 4xx/5xx; `low_speed_limit` /
  `low_speed_time` are valid curl options; no default total timeout in httr2.
- `readLAS(select = "xyzrc", filter = "-drop_withheld -keep_xy <xmin ymin xmax ymax>")`:
  keep_xy order matches `read_box`; withheld dropped by LASlib, so the `Withheld_flag`
  branch in `pc_readme_chm` is correctly skipped when the column is not loaded.
- `sys.nframe() == 0L` runs `main()` under Rscript and not when sourced.
- `system2(file.path(R.home("bin"), "Rscript"), ...)` returns the exit status (no
  `stdout = TRUE`), so a failing script stops the render.
- Rendered numbers in README.md match data/readme_chm.json (1.2 x 1 km, 30 m, 2 items,
  532 MB, 107.8 M, 23.4 M, 33% / 67%, 0.5 m, 25% / 8%, p99 25.5, max 39.5); class counts
  sum to `points_window`.
- `pc_readme_lines` markers are unique in both files; the excerpts render as intended.
- Tests use `withr::` and `data.table::` without declaring them in scripts/DESCRIPTION, but
  both are hard dependencies of testthat and lidR respectively, and this is not an
  `R CMD check`ed package.
