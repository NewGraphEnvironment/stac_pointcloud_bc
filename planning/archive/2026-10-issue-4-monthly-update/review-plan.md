# Plan review (#4), Plan agent, 2026-10-13

Spawned 01:45Z and delivered in reply text (the Plan type cannot write); recorded here. It
reviewed the plan and the Phase 1 work in progress. Triage of each finding is in the
`Disposition` column, verified as noted.

## Confirmed (no finding)

- The cache is complete with four files: `headers.jsonl`, `copc_headers.jsonl`,
  `classes.jsonl` and `classes_full.jsonl`. `class_targets.jsonl` is written and never read
  by the build. `classes_audit_ids.txt` is used only by `--audit`.
- Audit samples are not needed for a pass. They travel in `classes.jsonl` anyway.
- Every cache is tail-repaired before it is read, so a killed build leaves caches that are
  safe to push.
- Items are 2.5 to 4 KB, so every ETag is single-part. Botocore url-decodes listed keys, so
  the 143 names with a space are handled.
- Nothing in an item or the collection depends on the build time.
- Pushing the cache before publishing is safe: the caches record source reads, not
  publication.
- The collection rule holds for every case traced. Forcing the collection whenever an item
  uploads drops the stamp; that is intended, and must be documented.

## Findings

| # | Kind | Finding | Disposition |
|---|------|---------|-------------|
| B1 | Blocker | The OIDC session is 1 h (no `max_session_duration` on the role). The cache push and the publish run after a build of 53 min or more. | Accepted. Re-assume the role before the push and before the publish. |
| B2 | Blocker | `always()` on the push uploads after a failed or partial pull, which regresses the cache. | Accepted. Gate on the pull's outcome. The push refuses a file with fewer lines than were pulled, and skips an unchanged `.gz` (`gzip -n`). |
| A1 | Assumption | A Linux x86_64 rebuild may not be byte-identical to the Mac arm64 build (PROJ, last ulp). Then the first CI run rewrites everything and drops 0.3.0. | Probe in a linux/amd64 container before merge; see findings.md. |
| A2 | Assumption | Fork on Linux versus spawn on the Mac: peak RSS with workers is unmeasured. | Wrap the build in `/usr/bin/time -v`. Measure on the first dry-run dispatch. |
| A3 | Assumption | Runner time is unmeasured, and the build step needs a stated timeout. | Build step 240 min, job 345 min. Revisit after the first dispatch. |
| A4 | Assumption | Runner image and Python are unpinned. | Pin `ubuntu-24.04` and Python 3.12. |
| A5 | Assumption | Growth in an existing group shifts its density screen and can refuse a flagged file until `--classes-record`. The list of red-run causes is incomplete. | Document the full list in the README. |
| A6 | Assumption | A `HEADER_VERSION` bump makes CI read every header cold. | Document: rebuild locally first. |
| A7 | Assumption | GitHub disables a public repo's schedule after 60 days with no activity, and this run commits nothing. | Document the re-enable step. |
| G1 | Gap | `s3_sync.sh ""` trips the usage check. | Branch in shell inside the workflow. |
| G2 | Gap | The scratch probe cannot go through `s3_sync.sh`, whose build path is fixed. | Probe with `s3_publish.py --build <scratch>`. |
| G3 | Gap | `--expect` taken from `ls items` is circular. | Take it from the collection's item links. |
| G4 | Gap | The job summary is not under `always()`. | Accepted. |
| G5 | Gap | Nothing runs the suite on Linux before merge. | Add `tests.yml` on `pull_request` (no AWS). |
| G6 | Gap | tqdm bars bloat CI logs. | Set `TQDM_MININTERVAL=60`. |
| G7 | Gap | No rule for a local build and the shared cache. | Document: pull before a local build, push after. |
| O1-3 | Ordering | The second credentials step goes before the push. The push gate also covers a failed pytest or OIDC step. Seeding comes before the first dispatch. | Accepted. |
| S1 | Scope | A dry run throws away hours of reads. | Accepted. The cache is not publication: a dry run saves the cache and uploads no catalogue file, and the input description says so. |
| S2 | Scope | CLAUDE.md should change only the `s3_sync.sh` timing. The rtj bucket comment "Catalog JSON only" goes stale. | Accepted. Note the rtj comment in the PR. |
| S3 | Scope | The README md render with `update_query = TRUE` hits the live API. | Check the render options before rendering. |
| Acc1 | Acceptance | The dry run should also show 0 unbuilt keys. | Done: 0 unbuilt (progress.md). |
| Acc2-4 | Acceptance | A Linux reproduction criterion, runner RSS and timings, and the red-run list. | A1, A2 and A5. |
