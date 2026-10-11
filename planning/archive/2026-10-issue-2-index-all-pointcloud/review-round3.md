# Code review, round 3

Branch `2-index-the-rest-of-pointcloud-laz-165-667`, diff `be4bfbd...HEAD` over `scripts tests data`, at HEAD
b28972b. I read every changed script in full, plus CLAUDE.md and review rounds 1 and 2.

**Method.** I measured on copies of `data/build/{class_targets,classes,classes_full,headers}.jsonl`, taken
2026-10-11 09:07 UTC while the `--audit` run was still writing. All probes and mutations ran in a scratchpad
copy of the repo. The working tree was not touched; `git status` there shows only the three files that were
already modified. `uv run pytest -q` in the copy: 248 passed.

## Mechanism

Round 2's mechanism was "the required set was derived from current flags, not from what the build
publishes". It points the right way, but b28972b applied it only to files outside the screen.

The assumption both rounds rest on is that every class list a build publishes is one a build from an empty
cache would publish too. Two sets are assumed equal, and nothing compares them in full:

- **R, the lists a build publishes.** `classes_attach` applies every good whole read in the local
  `classes_full.jsonl`, whatever put it there. That covers this build's `want`, the research runs
  `laz_classes_probe.py --confirm`, `--ids` and `--audit`, and a re-read of a stale record
  (`confirm_work`'s second clause).
- **F, the lists an empty-cache build would publish.** These are `(screened ∩ flagged by a sample at the
  current inputs) ∪ CLASSES_REQUIRED`.

`classes_check` compares R with F only outside the screen. Two proxies stand in for the rest:

1. **"Screened" stands in for "the build re-derives this list".** That holds only for a screened file that
   its current sample also flags. A screened file read whole for any other reason is exempt
   (`catalogue_build.py:665`) and is published only where the cache holds the read (Finding 1).
2. **"A sample at the current laz ETag" stands in for "the sample a fresh build would take".** `item_probe`'s
   result also depends on whether the item has a `copc` asset, and on that COPC's bytes. `record_good` keys
   validity on the laz ETag alone (Finding 2).

The fix shape is one function that computes F. That function drives `want`, the class check and
`classes_attach` together, so the cache can only speed a build up and can never add a list. Sample validity
should be keyed on (laz ETag, copc href, copc ETag or none).

## Enumeration

### (a) Every path by which `classification:classes` reaches a published item

There is one writer, `laz_item.classes_add` (grep: its only caller is `catalogue_build.classes_attach:623`).
`classes_attach` takes every record that `classes_records_load(classes_full.jsonl)` returns for a kept URL
and applies it when it is good at the current listing ETag. So a list is published exactly when the local
whole-read cache holds a good record. The table lists what can put such a record there, and what reproduces
it on a machine with an empty `data/build`.

| how a good whole read gets into `classes_full.jsonl` | screened? | what reproduces it on an empty `data/build` | verdict |
|---|---|---|---|
| Build `want`: a current good sample flags it | yes | screen and sample, both derived (deterministic for the same laz ETag *and the same COPC pairing*) | reproduced, except across a COPC pairing change (Finding 2) |
| Build `want`: a current good sample flags it (an audit sample) | no | `CLASSES_REQUIRED`, enforced by `classes_check:664-669` | reproduced, once recorded; the build refuses until then |
| Build `want`: the id is in `CLASSES_REQUIRED` | either | `CLASSES_REQUIRED` | reproduced |
| Build `want`: `confirm_work` re-reads a prior record that is stale or failed, and no current flag or required id asks for it (re-delivery under the same key) | no | nothing. The check refuses it ("read whole outside the screen") until it is recorded | reproduced, once recorded (Finding 3: not in the same `--classes-record` run) |
| same | **yes** | **nothing.** Exempt from the check | **cache-only: Finding 1** (end-to-end probe, rc 0) |
| `laz_classes_probe.py --confirm`: `confirm_work(records_load(out), ...)` flags from *every* latest sample, not filtered by `record_good` (no-ETag survey samples, stale samples) | no | the check refuses until recorded | reproduced, once recorded |
| same | **yes** (its current sample does not flag) | **nothing** | **cache-only: Finding 1** |
| `--audit` reads: flagged by a good audit sample | no at pick time; can become screened when a group grows | `CLASSES_REQUIRED`, unless `--classes-record --force` drops it (`found` excludes screened ids even when the cache has a good read) | reproduced; with `--force` it is cache-only if the current sample does not flag |
| A record whose `id` is not `url_to_item_id(laz)`. `classes_attach` reads the cache by URL (`classes_records_load`), `classes_check` by id (`records_load`) | either | nothing. `classes_check` never sees it, `classes_attach` applies it | latent. Measured: 0 of 340. It needs the id scheme to change |

Measured today (174,282 targets, 17,552 screened, 340 good whole reads):

- screened ∩ read − flagged = **0**;
- good samples whose `copc` differs from the target's = **0**;
- URL/id-keyed record sets differ by **0**;
- R and the check's `read` set are equal (340 = 340).

So nothing is cache-only today. The gaps are reachable through ordinary operation: a re-delivery, a COPC
pairing re-recorded, or a research `--confirm`.

Also measured: `classes_check` with the committed `[]` list against today's cache gives **10 problems**:

- 6 screened samples that failed with a transient `ConnectionError`;
- 4 files outside the screen that need recording: R2's 2 reads (`082k017_1_3_3`, `092g028_2_1_1`) and 2 new
  flags.

The next full build refuses until `--classes-record` runs. That failure is loud, as designed. It does mean
b28972b did not record R2's two reads in the committed list.

### (b) Every committed file under `data/` the code writes

The grep covered `json.dump`, `os.replace`, `open(…"w")` and the `*_PATH` constants. These are the tracked
files under `data/` (`git ls-files data`).

| file | writer | `--limit` reach | can lower or drop a value without `--force` | same run validates against what it wrote |
|---|---|---|---|---|
| `pointcloud_groups.json` | `records_write` (`--groups-record`) | `--limit` can be combined with it, but `found` is computed from the whole listing before the slice (`:760` vs `:780`), so the slice cannot reach it | **yes, by under 10% per group.** It logs a warning and nothing more; a drop of 10% or more, or a vanished group, is refused | no. It returns 0 right after writing. The next run's `groups_check` reads it |
| `copc_pairs.json` | `records_write` | same as above. `pairs` come from `named` (the whole listing) | no. Any drop or vanished group is refused | no (as above). The next run's `copc_pairs_check` |
| `classes_required.json` | `--classes-record` (`:866-877`) | refused by `ap.error` (mutation M14 turns a test red) | no. It writes the union with the old list unless `--force` (M15 and M21 are red) | yes, `required` is passed to `classes_check`. **But** it records before the whole-read step, so a read made good in the same run is refused by that run (Finding 3) |
| `copc_not_copies.json` | nothing (curated by hand) | n/a | n/a | n/a |
| `readme_dem.json`, `readme_cache.rds` | `readme_dem.py` / README.Rmd (not in this diff) | n/a | n/a | n/a |

`collection_version.py` and `canelevation_overlap_probe.py` write paths given as arguments (the build
directory, or `data/canelevation/`), not tracked files. `laz_classes_probe.py --audit` writes
`data/build/classes_audit_ids.txt`, which is gitignored.

### (c) Every refusal in `classes_check` and the class step of `main()`: mutation table

Each mutation was applied alone to a copy of `catalogue_build.py`, then `pytest -x tests/` was run.

| # | mutation | result |
|---|---|---|
| M1 | screened file with no good sample: not refused | red (`test_a_screened_file_whose_sample_fails_is_refused`) |
| M2 | flagged with no good whole read: not refused | red |
| M3 | required with no good whole read: not refused | red |
| M3b | whole read checked for presence only, not ETag | red |
| M4 | "flagged outside the screen, unrecorded" clause removed | **green.** An equivalent mutant: a flagged file with no read is refused by M2's clause, and a flagged file that was read is refused by the "read outside" clause. Nothing lost |
| M5 | "read whole outside the screen, unrecorded" clause removed | red |
| M6 | screen exemption removed (over-refusal) | red |
| M7 / M7b | `unrecorded` forced off / forced on under `--limit` | red / red |
| M8 | `main` ignores `classes_check` | red |
| M9 | `classes_attach`: failed read not a problem | red (unit test only) |
| M10 | `classes_attach`: empty listing ETag accepted | red (unit test only) |
| M11 | `classes_attach`: stale ETag accepted | red (unit test only) |
| M12 | `classes_attach`: a read `classes_add` refuses (point count or LAS version mismatch) is swallowed | **green.** No test hands `classes_attach` a read that `classes_add` refuses. Removed, such a read is dropped silently and the item publishes with no list. The guard is correct by reading; it is just unpinned |
| M13 | `main` ignores `classes_attach`'s problems | **green.** Of the cases M9-M12 reach in `main`, only a failed or unmatched read of a file that is neither flagged nor required gets past `classes_check` (stale reads are re-read first). Nothing in the suite builds one |
| M14 | `--classes-record` together with `--limit` allowed | red |
| M15 / M21 | `--classes-record` replaces the list / ignores `--force` | red / red |
| M16 / M17 | `--classes-record` ignores cached reads / flags | red / red |
| M18 | `--classes-record` also records screened ids | green. It only over-records, and it is harmless |
| M19 | required ids not put in `want` | red |
| M20 | `classes_records_load` accepts a record with no `laz` | red |

## Findings

- **[fragile] scripts/catalogue_build.py:663-669 (and 878-879, 602-626): a screened file read whole for any reason other than its current sample's flag publishes its class list only where the cache holds it; the build passes on every machine.**
  The `unrecorded` loop exempts `by_id[k] in screened` on the premise that the build re-derives a screened
  file's list. That premise holds only when the file's current sample flags it. `classes_attach` publishes
  every good whole read regardless.
  - **How it happens in practice.** A screened file is flagged and read whole at ETag E1, then re-delivered
    under the same key (the monthly update, #4). The build re-samples it at E2, and the new sample does not
    flag it. `confirm_work`'s second clause still re-reads the stale whole read, because the prior record is
    not good. The result is a good read at E2, and the list is published. On an empty `data/build` the same
    listing samples the file, finds no flag, reads nothing and publishes no list.
  - **Other ways in:** a research `laz_classes_probe.py --confirm`, which flags from latest samples without
    `record_good` (so from stale or no-ETag ones); and `--classes-record --force`, which drops a recorded id
    once its file becomes screened, even though the cache has a good read of it.
  - **Verified end to end** in the copy (`_main_with_classes`, PC screened as a group of one):
    - a good cached read plus a mixed sample: rc 0, and the item carries `[1: 600, 2: 400]`;
    - the same build with an empty cache: rc 0, and the item has no list;
    - a second probe ran the re-delivery path (a flagged sample and read at `old`, then a mixed sample at
      `a`): rc 0 with a list here, rc 0 with none from an empty cache.
  - **Today:** 0 such files (measured), so nothing published is affected yet.
  - **Fix:** make the exemption the derived set, not the screen. At `:665`, use
    `if not (by_id[k] in screened and k in flagged):`. Tried in the copy, that makes both probes refuse and
    keeps all 248 tests green.
  - **Two lines must change with it, or the files can never be recorded:** `--classes-record`'s `found`
    (`:867-869`) must also take reads in `inside − flagged`, and `--force` must not drop an id the cache has
    a good read of.
  - **Better still:** apply in `classes_attach` only the records for ids in F, so the cache can never add a
    list.

- **[fragile] scripts/laz_classes_probe.py:296-304, 311-322 (record_good / probe_all), consumed at catalogue_build.py:859-863: a cached point sample stays "good" after the item's COPC pairing changes, so this machine's flags (and therefore its published lists) can differ from an empty-cache build's.**
  - **What the sample depends on.** `item_probe` takes a `copc_sample` when the target has a `copc` asset.
    `no_ground_ids` and `ground_only_ids` count that COPC sample when they decide a flag.
  - **What the cache checks.** `record_good` compares only the laz ETag. So a screened item sampled before
    its COPC pair existed is never re-sampled after a pair is recorded (`--groups-record` after CanElevation
    adds a file), and its flag comes from the laz alone.
  - **In each direction:**
    - An empty-cache build samples the COPC too and can flag the file. It then reads the file whole and
      publishes a list that this machine's build does not.
    - Conversely, an item sampled while it was paired with a COPC that is now in `copc_not_copies.json`
      (9db4857 recorded 26) keeps a flag decided partly by a different file's classes. It is read whole and
      published here only.
    - A re-delivered COPC under the same key is likewise never re-sampled.
  - **Verified:**
    - `probe_all` given a cached laz-only record at the current laz ETag and an item that now has a `copc`
      asset: zero re-samples. The fresh record for the same item (whose COPC holds no ground) flags it.
    - Measured on today's caches: 0 good samples whose `copc` differs from the target's, so nothing is
      affected yet.
  - **Fix:** store the target's `copc` href (and the COPC's ETag) in the sample record, and treat a mismatch
    as not good, the way a laz ETag mismatch is.

- **[fragile, low] scripts/catalogue_build.py:866-885: `--classes-record` refuses the run it was asked to record in.**
  - **Why.** It records from `prior` before the whole-read step. `confirm_work` then re-reads stale or failed
    records, so an unscreened file whose read only becomes good in this run is refused by `classes_check` in
    the same run, with "record it with --classes-record".
  - **Verified.** `_main_with_required(argv=["--classes-record"], cached_full=[a read of PC at ETag "old"])`
    gave rc 1, the list `[]`, and that message.
  - **Severity.** It fails loudly, and a second identical run succeeds. Move the record block after `full`
    is loaded (taking `read` from `full`), or record from `want` as well.

The tradeoffs listed as accepted were not re-flagged. Round 2's EXCLUDE residual and the ids kept under
`--classes-record` without `--force` were checked, and both behave as described.
