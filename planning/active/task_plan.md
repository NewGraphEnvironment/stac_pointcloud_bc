# Task: Monthly update in GitHub Actions with the rtj#362 role (#4)

**If we do it:** new LidarBC deliveries reach the collection without a local run, as stac_dem_bc's `update.yml` does for rasters. **If we never do:** the collection is as current as the last time someone built it by hand.

The bucket and the OIDC role `stac_pointcloud_bc_update` exist (NewGraphEnvironment/rtj#362). The trust names this repo. Registration still needs the tailnet, as it does for stac_dem_bc.


## Context

New LidarBC deliveries reach `stac-pointcloud-bc` only when someone builds it by hand. #4
asks for a monthly GitHub Actions run, as stac_dem_bc's `update.yml` does for rasters. The
bucket and the role exist (rtj#362). Registration stays manual because it needs the tailnet.

What exploration found that shapes the work:

- **The build is a full rebuild over local caches** (`data/build/headers.jsonl` 384 MB,
  `copc_headers.jsonl` 28 MB, `classes.jsonl` 18 MB, `classes_full.jsonl`; none committed).
  Cold, it is about 2.5 h of header reads plus 3 h 10 min of class samples (#2 archive).
  That doesn't fit a 6 h runner. Warm, it was 53 min. So the caches must persist between
  runs. **Decided: `s3://stac-pointcloud-bc/build-cache/`, gzipped, seeded once from this
  Mac.**
- **`s3_sync.sh` re-uploads everything on a fresh runner.** Every file there has a new
  mtime, so a run takes 95 min and rewrites all 174k items, leaving about 350 MB of
  noncurrent versions each month. rtj's bucket comment says to revisit if full rewrites
  become routine. Probed: an item's S3 ETag equals the MD5 of its local file (SSE-S3,
  single-part). `collection.json` is multipart (`-5`), so it is compared by body instead.
  Publish therefore becomes a digest diff. Locally that means one path for both callers,
  not a CI-only copy.
- **Role**: `arn:aws:iam::414155577829:role/role_gha_stac_pointcloud_bc` (confirmed with
  `aws iam get-role`). It has Get, Put and List across the bucket, **no delete**, and is
  trusted on **main only**. So the workflow cannot assume it from a branch, and the first
  real run is after merge.
- **The build already expects this**: a new mapsheet-year is logged and built, not refused
  (`groups_check`, comment citing #4). What it does refuse stays a red run for a human:
  a short group, a header fault, a new or changed COPC pair, an unrecorded class flag.
- **Collection version**: `version` is stamped at release (`collection_version.py`). CI
  never stamps. Rule: compare the stamp only when the build carries one. In an unchanged
  month nothing is published, so 0.3.0 survives. In a month that changes items, an
  unversioned collection is published, as stac_dem_bc's `--clear-version` does.
- **Decided: registration cue is the run summary only**: counts, plus the exact
  `stacs verify` / `stacs register --mode drift` commands. This matches stac_dem_bc.
- Nothing the run writes is committed back, so the workflow needs `contents: read` only.

## Phase 1: Publish by digest

- [x] Tests first, in `tests/test_s3_publish.py`, for pure functions:
  - items to upload: local MD5 ≠ bucket ETag, a multipart ETag, or absent from the bucket;
  - bucket item keys not built: reported, never deleted, with `build-cache/` and
    `collection.json` excluded;
  - the collection rule: it is published if any item uploads, or if it differs from the
    published one. `version` and the version-extension URI are ignored only when the
    build carries no `version`.
- [x] `scripts/s3_publish.py`:
  - list the bucket once (`aws s3api list-objects-v2`, one process);
  - hash the build;
  - fetch the published `collection.json`;
  - write a stage directory of hardlinks to the changed items, plus a plan line with the
    counts.
- [x] `scripts/s3_sync.sh` calls it, then `aws s3 cp --recursive` the stage (items first),
  then `collection.json` only if the plan says so. It keeps the `--dryrun` contract and
  the linked-equals-files set check, and adds no `--delete`.

## Phase 2: Build cache in the bucket

- [ ] `scripts/cache_sync.sh pull|push [--dryrun]` moves `headers.jsonl`,
  `copc_headers.jsonl`, `classes.jsonl` and `classes_full.jsonl` (laz_classes_probe
  names), gzipped, to and from `build-cache/`.
  - `pull` refuses a missing object or a failed gunzip, rather than building cold
    without saying so.
  - `push` uploads each `.gz` as a whole object, never a partial one.
- [ ] Seed `build-cache/` from this Mac's `data/build`, then pull it into scratch and `cmp`
  the round trip. This writes to the production bucket. If auto mode refuses it, I hand
  you the bare command.

## Phase 3: Workflow

- [ ] `.github/workflows/update.yml`:
  - Triggers: cron `17 10 6 * *` (6th of the month, staggered from stac_dem_bc's 3rd),
    plus `workflow_dispatch` with a `dryrun` boolean.
  - `permissions: {id-token: write, contents: read}`, a `concurrency` group,
    `timeout-minutes: 340`.
- [ ] Steps, in order:
  1. checkout → `astral-sh/setup-uv` → `uv sync --frozen` → `uv run pytest -q`;
  2. OIDC into the role → `cache_sync.sh pull`;
  3. the build, with `PYTHONUNBUFFERED=1` and its own step timeout so the cache push
     still gets time;
  4. `cache_sync.sh push` under `if: always() && !inputs.dryrun`, so a failed or timed-out
     run keeps the reads it made;
  5. `stacs audit --config stacs.toml --dir data/build/items --expect <built count>`;
  6. `s3_sync.sh` (or `--dryrun`);
  7. job summary with upload, unlinked and collection counts, plus the register and
     verify commands;
  8. log artifact under `always()`.
- [ ] Lint with `uvx --from actionlint-py actionlint` (nothing installed on the machine).

## Phase 4: Docs

- [ ] `README.Rmd`: add a "Monthly update" section covering what runs, where the cache
  lives, what a red run means, and that registration is by hand from the tailnet. Update
  the publish block's timings. Re-render `README.md` and `index.html` with the `build`
  chunk.
- [ ] `CLAUDE.md` (above the marker): replace the four-hour full-publish fact with the
  digest publish, and add the cache prefix and the main-only, no-delete role.

## Phase 5: Verify locally

- [ ] `uv run pytest` green, and each new guard shown red against a restored defect.
- [x] `bash scripts/s3_sync.sh --dryrun` against today's `data/build`, which is what 0.3.0
  published. It must plan **0 items and no collection**, and I record how long it takes
  against the old 95 min.
- [ ] Probe both directions: change one local item and one collection field in a scratch
  copy, and confirm the dry run plans exactly that one item, and then the collection.

## Corrections from the plan review (`review-plan.md`)

- [ ] Re-assume the role before the cache push and before the publish (1 h OIDC session, B1)
- [ ] Push gated on a successful pull; refuse fewer lines than pulled; skip an unchanged `.gz` (B2)
- [ ] Cross-platform footprints (A1): linux/amd64 differs from the Mac in the last ulp for 75%
  of a 1-in-20 sample (findings.md). Decision with the user; see findings.md.
- [ ] Pin `ubuntu-24.04` and Python 3.12; `/usr/bin/time -v` on the build; `TQDM_MININTERVAL` (A2, A4, G6)
- [ ] `--expect` from the collection's item links; summary under `always()`; dry run saves the cache (G3, G4, S1)
- [ ] `tests.yml` on `pull_request`, no AWS (G5)
- [ ] README: every red-run cause, the 60-day schedule rule, local pull-before-build (A5-A7, G7)

## Validation

- [ ] Tests pass
- [ ] `/code-check` clean (each commit, or once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion

## After the PR (not in this mandate)

Merge, then dispatch with `dryrun=true` to measure runner time. That is the first moment
the role can be assumed. Then run a real dispatch. Both need your go-ahead.
