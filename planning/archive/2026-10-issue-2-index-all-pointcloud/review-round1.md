# Code review, round 1: branch 2-index-the-rest-of-pointcloud-laz (be4bfbd...HEAD, scripts + tests)

Reviewed in full: scripts/catalogue_build.py, scripts/laz_item.py, scripts/laz_classes_probe.py,
scripts/catalogue_compare.py, scripts/copc_pairs_measure.py, tests/*.py (diff and current files).
`uv run pytest -q`: 239 passed. Read-only probes against data/build caches (nothing written).

## Findings

- **[fragile] scripts/catalogue_build.py:132-204, 499 — the EXCLUDE fingerprint is `mins` only, and for two entries the recorded fault is not in `mins`, so the "file was fixed" guard cannot fire.**
  The comment at 127-131 says that if the header no longer shows the fault, the build stops. But
  `exclusions_check` compares only `mins`:
  - `bc_092h011_1_2_2_xyes_4_utm10_2021.laz`: the fault is in `maxs` (easting 3,263,847). A
    re-delivery with the max corrected keeps mins `[578450.42, 5439128.86, 15.14]`.
  - `bc_093n052_1_2_3_xyes_8_utm10_2021.laz`: the fault is the declared CRS (UTM 9N where the
    data is UTM 10N). A re-delivery with the CRS corrected has the same coordinates, so the same mins.
  - `bc_092k005_...` (1 point) is probably caught, because a real re-delivery would move its min,
    but it is only "probably".
  In each case the good file is excluded on every later build, with only a WARNING line.
  Measured: with a header carrying the recorded mins and a corrected `maxs` (579900),
  `exclusions_check` returns the url as excluded and does not raise. All 11 recorded mins do
  equal the current header cache, so today the check passes as intended.
  Fix: fingerprint by the fault, not by one field. Require that `item_create(u, headers[u], ...)`
  still raises ValueError. All 11 current entries raise there: the box sides, the centre outside
  its sheet, or zero points. Pinning the listing ETag would also work.

- **[fragile] scripts/catalogue_build.py:618-640 (classes_check), 840-846 — class lists for files outside the density screen depend on caches nothing records. If the caches are absent, those lists drop with no error.**
  The derived check can require a whole-file read only for files flagged by a sample present in
  `classes.jsonl`. It re-creates samples for screened files only. Two kinds of file sit outside
  the screen:
  - files flagged by `--audit`, or by any earlier survey sample;
  - files that already have a good record in `classes_full.jsonl`.
  If either cache is missing (`data/build/` is gitignored, so on a fresh machine, CI, or after a
  cleanup), their `classification:classes` vanish and the build passes. The removed `CLASSES_READ`
  pin is what used to refuse that.
  Measured on the current caches (9,649 targets): 971 screened, 73 good whole reads, and 2 of
  those 73 are outside the screen. Neither is ground-only or groundless, so the loss today is two
  mixed-class lists. The case that matters is an `--audit` miss: a confirmed ground-only or
  groundless file outside the screen. That is exactly what the audit exists to find, and its
  list would silently disappear on a cache-less rebuild.
  `catalogue_compare` would catch it only against a release that already published the list.
  Fix: commit the ids that must carry a list (the audit's misses, and any flagged file outside
  the screen), as `copc_not_copies.json` is committed, and refuse a build where one lacks a good
  whole read.

- **[fragile, low] scripts/catalogue_build.py:263-281 (blocks_list) — a top-level directory that is not three digits is skipped without a word.**
  The function raises on an unknown 3-digit block because skipping "would drop a delivery without
  a word". Yet `re.fullmatch(r"\d{3}/", p)` drops any other root prefix silently, and neither the
  group floors nor the per-block `pointcloud_select` faults can see keys that were never listed.
  It drops nothing today: CLAUDE.md's walk puts all 181,708 .laz under `<block>/...`. A
  restructured or newly added root directory would be missed with exit 0. Fix: raise (or at least
  list it) on any root prefix that is not a known block, or list the root's non-block prefixes for
  `.laz`.

## Checked and found sound (no action)

- `compound_reorder`: handles quoted commas and brackets, and doubled `""` escapes (the toggle runs
  twice). Nesting depth is right. Anything other than `COMPD_CS[` with VERT_CS second returns None,
  so the original CRSError is raised (loud). laspy strips the trailing NUL from the WKT VLR, so
  `.strip()` suffices.
- EXCLUDE_DELIVERIES: the check fires if any file in the delivery gains a `crs_wkt`. All 11 EXCLUDE
  mins match the live header cache exactly.
- COPC_NOT_COPIES: both point counts are re-checked. Non-copies are popped from `pairs` before
  `class_targets_write`, so neither the targets nor the class sampler see a non-copy COPC.
- copc_pairs_check / records_write: exact per-group equality. Both files are checked before either
  is written. A vanished group counts as steep.
- groups_check: a recorded group listed at 0 is refused. A new group is built and logged, as
  designed.
- page_get: 4xx is returned and then refused by the caller; the last 5xx is returned and refused;
  the last connection error is raised. A retry reuses the same marker or token, so no keys are
  skipped.
- validate_all: errors other than STACValidationError propagate out of `ex.map`, so the build
  fails loudly. Each worker preloads the crate schemas.
- catalogue_compare: each expected change is asserted and then removed. A copc asset gained or
  lost, any other field, an extension added beyond the allowed ones or lost, and a missing
  published id all fail with exit 1. 0.2.0 published no class lists (NEWS), so popping them only
  on the build side is correct for this release.
- Date trust is per delivery, computed on the full listing before `--limit`. A non-date token
  stops the build with every file named.
- `--limit` writes only to data/build-limit (tested).
