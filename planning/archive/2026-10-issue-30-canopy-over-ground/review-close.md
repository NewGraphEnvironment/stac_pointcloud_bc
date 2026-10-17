# Code-check close (2026-10-17)

| Round | Findings | Fixed | Accepted | Inside previous fix? |
|---|---|---|---|---|
| 1 | 3 | 3 | 0 | — |
| 2 | 2 | 2 | 0 | n |
| 3 | 6 | 6 | 0 | y (r2's "only departure" reworded, not removed; r1's provenance line widened) |

Round 3 found defects inside earlier fixes, so the loop ended on an enumeration, not a quiet round.
The set: every quantified or directional claim in the README's CHM section, research/dem_alignment.md,
its index row, stac_elevation_bc#69 and the behaviour comments (round 3's table, 89 claims,
`review-round3.md`). Each row not plainly "holds" was remediated: #3, #81 (ramp trimmed, hue test);
#29 (opacity limit quoted from `opaque_m`); #32, #53, #55 (scoped to above the lake's shore / away from
the water); #34, #86 (provenance narrowed to measurements, format from gdalinfo); #50 (the shore's
departure measured by the probe and stated); #69 (eight 2017 deliveries excepted); #79 (docstring).
#7, #25, #37, #43, #72 hold as written. The new claims the fixes introduced were checked against their
sources: the hue test (no ground hue in 65-180°), `opaque_m` 15 in the JSON, the probe's new low-ground
line (27,439 cells, 20.6%, p95 0.25, max 0.45 m), `EXCLUDE_DELIVERIES` (8 entries).
Agents spent: one plan review and three review rounds.
