# Code review, round 2: branch 2-index-the-rest-of-pointcloud-laz (be4bfbd...HEAD, scripts + tests + data)

Focus: round 1's fixes in e4f198b. I read every changed file in full. Probes ran in a scratchpad copy of
the repo, against copies of `data/build/{class_targets,classes,classes_full,headers}.jsonl` taken at
2026-10-11 08:58 UTC. The working tree was not touched. `uv run pytest -q` in the copy: 243 passed.

## Findings

- **[bug] scripts/catalogue_build.py:856-862: `--classes-record --limit N` rewrites the committed
  `data/classes_required.json` from the slice.**
  `--limit` exists so that "a partial build cannot be published": its output goes to `data/build-limit`.
  But `CLASSES_REQUIRED_PATH` is the absolute path to the committed file, and the record block does not
  check `args.limit`. Under `--limit`, `screened` is also the density screen of partial groups, and
  `good` covers only the slice. So the committed list is replaced by the flags of N files, judged
  against the wrong screen, and the run returns 0.
  Verified in the copy with `_main_with_required(..., required=[PC id], samples=[PC flagged],
  argv=["--limit", "1", "--classes-record"])`: rc 0, and the list file went from `[PC]` to `[]`.
  Fix: refuse `--classes-record` together with `--limit`, as the `--limit` docstring promises.

- **[fragile] scripts/catalogue_build.py:856-862: `--classes-record` lowers the committed list without a
  word, on exactly the machine the list exists to protect.**
  The list is rebuilt only from samples in the local `classes.jsonl` that are good at the current ETag.
  Two cases record a shorter list, and the same run passes, so nothing refuses it:
  - A machine without the audit's samples (fresh checkout, CI, a cleaned `data/build`). This is the
    scenario round 1's finding 2 was about.
  - A required file re-delivered under the same key. The build never re-samples a file outside the
    screen, so its old sample is stale. It drops off the list, and from then on its class list exists
    only in the cache again.

  The only signal is the info line `recorded N ids`. `records_write` refuses the same kind of lowering
  for GROUPS and COPC_PAIRS unless given `--force`.
  Verified in the copy: `required=[an id]`, no cached samples, `--classes-record`: rc 0, and the file
  now reads `[]`.
  Fix: keep every recorded id unless `--force` is given (union with the old list), or refuse a record
  that would drop one.

- **[fragile] scripts/catalogue_build.py:126-132, 632-664, 854-857: round 1's two class lists outside the
  screen are still cache-only, because their flagging samples can never count as "good".**
  The comment on CLASSES_REQUIRED says the list covers "the first increment's survey of every file". The
  #10 survey's samples carry no ETag, so `record_good` is False for all of them:
  - 8,548 of the 26,355 cached samples for current targets are no-ETag survey records.
  - 7 more are errors.

  Such a sample is never in `good`. So it cannot set off the "flagged outside the screen and not in the
  list" check, and `--classes-record` cannot record it. Measured on the copied caches:
  - 340 whole reads are good.
  - 2 of them are outside the screen and flagged by no good sample:
    `082-082k-2017-pointcloud-bc_082k017_1_3_3_xyes_8_utm11_180827` (classes 1, 2, 7) and
    `092-092g-2016-pointcloud-bc_092g028_2_1_1_xyes_8_utm10_20170714` (classes 1, 2).
  - Both are flagged by their no-ETag survey sample.

  `classes_attach` publishes both lists from `classes_full.jsonl` alone. On a cache-less build they
  disappear and the build passes: round 1's finding, still open for these two. Running `--classes-record`
  today would not add them. Both are mixed-class files, so the loss today is two lists, not a
  ground-only or groundless file. The mechanism is that "flagged" here means flagged by a sample that
  is good at the current ETag, and a whole read made for any other reason is left uncovered.
  Fix: derive the required set from what is actually published. Every good whole read outside the
  screen must be in CLASSES_REQUIRED, or `classes_check` refuses. `--classes-record` should record those
  ids, not only the ids the current flags pick out.

## Checked and found sound

- **Fix 1 (EXCLUDE re-check through `item_create`).** All 11 entries' cached headers (header_version 2,
  mins equal to the recorded ones) raise `ValueError` from `item_create`, each for its recorded fault:
  - the box sides: 092h003, 082j025, 092g010, 092g020, 092h011, 092k005, 092k043;
  - the centre outside its sheet: 082m081, 093c080 under 092B and under 092N, 093n052.

  Nothing else on that path raises. The box and sheet checks run before any transform, and
  `CRS.from_wkt` receives WKT that `header_read` already parsed and re-serialised. All 11 names carry
  valid date tokens. The mins are compared first, so a moved box is still named by the mins message.
  - Residual, not a defect: a file re-delivered with a different fault, such as 093n052 losing its CRS,
    still raises `ValueError` and stays excluded under the old reason, without failing the build. It is
    still not published.
- **`classes_check` and `want` ordering.** The list is recorded after the screened samples are probed
  and before the whole reads it drives, so one run records and then requires the same set. A required id
  that is no longer listed is ignored (`k in by_id` / `k in current`), which `--limit` needs. A required
  id at a new ETag is read whole again: `want` includes it whenever its prior read is not good, and that
  holds even when its sample is stale and no longer flags it.
- The flagged-outside-screen check rejects an unrecorded flag only for unscreened files, which is
  correct. A screened flag is re-derived on any machine.
