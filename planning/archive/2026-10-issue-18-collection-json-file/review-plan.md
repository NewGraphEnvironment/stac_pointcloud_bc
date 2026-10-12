# Plan review — #18 (Plan agent, 2026-10-12)

Returned as reply text (Plan agents cannot write); condensed here.

- **Blocker, accepted:** Phase 3's check compared ids with `data/readme_cache.rds`, which holds no ids
  (`version`, `fetched_at`, `groups`, `rows`, `example`). Confirmed by the first live run
  (`c0$fetch$items: $ operator is invalid`). Check revised: new read vs the old `fromJSON(url)` read under
  `options(timeout = 1800)`, as sets both ways, plus the cache's `sum(groups$items)` and `version`.
- **Acceptance, accepted:** no test shows the timeout is gone. Added a live control (`pc_readme_bucket()`
  under `options(timeout = 5)`; the old read fails under the same setting) and a grep for
  `fromJSON(paste0(BUCKET_URL` (none left).
- **Acceptance, accepted:** the success test now records the path, checks it is under `tempdir()`, and
  that it is gone after the call.
- **Gap, accepted (issue text):** `pc_readme_fetch_file()` aborts below 10 kB/s for 120 s; the issue
  edit says so.
- **Gap, declined:** a guard for a `fetch` that returns without writing. The real fetch writes or raises.
- **Out of scope, reported:** `withr` used by the tests but not in `scripts/DESCRIPTION` Suggests (it was
  already the case before this work); `pc_readme_fetch()` reads the bucket only after its 19-min fetch.
- **Assumptions checked by the reviewer:** no other R URL-connection read in the render path (rstac uses
  httr, bcdata crul, header read httr2; README.Rmd's other `fromJSON` calls parse strings or local files).
