# Progress — README.Rmd landing page served on GitHub Pages, like stac_dem_bc (#9)

## Session 2026-10-09

- Plan-mode exploration — phases approved by user (R deps: DESCRIPTION manifest; build
  manual stays in README.Rmd)
- Created branch `9-readme-rmd-landing-page-served-on-github` off main
- Scaffolded PWF baseline from issue #9 with approved phases
- Next: start Phase 1
- Phase 1: DESCRIPTION manifest; `pc_readme_header()` / `pc_readme_header_parse()` in
  `scripts/readme_functions.R`; testthat file with three 375-byte fixtures, 19 pass, red on
  both restored bugs. Live read of the COPC returned the same values.
- Plan review returned; findings folded in (see findings.md). DESCRIPTION moved to
  `scripts/` to keep the gh-pr-merge release route.
- Phases 2–3: fetch with id-set guard, example (Similkameen River), header check, figure,
  cache; README.Rmd rendered to README.md + index.html, re-render byte-identical.
- Phase 4: Pages enabled from main `/` (building at 21:2xZ; serves main's README until the
  merge); About homepage + description set. The 200 check waits for the merge.
- Phase 5: stac_dem_bc PR #54 (hand-edited bullet in README.Rmd/README.md/index.html; a
  re-render there would also rewrite staticimports.R, README.html and the badges).
  Follow-up for floodplains' sister list: stac_floodplains_bc#73.
- Code-check round 1: one finding (`%||%` needs R 4.4) fixed in f53a21d.
- User redirected the lead figure to a search → COPC → DEM demo; Houston unavailable (not
  indexed, no COPC); Kanaka Creek chosen. Coverage map dropped at user request.
- Phase 6 landed: `scripts/readme_dem.py`, tests, README.Rmd lead section; renders identical.
