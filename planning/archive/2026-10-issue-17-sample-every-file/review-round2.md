# Code-check round 2: branch 17-sample-every-file (3b8e543...HEAD, HEAD 5c6b3e4)

Reviewer: subagent, 2026-10-17. The work ran in a scratch copy (`scratchpad/r2_copy`), and the
repo tree was not touched. `tests/test_catalogue_compare.py` and `tests/test_laz_item.py`:
251 passed (108 s).

## Clean

No issues found.

## The round-1 fixes, checked by mutation

- **Join of the two problem maps** (`catalogue_build.py:969-972`). Putting back
  `problems |= classes_check(...)` fails
  `test_a_classes_unreadable_entry_that_no_longer_shows_its_fault_is_refused[probe3-a-now samples]`.
  The other three cases still pass, so the fix is pinned by the case it was written for.
- **The description stated in the direction the flags make true** (`DESCRIPTION`, lines
  272-275). Changing it to "a file whose sample held ground..." fails
  `test_the_build_lists_the_classes_of_a_file_read_whole`. The restored file `cmp`-matches
  the repo.
- The new sentence holds on the code path. An unflagged good sample means the merged laz
  sample holds class 2 and a class outside {2, 7, 9, 18}. Where there is a COPC sample, it
  also holds ground (`no_ground_ids`) and is not ground-only. Every `to_sample` file without
  a good sample is refused (`classes_check`, first loop), and every `CLASSES_UNREADABLE`
  entry must fail with its recorded error at its recorded ETag
  (`classes_unreadable_check`). So in a whole build, an item without a list is either one
  of the `len(CLASSES_UNREADABLE)` files or holds ground plus another class. Neither
  unreadable file is in `data/classes_required.json`, so "carry no list" holds too.

## Checked and found sound

- **`CLASSES_UNREADABLE` keys.** They match the build's url form exactly: both appear
  verbatim in `data/build/class_targets.jsonl`, with the entries' ETags (`056c28d7…-9`,
  `54247648…-5`). The local sample cache holds exactly 2 error records, both
  `LazrsError: IoError: no chunks available in chunk table`.
- **The empty-sample refusal.** No kept file has a header `point_count` of 0. Thirteen have
  fewer than 10 points, and each is read whole as `"all"` and gives a non-empty sample, so
  the new refusal does not fire on any file known today. Its message cannot overwrite an
  earlier one: the first loop sets messages only for files without a good sample, and
  empty samples flag nothing.
- **The "the run saves what it sampled" claim** (`maintaining.md`). `update.yml` gives the
  build step `timeout-minutes: 240` and runs the cache push under
  `always() && steps.pull.outcome == 'success'`, inside a 345-minute job. `probe_all`
  flushes each record. `cache_sync.sh push` cuts a partial last line, and the build's
  `cache_tail_repair` does the same, so the claim holds. The pace figures are labelled as
  Mac-measured, and the runner's pace as not yet measured.
- **No other test file runs `catalogue_build.main()`.** So the autouse
  `no_unreadable_files` fixture in `test_laz_item.py` is enough, and the real entries'
  "not in this build" refusal cannot fire in the CI `Tests` step.
- **`catalogue_compare.classes_added`.** It is strict on both sides: the list and the
  extension must both be added, and the published item must have neither. It works on
  deep copies. A changed list, a dropped list, and a list without its extension are each
  still reported. A description change goes to `changes`, and a title change is still a
  problem.
- **`--classes-record`.** `flagged - inside` can hold only a `CLASSES_UNREADABLE` file that
  now reads and flags. That build is still refused by `classes_unreadable_check`, and with
  the round-1 join the operator sees both messages.

## Not flagged (pending by design or out of scope)

- **The `.copc.laz` file in `093c/2023`** (`093c058_1_1_1…20230902.copc`) has never been
  sampled: it was outside the old screen and the audit. Whether `LazrsParallel` samples it
  (COPC chunks vary in size) is something the sweep will show. If it fails, it needs a
  `CLASSES_UNREADABLE` entry, as the plan intends for any file the sweep cannot read.
- **The `maintaining.md` refusal list** names an unreadable entry that "has left the
  listing". The code refuses one "not in this build", which also covers a file that is
  still listed but excluded, and it refuses one that "fails otherwise". The prose
  understates the refusals but states nothing false.
- **Deferred to the sweep:** the description's "Most of the listed items hold no ground"
  sentence, and CLAUDE.md's classes bullet, which still describes the screen.
