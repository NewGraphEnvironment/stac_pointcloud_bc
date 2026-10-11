# Which LidarBC point clouds are ground-only, or hold no ground at all

**Verified:** 2026-10-11 · **Issues:** #10 (found in #9), #2 (the build step and the audit) ·
**Produced by:** `scripts/catalogue_build.py` (the screen, samples and whole reads) and
`scripts/laz_classes_probe.py` (`--audit 0.05 --seed 2`, `--summary`); logs
`logs/20261011_1010_catalogue_build_classes_record.log`, `logs/20261011_0900_laz_classes_audit.log`,
`logs/20261011_1100_laz_classes_summary.log` (gitignored; the numbers below are the record). The
first increment's survey (#10, 2026-10-10) is the section at the end.

The LAS header carries no class counts, so nothing the build reads from it says what a file holds.
A sample of points can only miss a class, never add one: a class seen is certain, and only an
**absence** can be wrong. So the build samples, and reads whole whatever a sample calls ground-only
or groundless.

## How the build does it (0.3.0, 174,282 files)

1. **Screen by density.** Point density (header point count over header box area) at or below the
   10th percentile of the file's mapsheet-year: **17,552 files**. The first increment's survey
   found every confirmed tile at or below the 3rd percentile (below).
2. **Sample every screened file**: the first 100,000 points plus one 50,000-point chunk at 25%, 50%
   and 75% (files of 250,000 points or fewer read whole), and where the item has a `copc` asset its
   octree levels 0–1. 6 samples failed on dropped connections and succeeded on re-run.
3. **Read whole every file a sample flags**: 338 in the screen.
4. **Audit the screen**: a seeded random 5% of the 156,730 files it leaves out (below). Its flags
   are read whole too, and recorded in `data/classes_required.json` with the survey's 2 reads
   outside the screen, so an empty cache reproduces them.

The build publishes a class list for exactly the screened files a current sample flags and the
recorded ones: **349 lists**, each every class present with its point count, in the `laz` asset's
`classification:classes`. It refuses a screened file without a current sample, a flagged or recorded
file without a current whole read, and a whole read nothing derives or records. A sample counts only
if taken at the file's current ETag and with the item's current COPC.

| verdict of the whole read | files |
|---|---|
| ground-only (class 2 and nothing outside 2, 7, 9, 18) | **12** |
| no ground (points, none of class 2) | **253** |
| mixed (a sample's false alarm) | 84 |

- **Ground-only is mostly empty tiles.** 7 of the 12 hold 2 to 29,726 points: near-empty tiles
  (2, 3, 10, 185 and 270 points) and two noise tiles in `102i/2019` (8,653 and 29,724 class-7
  points with 1 and 2 ground points). 5 are real ground-only tiles of 1.3 to 4.5 million points:
  four in `083d/2020` (las2las, 2021-03-20) and `092g028_1_1_1` (`092g/2016`, from the survey).
- **No ground**, by class set: `[1, 7]` 108, `[7]` 46, `[1, 7, 9]` 38, `[1, 9]` 29,
  `[1, 7, 9, 18]` 19, `[1]` 7, `[9]` 3, `[0]` 2, `[7, 9]` 1. They span 51 mapsheet-years; the
  largest counts are `082e/2018` 26, `082e/2017` 18, `082l/2019` 15. The two `[0]` files are the
  survey's never-classified `092h032` tiles.

## The audit: how often the screen misses (2026-10-11)

`laz_classes_probe.py --audit 0.05 --seed 2` drew 7,836 of the 156,730 unscreened files uniformly.
7,834 were sampled; **2 cannot be read by the sampler at all** (lazrs: "no chunks available in chunk
table", every time): `082e075_1_4_3` (`082e/2024`, 166 M points, 1.08 GB) and `094j045_3_3_4`
(`094j/2024`, 95 M points, 0.62 GB), both LAS 1.4 format 6, about 6.5 bytes a point. Not
investigated further. 9 samples flagged; whole reads confirmed **2 misses**:

| file | whole read | density percentile in its mapsheet-year |
|---|---|---|
| `082g002_2_2_2` (`082g/2016`) | classes 1 (2,394,812) and 7 (116): no ground | **95.9** (of 2,149) |
| `102i090_2_1_4` (`102i/2019`) | class 7 29,724, class 2 2: a noise tile | 17.7 (of 373) |

So the miss rate outside the screen is about **0.026%** (2 of 7,834; exact binomial 95% interval
0.003% to 0.092%): roughly **40 files** among the 156,730 unsampled (5 to 145) whose item lacks a
class list though it holds no ground or only ground. Inside the screen the rate is 263 of 17,552
(1.5%), about 58 times higher, so the screen concentrates them; it cannot catch all of them, because
`082g002_2_2_2` is denser than 96% of its group. Widening the screen does not help short of
sampling nearly everything: about 21 h and 380 GB at the audit's pace and the median below.

**Classes across the collection** (the audit's 7,834, a uniform sample of the unscreened 90%):
class 1 is in 7,773 (99.2%). Vegetation classes are rare: 4 (medium vegetation) in 170, 5 (high
vegetation) in 532, 3 in none; any of 3–5 in 702 (9.0%). Class 12 (overlap) is in 3,445 (44%),
which the first increment never showed. The commonest sets are `[1, 2, 7, 12]` 3,425 and
`[1, 2, 7]` 3,153. A canopy model built from this collection has to read class 1.

## Cost (0.3.0)

Laz sample: median 2.42 MB and 6.3 s a file (p95 21.4 s). COPC levels 0–1: median 3.17 MB. The
screened samples took 3 h 10 min at 16 workers; the audit's 7,836, 63 min.

## The first increment's survey (#10, 2026-10-10)

The text below is the survey of all 9,649 files of the first increment, which chose the screen.
Its samples carry no ETag, so the build does not count them; its whole reads do.

### Method

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

### Results

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
other item's samples no class 3–6 appears, so its vegetation and buildings are in class 1 unless
the sample missed them (a sample cannot show a class absent). A canopy model built from this
collection has to read class 1, not 3–5.

### Point density screens all 58 from the header

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

### Cost

| read | per file (median) | total |
|---|---|---|
| laz sample (first 100k + 3 chunks) | 2.12 MB, 4.2 s | 20.4 GB; 72 min at 16 workers |
| COPC levels 0–1 | 4.11 MB | 9.4 GB over 1,964 |
| full read of flagged files | | 1.57 GB over 73 |

Sampling all of #2's 165,667 files at this rate is about 350 GB and 20 hours. A 10th-percentile
density screen would sample about 16,600 (about 35 GB), plus full reads of what it flags.

## What this does not establish

- **About 40 unscreened files lack a list they should have** (the audit, above); which ones is
  known only by sampling them all.
- The 2 files the sampler cannot read have no sample at all.
- A tile that holds some ground is not shown to hold enough for a DEM; only the zero case is
  counted.
- The water reading of the no-ground tiles rests on classes and return counts, not on a water layer.
