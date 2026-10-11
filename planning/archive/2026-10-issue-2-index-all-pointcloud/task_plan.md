# Task: Index the rest of pointcloud/*.laz (165,667 files) (#2)

**If we do it:** the collection covers every LidarBC point cloud, not just the 11 mapsheet-years of the first increment. **If we never do:** stac-pointcloud-bc stays a partial index of 9,649 of 175,317 files.

## Phase 1: Whole-bucket listing

- [x] Replace `INCREMENT` with a walk per block (the `NTS_BLOCKS` prefixes) in `listing()`.
  - Keep only `<block>/<sheet>/<year>/pointcloud/*.laz`.
  - A key that `key_parse` refuses fails the walk, with the key named.
  - A `.laz` under a block outside `NTS_BLOCKS` is refused.
- [x] Record the per-group counts in a committed `data/pointcloud_groups.json`.
  - A recorded group listed under 90% of its count is refused.
  - A new group is logged, not refused, so the monthly update (#4) is not blocked by growth.
  - A `--groups-record` flag rewrites the file.
- [x] Tests: a short group is refused, a new group passes, a key off the pattern raises, an
  unknown block raises. The listing is mocked.
- [x] Measure: run the listing once and record the totals and the group count. Check against
  175,317 and the 9,650 of the increment.

## Phase 2: Item changes (pure, in `laz_item.py`)

- [x] `item_create` sets `lidarbc:delivery = "<block>/<sheet>/<year>"` from the key, and
  refuses a value that does not match `^[0-9]{3}/[0-9]{3}[a-p]/[0-9]{4}$`.
- [x] Items list both crate schema URLs in `stac_extensions`. The collection lists the
  `lidarbc` one, for `summaries.lidarbc:product`. The URLs are constants in `laz_item.py`.
- [x] The build refuses any item or collection that writes a `lidarbc:` or `las:` key
  without its schema URL. Prove that the guard fires by mutation.
- [x] The collection gets a `related` link to stac-elevation-bc. Changed at review (G9): the
  shape stac_dem_bc#55 already writes back, its S3 `collection.json`, before the item links.
- [x] Update `ITEM_PATHS` and `COLLECTION_PATHS` in `tests/test_laz_item.py`, plus
  `FIELDS_CUSTOM`, and add a test for each branch that writes a key.

## Phase 3: Class check moves into the build

- [x] Re-measure the screen. Compute the density percentile within each mapsheet-year from the
  headers.
  - Sample a random 5% (fixed seed) of the files above the 10th percentile, then read whole
    whatever that sample flags.
  - Any confirmed ground-only or no-ground file above the threshold is a miss. If there are
    misses, widen the screen to the smallest percentile that catches them all, and record it.
  - Write the result into `research/laz_classes.md`.
- [x] Build step: select the screen from the headers (the 10th percentile within each
  mapsheet-year, unless re-measured), then sample those files, then read whole what the
  samples flag. Reuse the probe's functions:
  - `item_probe`, `full_probe`, `probe_all`, `confirm_work`, `record_good`.
  - Also its caches: `classes.jsonl` and `classes_full.jsonl`.
  - `laz_classes_probe.py` stays as the research and `--summary` tool, importing the same
    functions.
- [x] Replace the `CLASSES_READ` count pin with a derived check. The build refuses unless:
  - every screened file has a good sample record at its current ETag, and
  - every file that sample flags has a good whole-file record at its current ETag.

  That keeps "missing, short or stale" refused without per-group numbers. Prove each refusal
  by mutation.
- [x] Update the `CLAUDE.md` source facts and the `CLASSES_READ` mentions.

## Phase 4: COPC pairs, dates and scale

- [x] Let the build measure pairs over all groups, check each one's header (as now), and record
  the new `COPC_PAIRS` per group. Expect about 14,000, against the 13,996 name matches.
- [x] Record which deliveries `groups_with_untrusted_dates` now flags. Check that the 4 known
  ones are among them and name any new ones.
- [x] Triage new header faults through `EXCLUDE`, one entry per file with its reason.
  - If more than a handful share one fault, stop and report rather than listing hundreds of
    entries.
  - Done: 10 single-file entries. 2,008 vertical-first compound CRSs read swapped
    (`compound_reorder`). 985 files in 8 deliveries with no CRS at all are held out by
    `EXCLUDE_DELIVERIES`; decided: they stay out of 0.3.0, and #15 indexes them from the DEM CRS.
- [x] Run validation in a process pool, timed. Record peak memory for about 175k items.
- [x] Generalise `copc_pairs_measure.py --published` (landed as `scripts/catalogue_compare.py`,
  which exits 1 on anything unexpected and compares the collection too):
  - map `nge:` to the new names (from #12's table);
  - remove the changes this release expects:
    - the `lidarbc:delivery` key,
    - the `stac_extensions` additions,
    - `classification:classes`,
    - `copc` assets on new pairs;
  - report any remaining difference, which should be none.

## Added at plan review (planning/active/review-plan.md)

- [x] Listing-time checks before any header read (O1, G10, G11a, A4): every `.laz` parsed,
  NTS letter, file-name charset, sheet in block, duplicate ids, pairs, date tokens; faults
  aggregated into one refusal.
- [x] `item_create` refusals aggregated by fault class (G5); bad date tokens named (G6).
- [x] `--groups-record` refuses to lower a floor without `--force` (G11b); `COPC_PAIRS` moved to
  committed `data/copc_pairs.json`, recorded by the same flag (G12).
- [x] Derived class check covers every flagged sample, screened or not, and runs under
  `--limit` (G3).
- [x] Early validation of one item per group; pooled validation of all (O2); CRS transformer
  cached (O5).
- [x] `laz_classes_probe.py --audit FRACTION --seed` for the screen audit, with a pass condition
  (zero confirmed misses) and a 95% bound (G2).
- [x] Rewrite the sampling claim in the collection description, CLAUDE.md and NEWS (G4).
- [x] Tell stac_dem_bc that `lidarbc/v1.1.0` 404s (A2): comment on stac_dem_bc#55 (2026-10-11 00:04Z).

## Phase 5: Full build and documents

- [x] Run the full build in the background, then the class steps, then build until green.
  Logs go to `logs/`.
- [x] Run the published-vs-build check against a copy of the 0.2.0 bucket. The 9,649 ids
  should differ only by the expected changes, and the rest should be new.
- [x] Update `research/laz_classes.md`, `research/README.md` if needed, and the `CLAUDE.md`
  source facts.
- [x] Re-derive the collection `DESCRIPTION` claims from the build. Today it says that most
  of the listed items hold no ground.
- [x] `NEWS.md` 0.3.0: the counts, each `nge:` → new name pair, the delivery key, the class
  lists, and the screen.
- [ ] `README.Rmd`: the field names, the counts, and the 0.2.0 `nge:` note. Re-render with its
  `build` chunk.

## Phase 6: Publish (after your explicit go)

- [x] Run `scripts/s3_sync.sh --dryrun`, and report the counts: 174,283 uploads (174,282 items
  + `collection.json`), 0 deletes (`logs/20261011_1320_s3_sync_dryrun.log`, after the last rebuild).
- [ ] **Ask.** Then stamp the version (`collection_version.py`), run the sync, then
  `stacs register`, then `stacs verify`. The verify must report IN SYNC: id sets equal in both
  directions and every body digest-equal.
- [ ] Record the publish in `NEWS.md`.

## Validation

- [x] Tests pass (`uv run pytest`): 255
- [x] `/code-check` clean (once over the branch with `/code-check branch`): four rounds, ended by
  enumeration (progress.md)
- [x] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
