# Progress — README: a canopy height model from the point clouds (Maxan Creek delta) (#19)

## Session 2026-10-11

- Plan-mode exploration — phases approved by user
- Created branch `19-readme-a-canopy-height-model-from-the-po` off main
- Scaffolded PWF baseline from issue #19 with approved phases
- Next: start Phase 1
- Phase 1: lidR 4.3.3 installed. `pc_readme_chm()` and `pc_readme_laz_get()` in
  `scripts/readme_functions.R`, four tests. Two lidR behaviours found on the way (findings.md).
  Mutation check: removing the noise filter, the withheld filter, normalisation, or keeping
  ground out of the CHM each turns a test red.
- Plan review (Plan agent) landed: 2 blockers, 14 gaps; saved to `review-plan.md`, dispositions
  in findings.md.
- Phase 2: `scripts/readme_chm.R`. Tiles downloaded (532 MB), profiled; CHM run 570 s, 9.4 GB.
  `data/readme_chm.json`, `fig/maxan_chm.png` written.
