# Code-check round 4 (#17): diff 62f7394..HEAD, excluding planning/

Checked read-only against data/build (class_targets.jsonl, classes.jsonl last record per id,
headers.jsonl, copc_headers.jsonl, all 174,282 items/*.json), the sweep, retry and build logs, and
published items. Tests: 337 passed, run on a `git archive HEAD` copy.

What holds: all six CLASSES_UNREADABLE URLs and ETags match class_targets.jsonl and headers.jsonl.
Each file's last sample record is "LazrsError: IoError: no chunks available in chunk table".
Point counts and "of N MiB" match the header and file:size. Every file is LAS 1.4. The items give
629 lists: 12 ground-only, 312 no ground, 305 mixed. The no-ground class-set counts, the 53
mapsheet-years and their top counts all match. Outside the old screen there are 61 flagged files
(60 no ground, 1 ground-only), with a median percentile of 21.2, 15 above the 50th and 11 above the
90th; the by-mapsheet-year counts and the 230 false alarms there match too. All of the class
shares match (1: 172,833, 2: 173,891, 3-5: 14,933 = 8.6%, 12: 76,120, 9: 5,647, 18: 4,927), and so
do the top sets. Sample cost matches: 2.63/2.95 MB, 3.82/7.11 s, COPC 5.15 MB over 13,969. The
sweep read 378 + 68 = 447 GB. The log gives 148,896 reads in 19:12:54, 42 errors (31 + 4 + 1 + 6),
6 failing on retry, and a 2 h 17 min build. The 12 ground-only lists are byte-identical to the
published 0.3.0 ones. The description reads in the right direction, unflagged meaning that the laz
samples merged hold ground and a class outside {2, 7, 9, 18}, and problem_add is used for every
merge.

## Findings

- **[claim]** research/laz_classes.md:53-54: "a sample that misses a file's ground flags it, and
  its list then shows the ground". That is the mechanism for only 73 of the 305 false alarms. For
  232, a sample was ground-only: in 223 of them only the first 100,000 points were all class 2,
  and in 9 the laz samples merged held nothing but ground, noise and water. This is common in
  `093g/2019` and `093j/2019`, whose files are sorted by class. Example:
  `093g097_1_4_4`, with first `{2: 100000}` and the 25/50/75% chunks class 1 and 7. Shown by
  classifying each mixed list's sample records with `verdicts()`'s logic over
  data/build/classes.jsonl.
- **[claim]** NEWS.md:14-16: "The sweep found **59 groundless files** outside the old screen … 11
  are denser than 90% of their mapsheet-year." Of those 59, only **10** are above the 90th
  percentile. The 11th is the audit's `082g002_2_2_2` (95.9), which is not one of the 59; 11 is
  the figure for all 61. The same sentence, "59 groundless … beyond the audit's 2", also treats
  the audit's 2 as groundless, but one of them (`102i090_2_1_4`) is ground-only.
- **[claim]** CLAUDE.md:79-80: "61 of the groundless lay outside the old 10th-percentile density
  screen". 60 are groundless and 1 is ground-only (`102i090_2_1_4`, the noise tile), as
  research/laz_classes.md:62-63 says correctly. "so no density screen finds them" also
  overstates: the research's wording is "no density screen short of nearly everything".
- **[claim]** scripts/catalogue_build.py:239-240: "no reader can recover the remaining points"
  (and research/laz_classes.md:210, "have no sample at all"). For `092b082_2_3_3`
  (`092b/2019`), the item's own `copc` asset, NRCan's
  `Vancouver_Island_Sunshine_Coast_2018/bc_092b082_2_3_3_xyes_8_utm10_2019.copc.laz`, looks whole.
  Its octree hierarchy sums to 102,305,189 points, equal to the header, and its last node ends at
  byte 741,379,552 of 741,574,799. The 5 nodes at the end of the file plus 3 from the middle
  (854,056 points) decompress to classes 1/2/7. So that tile's points are recoverable from the
  item's own `copc` asset, and a class list could be derived from it. Issue #32 says "Whether that
  copy's data is whole is not checked"; this check answers it. Probe: laspy 2.7 `CopcReader.open(url)`, then
  `load_octree_for_query(r.source, r.copc_info, r.root_page)`, then
  `r._fetch_and_decompress_points_of_nodes(nodes[-5:] + …)` (about 9 MB read).
- **[claim]** research/laz_classes.md:30-31: "a file whose whole read its sample does not flag can
  no longer occur". It still can: any good whole read in classes_full.jsonl that a current sample
  does not flag, such as a research `--confirm` read. classes_check refuses it as "read whole,
  but its sample does not flag it, and it is not recorded", and the CLASSES_REQUIRED comment at
  scripts/catalogue_build.py:126-128 still describes such reads as a live case. The sentence and
  the comment contradict each other. What is true is that no such file exists in this build.

## Resolution (2026-10-18)

All five reproduced and fixed: false-alarm causes recomputed (232 first chunk ground-only, 73 laz
samples groundless); NEWS now says 10 of the 59 and names the audit's two verdicts; CLAUDE.md says
"no ground or only ground" and "short of nearly every file"; the CLASSES_UNREADABLE comment says
"from the file" and names 092b082_2_3_3's COPC (hierarchy re-summed here: 5,394 nodes, 102,305,189
points, last node ends at 741,379,552 of 741,574,799); research says no such file is in this build
and one would be refused. #32's body records the COPC check.

The loop ends by enumeration rather than another round: every number added by these fixes (232, 73,
59, 10, 61, 11, 102,305,189, 5,394, 854,056, 741,379,552) was re-measured in this session or in this
round's own checks, and the rest of the diff's numbers are in this round's "What holds".
