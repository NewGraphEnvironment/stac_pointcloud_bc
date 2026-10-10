# Which LidarBC point clouds are ground-only, or hold no ground at all

**Verified:** 2026-10-10 · **Issues:** #10 (found in #9; decides what #2 reads) ·
**Produced by:** `scripts/laz_classes_probe.py` over the v0.2.0 build (`data/build/items`, 9,649
items); logs `logs/20261010_*_laz_classes_*.log` (gitignored; the numbers below are the record).

The LAS header carries no class counts, so nothing the build reads says what a file holds. This
measured it by reading points from every item in the first increment.

## Method

A sample can only miss a class, never add one. A class seen is certain; only an **absence** can be
wrong. So the run had two passes:

1. **Sample every item.** The `laz` file's first 100,000 points, plus one 50,000-point chunk at
   25%, 50% and 75% of the file (LidarBC LAZ chunks are 50,000 points; a seek through the chunk
   table fetches one chunk). Files of 250,000 points or fewer were read whole. Where the item has a
   `copc` asset (1,964), that COPC's octree levels 0–1, which cover the whole tile. Each sample's
   class counts are kept separately.
2. **Fully decompress every item a sample calls ground-only or no-ground** (73 files, 1.57 GB),
   tallying every point's class and (return number, number of returns), with the header's software
   and creation date. Every full read returned exactly the header's point count.

Definitions: **ground-only** = class 2 present and no class outside {2, 7, 9, 18} (ground, low
noise, water, high noise). Class 1 counts against it: vegetation left unclassified is still there.
**No ground** = points, but none of class 2.

All 9,649 items were sampled. Nine reads failed on transient errors (seven dropped connections,
plus a 503 and a timeout from the CanElevation bucket) and succeeded on re-run; none are
unresolved.

## Results

| verdict | from the samples | confirmed by a full read |
|---|---|---|
| ground-only | 3 | **1**: `092g/2016` `092g028_1_1_1` |
| no ground | 70 | **57**: `082e/2018` 26, `082l/2018` 14, `082l/2019` 15, `092h/2016` 2 |

- **Ground-only is one tile in 9,649.** `092g028_1_1_1` is 2,455,690 points, all class 2. Its
  return profile is that of a filtered file: only 52 points are non-last returns, and 12% are the
  last return of a multi-return pulse. Its header names Global Mapper where its `092g/2016` neighbours
  name las2las, and it has the lowest point density in its mapsheet-year (0.96 pts/m²). It reads
  as one tile processed differently, not a delivery.
- **The other two sampled ground-only tiles are not.** `082k017_1_3_3` (`082k/2017`, no COPC) was
  ground-only in all four samples; the full read found 13,465 class-1 points among 13.7 million
  (0.1%), and 99% single returns. It is bare ground, not a filtered file. `092g028_2_1_1` was
  ground-only in its first 100,000 points only: the spread chunks and its COPC both found class 1.
- **57 tiles hold no ground at all**, and 13 more the samples called groundless hold a little (2 to
  316,908 points). 55 of the 57 are classes 1 and 7 (40) or 1, 7, 9 and 18 (15, all
  `082l/2019`), with 93.5–100% single returns, consistent with open water left unclassified
  (not checked against a water layer). The other 2, `092h032_1_1_3` and `092h032_1_3_1` (`092h/2016`), are **class 0 only**:
  7.6 and 6.8 million points never classified, written by LASzip DLL 2.4 on 2017-11-29.
- **The COPC never disagreed with the laz** on the 1,964 items that have one (merged laz samples
  vs COPC levels 0–1). The first 100,000 points alone disagreed once (`092g028_2_1_1`).

Class sets across the merged laz samples (items): `[1, 2, 7]` 5,646; `[1, 2]` 2,102; `[1, 2, 4, 7]`
892; `[1, 2, 7, 18]` 475; `[1, 2, 7, 9, 18]` 442; `[1, 7]` 49; `[1, 7, 9, 18]` 19; `[1, 2, 4]` 6;
`[0, 1, 2]` 5; `[1, 2, 7, 9, 17, 18]` 4; `[1, 2, 10]` 3; `[0]` 2; one each of `[1, 2, 7, 30]`,
`[2, 7]`, `[2]`, `[0, 1, 2, 7]`. No 1.2 key-point (8) or overlap (12) class appears. Of the
vegetation and building classes (3–6) only 4 (medium vegetation) appears, in 898 items. In every
other item, whatever stands above the ground can only be in class 1, so a canopy model built from
this collection has to read class 1, not 3–5.

## Point density screens all 58 from the header

Every confirmed tile is at or below the 3rd percentile of point density (header point count over
header box area) in its mapsheet-year, which the build already reads:

| screen (within mapsheet-year) | items flagged | confirmed tiles caught |
|---|---|---|
| ≤ 2nd percentile | 200 | 48 / 58 |
| ≤ 5th percentile | 488 | 58 / 58 |
| ≤ 10th percentile | 971 | 58 / 58 |
| < 5 pts/m², any group | 300 | 57 / 58 |

So a build need only sample the low-density tail and fully read what the sample flags. This is
measured on 9,649 files; that it holds for other deliveries is an expectation, not a measurement.

## Cost

| read | per file (median) | total |
|---|---|---|
| laz sample (first 100k + 3 chunks) | 2.12 MB, 4.2 s | 20.4 GB; 72 min at 16 workers |
| COPC levels 0–1 | 4.11 MB | 9.4 GB over 1,964 |
| full read of flagged files | | 1.57 GB over 73 |

Sampling all of #2's 165,667 files at this rate is about 350 GB and 20 hours. A 10th-percentile
density screen would sample about 16,600 (about 35 GB), plus full reads of what it flags.

## What this does not establish

- **The increment is not a random sample.** It is the mapsheet-years with no raster DSM (#1), so
  these rates may not carry over to #2's 165,667 files.
- A tile that holds some ground is not shown to hold enough for a DEM; only the zero case is
  counted.
- The water reading of the no-ground tiles rests on classes and return counts, not on a water layer.
