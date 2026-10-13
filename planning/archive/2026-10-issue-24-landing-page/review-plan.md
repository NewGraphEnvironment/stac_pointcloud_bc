# Plan review — #24 (Plan agent, 2026-10-13)

Returned as reply text (Plan agents cannot write); recorded here.

| finding | verdict | action |
|---|---|---|
| Blocker: `pc_readme_fetch()` stops when API and bucket versions differ or are absent (`readme_functions.R:188`); a monthly run that adds items publishes no `version`, so every later render fails | reproduced by reading the code and `README.Rmd:300` | fetch removed; `pc_readme_version()` reads the API version or NA; its tests removed with it |
| `README.Rmd:188` version line not in the plan | true | reworded as "rendered from version X on DATE", NA-safe |
| "client" also at `README.Rmd:269` | true | reworded |
| Year range end goes stale | true | "since 2012", no end year |
| "Read only the part you need" holds only for `copc`, a minority | true | scoped to "files that also have a cloud-optimised copy" |
| "Flown more than once" shown at Maxan | false claim in the plan; only Kanaka shows it | ledger already said so; only Kanaka used |
| DSM bullet vs DSM specifications differing; DSMs not in this collection | true | DSM described as the top of what stands; DEM/DSM rasters pointed to stac-elevation-bc; change comparison hedged |
| `groups` dependencies (badge, intro, summary, table) | true | all removed in one edit |
| Ordering: Phase 2 links `maintaining.md` before Phase 3 writes it | true | Phases 2 and 3 in one commit |
| Phase 1 boxes unchecked | partly (two of three ticked; the BSD `sed` missed the third) | ticked |
| Grep for `client` hits `pystac-client` | true | grep `a client`; added 225, 233, 253, 38, `items-` |
| Served page has no check | true | curl the live page against `index.html` after merge |
| Demo re-run can change `items_found` wording | true | review figure and JSON diffs before committing renders |
