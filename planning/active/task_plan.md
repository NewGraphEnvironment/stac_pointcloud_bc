# Task: Some point clouds hold ground returns only, and nothing in the item says so (#10)

**If we do it:** a user knows, before reading a tile, whether it carries vegetation and buildings or ground returns only. **If we never do:** someone builds a canopy model from a search result and gets nothing above the ground for some tiles, with no hint why.

## Phase 1: Class probe script (tests first)
- [ ] Tests in `tests/test_laz_classes.py`: tally of a known LAZ (written by laspy with set
  classes) read through the local range server; verdict function on class-count dicts
  (ground-only, mixed, empty sample); spread sample seeks to chunks beyond the first
- [ ] `scripts/laz_classes_probe.py`: per item, from `data/build/items`
  - `laz`: first 100k points → class counts, bytes, seconds
  - where that sample is ground-only: also ~3 chunks spread through the file (`seek`), so a
    no-COPC verdict is not one strip
  - `copc` (1,964 items): octree levels 0–2 → class counts, bytes
  - one jsonl record per item in `data/build/classes.jsonl`, resumable (reuse
    `cache_tail_repair`); every failure recorded, none dropped
- [ ] Verdict defined as the class set, reported in full; "ground-only" = no point in any class
  outside {2, 7, 9, 18} (ground, noise, water, high noise), with the distinct class sets
  tabulated so the definition's spread is visible

## Phase 2: Measure the 9,649
- [ ] Smoke: `092g028_1_1_1` reads ground-only on all three samples; a neighbour reads mixed
- [ ] Full run in the background from a frozen copy, log `logs/<ts>_laz_classes_probe.log`
- [ ] Summary (in the script, `--summary`): ground-only count per mapsheet-year and per
  delivery; distinct class sets; first-points vs COPC agreement on the 1,964 (confusion
  table); spread-chunk confirmations; bytes and seconds per file → projected cost for #2's
  165,667
- [ ] `research/laz_header_read.md` section revised with the numbers (or a new
  `research/laz_classes.md` if it outgrows the section), `research/README.md` row
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

