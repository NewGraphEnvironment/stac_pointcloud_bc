# Code-check round 3: branch 17-sample-every-file (3b8e543...HEAD, HEAD 2c28b34)

Reviewer: subagent, 2026-10-17. Probes ran in a scratch copy (`scratchpad/r3_copy`, script
`scratchpad/r3_probe.py`), and the repo tree was not touched. The code has not changed since
round 2's green run of `tests/test_catalogue_compare.py` and `tests/test_laz_item.py` (HEAD
changed only `maintaining.md`), so the suite was not re-run.

## The mechanism

The build works out each of its sets in one place: which items carry lists
(`confirm_ids` and `classes_published`), and what it refuses and why (the `problems` map that
`classes_check` and `classes_unreadable_check` fill). Each earlier finding came from a
second statement of one of those sets that assumed a relation instead of deriving it:

- the direction of an implication (round 1: "flagged ⇒ ..." written where the code makes only
  "unflagged ⇒ ..." true);
- that two writers' keys are disjoint (round 1: `problems |=`, and each loop in `classes_check`
  assigning `problems[url] = ...`, as if it were the only writer for that url);
- that a list is complete (round 2: `maintaining.md`'s refusals written from memory rather than
  walked from the code).

This round walked every place in the diff that the mechanism reaches.

## Findings

- **[severity: fragile]** `scripts/catalogue_build.py:729`: the flagged/required loop in
  `classes_check` assigns `problems[by_id[k]] = ...`. That replaces a message an earlier loop
  set for the same url, which is the same defect round 1 fixed in `main()`. Both cases were
  reproduced in the copy:
  - **A file in `classes_required.json` whose sample failed and whose whole read failed.**
    The line-714 message, "no point sample ... (OSError: 503 sample)", is replaced by "in
    .../classes_required.json, with no whole-file read ... (OSError: 503 whole)". Before #17
    this needed a required id inside the density screen. Now every required id is in
    `to_sample`, so the diff widens the overlap.
  - **The new empty-sample refusal (line 723).** A file whose laz sample is empty but whose
    COPC sample is ground-only or groundless is flagged (`verdicts()["copc"]`,
    `no_ground_ids`). If its whole read then fails, the build reports only "flagged by its
    sample, with no whole-file read" and drops "its point sample holds no points". Round 2's
    reason for disjointness ("empty samples flag nothing") does not hold when the item has a
    COPC. With no COPC the empty-sample message survives (probe case B0).

  The build still refuses in every case, so nothing wrong is published. The operator sees one
  cause, and the other turns up only on the next run. Fix: join at line 729 with
  `"; ".join(filter(None, [problems.get(...), ...]))`, as line 737 already does.

- **[severity: fragile (prose)]** `maintaining.md:15`: the refusal list was rewritten from
  "a class read the screen requires" into an enumeration, and the enumeration leaves out two
  refusals the code makes:
  - a file in `data/classes_required.json` with no good whole read at its current ETag
    (`classes_check`, line 728, `why = f"in {CLASSES_REQUIRED_PATH}"`). The list says only "a
    flagged file without a whole read". The old wording covered this case.
  - a whole read that `classes_attach` cannot apply, because `laz_item.classes_add` rejects its
    point count or LAS version ("N class reads cannot be applied - not building"). This was
    not listed before either, but the new sentence presents itself as the list.

  This is the same class as round 2's note: it understates and states nothing false. It is
  flagged because the earlier fix was meant to make the list complete.

## Every reach of the mechanism, checked

Prose about which items carry lists:
- `README.Rmd:236` and `DESCRIPTION` (`catalogue_build.py:267-275`): "an item without a list
  holds ground and at least one class besides ground, noise and water, except the unreadable
  files". This holds. In a passing whole build, every `to_sample` file has a good sample
  (line 714), no good sample is empty (line 723), and an unflagged non-empty merged laz
  sample holds class 2 and a class outside {2, 7, 9, 18}. "Each file a sample found to hold
  only ground ... was read whole" holds too: `inside & flagged` is in `classes_published`, and
  `flagged - inside` is refused.
- `DESCRIPTION`: "[unreadable files] carry no list" holds today, but nothing enforces that
  `CLASSES_UNREADABLE` and `classes_required.json` share no id. It can break only through a
  good whole read of an unreadable file, and no command makes one. The build reads whole only
  `flagged | published`, and an error sample flags nothing. `laz_classes_probe --confirm`,
  with or without `--ids`, reads only `confirm_work`. `data/build/classes_full.jsonl` and
  `data/classes_required.json` hold neither id (grep, 0 each). Not a finding.
- The `CLASSES_REQUIRED` comment, the `classes_published` and `classes_check` docstrings, the
  `--classes-record` and `--force` help, and the `--limit` reason: each matches its code
  (`found = (flagged - inside) | (good reads - (inside & flagged))`, since `-` binds tighter
  than `|`; `keep` drops not-listed or sampled-and-flagged ids). The help's "its sample does
  not flag" is not true for `flagged - inside`, which is a `CLASSES_UNREADABLE` file that now
  reads and flags. Such a build is refused by `classes_unreadable_check`, and both messages
  show (round 2).
- `catalogue_compare.py` docstring ("a list the published item already carries must be
  unchanged, and none may be dropped; the description may change"): this matches
  `classes_added` and `collection_diff`. `classes_add` adds only the list and the extension
  (`ClassificationExtension.ext(asset, add_if_missing=True)`), so nothing else on an item
  changes.
- `CLAUDE.md` classes bullet, `research/`, and the description's "Most of the listed items"
  sentence: pending the sweep, by design. `NEWS.md:62` is a past release's note.

Merges into a refusal map:
- `main()` lines 969-972: joined. `classes_unreadable_check`: one message per url by
  `if/elif`. `classes_check` lines 714 and 723: disjoint, because 714 is for files without a
  good sample and 723 only for good ones. Line 737: joined. Line 729: overwrites (finding 1).
- `classes_attach` runs on a separate map after the `return 1`. `laz_classes_probe` audit
  `errors |=` is not in this diff, and its sample errors and whole-read errors are disjoint
  (`want` needs a good sample).

Docs restating what the build refuses or costs:
- `maintaining.md:15` (finding 2). Its `CLASSES_UNREADABLE` clauses match
  `classes_unreadable_check` (now reads, other error, re-delivered, not in the build).
  "Not in the build" covers both a file gone from the listing and an excluded file, because
  `ids` covers only kept files. The `r is None` branch ("no sample record") is not listed.
  It cannot happen in practice, since `probe_all` records every kept file, failures
  included.
- `CLASSES_UNREADABLE` comment and `classes_unreadable_check` docstring: these match the code.
- `cache_sync.sh` ("a day of samples"): 175,278 files at about 120 a minute is about 24 h.
  `maintaining.md`'s "about 20,000 a month inside 240 minutes" agrees with the plan review's
  180 usable minutes.
- `.github/workflows/update.yml` and the other scripts name no screen (grep).

## Resolution (parent session, 2026-10-17)

Both fixed. Every write into a refusal map now goes through `problem_add` or sits in an
exclusive if/elif chain run once per file. Enumerated: 15 write sites in
`catalogue_build.py` (4 in `classes_attach` and 5 in `classes_unreadable_check`, each an
exclusive chain per file; 4 in `classes_check` and 1 in `main()` through `problem_add`; the
helper itself). Mutation: `problem_add` made to overwrite fails 2 tests. The class refusals
(classes_check 5, classes_unreadable_check 5, classes_attach 4) were each matched against
`maintaining.md`'s list; the build's other refusals predate this branch. Loop ended by
enumeration.
