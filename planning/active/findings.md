# Findings — Some point clouds hold ground returns only, and nothing in the item says so (#10)

## Issue context

**If we do it:** a user knows, before reading a tile, whether it carries vegetation and buildings or ground returns only. **If we never do:** someone builds a canopy model from a search result and gets nothing above the ground for some tiles, with no hint why.

## What was seen

While building the landing page's DEM demo (#9), a 1.6 × 1.2 km window at Kanaka Creek read four `092g/2016` items. One, `092-092g-2016-pointcloud-bc_092g028_1_1_1_xyes_8_utm10_20170714`, returned 748,497 points in the window, **all class 2** (ground). Its neighbour `092g018_3_3_3` carries classes 1 and 2. The COPC and the LidarBC `laz` have the same point count (the #6 pairing check), so this is how the province delivered it, not a CanElevation change.

## Why the build cannot see it

The build reads the LAS header and VLRs only (`research/laz_header_read.md`). Class counts are not in the header, so nothing in an item says a file is ground-only.

## Do before #2

Whatever items should say about their classes has to be settled before #2's build, which rebuilds and re-registers every item. Otherwise the full registration happens twice (the same reasoning as `nge:delivery`, #5).

## Plan (2026-10-09)

1. **Measure on the 9,649 indexed files.** Decompress each file's first ~100k points and record the classes present. Earlier measurement put that at 1.0–1.5 MB and ~1–1.6 s per file (`research/laz_header_read.md`): ~12 GB for the increment, about an hour with parallel reads.
2. **Check the sample before trusting it.** A file's first points are a strip, not the tile. For the 1,964 items with a `copc`, the COPC's coarse octree levels (0–2) sample the whole tile cheaply. Compare the two verdicts on the same files. If they agree, the first-points sample stands for files with no COPC.
3. **Decide what items say, with the number in hand.** This decision is the user's. If ground-only is a few deliveries, a collection-level note naming them may be enough. If it is common, items carry a property (the classes seen, and how they were sampled; `pc:statistics` would claim whole-file statistics a sample cannot support).

## The cost that matters for #2

A per-item class sample makes #2's build read ~1.3 MB per file instead of a 64 KB header: roughly 215 GB instead of 10 GB for 165,667 files, and hours more. Step 1's prevalence decides whether that is worth it.



## Exploration (2026-10-09)

- `scripts/laz_header_probe.py` already decompresses the first N points and tallies classes;
  `scripts/laz_remote.py` `HttpRangeFile` counts bytes. laspy 2.7.0 has `LasReader.seek()`
  (chunk-table seek in LAZ) and `CopcReader.query(level=range(0, 3))`.
- `scripts/readme_dem.py` reads COPC windows; `scripts/copc_pairs_measure.py` is the model for
  a measure script over `data/build/items` (gitignored, 9,649 items, 1,964 with `copc`).
- `catalogue_build.headers_fetch` / `cache_tail_repair` are the resumable-jsonl, threaded
  pattern to reuse. `tests/test_laz_item.py` has a local 206-only HTTP server over a LAZ
  written by laspy, which the new tests can reuse with no network.


## Sampling design (measured 2026-10-09)

- LidarBC LAZ chunks are 50,000 points (LasZip VLR). `LasReader.seek()` over `HttpRangeFile`
  fetches only the target chunk: on `092g018_3_3_3` (17.2M points, 71 MB) the first 100k
  cost 0.44 MB / 0.4 s and each 50k chunk at 25/50/75% 0.39–0.52 MB / ~0.4 s. So the spread
  reads go on every file, not only those the first points call ground-only; that also
  measures the first-points estimator directly.
- COPC on the same tile: levels 0–2 = 1,443,451 points, 11.4 MB, 19.5 s; levels 0–1 =
  350,192 points, 3.2 MB, 5.5 s. Levels 0–1 already cover the whole tile, so the probe uses
  them.
- Smoke (`092g028_1_1_1`, `092g018_3_3_3`): ground-only on all three verdicts for the
  first, mixed {1, 2} for the second. Matches the #9 observation.
- "Ground-only" = no class outside {2, 7, 9, 18}. Class 1 counts against it (vegetation left
  unclassified is still there). The summary tabulates every class set, so the definition's
  spread is visible.

## Errors Encountered

| Error | Resolution |
|-------|------------|
