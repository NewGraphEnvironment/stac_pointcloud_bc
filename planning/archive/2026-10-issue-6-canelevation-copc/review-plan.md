# Plan review (Plan agent, 2026-10-09) — findings and disposition

Reviewer read task_plan.md, the code at eac6f0e plus the uncommitted Phase 2, and the
installed stacs. No blocker. Disposition after measuring all 1,964 pairs of the first full
build (max offset 0.01 m in x/y and z; every CRS agrees, 1,575 EPSG:3157 and 389 EPSG:2955;
1,575 copies are LAS 1.4/6 where the source is 1.2/1).

| # | finding | disposition |
|---|---|---|
| 1 | stacs accepts a second asset and an off-bucket href; verify digests whole bodies | confirmed, no change |
| 2 | box check was x/y only; the research compared z too | fixed: x, y and z compared against the LAZ header |
| 3 | 1 m tolerance ~1000x the offset seen | fixed: 0.05 m (5x the measured 0.01 m max) |
| 4 | no CRS check | fixed: horizontal EPSG must agree (WKT equality when either has none) |
| 5 | first mismatch stops the build with a traceback; no route past one | fixed in part: all mismatches reported, build returns 1. No COPC_EXCLUDE: none mismatched; add one when one does |
| 6 | item says nothing of the COPC's own format; "same points" overclaims | fixed: `nge:las_version` / `nge:point_format` on the asset; description says what was checked |
| 7 | licence of the copy | fixed: asset description names the Open Government Licence - Canada |
| 8 | `data/build-limit/` not gitignored | fixed |
| 9 | `--limit` cannot reach a 092g slice | recorded in progress.md how the slice was made (INCREMENT patched in a one-off) |
| 10 | no pre-publish check that only the COPC items changed | done: published items pulled from S3 and diffed as sets before sync |
| 11 | CanElevation listed after the LidarBC header pass | fixed: listed before any header read |
| 12 | headers_fetch reuse | confirmed, no change |
| 13 | CanElevation duplicate check covered unmatched names | fixed: only names a build file matches |
| 14 | 90% floor rationale borrowed from LidarBC | comment rewritten: a moved project stops the build on purpose. Periodic href check -> follow-up with CI update |
| 15 | excluded file has no copy, so 420 holds | confirmed |
| 16 | log zero for the other seven groups | covered by the set diff in 10 |
| 17 | build docstring | fixed |
| 18 | "9,649 items" as acceptance is a count | replaced by the set diff in 10 |
| 19 | tests for z, CRS, all mismatches reported | added |
| 20 | HEAD one copc href per contributing project | done in Phase 3 |
