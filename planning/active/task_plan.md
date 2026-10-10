# Task: Some point clouds hold ground returns only, and nothing in the item says so (#10)

**If we do it:** a user knows, before reading a tile, whether it carries vegetation and buildings or ground returns only. **If we never do:** someone builds a canopy model from a search result and gets nothing above the ground for some tiles, with no hint why.

## Phase 1: Class probe script (tests first)
- [x] Tests in `tests/test_laz_classes.py`: tally of a known LAZ (written by laspy with set
  classes) read through the local range server; verdict function on class-count dicts
  (ground-only, mixed, empty sample); spread sample seeks to chunks beyond the first
- [x] `scripts/laz_classes_probe.py`: per item, from `data/build/items`
  - `laz`: first 100k points → class counts, bytes, seconds
  - also one 50k chunk at each of 25/50/75% (`seek`), for **every** file, not only the
    flagged ones: it costs ~1.9 MB and ~2 s a file, and it measures how often the first
    points alone mislead (findings, "Sampling design")
  - `copc` (1,964 items): octree levels 0–1 (not 0–2: 3.2 MB vs 11 MB on a 17M-point
    tile) → class counts, bytes
  - one jsonl record per item in `data/build/classes.jsonl`, resumable (reuse
    `cache_tail_repair`); every failure recorded, none dropped
- [x] Verdict defined as the class set, reported in full; "ground-only" = no point in any class
  outside {2, 7, 9, 18} (ground, noise, water, high noise), with the distinct class sets
  tabulated so the definition's spread is visible

## Phase 2: Measure the 9,649
- [x] Smoke: `092g028_1_1_1` reads ground-only on all three samples; a neighbour reads mixed
- [x] Full run in the background from a frozen copy, log `logs/<ts>_laz_classes_probe.log`
- [x] Summary (in the script, `--summary`): ground-only count per mapsheet-year and per
  delivery; distinct class sets; first-points vs COPC agreement on the 1,964 (confusion
  table); spread-chunk confirmations; bytes and seconds per file → projected cost for #2's
  165,667
- [x] `research/laz_header_read.md` section revised with the numbers (or a new
  `research/laz_classes.md` if it outgrows the section), `research/README.md` row
  (new file `research/laz_classes.md`; header-read section points to it)
- [x] Added in the run: "no ground" verdict (no class 2) confirmed by full read too — the
  sample found 70, more consequential for DEM users than ground-only
- [ ] Issue #10 body edited with the result

## Phase 3: Decision — user's (gate)
- [ ] Report the numbers with two or three options, recommendation first:
  collection-level note naming ground-only deliveries; item property (`nge:classes` +
  `nge:classes_sample` saying how it was sampled, not `pc:statistics`); or both
- [ ] Phase 4 tasks fixed by the answer; Phases 1–2 do not depend on it

## Phase 4: Implement the chosen representation
- [ ] Tests first, then `laz_item.py` / `catalogue_build.py` (collection description or item
  property; its own cache, not a `HEADER_VERSION` bump)
- [ ] Rebuild; `copc_pairs_measure.py --published`-style body diff shows only the intended
  change; NEWS entry. Publishing/registration left for the user's go (or folded into #2)

## Validation
- [ ] Tests pass (`uv run pytest`)
- [ ] `/code-check` clean (once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion

