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
- Phase 3 decided by user 2026-10-10: flagged items only, `classification:classes` on the
  `laz` asset; `nge:` prefix rename filed as #12.
- Phase 4: `classes_add`, `classes_attach`, `CLASSES_READ`; full reads re-run with ETag
  (07:16–07:19 UTC; content identical to the first pass, 73/73 ETags match the header
  cache). Rebuild 07:22 UTC (`logs/20261010_*_catalogue_build_classes.log`). Body diff vs
  the bucket's 9,649 items: exactly the 73 changed, by the class list alone. 135 tests;
  three guard mutations each redden their test.
- Landing page (README.Rmd → README.md, index.html; cache-only render) and CLAUDE.md source facts updated to the measured result.
- /code-check branch round 1: 3 findings (failed full read crashed the build with KeyError; stale-ETag refusal pointed at a no-op re-run; collection description claimed unenforced sample coverage) + research wording. All fixed; 139 tests; both new guards mutation-checked.
