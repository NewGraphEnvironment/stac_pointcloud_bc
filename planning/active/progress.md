# Progress — Sample the point classes of every file (#17)

## Session 2026-10-17

- Plan-mode exploration — phases approved by user; scope: the build samples every file
- GitHub unreachable throughout; branch `17-sample-every-file` cut from local main (origin not
  fetched), to be renamed to the issue's slug and merged with origin/main before push
- Scaffolded PWF baseline with approved phases
- Next: start Phase 1
- Plan review (Plan agent, 2026-10-17 18:10-18:43 UTC) in `planning/active/review-plan.md`; folded
  in: carve-out keyed by ETag and sampled every run, empty-sample guard, catalogue_compare and
  README.Rmd added to the plan, push-then-merge ordering
- Phases 1-2 landed: the build samples every file but CLASSES_UNREADABLE's (2 entries); suite
  327 passed, 2 skipped
- Network: GitHub, the LidarBC objectstore and S3 all unreachable or 0 B/s from 18:04 UTC; the
  cache pull failed (aws s3 cp wrote no file); the sweep (Phase 3) cannot start
- `catalogue_compare.py` accepts a class list added with its extension and a changed description; README.Rmd, README.md, index.html (rendered with update_query = FALSE: only the classes paragraph moved), maintaining.md, cache_sync.sh comment
- `/code-check branch`, 3 rounds (review-round1..3.md): description direction, refusal-message overwrites (enumerated, 15 write sites), maintaining.md refusal list; suite 336 passed
- 22:54 UTC: the objectstore waiter expired after 4 h with the objectstore still down (0 B in 30 s);
  GitHub and pypi.org also time out, while example.com and google.com answer and S3 answers in 15 s.
  New waiters, 8 h each, probing every 3 min: objectstore (to start the sweep) and GitHub (issue body,
  branch rename, PR). Phase 3 onward waits on them.
- 00:35 UTC 2026-10-18: stood down on the user's word. DNS resolves GitHub, the objectstore and
  pypi.org, but no TCP connection to them completes; the user suspects this Mac's wifi. Waiters
  stopped. Resume from Phase 3 (cache pull, then the sweep at 10 workers) once the network works.

## Session 2026-10-18

- 01:28 UTC: network back (GitHub API, objectstore 1 MB in 0.7 s, S3). Earlier only HTTPS had
  failed: git over SSH and `ssh -T git@github.com` worked while HTTPS to GitHub never connected.
- Cache pull: no change (every cache merged to its own line count).
- Sweep started 01:29 UTC, `laz_classes_probe.py --workers 10`, log
  `logs/20261018_0130_laz_classes_sweep.log`: 148,896 to sample; 2.1 files/s after 10 min (~19 h).
- Issue #17 body fetched (last edited 2026-10-11, before plan mode) and diffed against the plan:
  nothing changes the phases. Its "decide whether the build keeps the screen" is the plan-gate
  decision (sample every file). Its "find out whether a whole read works" for the two unreadable
  files was deferred by plan review B1; now being tried with the sequential decoders.
- `git fetch`: nothing on origin/main since the branch point. Branch renamed to
  `17-sample-the-148-894-unscreened-files-and` (the issue slug).
- Sweep ended 20:42 UTC (19 h 13 min, 148,896 files, 42 failed). Retry at 4 workers
  (`logs/20261018_2045_laz_classes_sweep_retry.log`): 36 sampled (31 ConnectionError, 1 ReadTimeout,
  4 "Failed to use readinto": all transient); 6 still fail "no chunks available in chunk table".
- All 6 are zero-filled after part of their data (range-read probe; #32): the 2 known plus
  082e050_3_2_1 (082e/2025), 092b082_2_3_3 (092b/2019, which has a CanElevation COPC copy),
  093p045_3_3_3 (093p/2024), 094j046_2_4_2 (094j/2024). `CLASSES_UNREADABLE` now holds the 6,
  each reason citing #32. Suite 337 passed.
- Full build started 20:55 UTC, `logs/20261018_2055_catalogue_build_sweep.log`.
- (Correction: the full build started 20:48 UTC, not 20:55; its log keeps the 2055 name.) It built
  174,282 items in 2 h 17 min: 629 flagged, 629 read whole, 629 lists (12 ground-only, 312 no
  ground, 305 mixed). `--classes-record --force` (`logs/20261018_2310_catalogue_build_classes_record.log`,
  17 min warm): 0 ids recorded, 11 dropped; `data/classes_required.json` is `[]`.
- Measured (scratch scripts over the caches and built items): 61 true lists outside the 0.3.0
  screen (the audit's 2 + 59), percentile median 21.2, 11 above the 90th; class shares over every
  sample; sweep 447 GB. research/laz_classes.md, its README row, NEWS (Unreleased) and the
  CLAUDE.md classes bullet revised. Description: "Most of the listed items hold no ground" was
  false (312 of 629), now "A listed item may hold no ground ... its list says so"; the 6 carve-outs
  are called damaged at source.
- Mutation check (copy of the tree): the 10th-percentile screen restored fails 8 tests; the
  now-samples refusal removed fails its 2 cases. Suite 337 passed.
- Final build 23:27-23:43 UTC (`logs/20261018_2335_catalogue_build_final.log`) with the corrected
  description. `catalogue_compare.py` against a copy of the bucket
  (`logs/20261018_2345_catalogue_compare.log`): exit 0; 174,282 both sides, 280 published items
  given a list (629 - 349), 0 differing otherwise, collection description changed.
- Code-check round 4 (diff 62f7394..HEAD, `review-round4.md`): no code defects, 5 wrong claims in
  research/NEWS/CLAUDE.md and one comment, all reproduced and fixed; ended by enumeration of the
  fixes' numbers. 092b082_2_3_3's COPC looks whole: added to #32.
