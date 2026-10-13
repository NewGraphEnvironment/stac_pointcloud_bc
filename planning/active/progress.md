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
- `/code-check branch`: five rounds; rounds 2-5 each found a defect inside the previous fix, ended by enumerating the item-date set from all 174,282 built items (findings.md). Spawned 6 reviewer agents in all (1 plan review + 5 rounds), one over the usual bound
- Filed #25 (date parser misses `_pa`, `_1`, `.copc` tokens) and NewGraphEnvironment/stac_dem_bc#61 (`lidarbc:delivery` not yet on live elevation items)
- Rendered `README.md` (update_query = TRUE) and `index.html`: rc 0; demo figures and JSON byte-identical; no stale count in either (grep); prose read against the ledger
