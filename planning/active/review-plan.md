# Plan review (Plan agent, read-only; written here by the parent) — #9

Returned 2026-10-09 ~21:07Z. Disposition in findings.md, "Plan review".

- B1 numberMatched absent → id-set guard against the bucket's collection.json. **Fixed.**
- B2 COPC box differs by ≤0.01 m; pc:count is integer from jsonlite → absolute 0.05 m tolerance, numeric compare. **Fixed** (`pc_readme_header_check`).
- A1 root DESCRIPTION reroutes gh-pr-merge to the manifest route (no tag, no bump). **Confirmed; DESCRIPTION moved to scripts/.**
- A2 computed counts are a snapshot → labelled with version and fetch date. **Kept, labelled.**
- A3 the 375-byte read has no CRS → intro reworded. **Fixed.**
- G1 output must not depend on update_query → shown code eval=FALSE, run via ref.label. **Done.**
- G2 sort before cache/print. **Done.**
- G3 .gitignore knitr intermediates. **Done.** G4 absolute links for .md targets. **Done.** G5 .nojekyll. **Done.**
- G6 figure legibility → copc drawn last, one label per sheet. **Done; inset not taken.**
- G7 licence spelled out. **Done.** G8 local_install_dev_deps. **Done.** G9 CLAUDE.md line above the marker. **Done.**
- G10 status before body (req_perform_connection); rawToChar nul. **Fixed.** Same weakness in `laz_remote.py:57` — not in this diff.
- O1 Pages enabled before merge. **Done.** O2 determinism sequence md(T)→html(F)→md(F)→html(F). **Done, byte-identical.**
- S1 stac_dem_bc hand-edit rather than re-render. **Done (stac_dem_bc#54).** S2 floodplains list → stac_floodplains_bc#73. S3 no NEWS entry, stated.
- AC1 link the reader file (absolute URL). **Done.** AC2 stopifnot both kinds. **Done.** AC3 cache size fine (6 KB).
