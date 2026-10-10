# Progress — Some point clouds hold ground returns only, and nothing in the item says so (#10)

## Session 2026-10-09

- Plan-mode exploration — phases approved by user
- Created branch `10-some-point-clouds-hold-ground-returns-on` off main
- Scaffolded PWF baseline from issue #10 with approved phases
- Next: start Phase 1
- Phase 1: `scripts/laz_classes_probe.py` + `tests/test_laz_classes.py` (12 tests; 113 in
  suite). Mutations checked: removing the seek reddens the spread test; admitting class 1 to
  the ground-only set reddens three. Live smoke on `092g028_1_1_1` / `092g018_3_3_3` agrees
  with #9.
- Plan review (Plan agent) returned; disposition in `review-plan.md`. Taken: ground-only
  requires class 2; parallel backend pinned; `--confirm` fully reads every item any sample
  calls ground-only (makes the count exact); returns and header identity in the full read;
  density and near-ground-only in the summary; laspy floor 2.7. 118 tests pass.
- Full sample run started 2026-10-10 05:51 UTC from a frozen copy
  (`logs/20261010_055107_laz_classes_probe.log`).
- Full sample run 05:51–07:03 UTC; 9 transient failures re-read; `--confirm` full-read 73 files
  07:05–07:08 UTC. Added a "no ground" verdict (70 sampled, 57 confirmed). Research written to
  `research/laz_classes.md`; every quantified claim re-derived from the records before commit
  (three corrected: 52 non-last returns, not none; 2 not 6; class 4 does appear, in 898).
- Issue #10 body edited with the result (Result section; plan steps 1-2 marked done). Phase 3 question put to the user.
