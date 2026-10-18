# Code-check round 1: branch 17-sample-every-file (3b8e543...HEAD)

Reviewer: subagent, 2026-10-17. Suite at HEAD: 335 passed (`uv run --frozen pytest -q`, 8 min 39 s).

## Findings

- **[severity: bug (prose, published)]** `scripts/catalogue_build.py:272-273` (`DESCRIPTION`):
  "A sample can miss a class but never add one, so a file whose sample held ground and some
  other class has both, and its item carries no list." The second half is false, and this text
  is published as the collection description. A file is flagged, read whole and listed when
  *any* verdict is ground-only (`laz_classes_probe.verdicts`: the first 100k points alone, the
  laz samples merged, or the COPC sample) or the merged sample has no ground. So:
  - a sample holding ground plus only noise or water (7, 9, 18) is "ground and some other
    class", but it is flagged as ground-only and its item does carry a list;
  - a sample whose merged counts hold ground and class 1 is still flagged when its first 100k
    points are all ground. Measured in the local cache (`data/build/classes.jsonl`): **24 of
    the 349 flagged files** have merged laz samples holding ground plus a class outside
    {2, 7, 9, 18}, and they carry lists. Example: `093g096_2_3_3` (first `{2: 100000}`,
    at_0.25 `{1: 50000}`, at_0.5 `{2: 50000}`, at_0.75 `{1: 50000}`), which is in
    `data/classes_required.json` and is listed.

  The implication runs the wrong way. README.Rmd states it correctly: an item *without* a list
  holds ground and at least one class besides ground, noise and water. The description should
  say the same thing in that direction, not "ground and some other class → no list".

- **[severity: fragile, minor]** `scripts/catalogue_build.py:969-970`:
  `problems = classes_unreadable_check(...)` and then `problems |= classes_check(...)`. For the
  same URL the right side wins. Take a `CLASSES_UNREADABLE` file that starts to read and whose
  sample flags it. `classes_check` reports it as "flagged by a sample of a file the build need
  not sample ... record it with --classes-record", and that replaces the more useful "now
  samples; remove its entry". Following the advice shown records the id in
  `classes_required.json`, which is not the fix. The next build then refuses with "remove its
  entry", and the recorded id stays until a later `--classes-record --force`. The build still
  refuses either way, so nothing wrong is published. Only the operator is sent the wrong way.
  Merge the two messages, as the unrecorded branch of `classes_check` already does with
  `"; ".join`, or let the unreadable message win.

## Checked and found sound

- `CLASSES_UNREADABLE` ETags and error text match the local caches: `headers.jsonl` and
  `class_targets.jsonl` give the same ETags (`056c28d7...-9`, `54247648...-5`), and
  `classes.jsonl` records `LazrsError: IoError: no chunks available in chunk table` for both.
- An error record carries no ETag, so `sample_good` is False and `probe_all` samples each
  unreadable file again on every run, as the comment says. A re-delivery, a file that now reads,
  another error and a departed file are each refused, and `--limit` is exempt from the departed
  check only.
- README.Rmd's claim (an item without a list holds ground and another class, except the
  unreadable files) holds on the code path. An unflagged good sample means the merged laz
  sample holds class 2 and a class outside {2, 7, 9, 18}. Every kept file outside the
  carve-out must have a good sample or the build refuses.
- `laz_classes_probe.py` default mode samples with `current` and `match_copc=True`, as the build
  does, so its records are reusable as the docstring says.
- `catalogue_compare.item_expected_diff` deep-copies before it strips the added list, so
  `gained` in `main()` is computed on unmutated bodies. A changed list, a dropped list, or a
  list without its extension is still a difference.
- The collection gains no class-dependent field (`summaries` is `lidarbc:product` only), so
  only `description` changes at the collection level.
- No caller of the removed `catalogue_build.density_screen` or `SCREEN_PERCENTILE` remains.
- Mutation (in a scratch copy): putting the density screen back as `to_sample`, with sampling
  limited to it, fails 3 tests: `test_the_build_samples_every_file_whatever_its_density`,
  `test_a_dense_file_with_no_sample_is_refused` and
  `test_an_empty_point_sample_is_refused_not_passed`.
- Cost on the runner: the audit flagged 9 of 7,834 (0.11%), and their whole reads are at most
  about 330 MB each. Sampling dense files therefore does not make the whole-read step's temp
  disk a problem at 16 workers.

## Not flagged (pending by design)

- `DESCRIPTION`: "Most of the listed items hold no ground" and the class 3–5 sentence, and
  CLAUDE.md's source-facts bullet on classes (it still describes the 10th-percentile screen).
  These wait for the sweep (Phase 4).
