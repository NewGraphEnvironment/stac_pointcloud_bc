# README: a canopy height model from the point clouds (Maxan Creek delta) (#19)

## Outcome

The landing page gained a second demo, **From a search to a canopy height model**. A STAC search
over a 1.2 × 1.0 km window at the Maxan Creek delta, Bulkley Lake (`093/093l/2019`) finds two
`laz` items with no `copc`. They are downloaded whole once into gitignored `data/readme_laz/`, and
lidR builds a pit-free CHM: first returns over a ground TIN, noise and withheld points left out,
nothing chosen by vegetation class. `scripts/readme_chm.R` writes `fig/maxan_chm.png` and
`data/readme_chm.json`, and every number on the page comes from the json. The script refuses a
run whose inputs would make the page false: a `copc` asset now present, items not covering the
window, more than 2 tiles or 600 MB.

Two lidR behaviours shaped the code. `rasterize_canopy()` refuses a point outside its grid, and
pit-free rasterising leaves the grid's outer cells NA, so the code rasterises with a margin and
crops. The plan review then caught that `pitfree()` needs `ReturnNumber`, which the first run's
`select` did not read. The largest correction came from code-check round 3. Bulkley Lake's
surface returns are class 1, level with the shore, so the lake read 0 m like the meadow and
counted as land. Water is now masked where no ground return lies within 5 m. Round 4 then found
that my first version of that mask reached only ~2.75 m, while the page said 5 m: a defect
inside the fix, pinned by a test that tells the two reaches apart. The review ended on an
enumeration of every claim in the section (`review-enumeration.md`).

## Measurement

- Tiles `bc_093l040_3_4_1` and `_3_4_2`: 532 MB, 107.8 M points. They hold classes 1, 2 and 7
  only, with no class 9, no withheld points and no overlap flag. They average about 22
  returns/m², not the 39/m² the issue quoted from tiles further east.
- Window: 23.4 M returns, 33% class 2 and 67% class 1. Water is 41% of the cells. Of the land
  cells, 37% are at least 2 m and 12% at least 10 m. The 99th percentile is 27.8 m and the
  maximum 39.5 m.
- Time and memory:
  - Downloads took about 16 min, at roughly 0.5 MB/s from the objectstore.
  - The CHM script takes 570 s on the cached tiles, peaking at 8.8–9.4 GB RSS.
  - The `update_query = TRUE` render takes 46 min. Both figures were byte-identical across
    runs.
- The water finding is in [`research/laz_classes.md`](../../../research/laz_classes.md)
  ("Water reads as ground-level returns").

Closed by: PR for branch `19-readme-a-canopy-height-model-from-the-po`
