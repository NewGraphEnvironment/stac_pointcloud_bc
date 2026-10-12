# Code-check round 3: branch 18-readme-render-read-the-35-mb-collection-json vs main (2026-10-12)

Scope: the callers of `pc_readme_bucket_json()` and the end-to-end `update_query = TRUE` render
path, which rounds 1 and 2 did not cover. Nothing in the repo was edited; probes ran from scratchpad `r3/`.

## Clean
No issues found.

### What was checked, and how

- **Call path.** README.Rmd `query` chunk -> `pc_readme_fetch()` (rstac `items_fetch`, then
  `pc_readme_bucket()` at readme_functions.R:181) -> `pc_readme_bucket()` (rstac `get_request`
  for `api_version`, then `pc_readme_bucket_json()`). `pc_readme_bucket()` keeps its return
  shape (`ids`, `version`, `api_version`), and `pc_readme_fetch()`'s set and version checks
  read exactly those fields. Nothing else calls `pc_readme_bucket()` or `pc_readme_bucket_json()`.
- **Other R URL-connection reads in the render path: none.** I scanned the namespaces with
  `deparse()`:
  - rstac 1.0.1 makes every request through `httr::GET`/`httr::POST` (`make_get_request`,
    `make_post_request`). Its only `fromJSON` is in `get_spatial.character`, which the render
    does not call.
  - bcdata's `fromJSON` calls parse `r$parse("UTF-8")` from a crul response
    (`bcdc_get_record`), not a URL.
  - geojsonsf's `url()`/`readLines` are only in its character-input readers. README.Rmd and
    readme_chm.R call `sf_geojson`/`sfc_geojson` on sf objects.
  - readme_chm.R runs as a separate `Rscript`. Its only transfers are rstac (httr) and
    `pc_readme_laz_get()` -> `pc_readme_fetch_file()` (httr2).
  - readme_dem.py is Python.
  - README.Rmd:97, 98, 204 and readme_chm.R:60 parse local files or strings. None of these
    honours `getOption("timeout")`.
- **httr2 1.3.0 total timeout: none by default.** `req_handle()` is `curl::new_handle()` plus
  `req$options` only. `retry_max_tries()` is 1 unless a retry policy is set, so a failure is
  not retried silently. A curl error (for example the `low_speed_limit`/`low_speed_time`
  abort) comes back from `capture_curl_error` and is raised by `handle_resp()`
  (`cnd_signal(resp)`). The comment on `pc_readme_fetch_file()` (abandoned under 10 kB/s for
  two minutes, no total timeout) matches curl's semantics for those options.
- **The error path, live.** `req_perform(path=)` on a missing bucket key raised
  `HTTP 403 Forbidden.` and left the S3 `AccessDenied` XML in `path`. This confirms
  findings.md's probe, and shows the `on.exit(unlink(tmp))` is needed and sufficient.
- **tempdir under knitr.** `tempfile()` uses the R session's `tempdir()`, and rmarkdown's
  intermediates dir does not change that. The lazy default `fetch = pc_readme_fetch_file`
  resolves in the closure's environment. `source()` with `local = FALSE` defines both functions
  in the global environment, whatever `envir` knitr evaluates the chunk in. This is the same
  pattern `pc_readme_laz_get()` already uses.
- **Planning claims vs code.**
  - task_plan.md Phase 2 (signature and return shape kept, rstac still supplies
    `api_version`): true.
  - review-plan.md "pc_readme_fetch() reads the bucket only after its 19-min fetch": true
    (line 181 follows `items_fetch`).
  - review-plan.md "rstac uses httr, bcdata crul, header read httr2": true by the scan above.
  - findings.md's httr2 403 behaviour: reproduced.
  - The live-timing and mutation claims were confirmed in round 2 and were not re-run here.
