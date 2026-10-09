# Code review, round 1 (branch 9-readme-rmd-landing-page-served-on-github vs 9a9d02a)

## Findings

- **[severity: fragile]** scripts/readme_functions.R:155,156,162,186 with scripts/DESCRIPTION — `%||%` is
  used unqualified. It is in base R only from 4.4.0, and nothing on the page's search path supplies it
  (README.Rmd attaches only `sf`, which does not export it). `scripts/DESCRIPTION` declares no
  `Depends: R (>= 4.4.0)`, so `pak::local_install_dev_deps("scripts")` succeeds on R 4.1–4.3. The tests
  still pass there because they never reach those lines. The `update_query = TRUE` render then dies in
  `pc_readme_fetch()` / `pc_readme_rows()` with `could not find function "%||%"`. That is after the
  network fetch and before the cache is written. Fix: declare `Depends: R (>= 4.4.0)`, or use
  `rlang::"%||%"` and add rlang to Imports. Checked here on R 4.5.2, where it works.

Nothing else found. What was checked:
- Tests: 24 pass. The LAS offsets (point format at byte 104 with the 0x3F mask, legacy count at 107,
  u64 count at 247, scale/offset/extent at 131/155/179) agree with the LAS 1.4 R15 layout.
- `pc_readme_header()` was run live against the cached example's `laz` and `copc`. Both give the same
  values as the cache. A 404 fails loudly.
- rstac 1.0.1 `items_fetch()` with no `numberMatched` stops only when there is no `next` link (a
  `next_error`). An HTTP error mid-pagination raises rather than truncating. The bucket id-set
  comparison guards the full fetch in both directions.
- Bucket `collection.json`: 9,649 item links, version 0.2.0. 15 ids carry `%20(2)`, and they decode
  the same way as in s3_sync.sh.
- The guards fail toward stop on missing or NA `pc:count` / `proj:bbox`, a NULL version on either
  side, and a group regex that does not match.
- `index.html` and `README.md` show the same cache values (9,649 items, version 0.2.0, 2026-10-09).
  The DT widget id is seeded.
- Pages is configured as legacy, from main at `/`; `.nojekyll` is present.
