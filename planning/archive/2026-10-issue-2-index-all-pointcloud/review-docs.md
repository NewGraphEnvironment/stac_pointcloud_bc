# Docs fact-check, branch 2-index-the-rest-of-pointcloud-laz-165-667 (0.3.0)

Scope: `git diff be4bfbd...HEAD` of NEWS.md, README.Rmd, CLAUDE.md, research/, and the comments,
docstrings and DESCRIPTION in scripts/catalogue_build.py, laz_item.py and laz_classes_probe.py.
Every number below was re-derived from the build (`data/build/items/*.json` scanned in one Python
process, `headers.jsonl`, `classes*.jsonl`, `class_targets.jsonl`, `classes_audit_ids.txt`), the
committed `data/*.json`, the logs, and the published 0.2.0 copy. findings.md/progress.md were not
used as evidence. Nothing under `data/` was written; scratch scripts are in the session scratchpad.

## Findings (WRONG / UNSUPPORTED / misleading)

1. **README.Rmd:148: "Their dates are the delivery's year (`start_datetime` / `end_datetime`)" is
   wrong for 28,780 items (16.5%).** They carry a single-day `datetime` taken from the file name,
   with no start/end: 28,152 from 8-digit tokens and 628 from 6-digit tokens. The largest groups are
   082e/2025 (3,460), 094p/2025 (2,574) and 093j/2025 (2,298). In 0.2.0 every item had a year range
   (published copy: 6,475 `filename` and 3,174 `path`, none without `start_datetime`), so this is
   new in 0.3.0, and NEWS's "Dates." bullet does not say so either. A reader who filters by
   `datetime` would act on it.
   A related point for the code owner, outside the docs: 10,603 of those items have names carrying
   two different dates (`..._20250508_20251013`), and `_DATE` takes the **last** one (that item gets
   2025-10-13). `date_parse`'s own docstring says file-name dates can be processing dates. Whether
   the last token is the acquisition date was not measured.

2. **README.Rmd:139: "a random 5% of the other files puts about 40 more without a list in the same
   state" is wrong.** "The same state" refers back to "hold no ground at all". The ~40 estimate
   covers no ground **or** ground-only. Of the audit's 2 misses, one has no ground
   (`082g002_2_2_2`) and one is a ground-only noise tile (`102i090_2_1_4`: class 7 29,724, class 2
   2). The no-ground share alone extrapolates to about 19. CLAUDE.md and NEWS say "no ground or
   only ground", which is right.

3. **The "about 40 (5 to 145)" estimate uses the wrong population** (research/laz_classes.md:
   "roughly 40 files among the 156,730 unsampled (5 to 145)"; NEWS "about 40 items without a list
   (95% interval 5 to 145)"; CLAUDE.md "about 40 unlisted files"; README "about 40 more").
   156,730 is the unscreened set, not the unsampled set. The audit sampled 7,836 of them, and its 2
   misses now carry lists (`data/classes_required.json`). Applying 2/7,834 to the 148,894 files that
   were neither screened nor audited gives **38 (Clopper-Pearson 95%: 4.6 to 137)**. The rate itself
   (0.026%, 0.003% to 0.092%) re-derives exactly. So "about 40" is defensible, but "among the
   156,730 unsampled" is false and the upper bound should be about 137.

4. **research/laz_classes.md "Cost (0.3.0)": "median 2.42 MB and 6.3 s a file (p95 21.4 s)" is not
   a 0.3.0 figure.** It is the `--summary` line over all 33,641 cached samples, and 8,253 of those
   are the first increment's survey samples from 2026-10-10 (no ETag). Measured per run:
   - 0.3.0 screen (17,552): median 2.44 MB, 6.7 s, p95 26.0 s.
   - Audit (7,834): median 2.65 MB, 6.5 s, p95 7.7 s.

   The sentence above it ("about 21 h and 380 GB at the audit's pace and the median below") then
   mixes the audit's pace with the pooled median. At the audit's own median it is about 416 GB.
   The 21 h figure holds: 63 min for 7,836, scaled to 156,730.

5. **UNSUPPORTED, catalogue_build.py EXCLUDE_DELIVERIES comment and `_NO_CRS` reason (logged on
   every build): "One DEM tile of each delivery declares NAD83(CSRS) / UTM 8N or 9N (EPSG:3155,
   3156)" and "only the LASzip VLR".** No artifact in the repo or logs shows the DEM reads or the
   VLR lists. `headers.jsonl` keeps no VLR list, and the only trace is planning/active/findings.md
   (lines 126 and 127, which also say "Not every DEM tile was read"). What the artifacts do show
   holds: all 985 files of the eight deliveries have no `crs_wkt`, and no other file lacks one.

6. **Minor imprecision, laz_item.py `nts_sheet_bounds` docstring: "over the 175,278 listed files,
   4 fail".** Re-running `item_create` offline on the 11 EXCLUDE headers confirms exactly 4
   sheet-check failures (082m081, 093c080 x2, 093n052). But 985 no-CRS files and 7 bad-box files
   are refused before the sheet check, so 992 of the 175,278 were never tested. "Of the 174,286
   that reach the check, 4 fail" would be exact.

7. **Minor, README.Rmd:153: "three have a box no tile could have (from the UTM origin, or thousands
   of kilometres wide)".** Only 092h003 runs from the origin (mins 0,0,0), and only 092h011 is
   thousands of km wide (2,685 km). The third, 082j025, starts at easting 0 but northing 5,562,688,
   and is 641 x 1,437 km. Neither phrase fits it.

8. **Misleading over time, the collection DESCRIPTION (catalogue_build.py): "...and from a random 5%
   of the rest".** That is true of 0.3.0, but the audit is a research run (`laz_classes_probe.py
   --audit`), not a build step. The monthly rebuilds (#4) will keep publishing this sentence while
   new deliveries' unscreened files get no random sample. "A few of them hold no ground either" is
   also slightly off: one of the two misses holds 2 ground points (ground-only noise).

9. **Rounding nit, research/laz_classes.md: "about 58 times higher".** 1.498% / 0.0255% = 58.7,
   which rounds to 59.

10. **Nit, research/laz_classes.md: "`[1, 2, 7]` 3,153".** That counts LAZ samples only. With the
    COPC levels merged, as for the other verdicts, it is 3,208. Every other class figure in that
    paragraph is the same either way. Say "LAZ samples" or use 3,208.

## Claims checked

| claim | where | artifact | re-derived | verdict |
|---|---|---|---|---|
| 175,278 files in 233 mapsheet-years, walk of 2026-10-10 | CLAUDE.md, NEWS | pointcloud_groups.json; final log block sums | 233 / 175,278 | OK |
| eight NTS blocks | CLAUDE.md, NEWS | final log | 8 blocks (082..104) | OK |
| 11 files held out by EXCLUDE | CLAUDE.md, NEWS, README | catalogue_build EXCLUDE; final log | 11 | OK |
| 4 hold 0 or 1 points / 3 bad box / 3 outside sheet / 1 CRS contradicts | NEWS, README | headers.jsonl; item_create offline | 3x0 + 1x1; 092h003, 082j025, 092h011; 082m081, 093c080 x2; 093n052 | OK (see 7) |
| 985 files, eight 2017 deliveries, no CRS | CLAUDE.md, NEWS, README, code | headers.jsonl crs_wkt empty | 985, exactly those 8 | OK |
| DEM declares UTM 8N/9N; only LASzip VLR | code comment/reason | none | not in artifacts | UNSUPPORTED (5) |
| 174,282 items | all | items/ | 174,282 | OK |
| 225 mapsheet-years, up from 9,649 in 11 | NEWS | items; published 0.2.0 | 225; 9,649 in 11 | OK |
| 2,008 files, seven 2021 deliveries, vertical-first COMPD_CS | CLAUDE.md, NEWS, compound_reorder | 20261011_0014 log CRSError lines | 2,008 in 082l, 092h, 092i, 092p, 093a, 093i, 093p (all 2021) | OK |
| 42 deliveries with disagreeing years; first increment had 4 | CLAUDE.md, NEWS | final log; items fdate vs dir year; 0.2.0 | 42 (set equal); all items path-dated; 0.2.0: 4 | OK |
| only 092p/2017 mixes a day token with no token | CLAUDE.md, NEWS | items | 8 groups mix filename/path; only 092p/2017 has day tokens (208) vs none (127) | OK |
| dates are the delivery's year | README:148 | items | 28,780 carry a day datetime | WRONG (1) |
| 13,996 name pairs; 26 not copies, all VISC_2018, fewer points | CLAUDE.md, NEWS, canelevation | copc_pairs.json sum; copc_not_copies.json | 13,996; 26; all fewer | OK |
| 13,970 copc items in 28 mapsheet-years; 0.2.0 1,964 in 4 | CLAUDE.md, NEWS, canelevation | items; published copy | 13,970 / 28; 1,964 / 4 | OK |
| project table 7,847 of 7,873 / 3,866 / 682 / 1,575 | canelevation | items copc hrefs; build log | same | OK |
| 9% (8.45 M of 93.1 M) to 99.6% (85.75 M of 86.09 M); 20 of 26 multiples of 50,000 | canelevation | copc_not_copies.json | 9.07%, 99.60%; 20 | OK |
| 3,819 identical, 10,151 differ, max 0.01 m | canelevation, NEWS, laz_item | copc_pairs_measure log | same | OK |
| EPSG 3157 for 13,288, 2955 for 682; CGVD2013 dropped in 12,395; 1,575 LAS 1.2/1 to 1.4/6 | canelevation, NEWS | items; measure log | same | OK |
| 349 lists; 12 ground-only; 253 no ground; 84 mixed | all | items classification:classes | 349 / 12 / 253 / 84 | OK |
| ground-only detail: 2, 3, 10, 185, 270; 8,653/29,724 class 7 with 1/2 ground; 5 of 1.3 to 4.5 M; four 083d/2020 las2las 2021-03-20 | laz_classes | items; classes_full generating_software | same (1,260,211 rounds to 1.3 M) | OK |
| no-ground class-set counts; 51 mapsheet-years; 26/18/15 top; [0] = 092h032 | laz_classes | items; classes_full | same | OK |
| 17,552 screened | all | final log; density_screen re-run on headers | 17,552 | OK |
| 338 flagged in screen; 9 audit flags + survey's 2 = classes_required (11) | laz_classes | confirm_ids over good samples; classes_required.json | 338; 9 + 2 = 11 | OK |
| sampling recipe 100k + 3 x 50k, whole if <= 250k, COPC levels 0-1 | laz_classes | laz_classes_probe constants | same | OK |
| 6 samples failed on dropped connections, re-run fine | laz_classes | 0525 log (6 RemoteDisconnected), 1010 log (6 to read, ok) | same | OK |
| screened samples 3 h 10 min; audit 63 min | laz_classes | 0525 log 22:34 to 01:44; audit log 01:56 to 02:59 | same | OK |
| 156,730 unscreened; 7,836 drawn; 7,834 sampled; 2 unreadable | laz_classes, NEWS | 174,282 - 17,552; audit ids file; audit logs | same | OK |
| unreadable: 166 M / 1.08 GB, 95 M / 0.62 GB, LAS 1.4/6, ~6.5 B/pt | laz_classes | items | 165,982,257 / 1.075 GB; 95,430,699 / 0.625 GB; 6.48 / 6.55 | OK |
| 9 flagged, 2 misses; percentiles 95.9 (of 2,149), 17.7 (of 373) | laz_classes, NEWS, CLAUDE.md, code | audit log; density recomputed | same | OK |
| 0.026% (0.003% to 0.092%) | laz_classes, code | Clopper-Pearson recomputed | 0.0255% (0.0031% to 0.0922%) | OK |
| ~40 (5 to 145) among 156,730 unsampled | laz_classes, NEWS, CLAUDE.md, README | as above | 38 (4.6 to 137) over 148,894 | WRONG population (3) |
| about 40 more in the same state (no ground) | README:139 | audit misses | ~19 for no ground alone | WRONG (2) |
| inside rate 263 of 17,552 (1.5%), ~58x | laz_classes, code | listed verdicts in screen | 263, 1.498%, 58.7x | OK (nit 9) |
| 21 h, 380 GB | laz_classes | audit pace; medians | 21 h OK; 380 GB uses pooled median (416 GB at audit's) | see 4 |
| class 1 99.2%; 4 in 170; 5 in 532; 3 none; 3-5 in 702 (9.0%); 12 in 3,445 (44%) | laz_classes, NEWS, CLAUDE.md | audit samples | same | OK |
| class 12 never in first increment | laz_classes | 20261010 summary log class sets | none with 12 | OK |
| sets [1,2,7,12] 3,425, [1,2,7] 3,153 | laz_classes | audit samples | 3,425; 3,153 LAZ-only / 3,208 with COPC | OK (nit 10) |
| laz median 2.42 MB, 6.3 s, p95 21.4 s; COPC 3.17 MB | laz_classes Cost (0.3.0) | classes.jsonl | pooled incl. survey; 0.3.0 runs differ | misleading (4) |
| SCREEN_PERCENTILE: at 5 caught all 58 | code | survey (<= 3rd pct) | consistent | OK |
| 0.2.0 items unchanged beyond renames/schemas/delivery/classes/copc; 164,633 new | NEWS | independent diff of 9,649 published vs build | 0 differ; 174,282 - 9,649 = 164,633 | OK |
| 0.2.0 nge: names (5 item, 2 copc) | NEWS, README | published copy | exactly those | OK |
| three changes merged since 0.2.0 unpublished (incl. class lists) | NEWS | published copy has no classification:classes | none | OK |
| every item validates | NEWS | final log: validated 174,282, no invalid | OK | OK |
| tile median 1,660 x 1,417 m, none over 2.4 km, 1,302 under 100 m | laz_item | items proj:bbox | 1,659.6 x 1,417.0; max 2,342 m; 1,302 | OK |
| nts check: 4 of 175,278 fail | laz_item | item_create offline on EXCLUDE | 4; but 992 never reach the check | imprecise (6) |
| ~40 ms each, two hours in one process | catalogue_build validate_all | 765 s x 10 CPUs / 174,282 | 44 ms, ~2.1 h | OK |
| a handful of distinct WKTs | laz_item _crs_to_wgs84 | headers.jsonl | 32 distinct | loose, harmless |
| RemoteDisconnected on a CanElevation page; 10-minute walk | laz_item PAGE_ATTEMPTS | 20261011_0000 log traceback in canelevation_keys_list; walks took 1.5 to 6+ min | disconnect OK; duration loose | OK |
| 349 = 338 + 11; log 347 flagged, 349 read whole | NEWS, laz_classes | final log | same | OK |
| canelevation `Verified` / `Produced by` lines | research | logs exist | yes | OK |
