# Plan review — #12 (Plan agent, returned 2026-10-10 ~19:20Z, branch at 0254474)

No blockers. The inventory was confirmed: no other script, cache or config reads the item keys. The header
record's own `las_version`/`point_format` is the cache shape and stays.

| # | class | finding | disposition |
|---|---|---|---|
| 1 | Gap | `copc_pairs_measure.py --published` will report every item changed once published bodies carry `nge:` | Written into #2's body: its published-vs-build proof must map old → new names first |
| 2 | Gap | the guard checked prefixed keys only | Fixed: unprefixed property keys ⊆ core datetimes, asset keys ⊆ href/type/roles/title/description |
| 3 | Gap | the guard walked a hand-built item, not main()'s output | Fixed: `test_every_field_the_build_writes_is_a_standard_one_or_declared` checks a COPC build and a class-read build. Mutation (a bare `delivery` added at build level) → red |
| 4 | Gap | no docstring names the fields | Ticked as n/a in task_plan |
| 5 | Acceptance | the `--limit 40` build has no COPC pair | Accepted: the copc asset keys are covered by the main()-output guard (3) |
| 6 | Acceptance | strict equality is good | kept |
| 7 | Assumption | README names fields the live catalogue does not serve until #2 | Its precedent claim is wrong: README.Rmd L123 names `classification:classes` (#10). Added one sentence: releases up to 0.2.0 publish them as `nge:` |
| 8 | Assumption | nothing stops a publish before #2 without the crate schemas | Stated in #2's body |
| 9 | Assumption | `las:` collides with nothing in pystac 1.15.2 or the extension registry | noted. crate#23 asks for a namespaced `$id` and a version |
| 10 | Assumption | item-level `las:*` describes the source-of-record `laz` asset | crate#23's schema text says so |
| 11 | Ordering | file crate first | done (crate#23 before the sibling issues) |
| 13 | Scope | stac_orthophoto_bc and stac_dem_bc have no `nge:` fields | stated in #12's body |
