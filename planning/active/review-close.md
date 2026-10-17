# Code-check close, part 2 (2026-10-17)

| Round | Findings | Fixed | Accepted | Inside previous fix? |
|---|---|---|---|---|
| 1 | 5 | 5 | 0 | — |
| 2 | 2 | 2 (window trimmed by the user's choice; bed built over a buffer and capped) | 0 | y (round 1's below-bed rule overshot ~1 km downstream) |
| 3 | 2 | 2 (wording: the read includes the margin; the cap's reach is about 150 m, on 40 m blocks) | 3 measured residuals, under the stated heuristic | n |

Round 2 found a defect inside round 1's fix, so the loop closed on enumeration, not a quiet round:
round 3's claim table (`review-p2-round3.md`) covers every quantified or directional claim in the
valley-floor section and the canopy-caption sentence; the two false ones are fixed, the rest hold
against `data/readme_rem.json`, the code path or its measurement. Its measured residuals, left as
they are: seams 1 pair (my count 3); land more than 1 m below the bed 2.63 ha in 48 patches, about
1 ha of it a real backswamp; flat floor drawn 3 m+ 0.12% of land; steep hillside drawn under 1 m
0.13%; a bed too low on one small valley's north slope (707 cells, 0.17%).

Agents spent on #30: one plan review, three rounds on part 1, three on part 2.
