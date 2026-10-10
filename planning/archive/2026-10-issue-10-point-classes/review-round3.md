# Code-check round 3 (#10, branch 10-some-point-clouds-hold-ground-returns-on, HEAD c6fb7db)

## Mechanism

R1 and R2 come from one assumption: that **what the probe reads** and **what the build checks**
are the same set of files, and that both judge "current" the same way. They are not. They come
from different sources:

| | probe | build |
|---|---|---|
| file list | `data/build/items`, written only by a *successful* build | the live listing (`kept`) |
| key | item id | laz url |
| current ETag | `headers.jsonl` (later lines win) | listing `o["etag"]` |
| missing ETag | `None` (fixed in R2) or `""` | `""` |

Round 2's fix made `--confirm` read every record that is not good. That covers one gap: the
records the samples no longer flag. It does not cover the gap between the file lists. The
build's refusal is a precondition on *producing* `data/build/items`, and the probe's remedy
needs that directory as its input. That is a cycle. Any state where a file in the listing has a
bad record, or no record at all, and is not in the last successful `items/` cannot be cleared by
the commands the build names.

## Findings

- **[severity: bug]** scripts/catalogue_build.py:476-483 (CLASSES_READ refusal) with
  scripts/laz_classes_probe.py:429 (`items_load(f"{args.build}/items")`). **Starting from a clean
  state (a fresh clone, another machine, CI, or after `rm -rf data/build`), the build cannot
  complete, and the remedy it names crashes.**
  1. With no `classes_full.jsonl`, `read == {}` differs from `CLASSES_READ`. The build refuses
     before it writes `items/`, although `headers_fetch` has already written `headers.jsonl`.
  2. The message says to run `laz_classes_probe.py` and then run it with `--confirm`. The probe
     calls `os.listdir("data/build/items")` and raises `FileNotFoundError`. Reproduced in a temp
     copy (scratchpad/r3, dir `b1`):
     `FileNotFoundError: [Errno 2] No such file or directory: 'b1/items'`.

  The comment at catalogue_build.py:93-95 calls the cache "regenerable", but no documented path
  regenerates it. The only way out is an undocumented detour:
  - `catalogue_build.py --limit <more than all>`, which writes `data/build-limit` and skips the
    count check;
  - then `laz_classes_probe.py --build data/build-limit --out data/build/classes.jsonl --full
    data/build/classes_full.jsonl`.

  This matters most for #2, which rebuilds everything, possibly somewhere new. Possible fixes:
  - have the probe build its item list from the listing or header cache rather than from
    `items/`;
  - or have the build write its items, or a staging list, before the class-cache refusals.

- **[severity: bug]** Same mechanism, on a machine that has `items/`. Take a file that is in the
  listing but not in the last successful build, and that has a bad record in
  `classes_full.jsonl`. Its refusal is unclearable. This is how it gets there:
  - The file was read whole at E1.
  - It left the listing (deleted upstream, or added to `EXCLUDE`). A build then succeeded after
    `CLASSES_READ` was updated, which is the remedy the count refusal itself names.
  - It came back: re-delivered at E2, or removed from `EXCLUDE`.

  The build's `classes_attach` then refuses on every run with "read at ETag E1, listed at E2 ...
  re-run laz_classes_probe.py, then with --confirm". A failed record in the same position gives
  "the class read failed ... re-run --confirm" instead. Neither command can reach the file:
  - `confirm_work` puts its id in `want`;
  - main() then filters with `items = [i for i in items if i["id"] in want]` (probe.py:458),
    which drops the id because it is not in `data/build/items`;
  - so the sample pass skips it too, and every rebuild refuses again.

  Reproduced (scratchpad/r3, dir `b2`): `want {'x'} items read by --confirm []`, followed by the
  stale-ETag problem from `classes_attach`. The enumeration in findings.md says the ETag-changed
  and failed-read rows clear. They clear only for files that are also in `data/build/items`.

- **[severity: fragile]** scripts/laz_classes_probe.py:255 and scripts/catalogue_build.py:342.
  **Round 2's missing-ETag fix covers `None` and not `""`.** Each side spells a missing ETag as
  `""`:
  - `HttpRangeFile.etag` and `laz_full` use `headers.get("ETag", "").strip('"')`;
  - the listing uses `findtext("s3:ETag", default="")`.

  So a missing ETag on both sides still compares equal:
  - in the probe, `record_good({"id": "i0", "full": {"etag": ""}}, {"i0": ""})` is `True`
    (checked);
  - in the build, `"" != ""` is False, so the record is applied as current.

  This is the guard R2 named, failing toward pass. `test_an_etag_missing_on_either_side_is_not_a_match`
  tests only `None` and absent keys. Every ETag present today is non-empty (9,650 header
  ETags; 73 full-read ETags all match), so this is not live. Treating a falsy ETag as "unknown"
  on both sides closes it.

- **[severity: fragile]** findings.md "Code-check enumeration", rows 2 and 4, and
  catalogue_build.py:337-352. The enumeration says "re-run `--confirm`" clears a failed read, and
  "remove the line and re-run" clears a `classes_add` refusal. Both clear only when the failure is
  transient. Suppose a flagged file fails the same way every time: a corrupt or truncated LAZ that
  lazrs cannot decode, or a decode whose tally differs from `pc:count`. The re-read then writes the
  same error, or the same refusal follows. Every build then stops, and the messages offer no exit.

  Header reads have `EXCLUDE` as an escape. Class reads have no equivalent short of editing the
  gitignored cache and then changing `CLASSES_READ`. And once that is done, the collection
  description's "Files that a sample ... found ... were read whole" is false for that file. No
  current file is in this state (all 73 applied; `--summary`: `unread []`, no failures), so this
  is an overclaim in the enumeration rather than a live failure.

## Checked and sound

- Published numbers. `--summary` gives:
  - 9,649 recorded, 0 failed;
  - to confirm 73, read 73, unread `[]`;
  - sampled ground-only 3, confirmed 1;
  - sampled no ground 70, confirmed 57.

  57 of the 73 listed items hold no class 2, so "Most of the listed items hold no ground" holds,
  and so does `CLASSES_READ`'s sum of 73. 73 of the 9,649 built items carry
  `classification:classes`.
- ETags agree: all 73 full-read ETags equal the `headers.jsonl` ETags. Every item href,
  unquoted, is a listing url, including the 15 with spaces.
- `nge:las_version` and the full read's `las_version` both come from `str(h.version)` ("1.4" or
  "1.2"), so `classes_add`'s version check compares like with like.
- The ETag-change path works for a file that *is* in `items/`. `headers_fetch` appends the new
  ETag before `classes_attach` refuses, and `confirm_work` then re-reads the stale record whether
  or not the sample flags the file.
- `uv run pytest -q tests/`: 142 passed.
