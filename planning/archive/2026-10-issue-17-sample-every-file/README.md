# Sample the point classes of every file (#17)

## Outcome

The build now samples every one of its 174,282 files for point classes, not only the 17,552 at or
below the 10th density percentile of their mapsheet-year, and reads whole each one a sample flags.
**629 items** carry `classification:classes`, up from 349. Because a sample can only miss a class,
an item without a list now holds ground and a class outside {2, 7, 9, 18}, and the collection
description says so. The published set is derived from samples alone:
`data/classes_required.json` is empty. Six files cannot be sampled because they are damaged at
source (#32): their point data stops part-way and the rest of the file is zero bytes. They are
named, keyed by ETag, in `CLASSES_UNREADABLE`, which refuses the build if one now samples, fails
otherwise, is re-delivered or leaves the build. `catalogue_compare.py` accepts a build that gives
an item a list and changes the description, and nothing else.

GitHub's HTTPS and the objectstore were unreachable from this machine for about 7 h on
2026-10-17 (SSH to GitHub kept working), so the plan was made from the repo's own record of #17
and the issue body diffed afterwards; nothing in it changed the phases. Four review rounds:
round 1 found the description stating the guarantee backwards and refusal messages overwriting
each other, round 3 found the overwrite class still open inside the fix, and the loop ended by
enumerating all 15 writes into a refusal map. Round 4, over the sweep's results, found five claims
in the documents wrong against the data (the false alarms' cause, 10 not 11 above the 90th
percentile, and that one damaged tile's COPC copy looks whole).

## Measurement

- **Sweep** (2026-10-18): 148,896 files in 19 h 13 min at 10 workers, 447 GB of range reads (378 GB
  laz, 68 GB COPC levels). 42 failures: 36 transient (sampled on re-run), 6 damaged at source.
- **Lists**: 629 = 12 ground-only (unchanged), 312 no ground (253 in 0.3.0), 305 false alarms (232
  flagged by an all-ground first chunk, 73 by groundless laz samples). Build that read the 280
  newly flagged files whole: 2 h 17 min; a warm build, 17 min.
- **What the 0.3.0 screen missed**: 61 files with no ground or only ground outside it, the audit's
  2 and 59 more, against its estimate of 38 (5 to 137). Median density percentile 21.2, 11 above
  the 90th. Settled the issue's question: no density screen short of nearly every file finds them.
- **Classes across the collection**: class 1 in 99.2% of files, classes 3–5 in 8.6%, class 12 in
  43.7% (the audit's 5% had given 99.2%, 9.0%, 44%).
- **Damaged files**: two downloaded whole and matched to their ETags at a 128 MiB part size; all
  six located by binary search over 1 MiB range reads. `092b082_2_3_3`'s CanElevation COPC octree
  sums to its header's 102,305,189 points.

The durable verdict is `research/laz_classes.md`.

## Evidence

`logs/20261018_*` (sweep, retry, the three builds, the compare); `review-plan.md`,
`review-round1.md` to `review-round4.md` here.
