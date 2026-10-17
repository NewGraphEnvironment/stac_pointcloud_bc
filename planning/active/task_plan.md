# Task: Sample the point classes of every file (#17)

The build samples point classes only for files at or below the 10th density percentile of their
mapsheet-year (17,552 in 0.3.0) plus a one-off random 5% audit (7,834). The audit found 2 misses in
7,834, so about 38 of the 148,894 unsampled items (5 to 137) hold no ground or only ground and carry
no `classification:classes` list (`research/laz_classes.md`). #17 samples the rest.

Issue body not yet read: GitHub was unreachable from this machine through planning (2026-10-17
18:04 UTC on). This frame is from the repo's own record of #17 (research/laz_classes.md, NEWS 0.3.0,
the #2 archive); the body is fetched and diffed before the PR.

Decided at the plan gate (2026-10-17): the build samples every file, not a one-time research sweep.

## Phase 1: Tests first
- [x] `tests/test_laz_item.py`: the build's class step samples every kept file (replaces
      `test_the_screen_is_the_research_percentile_within_each_group`); a kept file with no good
      sample refuses the build, whatever its density
- [x] A named carve-out for files the sampler cannot read: each entry carries its reason, is
      left without a list, and refuses the build if it now samples good or leaves the build
      (same shape as `EXCLUDE`)
- [x] The collection description names no percentile and no audit, and says every file was sampled
- [ ] Restore each defect (screen back to 10%, carve-out entry that now reads) and see each test go red

## Phase 2: Build samples everything
- [x] `scripts/catalogue_build.py`: `screened` becomes every kept file minus the carve-out;
      drop the `density_screen`/`SCREEN_PERCENTILE` imports and the "screened" log wording
- [ ] Carve-out `CLASSES_UNREADABLE` in `catalogue_build.py`: `082e075_1_4_3` and `094j045_3_3_4`
      (lazrs "no chunks available in chunk table", research/laz_classes.md), each with its ETag.
      Plan review B1: a whole read uses the same parallel lazrs backend, so it is no trial; a
      sequential-backend read is a follow-up, not this issue
- [x] `classes_check` / `classes_published` docstrings and messages; `--classes-record` help text
      (an audit flag is now derived, so `--force` drops it)
- [x] `scripts/laz_classes_probe.py`: keep `density_screen`, `audit_select` and `--audit` for the
      research record; comment that the build no longer uses the screen
- [x] `COLLECTION_DESCRIPTION` rewritten for sampling every file
- [x] `maintaining.md`: drop "growth moves its density screen"; a monthly run samples new files

## Phase 3: The sweep (local, ~20 h)
- [ ] Commit, `cache_sync.sh pull`, then `PYTHONUNBUFFERED=1` build `--workers 16` to a log under
      `logs/`; re-run until no sample fails for a transient reason
- [ ] `--classes-record --force`: the audit's 2 ids and other now-derived ones leave
      `data/classes_required.json`; commit it
- [ ] Measure: files sampled, flagged, read whole, lists published, by verdict; the audit's two
      misses now flagged; how many new lists the screen missed (against the ~38 estimate)
- [x] `catalogue_compare.py` taught the expected #17 diff (new `classification:classes`, its
      `stac_extensions`, the description), with its tests (plan review B2)
- [ ] `catalogue_compare.py` against the published catalogue: only class lists and the collection change
- [ ] `cache_sync.sh push` (**before merge**: a monthly run on code that samples everything and a
      cache that lacks the sweep would try 148k samples and hit its 240-min limit)

## Phase 4: Record
- [ ] `research/laz_classes.md` revised in place: the full sample's verdicts, cost, what the screen
      missed (by density percentile), what it still does not establish; header line and README row
- [ ] Classes across the collection from every file rather than the audit's 5% (the class 1 / 3–5 / 12 shares)
- [x] `README.Rmd` (renders README.md, index.html): the "build samples the least dense files"
      paragraph; `scripts/cache_sync.sh` cold-cost comment; maintaining.md cache size and the
      monthly ceiling of about 20k new files (plan review G1, CI cost)
- [ ] Push the cache and merge back to back, with no monthly run between (plan review O1)
- [ ] `NEWS.md` entry; `CLAUDE.md` source-facts bullet on classes (above the marker) with measured numbers
- [ ] `tests/test_laz_item.py` `ITEM_PATHS` unchanged (no new field), confirmed by the suite

## Validation
- [ ] Tests pass
- [x] `/code-check` clean (each commit, or once over the branch with `/code-check branch`): 3 rounds over 3b8e543...2c28b34, ended by enumeration; the sweep's own changes get a further round
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
