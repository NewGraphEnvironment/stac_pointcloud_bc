# Index the rest of pointcloud/*.laz (#2)

## Outcome

The build now walks the objectstore's eight NTS blocks and indexes every
`<block>/<sheet>/<year>/pointcloud/*.laz`: **174,282 items in 225 mapsheet-years**, up from 9,649
in 11. It is also the release that publishes the renamed fields (#12), the class lists (#10) and
`lidarbc:delivery` with a `related` link to stac-elevation-bc (#5). Per-group listing floors and
COPC pair counts are committed records (`data/pointcloud_groups.json`, `data/copc_pairs.json`),
not code constants. Items are validated against checked-in copies of the crate schemas
(crate#23).

The full listing surfaced faults the first increment never showed, each triaged into a named,
self-checking entry: 2,008 compound CRSs written vertical-first (read swapped); 11 files with
headers no item can be built from (`EXCLUDE`); 985 files in eight 2017 deliveries with no CRS at
all (`EXCLUDE_DELIVERIES`, the user's decision, follow-up #15); 26 CanElevation name matches
that are not copies (`data/copc_not_copies.json`).

The class check moved into the build as a density screen (10th percentile per mapsheet-year),
point samples, and whole reads of what a sample flags. Four review rounds then reshaped it: what
the build publishes is now one derived set (`classes_published`: the screened files a current
sample flags, plus the committed `data/classes_required.json`) that drives the reads, the check
and the attach, so a local cache can speed a build up but never add a list. Rounds 2, 3 and 4
each found a defect inside the previous fix; the loop ended by enumerating the one publish path
and the one committed write, each arm pinned by a test that a mutant turns red.

What was learned: **the density screen gathers the files without ground but cannot catch them
all.** The 5% audit found one at the 96th density percentile, so the plan's fallback (widen the
screen) does not work; that decision went to the user. And **a two-day file name is the first
and last day flown**, which the docs fact-check and a review of the fix found in two steps
(10,603 items given the last day; then 80,337 files distrusted for a range ending in a later
year). GPS times settled both (`research/filename_dates.md`).

## Measurement

- **Listing** (2026-10-10): 175,278 `pointcloud/*.laz` in 233 mapsheet-years (2026-10-06: 175,317).
- **Build**: 53 min with headers and COPC headers cached, peak RSS 4.09 GB; validation of
  174,282 items in a process pool, 765 s. The first cold build: 9,028 s, headers about 20/s at
  16 workers, peak RSS 1.17 GB. Serial validation would have been about 5 h.
- **COPC**: 13,970 items linked over 28 mapsheet-years; largest box offset 0.01 m; horizontal
  EPSG equal in every pair. 26 non-copies hold 9% to 99.6% of their LAZ's points.
- **Classes**: 17,552 screened, 347 flagged, 349 read whole; published lists 12 ground-only
  (7 of them near-empty or noise tiles), 253 no ground, 84 mixed. Screen samples: median
  2.44 MB, 6.7 s; 3 h 10 min at 16 workers.
- **Audit**: 7,834 of 7,836 sampled, 9 flagged, 2 misses; rate 0.026% (95% 0.003% to 0.092%),
  so about 38 (5 to 137) of the 148,894 unsampled files hold no ground or only ground with no
  list. Inside the screen the rate is 1.5%, about 59 times higher. Changed the plan: the screen
  is kept, its limit is stated, and full sampling (about 20 h, 400 GB) went to the user.
- **Dates**: 30 two-day files from 15 deliveries and 12 same-day files from 6, all GPS days
  within the named days. Untrusted deliveries 42 -> 9; items 64,372 days, 44,744 ranges,
  65,166 years.
- **Published-vs-build** against the 0.2.0 bucket: 0 of 9,649 differ beyond the expected
  changes; 164,633 new. Sync dry run: 174,283 uploads, 0 deletes.

Wrong turns kept in `progress.md` and `findings.md`: three rounds of fixes to the class-list
record before the structural fix; "widen the screen" disproved by the audit; the date rule
fixed twice, first for in-year pairs only.

Research: `research/laz_classes.md`, `research/canelevation_overlap.md`,
`research/filename_dates.md`.

## Evidence

`logs/20261010_*`, `logs/20261011_*` (gitignored). Reviews: `review-plan.md`,
`review-round1.md` to `review-round5.md`, `review-docs.md` in this directory.

Closed by: the PR for branch `2-index-the-rest-of-pointcloud-laz-165-667` (publish pending the
user's go).
