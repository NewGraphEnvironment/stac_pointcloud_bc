# Code-check enumeration for #19 (2026-10-12): every claim the CHM section makes

Round 4 found a defect inside round 3's fix (the water mask reached ~2.75 m while the page said
5 m), so the loop ends on enumeration, not on a quiet round. The candidate set is round 3's
mechanism: a statement about the data that is neither derived from `data/readme_chm.json`,
guarded by `scripts/readme_chm.R`, nor measured on the pinned inputs. Walked from the rendered
README.md (18 sentences and the alt text) and every comment in `scripts/readme_chm.R` and
`pc_readme_chm()`.

Inputs are pinned: delivery `093/093l/2019`, items checked to cover the window, each file
refused unless it matches its `file:size`, no `copc`. So a statement measured on these tiles
holds on every render that does not stop.

| claim | source |
|---|---|
| alt: trees up to N m | json `height_m$max` |
| alt: meadow at 0 m, channel, south slope, lake light blue | figure of the pinned inputs; NW 77% class 2 (findings) |
| 1.2 × 1 km window, 30 m margin, 2 items, delivery | json |
| "covering it" | guard: `st_covers(union of proj:bbox, read box)` |
| no `copc` asset | guard: refused before download |
| downloaded whole, once; MB, points, points in window | code; json |
| 33% class 2, 67% class 1 | json |
| class 1 is where LidarBC leaves most vegetation | research/laz_classes.md |
| only noise and withheld left out; nothing by vegetation class | code (`NOISE_CLASSES`, `-drop_withheld`, Withheld_flag); tests |
| heights above a ground TIN; first returns, pit-free, at 0.5 m | code (`normalize_height(tin())`, `pitfree()` = `ReturnNumber == 1L`, lidR source); json `cell_m` |
| open ground reads 0 m | code (ground kept, clamp); test |
| light blue N% of window; no ground within 5 m, or no return | json `cells_na`, `ground_gap_m`; code w = 2·ceiling(gap/res)+1; test discriminates the old reach |
| lake and channel | figure of the pinned inputs |
| lake returns class 1, level with the shore | measured (findings: 712.5–712.8 m, class 1 only) |
| land shares ≥ 2 m, ≥ 10 m; p99; max | json |
| LidarBC CHMs 2023–24 only, as of August 2026; DSM specs differ | stac_dem_bc#47, dated |
| historic channels, forest lost since 2017 | floodplains#121 |
| comment: only 2019 covers the reach | floodplains#121 measurement; delivery pinned anyway |
| comment: ~0.5 MB/s from the objectstore | measured 2026-10-12 (findings) |

Fixed while walking it: "the model is built from every return but noise" (README and the
script header) — the surface is first returns over a ground TIN; reworded.
Nothing sits above its source. Loop ends.
