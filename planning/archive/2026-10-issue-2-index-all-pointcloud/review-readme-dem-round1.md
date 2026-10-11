# Review: readme_dem.py delivery-year fix, round 1

**Date:** 2026-10-11 · **Diff:** scripts/readme_dem.py, tests/test_readme_dem.py (uncommitted)

## Clean

No issues found.

## What was checked

- **The fix is needed, and it works against the live API.** A read-only window search
  (`window_items` at the Kanaka mouth, EPSG:3157) returns 8 items, not the 4 in the committed
  `data/readme_dem.json`:
  - 4 x `092/092g/2016`, `copc` + `laz`, year-dated (`start_datetime` 2016-01-01,
    `end_datetime` 2016-12-31, `datetime_source: path`)
  - 2 x `092/092g/2024`, `laz` only, range 2024-02-17 to 2025-04-25
  - 2 x `092/092g/2025`, `laz` only, one day (`datetime` 2025-04-25, no `start_datetime`)

  The old `i.properties["start_datetime"][:4]` raises `KeyError` on the two 2025 items, so
  the demo cannot run on 0.3.0 without this change. With it, `flight_year` returns 2016 for
  the mouth item (the only `copc` item at the point: the 2024 item there is laz-only and is
  filtered out first), and the filter keeps exactly the same 4 ids as the committed JSON.
  Every item in the window carries `lidarbc:delivery`.
- **Delivery year vs the old date year: no change in selection.** For every item that had
  `start_datetime`, its year equals the directory year (ranges begin in it; year-only items
  span it; the 9 disagreeing deliveries carry the directory year). So the switch selects the
  same items wherever the old code ran, and additionally runs where it crashed.
- **Failure direction.** An item without a well-formed `lidarbc:delivery` anywhere in the
  window raises `ValueError` and aborts the render (README.Rmd stops on the non-zero exit),
  rather than being silently dropped. Fails toward fail.
- **Other readers of the date fields.** `scripts/readme_functions.R` and `README.Rmd` read no
  `datetime`/`start_datetime`/`end_datetime`; `group` there is taken from the laz href path.
  `catalogue_build.collection_build` already branches on `i.datetime`. Nothing else broken.
- **Tests:** `tests/test_readme_dem.py` 10 passed (run with caches disabled).

## Observations, not defects (pre-existing, unchanged by this diff)

- The filter is by **year**, not by delivery, while the comment at line 104-106 says "read
  only its delivery". `lidarbc:delivery` is `<block>/<sheet>/<year>`, so a window crossing a
  sheet edge with two same-year deliveries would read both. The old code did the same, and
  the current window lies wholly in 092g, so nothing changes today. Filtering on
  `i.properties["lidarbc:delivery"] == at_mouth[0].properties["lidarbc:delivery"]` would match
  the comment exactly but would then drop adjacent-sheet tiles of the same flight; which is
  wanted is a choice, not a bug.
- The live data shows one acquisition split across year directories: 092g018 tiles under
  `2024/` (20240217_20250425) and 092g028 tiles under `2025/` (20250425). If a later release
  gave those `copc` assets and the demo picked them, a directory-year filter would read only
  half the window. Neither old nor new code handles that; today those items are laz-only and
  never chosen.
- The rerendered page will report 8 items found and 4 used ("from more than one flight"),
  since 0.3.0 indexed the 2024 and 2025 deliveries. That is the README's existing branch
  working as intended.
