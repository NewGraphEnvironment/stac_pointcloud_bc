# Code-check round 2: branch `4-monthly-update-in-github-actions-with-the` (b932c3c...7266407)

Reviewer: subagent, 2026-10-12. Concentrated on the round 1 fixes (`round1_fixes.patch`). All
probes ran in scratch copies under `$TMPDIR` (scratchpad `r2/`), with a fake `aws` backed by a
local directory for `cache_sync.sh`. No repo file or remote object was written.

## Findings

- **[bug] scripts/cache_sync.sh:70 (read at :99): the round 1 fix records the "unchanged"
  checksum of the *merged* file at pull, not of the remote copy. A merge-pull followed by a
  push therefore uploads nothing, and the local reads never reach the bucket.** Before the
  fix, push compared against `$PULLED/$f.gz`, the remote's bytes, so a merged file (which
  differs from the remote) was uploaded. Now `.cksum` holds `cksum` of `$BUILD/$f` *after*
  the merge, so push finds the merged file "unchanged since pull, not uploaded". It exits 0,
  and the remote lacks every line the local tree had and the remote did not. This is the
  recovery path the script prescribes. A local build (for example the 2.5 h
  `HEADER_VERSION` re-read the README says to "build once locally and push") meets a
  monthly push made meanwhile. `push` refuses with "pull first", the operator pulls (a merge),
  pushes, is told "unchanged", and the re-read is lost. The next monthly run then re-reads
  for hours, or does not fit the runner. The same happens to any tree that built before its
  first pull. Reproduced with a fake `aws` (pull, append LOCAL, remote replaced by a "CI"
  push, push, pull, push):

  | script | push after the merge-pull | remote afterwards |
  |---|---|---|
  | HEAD 7266407 | `headers.jsonl: unchanged since pull, not uploaded` (rc 0) | `r1 CI` (LOCAL lost) |
  | 5d2f83b (before the fix) | `headers.jsonl: 3 lines pushed` | `r1 LOCAL CI` |

  Fix, verified in a copy: in the pull branch take the checksum from the pulled remote copy
  before merging, `cksum < "$PULLED/$f" > "$PULLED/$f.cksum"` right after the
  `[ "$n" -gt 0 ]` check, and drop the `cksum < "$BUILD/$f"` at line 70. With that change, an
  unchanged pull-then-push still uploads nothing, the merged push uploads (`r1 LOCAL CI`), and
  a second push is "unchanged". The CI path (pull into an empty tree) behaves the same either
  way, which is why the fresh-runner probe in round 1 could not see this. The push-side
  record at line 108 is correct as is: after a push, the remote holds `$BUILD/$f`.

## Checked and fine

- `rounding_equivalent` / `_on_grid`: over 1M random BC lon/lat values, `round(v, 8)` was
  always on the grid (rounding is idempotent), one step apart was always equivalent, and two
  steps apart never was. Only `geometry` and `bbox` carry lon/lat (`laz_item.item_create`
  rounds just the corners; `proj:bbox` is header coordinates, left out of the tolerance). The
  collection's lon/lat sits only under `extent.spatial.bbox`, which the tolerance covers.
  Booleans, ints and type changes still compare strictly.
- `same_items`: `ex.map` keeps its input order, so the `zip` pairs each result with its name.
  `urllib.parse.quote` encodes a space and `+`. A failed fetch raises, which fails
  `s3_sync.sh`'s `PLAN=$(...)` under `set -e`, so a failure never reads as "same".
  `requests` is a declared dependency (pyproject.toml, uv.lock).
- Leaving an item "as published" does not upset `stacs verify` or `register --mode drift`.
  Both digest the bucket's bodies against the API (`stacs/verify.py`,
  `catalogue.published_digests`), never against a local build.
- Over `SAME_CHECK_MAX`, every changed item uploads and the collection is published, so a
  flipped item uploads with it. No inconsistent state results.
- update.yml: with `continue-on-error`, a failed `cache_creds` still has `outcome` failure, so
  the `outcome == 'success'` gate skips the push, and a failed push leaves the job on
  `success()` for Audit and Publish. `MAX_UPLOAD=40000` is exported on every path. No
  `rewrite` input or mention is left in the workflow, README.Rmd/README.md or CLAUDE.md.
- README's CanElevation exception matches `copc_pairs_check` (catalogue_build.py:445-448),
  and `--groups-record` writes `copc_pairs.json` too (catalogue_build.py:759-761).
- A tree pulled by the earlier script has no `.cksum`, so its first push uploads once.
  Harmless.
- `tests/test_s3_publish.py` (17 tests) passes in a copy.

## Disposition (session)

Reproduced (scratch tree: pull, append a local line, pull again to merge, push --dryrun:
"unchanged since pull, not uploaded"). Fixed as proposed: `.cksum` recorded from the pulled
copy before the merge. After: unchanged pull-then-push uploads nothing; merged push uploads.

A defect inside a round 1 fix, so enumerated the mechanism (a marker standing in for the
remote's state). Every marker site in cache_sync.sh:

| marker | means | writes | reads |
|---|---|---|---|
| `.etag` | remote object as last seen | 72 pull (listed before fetch), 110 after upload | 80 push guard |
| `.cksum` | remote content | 58 pulled copy, before merge; 109 local just uploaded | 100 unchanged test |
| `.lines` | floor for the local file | 71 after merge; 108 after upload | 84-85 shrink guard |

Each write records what its name means; dry runs write none. s3_publish reads the bucket
directly (listing, fetched bodies), never a marker.
