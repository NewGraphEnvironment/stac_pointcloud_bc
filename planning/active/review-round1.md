# Code-check round 1 — branch 18-readme-render-read-the-35-mb-collection-json vs main (2026-10-12)

## Clean
No issues found.

Checked:
- `pc_readme_bucket_json()` (scripts/readme_functions.R:158-165): tempfile + `on.exit(unlink(tmp))` inside a function (fires); default `fetch = pc_readme_fetch_file` is a lazy default, so defining the helper later in the file is fine once the file is sourced whole; `jsonlite::fromJSON(tmp)` treats a short existing path as a file (path < 2084 bytes, `file.exists`), so it parses the download, not the path string.
- Id/version extraction is byte-for-byte the old logic; `pc_readme_bucket()` keeps its signature and return shape (`ids`, `version`, `api_version`), so `pc_readme_fetch()`'s set and version checks are unchanged.
- Error path: `pc_readme_fetch_file()` raises on HTTP error status (httr2 `req_perform`), and the error body it writes to `path` is removed by the `on.exit`; a truncated transfer would raise in curl or fail the JSON parse, never yield a short id list silently.
- No other URL-connection read remains in the render path (grep of README.Rmd and scripts/*.R: the remaining `fromJSON` calls parse local files or strings).
- Tests: ran `testthat::test_file("tests/readme_functions_test.R")` in a temp copy of scripts/ and tests/: 14 tests, 0 failed, 0 errors. Test 1 would fail if the function read the URL directly (`got` stays NULL); both tests check the temp file is removed.
