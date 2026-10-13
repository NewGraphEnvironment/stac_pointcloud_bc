# Code-check round 3: branch `4-monthly-update-in-github-actions-with-the` (b932c3c...ccbe603)

Reviewer: subagent, 2026-10-12. Suite in a fresh clone of ccbe603: **282 passed**. Probes ran
in scratch copies under `$TMPDIR` (scratchpad `r3/`), with a fake `aws` backed by a local
directory for `cache_sync.sh`, under macOS `/bin/bash` 3.2. The only remote reads were a
read-only `list-objects-v2` of `build-cache/`, a `head-object` of `collection.json`, and one
public HTTPS GET of an item. Nothing in the repo or any remote was written, apart from this file.

## The mechanism

R1 and R2 come from one assumption. **A value recorded or computed on this side (a marker
file, a local digest, this platform's float bytes) is taken to say what the other side holds
now (the bucket, the remote cache, the other platform's build).** That holds only if the
value was taken from the other side, and if nothing can write there between taking it and
acting on it. R1's gzip bytes and 8-dp flips failed the first condition, and so did R2's
post-merge checksum. Applying the same test to the second condition finds the instance below.

## Findings

- **[fragile, low] scripts/cache_sync.sh:79-83 (check) / :103-110 (act, then record): the push
  guard is check-then-act, and the ETag it records afterwards comes from a separate listing.
  An interleaved push can therefore get its ETag recorded as this tree's own, which defeats
  the guard silently.** Loop 1 compares the remote ETag with `.etag`. Loop 2 gzips (seconds,
  for the 400 MB `headers.jsonl`) and uploads. Only then does `remote_etag` list the object
  again and write whatever it finds to `.etag`. Neither step is atomic with the upload, so
  there are two windows:
  1. Another writer lands between this tree's check and its upload. This tree overwrites the
     other's reads. When the other writer is the CI runner, they are lost for good, because
     the runner is gone: next month re-reads them. The guard exists to prevent exactly this
     ("so a local push cannot drop the reads a monthly run made").
  2. Another writer lands between this tree's upload and its listing. This tree records the
     *other* writer's ETag beside its *own* checksum. Its next push reports "unchanged since
     pull, not uploaded" while the remote lacks its reads. Its next push after a build then
     passes the ETag guard and overwrites the other writer's reads, again with no refusal.

  Reproduced with the fake `aws`, a local tree A and a CI tree C, each adding one header
  read. The interleaving was: C checks, A checks and uploads, C's upload lands, A lists.

  | step | A's output | remote `headers.jsonl` |
  |---|---|---|
  | interleaved pushes | `3 lines pushed` (both) | `seed1 seed2 C1` (A1 lost) |
  | A pushes again | `headers.jsonl: unchanged since pull, not uploaded` | `seed1 seed2 C1` |
  | A adds A2, pushes | `4 lines pushed`, no refusal | `seed1 seed2 A1 A2` (C1 lost) |

  The windows are seconds wide (a local push in the same minute as the monthly push), so the
  probability is low. The cost is a re-read (hours of runner time), not a wrong catalogue.
  Fix: make the write itself the compare-and-swap, and take the ETag from the write. Use
  `aws s3api put-object --bucket "$BUCKET" --key "$PREFIX/$f.gz" --body "$BUILD/$f.gz"
  --content-type application/gzip --if-match "$etag"` (or `--if-none-match '*'` when there is
  no remote). Record the `ETag` it returns (`--query ETag --output text`) as `.etag`, and drop
  the listing at :110. A 412 is the refusal "pull first". This needs only `s3:PutObject`. The
  local CLI (2.34.34) has both flags, and S3 has supported `If-Match` on PutObject since
  November 2024. The caches are 15.6 MB at most, far under PutObject's 5 GB, so put-object
  needs no multipart. Pull's own window (list, then fetch) fails toward refusing, so it can
  stay as it is.

## Where the mechanism reaches, checked against its source of truth

| place | value used as the other side's state | taken from | verdict |
|---|---|---|---|
| s3_publish `items_to_upload` | bucket ETag = MD5 of the local file | the live listing, one call at plan time | fine. Single-part items (accepted). An SSE-KMS change would make every ETag differ, so >2000 changed, a rewrite, refused by MAX_UPLOAD: fails safe |
| s3_publish `same_items` | published body | public HTTPS GET of each object (probed: 200 on the global endpoint, `(2)` name quoted) | fine. A failed fetch raises |
| s3_publish `collection_differs` | published collection | `aws s3 cp` of the object, fetched only when listed | fine. Link order is deterministic (`listing()` sorts by url), so the comparison is not noisy |
| s3_publish `items_unbuilt` | bucket keys | listing | fine. `build-cache/` excluded. stacs enumerates by collection links (`catalogue.py`), so the cache objects are invisible to register and verify |
| s3_publish plan, then s3_sync upload | the plan still describes the bucket at upload | listing at T0 | fine for the one writer (workflow `concurrency`). Not atomic against a simultaneous local release, which is out of scope |
| laz_item rounding | the other platform's bytes | rounded to the 8-dp grid, and flips are absorbed by `same_items` | fine. `proj:*` is header data or PROJ wkt (0 of 8,713 differed, A1). The unrounded centre is used only for a check, never written |
| cache_sync `.etag` (pull) | remote object | listed before the fetch | fine. A change between the list and the fetch leaves `.etag` older than the content, so the next push refuses |
| cache_sync `.cksum` (pull) | remote content | the pulled copy, before the merge (R2 fix) | fine. Reproduced again: merge-pull then push uploads; unchanged pull then push does not |
| cache_sync `.lines` | floor for the local file | merged count at pull, uploaded count at push | fine. Conservative, and it is only consulted when `.etag` matches |
| cache_sync push guard and `.etag` (push) | remote is still what this tree last saw, and is now what it wrote | listing, before and after the upload | **finding above** |
| update.yml `steps.pull.outcome == 'success'` | data/build caches are a superset of the remote | the pull step | fine. The build only appends and tail-repairs (`headers_fetch`, `cache_tail_repair`), and single-writer appends flush per line |
| update.yml re-assume | fresh credentials | `configure-aws-credentials@v4` OIDC path (read upstream `src/index.ts`) | fine. With OIDC and no input keys it calls `AssumeRoleWithWebIdentity`, which STS serves without signing, so the expired env credentials from an earlier step are not used |
| update.yml Summary | what was published | `publish_plan.json`, which records a plan, not an upload | fine. The outcome column carries the result, and the line says "to upload" |

## Also checked, fine

- A scheduled run before #22 ships: about 174k items are changed, which is over
  SAME_CHECK_MAX, so it is a rewrite, and 174,282 is over MAX_UPLOAD, so it is refused before
  any upload. The run is red and the cache is still saved. It fails safe.
- `${#EXTRA_ARGS[@]}`, `${A[@]+…}` and `${A[@]+"${A[@]}"}` on an empty array under `set -u` in
  `/bin/bash` 3.2: all fine.
- A dry-run push still applies the tail cut to `$BUILD/$f`. That is the same repair the build
  makes, so it is not a published write.

## Verdict

One low-severity race in `cache_sync.sh push`, with an atomic fix. No other place the
mechanism reaches reads a stand-in where the source of truth was available.

## Disposition (session)

Accepted. `cache_sync.sh push` now writes with `aws s3api put-object --if-match <ETag the check
saw>` (`--if-none-match '*'` when there was none) and records the ETag the write returns.
Probed on the real bucket: a wrong If-Match on `build-cache/classes_full.jsonl.gz` returned
PreconditionFailed (exit 254) and left the object unchanged; a forced push of the same file
under the right If-Match succeeded, recorded `"4363159f…"` equal to the listing, and the next
push was a no-op. The mechanism's other reaches were checked by the reviewer against their
sources of truth (table above): none breaks.
