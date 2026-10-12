# Code-check round 2: branch 18-readme-render-read-the-35-mb-collection-json vs main (2026-10-12)

## Clean
No issues found.

### What was checked, and how

- **Tests, on a copy** (scratchpad `r2/`): `testthat::test_file("tests/readme_functions_test.R")`
  gave 14 tests, 0 failed and 0 errors. Counted as `failed > 0 | error`, not `failed` alone.
- **Mutation table, on the copy.** Each mutation was applied to `pc_readme_bucket_json()` and
  tests 13 and 14 were re-run. The source was restored and `cmp`'d against the repo afterwards.

  | mutation | test 13 | test 14 |
  |---|---|---|
  | drop `on.exit(unlink(tmp))` | RED | RED |
  | parse the URL instead of `tmp` | RED | green |
  | `fromJSON(tmp)` without `simplifyVector = FALSE` | RED | green |
  | drop the `%20` decode | RED | green |
  | drop the `rel: item` filter | RED | green |

  Every behaviour the change introduces is pinned by at least one test. The claim in
  findings.md that removing `on.exit` fails both cleanup assertions is confirmed.
- **Live read, independent of the branch's own check.** `pc_readme_bucket_json()` ran under
  `options(timeout = 3)`, 15:19:41 to 15:22:03 UTC. It succeeded in 2.30 min, with 174,282 ids,
  no duplicates, version 0.3.0 and no `.json` left in `tempdir()`. So the httr2 transfer does
  not inherit R's URL timeout. The old `fromJSON(<url>)` under the same `timeout = 3` failed in
  3.0 s with `Timeout of 3 seconds was reached` / `cannot read from connection`, which is the
  incident's error. Both findings.md claims reproduce.
- **jsonlite path handling (2.0.0):** a short existing path is opened as a file. An empty or
  partial file raises a parse error; it does not return an empty `links`.
- **Error path:** an HTTP error raises from `req_perform` (httr2 1.3.0), and `on.exit` removes
  the error body written to `tmp`. `on.exit` is registered in a function frame, so it fires.
  The lazy default `fetch = pc_readme_fetch_file` resolves at call time, so the helper being
  defined later in the file is fine.
- **Return shape:** `pc_readme_bucket()` still returns `ids`, `version` and `api_version`, so
  `pc_readme_fetch()`'s set and version checks are unchanged. The id extraction is the old
  logic byte for byte.
- **Other URL-connection reads in the render path:** none. The remaining `fromJSON` calls
  (README.Rmd:97, 98, 204; scripts/readme_chm.R:60) parse local files or strings.

### Notes on the planning text (not code defects)

- findings.md, "Live check": *"Script: scratchpad `bucket_check.R`, its body is in the PR."*
  No PR exists yet (`gh pr list --head <branch>` is empty), and the script lives only in the
  session scratchpad, which is temporary. The claim holds only if the PR body is written with
  that script in it.
- findings.md, "Issue context", still carries the issue's original prescription
  (`curl::curl_fetch_disk()`, declare `curl`). The section is labelled as the issue's text, and
  task_plan.md's notes and the edited issue body both record the change to httr2. It reads
  correctly in context, so it is listed here only for completeness.
