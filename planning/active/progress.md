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
