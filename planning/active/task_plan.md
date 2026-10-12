# Task: README render: read the 35 MB collection.json to a file, not through R's 60 s URL timeout (#18)

**If we do it:** the README render survives a slow link. **If we never do:** a render on a slow connection (or in the monthly update, #4, if it renders) fails after the 19-minute API fetch, with an error that names `readBin`, not the timeout.

## Phase 1: Tests first (`tests/readme_functions_test.R`)
- [ ] Test: `pc_readme_bucket_json(fetch = fake)` calls `fetch` once with
      `<BUCKET_URL>/collection.json` and a local path, parses the file `fake` writes (a small
      inline collection with two `rel: item` links, one with `%20`, one `rel: self`), and
      returns `ids` (decoded, `.json` stripped, item links only) and `version`
- [ ] Test: an error raised by `fetch` propagates, and no temp file is left behind
- [ ] Confirm both fail against the current code (function absent)

## Phase 2: Read through a file (`scripts/readme_functions.R`)
- [ ] New `pc_readme_bucket_json(fetch = pc_readme_fetch_file)`: tempfile, `on.exit(unlink)`,
      `fetch(paste0(BUCKET_URL, "/collection.json"), tmp)`, `jsonlite::fromJSON(tmp,
      simplifyVector = FALSE)`, return `list(ids, version)`; roxygen note says why (35 MB,
      R's 60 s URL timeout, #18)
- [ ] `pc_readme_bucket()` keeps its signature and return shape; calls the new helper
      for the bucket side, rstac for `api_version` as now
- [ ] Tests pass: `Rscript -e 'testthat::test_file("tests/readme_functions_test.R")'`

## Phase 3: Verify live, and the issue body
- [ ] Live: `pc_readme_bucket()` once; its ids equal the ids in `data/readme_cache.rds` as
      sets in both directions, and `version` equals the cache's (no full 19-min render)
- [ ] Edit issue #18's body: fix uses the existing `pc_readme_fetch_file()` (httr2), not
      `curl`, and why

## Validation
- [ ] Tests pass
- [ ] `/code-check` clean (once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion

## Notes from planning

#19 added `pc_readme_fetch_file()` (httr2, no total timeout, low-speed abort, raises on HTTP error status), so the fix reuses it rather than adding `curl` as the issue prescribed. No `scripts/DESCRIPTION` change.
