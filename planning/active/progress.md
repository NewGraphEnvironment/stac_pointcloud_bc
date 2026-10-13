# Progress — Landing page rewrite (#24)

## Session 2026-10-13

- Audited every claim on the landing page against code, the live API and bucket, sibling repos and the QGIS changelog; filed #24
- Plan-mode exploration — phases approved by user (drop the mapsheet-year table; short build section plus `maintaining.md`)
- Created branch `24-landing-page-say-why-it-is-useful-first` off main
- Scaffolded PWF baseline from issue #24 with approved phases
- Next: start Phase 1
- Phase 1: claim ledger in `findings.md` (ae3e123)
- Plan review landed; findings and actions in `review-plan.md`
- Phases 2+3: `README.Rmd` rewritten (plain-language case first, no counts, three inaccuracies fixed, code and header read collapsed), `maintaining.md` written, whole-collection fetch replaced by `pc_readme_version()`; `tests/readme_functions_test.R` 0 failed, 0 errors
