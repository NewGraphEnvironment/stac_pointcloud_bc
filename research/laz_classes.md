# Which LidarBC point clouds are ground-only, or hold no ground at all

**Verified:** 2026-10-18 (the 0.3.0 screen and audit 2026-10-11, water 2026-10-12) · **Issues:** #10
(found in #9), #2 (the screen and the audit), #17 (sampling every file), #19 (water), #32 (files
damaged at source) ·
**Produced by:** `scripts/laz_classes_probe.py` (the sweep, `--audit 0.05 --seed 2`, `--summary`) and
`scripts/catalogue_build.py` (whole reads and lists); logs `logs/20261018_0130_laz_classes_sweep.log`,
`logs/20261018_2045_laz_classes_sweep_retry.log`, `logs/20261018_2055_catalogue_build_sweep.log`,
and for 0.3.0 `logs/20261011_1010_catalogue_build_classes_record.log`,
`logs/20261011_0900_laz_classes_audit.log` (gitignored; the numbers below are the record). The
first increment's survey (#10, 2026-10-10) is the section at the end.

The LAS header carries no class counts, so nothing the build reads from it says what a file holds.
A sample of points can only miss a class, never add one: a class seen is certain, and only an
**absence** can be wrong. So the build samples, and reads whole whatever a sample calls ground-only
or groundless.

## How the build does it (#17, 2026-10-18, 174,282 files)

1. **Sample every file**: the first 100,000 points plus one 50,000-point chunk at 25%, 50% and 75%
   (files of 250,000 points or fewer read whole), and where the item has a `copc` asset its octree
   levels 0–1. **174,276 sampled.** The other 6 are damaged at source (#32): the point data stops
   part-way and the rest of the file, its chunk table included, is zero bytes. They are named in
   `CLASSES_UNREADABLE` and carry no list. Of the sweep's 148,896 reads, 42 failed; 36 were
   transient (31 dropped connections, 4 lazrs "Failed to use readinto", 1 read timeout) and
   sampled on re-run, and 6 are those files.
2. **Read whole every file a sample flags** (ground-only or groundless in any sample): **629**.

The build publishes a class list for exactly the files a current sample flags: **629 lists**, each
every class present with its point count, in the `laz` asset's `classification:classes`. Every file
has a sample, so no list needs recording: `data/classes_required.json` is empty, and no file in this
build has a whole read its sample does not flag (one would be refused). A sample can only miss a class, so an item without a list
holds ground and at least one class outside {2, 7, 9, 18}. The build refuses a file without a
current sample, a flagged file without a current whole read, an empty sample, and a
`CLASSES_UNREADABLE` entry that now samples, fails otherwise, was re-delivered or left the build. A
sample counts only if taken at the file's current ETag and with the item's current COPC.

| verdict of the whole read | files | 0.3.0 |
|---|---|---|
| ground-only (class 2 and nothing outside 2, 7, 9, 18) | **12** | 12 |
| no ground (points, none of class 2) | **312** | 253 |
| mixed (a sample's false alarm) | 305 | 84 |

- **Ground-only is mostly empty tiles, and unchanged.** The sweep found no new one: the 12 are
  0.3.0's. 7 hold 2 to 29,726 points: near-empty tiles (2, 3, 10, 185 and 270 points) and two noise
  tiles in `102i/2019` (8,653 and 29,724 class-7 points with 1 and 2 ground points). 5 are real
  ground-only tiles of 1.3 to 4.5 million points: four in `083d/2020` (las2las, 2021-03-20) and
  `092g028_1_1_1` (`092g/2016`, from the survey).
- **No ground**, by class set: `[1, 7]` 134, `[7]` 73, `[1, 7, 9]` 38, `[1, 9]` 32,
  `[1, 7, 9, 18]` 19, `[1]` 10, `[9]` 3, `[0]` 2, `[7, 9]` 1. They span 53 mapsheet-years; the
  largest counts are `082e/2018` 26, `092f/2020` 21, `082e/2017` 20, `082f/2017` 16. The two `[0]`
  files are the survey's never-classified `092h032` tiles.
- **Nearly half the lists (305) are false alarms**, which the whole read corrects. In 232 the
  first 100,000 points were all ground though the file holds other classes; in 73 the laz samples held no ground and the whole read found some. All 59 new no-ground files
  were outside the 0.3.0 screen (below); none is ground-only.

## What the 0.3.0 screen missed (2026-10-18)

The 0.3.0 build sampled only the files at or below the 10th density percentile of their
mapsheet-year (17,552), plus the audit below. The sweep found **61 files outside that screen that
hold no ground (60) or only ground (1)**: the audit's 2 and **59 more**, against its estimate of 38
(5 to 137). Their density percentiles in their mapsheet-years: median 21.2, 15 above the 50th, 11
above the 90th. So no density screen short of nearly everything would have caught them. By
mapsheet-year: `092f/2020` 13, `092g/2021` 12, `082g/2016` 7, `082f/2017` 5, `092c/2019` 5,
`092k/2019` 4, `092f/2019` 3, `082e/2017` 2, and 1 each in 10 more. Outside the screen, samples
also raised 230 false alarms that whole reads cleared.

## The audit: how often the screen misses (2026-10-11)

`laz_classes_probe.py --audit 0.05 --seed 2` drew 7,836 of the 156,730 unscreened files uniformly.
7,834 were sampled; **2 cannot be read by the sampler at all** (lazrs: "no chunks available in chunk
table", every time): `082e075_1_4_3` (`082e/2024`) and `094j045_3_3_4` (`094j/2024`). Both are
damaged at source (#32): downloaded whole, each matching its ETag, their point data stops at 383 of
1,026 MiB and 203 of 596 MiB and the rest, chunk table included, is zero bytes. 9 samples flagged; whole reads confirmed **2 misses**:

| file | whole read | density percentile in its mapsheet-year |
|---|---|---|
| `082g002_2_2_2` (`082g/2016`) | classes 1 (2,394,812) and 7 (116): no ground | **95.9** (of 2,149) |
| `102i090_2_1_4` (`102i/2019`) | class 7 29,724, class 2 2: a noise tile | 17.7 (of 373) |

So the miss rate outside the screen was estimated at about **0.026%** (2 of 7,834; exact binomial 95% interval
0.003% to 0.092%): roughly **38 files** among the 148,894 neither screened nor audited (5 to 137)
whose item lacks a
class list though it holds no ground or only ground. The sweep found 59 (above). Inside the screen the rate is 263 of 17,552
(1.5%), about 59 times higher, so the screen concentrates them; it cannot catch all of them, because
`082g002_2_2_2` is denser than 96% of its group. Widening the screen does not help short of
sampling nearly everything: the 148,894 left are about 20 h and 400 GB at the audit's pace and
median below.

**Classes across the collection** (every file's laz samples, 174,276, 2026-10-18): class 1 is in
172,833 (99.2%) and class 2 in 173,891 (99.8%). Vegetation classes are rare: 5 (high vegetation) in
11,254 (6.5%), 4 (medium vegetation) in 3,678 (2.1%), 3 in 1; any of 3–5 in 14,933 (8.6%). Class 12
(overlap) is in 76,120 (43.7%), 9 (water) in 5,647 (3.2%), 18 (high noise) in 4,927. The commonest
sets are `[1, 2, 7, 12]` 75,681, `[1, 2, 7]` 71,391, `[1, 2, 5, 7]` 6,802, `[1, 2]` 5,623 and
`[1, 2, 4, 7]` 3,667. The audit's uniform 5% had given 99.2%, 9.0% and 44% for classes 1, 3–5 and
12. A canopy model built from this collection has to read class 1.

## Cost

The sweep (#17): 148,896 files in **19 h 13 min at 10 workers** (2.15 a second), **447 GB** of range
reads (378 GB laz, 68 GB COPC levels). Over all 174,276 samples the laz sample is a median 2.63 MB
(p95 2.95) and 3.8 s (p95 7.1); COPC levels 0–1 a median 5.15 MB over 13,969. The build that then
read the 280 newly flagged files whole and built every item took 2 h 17 min. A month's new or
re-delivered files are sampled the same way.

0.3.0: laz sample median 2.44 MB and 6.7 s a file over the screen (p95 26.0 s), 2.65 MB and 6.5 s
over the audit (p95 7.7 s); COPC levels 0–1 median 3.17 MB. The screened samples took 3 h 10 min at
16 workers; the audit's 7,836, 63 min.

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

## Water reads as ground-level returns, not as class 9 (093/093l/2019, #19, 2026-10-12)

In the two tiles under the Maxan Creek delta (`bc_093l040_3_4_1`, `_3_4_2`), every return is
class 1, 2 or 7: no class 9, no withheld points, no overlap flag. Bulkley Lake's surface returns
are class 1, about 4.6/m², flat (712.5–712.8 m), level with the ground at the shore. So a canopy
height model over water reads 0 m, the same as a meadow, unless water is found some other way.
The meadow beside it is 77% class 2; the lake has no class 2 at all. `pc_readme_chm()`
(`scripts/readme_functions.R`) masks a cell with no ground return within 5 m, which took 41% of
that window as water and left no cell with a height under the forested south-west strip
(560,000 cells checked). Measured on these two tiles only; whether other deliveries classify
water as 9 is not established here.

## What this does not establish

- The 6 files damaged at source (#32) have no sample and no list. One of them, `092b082_2_3_3`,
  has a CanElevation COPC copy whose octree sums to the header's 102,305,189 points (2026-10-18), so
  its classes could come from that copy; the build does not do so.
- A sample reads the first chunk, three spread chunks and the COPC levels. A file whose chunk table
  is intact but whose data is damaged further in would pass it; the 6 were found because their
  tables are zeroed (#32).
- A tile that holds some ground is not shown to hold enough for a DEM; only the zero case is
  counted.
- The water reading of the no-ground tiles rests on classes and return counts, not on a water layer.
