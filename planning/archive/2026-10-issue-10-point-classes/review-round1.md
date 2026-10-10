# Code-check round 1: branch 10-some-point-clouds-hold-ground-returns-on

## Findings

- **[severity: bug]** scripts/catalogue_build.py:321 (`classes_records_load`), with
  scripts/laz_classes_probe.py:252 (`probe_all`). A failed whole-file read is written to
  `classes_full.jsonl` as `{"id", "error"}` with **no `laz` key**, and `classes_records_load`
  keys every line by `r["laz"]`. The first failed `--confirm` read therefore makes the build die
  with a bare `KeyError: 'laz'`, not the "the class read failed" refusal `classes_attach`
  provides. The error line stays in the append-only cache after a successful retry, so the
  build keeps failing even then, until someone edits the gitignored cache by hand. Reproduced in
  a scratch dir: `probe_all(..., probe=raises)` and then `probe_all(..., probe=succeeds)` on
  the same file give `classes_records_load` -> `KeyError 'laz'`. The test
  `test_a_class_read_applies_only_to_the_file_it_was_read_from` builds its failed record as
  `{"laz": PC, "error": ...}`, a shape the probe never writes, so it cannot reach the failure
  (code-check.md, "A fixture that cannot reach the failure mode"). The current cache holds no
  error lines (73 lines, 0 errors), so the v0.2 build is unaffected. Fix: write `laz` (and
  `id`) on the error record in `full_probe`'s failure path, or key the loader by id, or skip
  error lines that a later good line supersedes.

- **[severity: bug]** scripts/catalogue_build.py:336-338 with scripts/laz_classes_probe.py:236.
  When the ETag check refuses a stale read, it says to "re-run laz_classes_probe.py --confirm",
  and that does nothing. `probe_all` skips every id that already has a non-error record in
  `classes_full.jsonl`, and the stale record is one, so `--confirm` re-reads nothing. The build
  then refuses on every run, and the only way out is to delete cache lines by hand. Reproduced:
  a second `probe_all` over an id that has a good record makes zero probe calls. The same skip
  keeps `classes.jsonl`'s sample of the old delivery, so the re-delivered file is never
  re-sampled either. The remedy the message names has to work: compare `full.etag` (and give
  the sample record an ETag) against the current object in `probe_all`'s `done` set, or change
  the message to name what actually clears it.

- **[severity: fragile / published claim]** scripts/catalogue_build.py:127-131 (`DESCRIPTION`,
  "Every file here was sampled"), and the README/index.html sentence "Every file a point sample
  flagged was read whole". The build never reads `classes.jsonl`, so nothing checks that every
  built item has a sample, or a sample of its current ETag. `CLASSES_READ` counts only the
  whole-file reads per group. `INCREMENT` deliberately accepts listings that grow past their
  recorded counts. So a file added to a group, or re-delivered, is published unsampled while the
  collection description says it was sampled. If that file is groundless or ground-only, it gets
  no `classification:classes` and no gate fires. The claim holds for today's 9,649 items
  (summary: recorded 9649, unrecorded 0, recorded but not in build 0), but the code does not
  enforce it. Fix: have the build refuse any kept item without a good sample record, matched by
  id and ETag, as it already does for the full reads.

## Verified, no finding

- research/laz_classes.md against `laz_classes_probe.py --summary` and a separate density
  recomputation:
  - the 3 sampled ground-only tiles and 1 confirmed; 70 sampled no-ground and 57 confirmed
    (26/14/15/2 per group);
  - 13 with a little ground, holding 2 to 316,908 points;
  - 40 tiles of classes {1,7} plus 15 of {1,7,9,18}; single returns 93.5-100%;
  - the class-set table; class 4 in 898 items;
  - the first 100k points vs the merged samples disagree once; laz vs COPC disagree 0 times;
  - every confirmed tile is at or below the 2.96th percentile;
  - the screen table: 200/48, 488/58, 971/58, and 300/57 at <5 pts/m²;
  - cost: 2.12 MB and 4.23 s median, 20.4 GB and 9.4 GB totals;
  - extrapolation to 165,667 files: about 351 GB and about 20.6 h.
- `CLASSES_READ` matches the cache per group (32/1/17/19/2/2 = 73), and 73 built items carry
  `classification:classes`.
- The 9 sample failures in `classes.jsonl` were all on items with a `copc` asset. Two name the
  CanElevation host; the other seven are RemoteDisconnected, with no host recorded. "Mostly
  against the CanElevation bucket" is plausible, but only 2 of the 9 are shown. Not raised as a
  finding.
