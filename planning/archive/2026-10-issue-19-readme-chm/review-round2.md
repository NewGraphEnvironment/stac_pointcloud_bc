# Code-check round 2 (#19): branch diff against main

## Clean

No issues found.

Checked, and why each holds:

- **Round 1's fix, the copc guard** (scripts/readme_chm.R): it runs on the delivery-filtered,
  sorted items before any `pc_readme_laz_get()` call, so a release that pairs a COPC stops the
  run before 0.5 GB is fetched. Probed live 2026-10-11: both items
  (`bc_093l040_3_4_{1,2}_xyes_8_utm09_2019`) carry only a `laz` asset, with `file:size`
  241289305 and 291068517, which match the cached files in data/readme_laz/ byte for byte. So
  the committed data/readme_chm.json, written by 67e1941 before the guard existed, still states
  something true ("None of them has a `copc` asset").
- **The mouth point**: BC Geographical Names gives Maxan Creek at -126.12556, 54.38139, which is
  the script's MOUTH_LON/MOUTH_LAT. Bulkley Lake's named point is at -126.1033, east of it, so
  the alt text and prose ("the lake on the east") agree with the geometry and with
  fig/maxan_chm.png.
- **Ordering**: `size` is taken after the items are sorted, so `size[i]` pairs with
  `items[[i]]`'s href; the json's `items`/`laz` are in the same order.
- **pc_readme_chm()**: `!x %in% y` parses as `!(x %in% y)`; the grid built from `b = box ± 2*res`
  gets the expected dimensions (terra, 1202 x 1002 m at 0.5 m gives 2404 x 2004 even with
  non-round origins), so the crop to `box` lands on cell edges; the 4,800,000 cells in the json
  agree.
- **Tests**: rerun in a scratch copy, 11 expectations blocks, 0 failed, 0 errors, 0 skipped. The
  noise and withheld fixtures put an 80 m first return in the cloud, so removing either filter
  would push the max past the 20.1 m bound; they can reach their failure mode.
- README.Rmd: system2 status check, the CHM_JSON added to the missing-cache loop, and the
  `pc_readme_lines()` markers (distinct strings, one pair per file) are sound.

Not raised (style or grammar only, not failures): the prose would read "the 1 items ... all
from" if the window ever covered a single item.
