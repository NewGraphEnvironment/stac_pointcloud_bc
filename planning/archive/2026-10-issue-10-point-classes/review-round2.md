# Code-check round 2 (#10, branch 10-some-point-clouds-hold-ground-returns-on, HEAD 5bab91b)

## Findings

- **[severity: bug]** scripts/laz_classes_probe.py:435-439 with scripts/catalogue_build.py:339-342.
  A whole-file record can get stuck in `classes_full.jsonl`, and the build's advice cannot clear it.
  This is the round-1 stale-ETag defect again, from a different direction. `--confirm` re-reads
  only `confirm_ids(<current sample records>) ∩ items`. Records in `classes_full.jsonl` are never
  retired, and `classes_attach` checks every one of them. Take a file that was read whole at ETag E1
  and then re-delivered at E2:
  1. The build refuses: "read at ETag E1, listed at E2 ... re-run laz_classes_probe.py, then with
     --confirm".
  2. The user follows that. The sample re-run reads the file at E2. The new file has ground, or
     holds a class outside {2, 7, 9, 18}, so the sample does not flag it.
  3. `--confirm` no longer wants the item and never touches its E1 record.
  4. Every later build refuses with the same message. Re-running the advice changes nothing, and
     the only way out is editing the gitignored cache by hand.

  I reproduced this with `probe_all`, `confirm_ids` and `classes_attach` against temp caches
  (scratchpad/sim/sim.py). The final output was `want after re-sample: set()`, then
  `full record etag: E1`, then the stale-ETag problem again.

  The same trap has two other entries:
  - A failed full-read record (`"error"`) whose item a later sample no longer flags gives "the
    class read failed" on every build.
  - A record for a file that leaves the build (deleted upstream, or added to EXCLUDE) gives "a
    class read of a file that is not in the build", with no remedy named.

  Possible fixes: have `--confirm` also re-read every id that already has a record in `--full` but
  no good record at the current ETag, so the build's advice converges. Or have the build's
  messages say to drop that line and update `CLASSES_READ`.

- **[severity: fragile]** scripts/laz_classes_probe.py:252-253 and :434. `done` tests
  `record_etag(r) == current.get(k)`. When the header cache has no entry for an item's laz url,
  `current[k]` is `None`. A record with no ETag then also gives `None`, so `None == None` counts as
  current. This guard fails toward pass, and it applies to every sample record written before
  ETags were kept (all 9,658 lines of `classes.jsonl` today). Those records would be kept rather
  than re-read, which is the opposite of what the probe_all docstring promises. It is only
  reachable when `headers.jsonl` is missing urls that `items/` has, for example after the cache was
  deleted and a rebuild failed partway. That makes it low-likelihood, but treating a missing
  current ETag as "unknown, read again" closes it.

## Checked and found sound (no action)

- **ETag form is the same on all three sides.** The listing (`s3:ETag`, quotes stripped), HEAD
  (`HttpRangeFile.etag`, stripped) and GET (`laz_full`, stripped) all give the multipart form
  `24aaec14f495b1bf45d50174e795a847-5`. A live HEAD returned exactly the `headers.jsonl` value, and
  all 73 `classes_full.jsonl` ETags equal the header-cache ETags.
- **The header cache is refreshed before the build refuses.** `headers_fetch` appends the new ETag,
  and later lines win, before `classes_attach` runs. So the probe's `current` sees a re-delivery by
  the time the build reports one.
- **`current` covers every item main() passes.** It is built after the `--ids`/`--limit` filtering,
  and `--confirm` filters to a subset of it.
- **URL keys agree.** `laz_url()` unquotes `%20` hrefs into the space-bearing listing urls that key
  `headers.jsonl` and `classes_full.jsonl`. No href is missing from the header cache.
- **Every number in research/laz_classes.md, CLAUDE.md, README and the collection description
  matches what I recomputed** from the caches:
  - 3 sampled ground-only, 1 confirmed; 70 sampled groundless, 57 confirmed.
  - 40 [1,7], 15 [1,7,9,18] and 2 [0].
  - Single-return share 93.5–100%.
  - Density screens of 200/48, 488/58, 971/58 and 300/57; the confirmed maximum is the 2.96th
    percentile.
  - 1.57 GB full reads; CLASSES_READ totals 73.
  - The class-set table.
- **The "exact" claims hold.** A sample can only miss a class, and every unflagged item had a
  class that rules out each verdict.
- `uv run pytest -q tests/`: 139 passed.
