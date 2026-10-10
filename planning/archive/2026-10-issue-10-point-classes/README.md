## Outcome

Measured which of the 9,649 indexed LidarBC point clouds are ground-only, by reading points: a
sample of every file (first 100,000 points plus a chunk at 25/50/75%, and COPC levels 0–1 where
an item has one), then a whole-file read of every file a sample called ground-only or
groundless, since a sample can only miss a class. Ground-only turned out to be one tile; the
bigger case, which the issue had not asked about, is 57 tiles with no ground at all. On the
user's decision, items read whole now carry `classification:classes` (the STAC classification
extension) on their `laz` asset; the `nge:` prefix was questioned and its rename filed as #12.
Four code-check rounds each found a defect inside the previous fix, in how the probe's and the
build's caches agree on files and ETags. Round 3 named the mechanism (two derivations of "which
files, at which ETag"), fixed by the build writing `class_targets.jsonl` before its class check.
The loop ended by an enumeration of every class-cache refusal and its remedy (`findings.md`).
Not yet published: publishing goes with the release.

## Measurement

Durable record: [`research/laz_classes.md`](../../../research/laz_classes.md).

- Ground-only: sampled 3, **confirmed 1** (`092g028_1_1_1`). The other two hold class 1; one was
  ground-only in its first 100,000 points only, so the first points alone misled once.
- No ground: sampled 70, **confirmed 57** (55 water-like, 2 never classified).
- COPC levels 0–1 never disagreed with the laz samples (1,964 items).
- A header density screen at or below the 5th percentile of the mapsheet-year catches all 58
  (488 flagged); this turned "sample all 165,667 files for #2" (about 350 GB, 20 h) into
  "sample the low-density tail".
- Cost: sample 2.12 MB and 4.2 s per file (median), 20.4 GB and 72 min at 16 workers; whole
  reads 1.57 GB for 73 files.
- Wrong turn kept: the plan review's first suggestion was to validate no-COPC deliveries by
  agreement with COPC ones; whole reads of every flagged file replaced that, because mixed is
  certain and only absences can be wrong.

## Evidence

`logs/20261010_*_laz_classes_*.log`, `logs/20261010_*_catalogue_build_classes.log` (gitignored;
the research file holds the numbers).

Closed by: PR #13
