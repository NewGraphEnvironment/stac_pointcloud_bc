# Code-check round 4 (#10): commit 0095112 and the branch

Reviewer read: `git show 0095112`, `scripts/catalogue_build.py`, `scripts/laz_classes_probe.py`,
the `laz_item.py`/`laz_remote.py` diff, the doc diffs (CLAUDE.md, README.Rmd, research/), and
`planning/active/findings.md`. Ran `uv run pytest -q tests/` (145 passed) and
`laz_classes_probe.py --summary` (read-only). Nothing in the working tree or data/ was modified.

## 1. Attack on 0095112 (class_targets.jsonl)

**The mechanism fix holds.** Every path in `catalogue_build.main()` that refuses on class
records (`classes_records_load`, `classes_attach` problems, the `CLASSES_READ` mismatch) comes
after `class_targets_write` (line 480). Every path that returns before it (header read failure
:430-436, `copc_pairs`/`copc_pairs_check` raise :452-454, COPC header failure :455-462, COPC
mismatch :470-475, listing raise, `exclusions_check` raise, an `item_create` raise) is not about
class records, and its own remedy has to clear first; until then the probe reads the previous
build's targets, which is harmless. The targets are exactly `kept` (EXCLUDE removed), with
`etags[u]` from the same `objs` the class check uses and the same `pairs`. `--limit` writes to
`data/build-limit`, so it cannot overwrite `data/build` targets. Ids are `key.replace("/", "-")`
of the full key, so the probe's id-keying and the build's url-keying are 1:1.
`href_encode` then `unquote` is an identity on any string, so `laz_url(target)` equals the build's
`u`, including ` (2)` and `%` names.

After any build that refuses on class records, the probe's `current` equals that build's
listing, so `record_good` and `classes_attach` agree record for record. A re-delivery between
build and probe makes the probe re-read until the next build re-lists, which then matches the
GET ETag: convergent. Local data agrees: 9,649 targets, no empty ETag, no duplicate id; all 73
latest `classes_full.jsonl` records match their target's laz url and ETag; group counts equal
`CLASSES_READ`.

The only loop the three commands cannot close on their own is a `CLASSES_READ` change, and that
loop is deliberate: a person records the new count.

## Findings

- **[severity: fragile]** `scripts/catalogue_build.py:329-341` (call at :481): the build reads
  `classes_full.jsonl` without `cache_tail_repair`, unlike `headers.jsonl` (:263). If a
  `--confirm` run dies mid-append, the next build stops with a bare `JSONDecodeError` traceback
  that names no remedy. The probe's sample mode does not repair `full` either (only `out`, via
  `probe_all`). Only `--confirm` (:460) and `--summary` (:451) repair it. So the state can be
  cleared, but no message says how. It needs a kill or ENOSPC inside a write of about 1 KB, so
  it is unlikely. Fix: call `cache_tail_repair(path)` at the top of `classes_records_load`, or
  catch the decode error and name `--confirm`. (Predates R3; not inside the R3 fix.)

- **[severity: fragile, not live] INSIDE R3 FIX** `scripts/catalogue_build.py:358-361`: when the
  listing carries no ETag for a kept file (`not etags[u]`), the refusal says "the file was
  re-delivered; re-run laz_classes_probe.py, then with --confirm". That remedy cannot clear it.
  The probe's `record_good` also treats the empty ETag as a non-match, so every `--confirm`
  re-reads the file (the full read's ETag is the GET's, never empty), and every build refuses
  again. This is a refusal whose named remedy does not clear it, and its message misstates the
  cause. Not live: 0 of 9,649 targets have an empty ETag, and `keys_list` reads it from the
  listing XML. If it ever happens, the message should say the listing returned no ETag.

- **[severity: published claim, minor]** `research/laz_classes.md:60-62`: "In every other item,
  whatever stands above the ground can only be in class 1". This is an absence claim drawn from
  samples (first 100k points plus 3 chunks). The file's own Method says a sample can only miss a
  class, so it cannot establish that classes 3, 5 or 6 are absent from the 8,751 items read only
  by sample. Class 17 (bridge deck, above ground) also appears in 4 items' samples. The weaker
  form ("vegetation is mostly unclassified, class 1"), which the collection DESCRIPTION and
  CLAUDE.md use, is supported. Suggest "in the samples of every other item, nothing above the
  ground was classified 3-6".

## 2. Enumeration table (findings.md, "Code-check enumeration") — completeness

Every class-record exit in `catalogue_build.main()`:

| exit | line | in table? | remedy clears? |
|---|---|---|---|
| `classes_records_load` ValueError: a line with no `laz` | 337 | row 1 | yes |
| `classes_records_load` JSONDecodeError: a truncated tail line | 335 | **missing** | yes, via `--confirm` or `--summary`, but no message names it (finding 1) |
| `classes_attach`: failed read → return 1 | 355, 488-492 | row 2 | yes |
| `classes_attach`: ETag differs → return 1 | 358 | row 3 | yes. **But row 3's "clears?" text is stale:** it says `record_good` compares against `headers.jsonl`. Since 0095112 it compares against `class_targets.jsonl` |
| `classes_attach`: empty listing ETag → return 1 | 358 | **missing** | **no** (finding 2; not live) |
| `classes_attach`: `classes_add` ValueError → return 1 | 365 | row 4 | yes (remove the line; re-read only if a sample flags the file, otherwise row 5) |
| `CLASSES_READ` mismatch → return 1 | 494-500 | row 5 | yes (a person records the count) |

Exits in `laz_classes_probe.main()`:

| exit | line | in table? | remedy clears? |
|---|---|---|---|
| `targets_load` SystemExit: no `class_targets.jsonl` | 229 | **missing** | yes: the build writes it unless a non-class refusal stops it first, and that refusal's own remedy applies |
| `--ids` SystemExit: ids not in the build | 445 | n/a (user input) | n/a |
| return 1 on any failed read | 469 | covered by row 2 | yes for a transient failure; a deterministic one is the accepted tradeoff |

Non-class exits in the build: listing/COPC RuntimeErrors, header/COPC-header/COPC-mismatch
return 1, `exclusions_check`, duplicate ids, missing `laz` asset, validate. None of them reads
class records.

## 3. Rest of the diff (brief)

- `classes_add` / `asprs_class_name`: the string compare `las_version < "1.4"` is sound for
  1.0-1.4. All 73 whole-read files are LAS 1.4 (69) or 1.2 with classes 0, 1 and 2 only (4), so
  no LAS 1.2-only name is at stake. A built item (`082l095_3_1_2`) carries the classification
  v2.0.0 extension and the expected list.
- Re-derived from local data, all of which reproduce: the `research/laz_classes.md` numbers
  (73 read; 1 ground-only and 57 no-ground confirmed; per-group counts) and the density table
  (≤p2 200/48, ≤p5 488/58, ≤p10 971/58, <5 pts/m² 300/57). The confirmed tiles' maximum
  in-group percentile is 2.96, so "every confirmed tile is at or below the 3rd percentile" holds.
  The collection DESCRIPTION, CLAUDE.md and README.Rmd claims hold too.
- Tests: 145 pass.
