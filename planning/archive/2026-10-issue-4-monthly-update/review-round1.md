# Code-check round 1 — branch `4-monthly-update-in-github-actions-with-the` (b932c3c...5d2f83b)

Reviewer: subagent, 2026-10-12. Suite run in a fresh clone of HEAD (no data/build, as CI):
277 passed. `cache_sync.sh` exercised in a scratch tree against a fake `aws` (seed push,
pull into an empty tree, append + interrupted tail + push, stale-tree push refused, merge
pull, push): every guard behaved as documented.

## Findings

- **[fragile] scripts/laz_item.py:351-354 — 8-dp rounding still leaves about 5 items that round
  differently on macOS and linux, so the first monthly run after a Mac-built release publishes
  them and drops the collection's `version`.** Rounding moves the platform difference from
  "every last bit" to "values that sit within a few ulp of a rounding boundary", which it
  cannot remove. Measured over the 174,282 unrounded (0.3.0, Mac) footprints in
  `data/build/items`: values within 1 ulp of an 8-dp half-way point are in 5 items
  (`093n024_3_4_4…2022` lon -125.324987385 at 0.00 ulp; `092h011_3_4_2…20170713` 0.09;
  `092i089_4_4_3…2019` 0.60; `093k079_3_3_3…20240815` 0.77; `082l026_1_4_3…2019` 0.86), and
  9 items within 4 ulp. A1 measured 75% of values differing by up to 5.68e-14 (1 to 4 ulp at
  these magnitudes), so 3 to 6 items should round apart. The A1 re-probe ("0 of 8,713
  differ") sampled every 20th file, where about 0.25 hits were expected, so it could not see
  this. Consequence: #22 releases 0.4.0 from a Mac build (stamped); the next scheduled run on
  linux finds those items' bytes differ, uploads them, and since any upload publishes the
  collection, publishes it unstamped. That contradicts README.Rmd's "A month with nothing new
  publishes nothing, and the collection keeps its release `version`", and every later
  Mac-built release flips the same items back. Options: build the release on the runner (but
  see the next finding), or compare such items in `s3_publish.py` by parsed content with a
  tolerance on coordinates rather than by MD5. Script: the count is reproducible with a
  `Decimal` distance-to-boundary pass over `data/build/items` (scratchpad `near2.py`).

- **[fragile] .github/workflows/update.yml:153-167 — a `rewrite` dispatch cannot publish a
  full rewrite inside the one-hour session.** The publish role is assumed once, just before
  Publish, and the session is 3600 s with static env credentials (no refresh). The measured
  full upload is 95 min for 174k items (CLAUDE.md), and `s3_publish.py`'s plan alone is
  about 9 min. A rewrite of more than roughly 100k items therefore dies mid-`aws s3 cp` with
  expired credentials: the items uploaded so far are live, `collection.json` is not
  (items-first order holds, so no dangling links), and the run is red. Re-running resumes
  (digest-based), but each re-run is a whole rebuild. README.Rmd offers "dispatch with
  `rewrite` to publish one on purpose", and #22 is exactly that case (every item's footprint
  changes). Either say a full rewrite takes re-runs / is published locally, or split the
  upload into batches each preceded by a re-assume.

- **[fragile] .github/workflows/update.yml:143-167 — the publish is gated on the cache push
  succeeding.** "Save the build cache" runs under `always()`, but Audit, the publish
  credentials and Publish run under the default `success()`, so a failed push skips them.
  `cache_sync.sh push` fails by design when the remote cache's ETag is not the one this run
  pulled, i.e. whenever someone does `cache_sync.sh push` from a local build during the
  4-hour window, and also on any transient S3 error. Then a good build publishes nothing and
  the run is red for a reason that is not "a build that refused something" (the README's
  definition of a red run). If that coupling is intended, the README should name it;
  otherwise give the cache step `continue-on-error: true` and report its outcome in the
  summary (the summary already has the table).

- **[fragile, low] scripts/cache_sync.sh:372-374 — "An unchanged cache is not uploaded" holds
  only on one platform.** The unchanged test is `cmp` of `gzip -n` output against the pulled
  `.gz`. This Mac's gzip is Apple gzip 457 (zlib); the runner's is GNU gzip, whose deflate
  output is not byte-identical (not measured here: no GNU gzip on this machine). If they
  differ, every monthly run re-uploads all four caches although nothing changed, which
  changes their ETags and makes every local tree's next `push` refuse until it pulls.
  Harmless beyond that (20 MB, and pulling first is the documented workflow), but the
  comment and the findings' "an unchanged push uploads nothing" are same-platform results.
  Comparing the uncompressed bytes (or line count + digest of `$BUILD/$f` recorded at pull)
  would make it platform-independent.

- **[docs, low] README.Rmd:263 — "A new mapsheet-year is built, not refused" has an
  exception.** `catalogue_build.copc_pairs_check` (catalogue_build.py:445-448) refuses any
  group that pairs with a CanElevation COPC but is not in `data/copc_pairs.json`, so a new
  mapsheet-year whose file names match a CanElevation file is refused until
  `--groups-record`. Unlikely with CanElevation's four fixed projects, but the sentence is an
  operator's triage guide.

## Checked and fine

- `inputs.*` on a scheduled run are empty, so MAX_UPLOAD=40000 applies and dryrun is off.
- `bash` shell default is `-eo pipefail`; `/usr/bin/time` and the `tee` pass the build's exit.
- Item ETags from `list-objects-v2 --output json` are quoted and stripped; names with spaces
  are raw keys; `--query` on JSON output is applied after pagination merging.
- `collection_differs`: `version_stamp` adds only `version` and `VERSION_EXT`, both removed by
  `_unstamped`; `collection_build` is otherwise deterministic (no timestamps).
- `cache_sync.sh`: merge order (local first, pulled last, readers keep the last line and
  re-check the ETag) can shadow a newer local read with an older pulled one, which costs a
  re-read, never a wrong record. Line-count check precedes the tail cut, and `wc -l` does
  not count the partial line, so the order is safe.
- `stacs register/verify` read the bucket (`--bucket-url`), so the summary's commands do not
  need the CI build locally. `stacs` is public, so `uv sync --frozen` works on the runner.
