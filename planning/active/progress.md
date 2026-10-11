# Progress — Index the rest of pointcloud/*.laz (165,667 files) (#2)

## Session 2026-10-10

- Plan-mode exploration — phases approved by user
- Decisions at the gate: screen checked on a random 5% of unscreened files; publish on this branch only after explicit go
- Created branch `2-index-the-rest-of-pointcloud-laz-165-667` off main
- Scaffolded PWF baseline from issue #2 with approved phases
- Plan review (Plan agent) returned; triaged in `review-plan.md`, its gaps folded into the code
- Whole-bucket walk: 233 groups, 175,278 `pointcloud/*.laz`; recorded `data/pointcloud_groups.json`
  and `data/copc_pairs.json` (28 groups, 13,996 pairs) with `--groups-record`
  (`logs/20261010_2346_catalogue_build_groups_record.log`)
- Phases 1-2 done; Phase 3-4 code done (class step in the build, derived check, audit, pooled
  validation, catalogue_compare.py); 12-guard mutation table all red
- Next: the full build (cold headers ~165.6k), triage faults, then the audit

## Session 2026-10-11 (overnight)

- Full build `logs/20261011_0525_catalogue_build_full.log` (05:05Z to 08:55Z, 13,749 s, peak RSS
  4.13 GB): 174,282 items; 13,970 `copc` assets over 28 groups; 17,552 of 174,282 screened at the
  10th percentile; exit 1 on 6 transient sample failures (findings, Errors).
- Review round 1 (`review-round1.md`): no bugs, three fragile. Fixed two: `exclusions_check`
  also re-runs `item_create`, so an entry fixed outside its `mins` stops the build; class lists
  outside the screen come from the committed `data/classes_required.json` (`--classes-record`),
  not the gitignored cache. The third (`blocks_list` drops non-block prefixes) is accepted.
- #15 filed for the 985 no-CRS files; `EXCLUDE_DELIVERIES` cites it.
- 5% audit started (`logs/20261011_0900_laz_classes_audit.log`).
- Review round 2 (`review-round2.md`): one bug and two fragile, all inside round 1's
  class-list fix. The bug: `--classes-record --limit` rewrote the committed list from a slice.
  Fragile: recording could shrink the list, and whole reads outside the screen with no flagging
  sample at the current ETag (the #10 survey's samples have none) stayed cache-only. The
  mechanism was a required set derived from current flags, not from what the build publishes.
  Fixed: `--classes-record` refuses `--limit`, only adds ids unless `--force`, and records every
  good whole read outside the screen; `classes_check` refuses any such read the list lacks (not
  under `--limit`, whose screen is partial). 248 tests; six mutants, each caught.
- Review round 3 (`review-round3.md`): three fragile, none affecting today's caches (each
  measured at zero). Mechanism: the published class lists (every good whole read in the local
  cache) and the lists an empty `data/build` would publish were assumed equal and compared
  only outside the screen; and a cached sample was "good" on the laz ETag alone though its
  flags count the item's COPC. Fixed structurally: `classes_published` (the screened files a
  current sample flags, plus `CLASSES_REQUIRED`) drives the whole reads, `classes_check` and
  what `classes_attach` applies, so a cache can only speed a build up. A stale read outside it
  is neither re-read nor applied. Samples must match the item's COPC (`sample_good`,
  `probe_all(match_copc=True)`). `--classes-record` records after the reads. Residuals
  accepted: a COPC re-delivered under the same href, and a cache record whose id disagrees
  with its URL (0 of 340). 253 tests; 12 mutants over rounds 2 and 3, each caught.
- Review round 4 (`review-round4.md`, on 9884d5a alone): one bug inside round 3's fix and one
  latent fragility. Bug: `--classes-record --force` dropped a listed required id whose re-read
  failed in that run, and the build then passed with no list. Fixed: `--force` drops only ids
  no longer listed or now screened and flagged. Fragile: `targets_load` gave the probe a raw
  COPC href where the build's items carry `href_encode`'s (equal today for all 13,970); now
  encoded alike. `confirm_work`'s docstring no longer claims the build uses it. The claim
  9884d5a rests on was measured on the real caches and held (338 published ids, none without
  a good read; no screened read outside the published set).
- Ended by enumeration, not a fifth round. The publish path has one writer (`classes_add` <-
  `classes_attach`), fed only ids in `classes_published`. The one committed write
  (`--classes-record`) was enumerated per id: an old id not listed, or now screened and
  flagged, is dropped only with `--force`; any other old id is always kept, and is refused
  without a good read; a new id enters only as a flag outside the screen or as a good read
  not screened and flagged. Each arm has a test that a mutant turns red.
- 5% audit (`logs/20261011_0900_*`, retry `_1005_*`): 7,836 picked, 7,834 sampled (2 files the
  sampler cannot read: findings), 9 flagged, 2 confirmed misses, one at the 96th density
  percentile of its group, so the plan's "widen the screen" cannot catch it. Put to the user
  (findings); proceeding with the screen plus the audit's reads.
- Build with `--classes-record` (`logs/20261011_1010_*`, 53 min, exit 0, peak RSS 3.96 GB):
  174,282 items validated in 768 s; 17,552 screened, 347 flagged, 349 read whole;
  `data/classes_required.json` records 11 ids (9 audit flags, the #10 survey's 2 reads).
  Published lists: 12 ground-only, 253 no ground, 84 mixed (`logs/20261011_1100_*` summary).
- Collection DESCRIPTION re-derived (G4): the screen and the random 5%, and that a few unlisted
  items hold no ground too.
- Final build (`logs/20261011_1115_catalogue_build_final.log`, 53 min, exit 0, peak RSS
  4.08 GB): 174,282 items, validated in 765 s. `catalogue_compare.py` against the 0.2.0 bucket
  (`logs/20261011_1200_catalogue_compare.log`): exit 0; all 9,649 still built, 0 differing
  beyond this release's changes, 164,633 new (12,006 with `copc`). `copc_pairs_measure.py`
  (`logs/20261011_1200_copc_pairs_measure.log`): 13,970 pairs, largest offset 0.01 m.
- Docs: NEWS 0.3.0, research (classes, CanElevation), CLAUDE.md source facts, README.Rmd prose
  (its render waits on the publish: it reads the live API), code comments' counts.
- `scripts/s3_sync.sh --dryrun` (`logs/20261011_1215_s3_sync_dryrun.log`): exit 0; 174,283
  uploads (174,282 items + `collection.json`), 0 deletes. Not published: that waits on the
  user's go.
- Docs fact-check (`review-docs.md`, about 60 numbers re-derived): two wrong, one wrong
  population, one mislabelled cost, one unsupported, minors; all fixed. It also found that
  10,603 items named with two days (`_20250509_20251014`) published the second as their single
  `datetime`. GPS times of 16 such files (8 deliveries, a sample at 0%, 50% and 95%) all fall
  between the two days, so they are the first and last day flown: now
  `start_datetime`/`end_datetime`. A pair outside the directory year, or out of order, gets
  the year range (source `path`). Untrusted deliveries unchanged at 42. 258 tests; three
  mutants caught. The `EXCLUDE_DELIVERIES` DEM-CRS claim's evidence is #15's body.
