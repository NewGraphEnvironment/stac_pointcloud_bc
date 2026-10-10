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
