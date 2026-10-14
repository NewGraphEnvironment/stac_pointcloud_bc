# Progress — Release 0.4.0: publish the rounded footprints (#22)

## Session 2026-10-14

- Plan-mode exploration; phases approved by the user ("go all phases").
- Created branch `22-release-0-4-0-publish-the-rounded-footpr` off main (`2e6b784`, after #27).
- Scaffolded the PWF baseline from issue #22 with the approved phases.
- Started Phase 2's build early, since it reads nothing Phase 1 edits: caches pulled
  (headers 175,318, copc 13,996, classes 35,053, classes_full 349 lines), build launched
  2026-10-14 03:56 UTC, `logs/20261014_0400_catalogue_build_v0.4.0.log`.
- Next: Phase 1 (the compare) while the build runs.
- Plan review (Plan agent) returned: no blockers; gaps folded into `task_plan.md`, summary in
  `review-plan.md`, one claim corrected in `findings.md` (a drift dryrun does not reach pypgstac).
- Host pypgstac 0.9.9 (inside stacs v0.2.0's 0.9.6–0.10.0).
- **Build** (`logs/20261014_0400_catalogue_build_v0.4.0.log`), 03:56–04:17 UTC, 1,259 s, exit 0, peak
  RSS 3.54 GB. Listing 175,278 `pointcloud/*.laz` in 233 groups, the same as 2026-10-10. Every cache
  warm: 175,278 headers, 13,996 COPC headers, 17,552 class samples, 0 to read. Built 174,282 items
  (996 excluded, 13,970 with a COPC copy); classes 17,552 screened, 347 flagged, 349 read whole;
  validation 391 s. Every count equals 0.3.0's, so nothing new since 0.3.0 (new items 0).
  21 min against 0.3.0's 53: nothing to read.
- Phase 1: compare rewritten; review round 1 (an emulation over all 174,282 footprints: 0 diffs,
  largest shift 4.999997e-9) found two low gaps, fixed (main() exit tested; new items may only
  widen the extent); plan review's G3 added (exact-rounding count, largest shift, half-way test).
  Every guard mutation-tested (about 20 mutants, each fails a test). Round 2 running.
- Phase 1 closed. Review rounds 2 and 3 each found a defect inside the previous fix (round 2: an
  interrupted local copy read as new items, and untested extent branches; round 3, the mechanism: the
  gate checked the build against the published side but never against itself — items/ vs its
  collection links, its extent vs its items' envelope, new items' rounding). Ended by enumeration:
  every failure-reporting site (24) and the conditions the patterns miss (6) mutated one at a time,
  each fails a test; the seven artifact cross-checks are listed in `findings.md`. 49 compare tests,
  321 in the suite. Reviews: `review-round1.md` to `review-round3.md`.
- **Published copy** (`logs/20261014_0400_s3_sync_published_v0.3.0.log`): 03:59–04:26 UTC, 27 min,
  174,283 JSON (174,282 items + collection.json).
- **Compare** (`logs/20261014_0500_catalogue_compare_v0.4.0.log`, the final gate), exit 0: 174,282
  published and built, 0 new, 0 only published; every bbox moved; 2,439,948 coordinates, all equal to
  the published value rounded to 8 decimals; largest shift 5e-9 degrees; 0 differing beyond the
  rounding; the local copy and the build each agree with their collection's links; collection
  differs only in `version` (0.3.0 -> unstamped). An earlier run with the round-1 gate
  (`..._0435_...`) gave the same.
- Cache push: `classes.jsonl` 35,053 lines (the pull's merge dropped 2 duplicate lines); the other
  three unchanged since pull.
- **Publish dryrun** (`logs/20261014_0440_s3_sync_dryrun_v0.4.0.log`, 04:29–04:31 UTC): 174,282
  items to upload, collection changed, 0 unbuilt. The 2,000-item rounding check is skipped as a
  rewrite, which is this release.
- Log names carry the planned start; the UTC times inside each log are the measured ones.
- **Publish** (on the plan's approval). `collection_version.py --version 0.4.0`, asserted `version`
  0.4.0 and the version extension in `data/build/collection.json` before the upload.
  `s3_sync.sh` (`logs/20261014_0510_s3_sync_v0.4.0.log`), 04:34–05:10 UTC, 36 min (0.3.0: 95):
  174,282 items and collection.json uploaded, 0 unbuilt, exit 0.
- Post-upload `s3_sync.sh --dryrun` (`..._0510_s3_sync_dryrun_post_v0.4.0.log`, 05:10–05:12 UTC):
  0 to upload, collection unchanged, 0 unbuilt, so every object's ETag is the build's MD5.
- The 0.3.0 bodies stay in the session scratchpad (`published/`) until the final verify.
- **Register dryrun** (`logs/20261014_0512_stacs_register_dryrun_v0.4.0.log`), 05:12–05:38 UTC, 25 min,
  in place of the first verify: published 174,282, registered 174,282, missing 0, orphaned 0,
  changed 174,282, collection changed, queryables 1 missing, 0 changed. Exactly the expected drift.
- Register (`..._0538_stacs_register_v0.4.0.log`) started 05:38 UTC.
- **Register** (`logs/20261014_0538_stacs_register_v0.4.0.log`), 05:38–06:20 UTC, 42 min (0.3.0: 65),
  exit 0: 1 collection, 174,282 items and 1 queryable loaded, each "reached: stac" (stacs v0.2.0's
  database check, its first live run); its own read-back: the collection and every item served with
  the published body, "1 declared queryable(s) served as declared". The host's psycopg warns
  `unknown PostgreSQL timezone: 'Canada/Pacific'; will use UTC`, as it did in 0.3.0's register.
- Live, after the register: collection `version` 0.4.0, spatial extent rounded;
  `/collections/stac-pointcloud-bc/queryables` lists `lidarbc:delivery` as declared;
  `/collections/stac-elevation-bc/queryables` unchanged (`datetime`, `geometry`, `id`); the root
  `/queryables` lists the key (stac-fastapi aggregates collections; no global row); a
  `lidarbc:delivery='093/093l/2019'` filter returns items with 8-decimal bboxes.
- Final verify (`..._0620_stacs_verify_post_v0.4.0.log`) started 06:20 UTC.
- **Final verify** (`logs/20261014_0620_stacs_verify_post_v0.4.0.log`), 06:20–06:46 UTC, 26 min:
  `IN SYNC: 174282 published, all registered with the published body, no orphans; 1 declared
  queryable(s) served as declared`. #5's queryable box ticked in its body.
- NEWS 0.4.0 written from the logs; README render started 06:48 UTC.
- README render (`logs/20261014_0648_readme_render_v0.4.0.log`), 06:48–06:59 UTC, exit 0: the only
  change to `README.md` and `index.html` is "rendered from catalogue version 0.4.0"; the demos'
  figures and JSON are byte-identical, `data/readme_cache.rds` rewritten with the same size.
