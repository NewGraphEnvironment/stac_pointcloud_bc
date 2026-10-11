# Code review, round 4

Commit 9884d5a. I read `scripts/catalogue_build.py` (classes_check, classes_published, classes_attach, the
class step of main()) and `scripts/laz_classes_probe.py` in full, plus review-round3.md.

**Method.** All probes and mutations ran in a scratchpad copy of the repo (rsync without data/build,
data/build-limit or logs). The caches were snapshotted read-only at 2026-10-11 09:32 UTC, while the `--audit`
run was still writing. That run started at 08:56 UTC, before the commit, so it runs the pre-commit code. The
suite in the copy: 253 passed. Nothing in the working tree was touched except this file.

## Findings

- **[bug] scripts/catalogue_build.py:890-897: `--classes-record --force` drops a recorded id that is still
  listed and not derived when its whole read fails in that run. The build then passes and publishes no
  list for it.**
  - **Why.** `found` takes only good reads (`record_good`) and current flags. A required id goes into `want`
    whenever its prior read is missing, failed or stale. If that read fails in this run (a 503, or a fresh
    machine with an empty `data/build`), the id is absent from `found`, and `--force` writes
    `required = found`.
  - **What follows.** `classes_check` then sees an id that is neither flagged nor required and raises
    nothing. `classes_published` excludes it, so its list disappears with rc 0. The log line misreports it
    as "1 no longer needed, dropped".
  - **What it contradicts.** The new help text ("drop recorded ids no longer listed or now screened and
    flagged") and the docstring of `test_classes_record_keeps_a_recorded_id_this_cache_cannot_support_unless_forced`
    ("it keeps PC even forced; only an id no longer listed can be dropped"). That test only covers a read
    that succeeds.
  - **Verified in the copy**, with `_main_with_required` and `full_probe` raising `OSError("503")`:
    - `[pc]` with `--classes-record --force` and an empty cache: rc 0, `classes_required.json` rewritten to
      `[]`, and the item carries no `classification:classes`.
    - The same with a stale prior read (`etag="old"`): rc 0, `[]`.
    - Without `--force`: rc 1, and `[pc]` is kept. That is the correct behaviour.
    - A follow-up plain build against the rewritten `[]`: rc 0, no list.

  An empty-cache build from the committed list before that run would have published the list. So this
  silently rewrites a committed file and drops a list.
  - **Fix.** Under `--force`, drop only what the help names. Keep
    `{k for k in CLASSES_REQUIRED if k in current and k not in inside & flagged}` and union it with `found`.
    Then a failed read stays required, and the same run refuses it.

- **[fragile, latent] scripts/laz_classes_probe.py:272-275 vs laz_item.py:474 / catalogue_build.py:873-874:
  the probe's samples and the build's samples carry the COPC href in different forms.** They agree today
  only because no CanElevation path needs encoding.
  - **Where the forms come from.**
    - The build's items carry `href_encode(pair url)`. `class_target` and `copcs` both take it from there,
      so the build agrees with itself.
    - `targets_load` (the `--audit` and default probe runs) takes `class_targets.jsonl`'s `copc`, which is
      the raw pair URL, and does not encode it. It does encode the laz href.
    - `item_probe` stores whichever form it is given in `rec["copc"]`, and `sample_good` compares by string.
  - **Measured on the snapshot:**
    - 13,970 targets have a COPC, and `href_encode` changes 0 of them. It changes 143 laz hrefs.
    - 3,693 latest sample records carry `copc`, and all equal both the raw and the encoded form.
    - 0 records lack a `copc` their target now has.
  - **What happens if a CanElevation path ever needs encoding** (a space, `%`, `+`):
    - every audit sample of that item is "not good" to the build, so the build's "flagged by a sample
      outside the screen ... record it" refusal cannot fire for it;
    - a screened item's sample is retaken alternately by each build and each default probe run, each
      overwriting the other's latest record.

    The probe in the copy confirms the mismatch: `targets_load` gives `.../A B/...` and the build expects
    `.../A%20B/...`, so `sample_good` returns False.

    No wrong list follows from this. An empty-cache build would not have that audit sample either, and
    `audit_report` still reports the miss.
  - **Fix.** Encode the COPC href in `targets_load` the way the laz href is encoded.

## Tried and found sound

- **`flagged` in main() and in classes_check are identical.** Both use the same `samples` (latest by id,
  restricted to listed ids; `k in current` and `k in by_id` are the same key set), the same predicate
  `sample_good(r, current, copcs)`, the same `copcs` dict and `confirm_ids`.
  - Mutation M2 (main's `flagged` uses `record_good` and ignores COPC) stays green. It is near-equivalent:
    the build has just re-sampled every screened item with `match_copc`, so the two differ only on samples
    outside the screen with a changed COPC. There the mutant would over-read and over-record, and publishes
    nothing wrongly.
- **Claim (1), measured on the snapshot** (174,282 targets, 17,552 screened, 346 flagged, 340 good reads,
  required `[]`):
  - 338 ids are published;
  - 2 good reads are outside the published set, both unscreened (round 3's two R2 reads), and refused until
    recorded;
  - 0 screened reads are outside the published set;
  - 0 published ids lack a good read.

  `classes_check` gives 16 problems: 8 audit flags whose whole reads have not run yet (the audit is still
  running), 6 transient sample failures, and those 2 reads. All three kinds are loud.
- **Claim (2).** `want ⊇ published − {ids with a good prior}`, and `classes_check` requires a good read for
  `flagged ∪ (required ∩ listed) ⊇ published`. `classes_attach` gets every URL record of a published id.
  So a passing full build lists every published id. I found no published id whose stale or failed record
  could escape a re-read. A failed re-read is refused and retried on the next run.
  - Mutations M1 (drop the `published` filter on records), M4 (`want` omits flags outside the screen) and
    M5 (exempt screened reads again) are all red.
- **`--limit`.** It writes only `data/build-limit`, `--classes-record` is refused with it, and `unrecorded`
  is off. The `published` filter keeps a slice-cache read outside the set from being applied (M1 red). No
  path writes to `data/build` or `classes_required.json`.
- **`--classes-record` after the reads.** `found` takes only `record_good` reads and good-sample flags, and
  operator precedence groups it as intended: `(flagged − inside) | (reads − (inside & flagged))`. Without
  `--force`, every id it adds was either in `want` (a flag) or already has a good read. So nothing is
  recorded from a failed read, and everything recorded is reproducible from an empty cache. The `--force`
  case is Finding 1.
- **`confirm_work` in the probe disagrees with the build, but loudly.** `--confirm` flags from unfiltered
  samples (stale ones, and ones taken with another COPC) and re-reads every stale whole read. Probe:
  `confirm_work({A: mixed@new}, {A: full@old}, {A: new})` returns `{A}`.
  - So a research `--confirm` turns a stale read that the build deliberately leaves alone into a good read
    outside the published set. The next build refuses with "record it with --classes-record".
  - That is loud and clears by recording, so I did not flag it. But the docstring's premise ("would
    otherwise refuse every build") is no longer true of the build.
- **`--audit` and the default probe run** pass `match_copc=True`, and `--audit`'s whole-read `want` uses
  `record_good` after a fresh `match_copc` sample, so it is consistent.
- **The running `--audit` process** loaded the pre-commit module (started before 9884d5a), so its records
  are written without the COPC check. All 3,693 COPC-bearing records match today's targets, so this changes
  nothing.
- **Sample-shape drift.** All 21,747 good samples have the sample keys the current constants produce, and
  every COPC sample has levels (0, 1). So no cached "good" sample was taken under a different design.
