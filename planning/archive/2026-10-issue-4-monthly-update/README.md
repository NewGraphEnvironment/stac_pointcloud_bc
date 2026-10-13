# Monthly update in GitHub Actions (#4)

## Outcome

`.github/workflows/update.yml` rebuilds the whole catalogue on the 6th of each month and
publishes what changed. It is warm because it starts from read caches kept in
`s3://stac-pointcloud-bc/build-cache/` (`scripts/cache_sync.sh`). Cold, the build is about
2.5 h of headers plus 3 h of class samples, which does not fit a runner. Publishing became a
digest diff (`scripts/s3_publish.py`, behind `scripts/s3_sync.sh`): only items whose MD5 the
bucket's ETag lacks are uploaded, and the collection goes only when something changed, so an
unchanged month publishes nothing and keeps the release stamp. Registration stays manual
(tailnet), and the run's summary gives the commands. `tests.yml` runs the suite on pull
requests.

The plan review found the one-hour OIDC session, which is shorter than the build, and that an
unguarded cache push could overwrite a good cache. It also raised whether a Linux build
matches a Mac one. It does not: 75% of footprints differ in their last bits. The user chose
to round lon/lat to 8 decimals, which needs a one-time rewrite of every item, the 0.4.0
release (#22). Code review then ran four rounds:

1. Rounding still flips about 5 boundary items. `same_items` now leaves an item that differs
   only by one grid step.
2. Round 1's checksum fix recorded the merged cache's checksum, which lost local reads.
3. The mechanism, a local value standing in for the remote's state, reached one more place:
   the push's check-then-act window. The push is now a conditional PUT.
4. Clean.

The research file is `research/build_reproducibility.md`.

## Measurement

- **Publish dry run** against the 0.3.0 build: 0 items to upload, collection unchanged,
  0 unbuilt, in **9 min 17 s**. The full-sync publish took 95 min.
- **Cross-platform footprints**, macOS arm64 against linux/amd64 (QEMU), PROJ 9.8.1, 8,713 items:
  - unrounded: **6,559 differ**, by at most **5.68e-14°**;
  - rounded to 8 dp: **0 differ**.
  - Over all 174,282 published footprints, **5 items** sit within 1 ulp of a rounding
    half-way point and 9 within 4 ulp. That is why `same_items` exists.
- **Cache**: 20 MB gzipped (headers 15.7 MB). The round trip was byte-identical.
- **Conditional PUT on the bucket**: a wrong If-Match returned PreconditionFailed and left the
  object unchanged; the right one recorded its own ETag.
- Changed the plan: the rounding, the 40,000-item ceiling, and dropping the `rewrite` input
  (one publish must fit the 1 h session).
- Not yet measured: runner wall time and peak RSS. The first dry-run dispatch after merge
  measures them.

## Evidence

Reviews: `review-plan.md` and `review-round1.md` to `review-round4.md` in this directory.
Probe scripts are described in `findings.md`; their outputs were scratch files, not kept.

Closed by: PR (see `progress.md`)
