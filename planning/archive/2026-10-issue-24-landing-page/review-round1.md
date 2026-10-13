# Code-check round 1 — branch 24-landing-page-say-why-it-is-useful-first (base 9c0a9f6)

Reviewed 2026-10-13. Scope: README.Rmd, maintaining.md, scripts/readme_functions.R,
tests/readme_functions_test.R, plus the claim ledger in planning/active/findings.md.

## What was run (in a copy, scratchpad/rcopy, from `git archive HEAD`)

- `testthat::test_file("tests/readme_functions_test.R")`: 12 tests, 0 failed, 0 errors.
- Both renders with `update_query = FALSE` against the committed `data/readme_cache.rds`
  (old shape, still carrying `groups`): github_document and html_document both rendered
  without error. Nothing still refers to `groups`, `n_items`, `n_copc`, `all`, `BUCKET_URL`,
  `pc_readme_fetch` or `pc_readme_bucket*` (grep across *.R, *.Rmd, *.py, *.sh, *.yml, *.md
  outside planning/archive).
- `<details>` blocks: markdown, code and the kable inside them render in both outputs.
  `#which-classes-a-file-holds` resolves: `id="which-classes-a-file-holds"` is in the html, and
  GitHub derives the same slug from the `###` heading.
- `%||%`: base R since 4.4; R here is 4.5.2. `pc_readme_rows()` already used it, so the
  change adds no new requirement.
- `pc_readme_version()`: the live collection returns `version: "0.3.0"`; a missing version
  becomes `NA_character_`, and line 207's `is.na()` branch handles it.
- Checked against code or live service: extensions list (live item `stac_extensions` =
  lidarbc, las, pointcloud, projection, file; classification added through
  `ClassificationExtension.ext(asset, add_if_missing=True)`), four CanElevation projects
  (`CANELEVATION_PROJECTS`), eight 2017 deliveries (`EXCLUDE_DELIVERIES`), 0.05 m pairing,
  years 2012–2026 (`data/pointcloud_groups.json`), `related` link to stac-elevation-bc
  (live), DEM/CHM inline text against `data/readme_dem.json` / `data/readme_chm.json` (the
  8 found / 4 used for 2016 branch, 1 ground-only item, 2 items "both" from 093/093l/2019,
  no copc asserted by readme_chm.R:85), s3_sync.sh (upload by digest, collection.json only
  when an item goes or it changed, deletes nothing), update.yml (cron on the 6th, `dryrun`,
  `MAX_UPLOAD=40000`, no register).

## Findings

No bugs. No security issues. Three small claims the code contradicts, and one stale row in
the ledger the PR body will be built from.

- **[claim]** README.Rmd:192 — "The screen misses a few, so an item without a list has not been
  checked". About 17,500 screened files (0.3.0) were sampled and not flagged. They carry no
  list, but they were checked by their sample. The collection's own description
  (`catalogue_build.py:253`) says it correctly: "An item without that list was not read
  whole". As written, the page tells a reader that every listless item went unexamined.
  Suggested: "an item without a list was not read whole".

- **[claim]** README.Rmd:186 — "An item's date comes from its file name when every name in the
  delivery agrees with its year directory … Otherwise the item spans the directory's year."
  The code distrusts a delivery only when some name carries a date that *disagrees*
  (`catalogue_build.py` `groups_with_untrusted_dates`: `filename_date and source == "path"`).
  A name with no date token does not count against it. So in `092p/2017`, which mixes day
  tokens and no tokens (CLAUDE.md), the files with a token get their day, not the directory
  year, although not every name there "agrees". Suggested: "when no file name in the
  delivery carries a date that disagrees with its year directory".

- **[claim]** README.Rmd:198 — "a few files whose header no item can be built from". Two of the
  11 `EXCLUDE` entries (`bc_093c080_4_4_4_…` under `092b/2023` and `092n/2023`) have a sound
  header. The fault is their path: a 093C tile filed under the wrong sheet
  (`catalogue_build.py:165-170, 201-206`). That is low stakes, but the sentence states a
  reason that is false for those two. Suggested: "a few files whose header, or the sheet
  they are filed under, no item can be built from", or "a few files with a faulty header or
  path".

- **[claim, ledger]** planning/active/findings.md, claim-ledger row "API serves exactly the ids
  collection.json links | readme_functions.R:182-186 setdiff both ways | true". This branch
  deletes that code, and the page no longer makes the claim (the old line "Every id the
  bucket's collection.json links was served by the API" is gone). The plan's done-when says the
  PR lists the checked claims. A PR built from this ledger would cite a check that no longer
  exists. Drop the row, or mark it as removed with `pc_readme_fetch()`.

Not flagged (accepted or checked fine): demo numbers dated by the render; "four
CanElevation projects" and "eight 2017 deliveries"; README.md and index.html not yet
re-rendered; maintaining.md text moved as it stood, with its measurement dates added.
