# Task: Release 0.4.0: publish the rounded footprints (#22)

**If we do it:** the published items carry footprints rounded to 8 decimals (`laz_item.LONLAT_DECIMALS`, #4), so a monthly CI build on linux/amd64 writes the same bytes as the published catalogue, and the monthly update publishes only real growth. **If we never do:** every monthly run plans about 174k uploads and is refused by its 40,000-item ceiling (`MAX_UPLOAD`), so the update never publishes.

Why: unrounded, 6,559 of 8,713 sampled footprints differed between macOS arm64 and linux/amd64 in their last bits (at most 5.7e-14 degrees). Rounded, 0 of 8,713 differ (#4, `planning/archive/…issue-4…/findings.md`). Every item's `geometry` and `bbox` change once, by under 1 mm, and the collection extent with them. Nothing else should change.


## Context

#4 rounds every footprint's lon/lat to 8 decimals (`laz_item.LONLAT_DECIMALS`), so a linux/amd64 CI build writes the same bytes as a macOS build. The published 0.3.0 items are still unrounded. Until they are republished, every monthly run plans about 174k uploads and is refused by its 40,000-item ceiling. The first scheduled run is 2026-11-06.

Since v0.3.0 the only change to what an item holds is that rounding (`git diff v0.3.0..origin/main -- scripts/` shows `laz_item.py` +7 lines, the rounding only; `catalogue_build.py` is unchanged). So the release is: every item's `geometry` and `bbox` move by under 1 mm, the collection's spatial extent with them, and nothing else. #27 (merged) adds one more thing the register publishes: the `lidarbc:delivery` queryable, which closes #5.

This is a full production publish from m1 (tailnet: geopro reachable), the same procedure as 0.3.0 (`planning/archive/2026-10-issue-2-index-all-pointcloud/progress.md`, "Publish"). **Approving this plan is the go for the publish (Phases 4 and 5)**, as the user gave it for 0.3.0. If auto mode refuses an upload or register as a production write, I stop and offer the two routes (leave auto mode for that step, or the bare command for you to run), rather than retry.

Out of scope, so "nothing else changes" holds: #25 (date parser), #15, #17, #3.

## Phase 1: Compare for 0.4.0
- [x] Rewrite `scripts/catalogue_compare.py`'s expected diff for this release. A published item and its build may differ only in `geometry` and `bbox`. Each built coordinate has at most 8 decimals and lies within 5e-9 degrees of the published one (half a unit in the 8th place, so a last-bit difference that straddles a rounding boundary still passes). Everything else is equal, `copc` asset included. Items only in the build (new LidarBC files since 2026-10-10) are reported as new, not failed. Items only in the bucket fail. The collection: item links are a superset; only `extent` (spatial within 5e-9) and `version` may differ; anything else is printed and fails.
- [x] Rewrite `tests/test_catalogue_compare.py` to match. Passes: the 0.3.0-shaped published item (unrounded) against its rounded build. Named: a coordinate off by 1e-7, a changed property, a changed asset, an added extension, a ring with a vertex more. Prove each guard fires by mutating `catalogue_compare.py` in a copy.
- [x] Update the module docstring (the 0.3.0 version stays in git at `v0.3.0`).
- [x] From the plan review (`review-plan.md`, G3): print how many coordinates equal `round(published, 8)` exactly and the largest shift, and test a published value exactly half-way.
- [x] `/code-check`, then commit.

## Phase 2: Build
- [x] `bash scripts/cache_sync.sh pull`.
- [x] `PYTHONUNBUFFERED=1 PYTHONPATH=scripts uv run python scripts/catalogue_build.py` in the background, logged to `logs/<YYYYMMDD_HHMM>_catalogue_build_v0.4.0.log` (warm, about 53 min in 0.3.0). Exit 0 required. A refusal (a group under 90% of its count, a COPC count change, a class read the screen requires) is a finding: record it in `findings.md`, and if it needs `--groups-record` or `--classes-record` (`maintaining.md`), say so before running that.
- [x] Record items built, new since 0.3.0, peak RSS and duration in `progress.md`.

## Phase 3: Compare against the published bucket
- [x] `aws s3 sync s3://stac-pointcloud-bc <scratch>/published --exclude 'build-cache/*'`. Time it; it is about 174k small objects.
- [x] `uv run python scripts/catalogue_compare.py --published <scratch>/published`, logged. Exit 0 required: 0 published items differing beyond the rounding, 0 only published.
- [x] `bash scripts/cache_sync.sh push`.
- [x] Commit the logs and the PWF.

## Phase 4: Publish to the bucket
- [x] `bash scripts/s3_sync.sh --dryrun` with `MAX_UPLOAD` unset: expect uploading equal to the compare's changed count, 0 unbuilt, `collection.json yes` (G4).
- [x] `uv run python scripts/collection_version.py --version 0.4.0`, last, and assert `version == "0.4.0"` and the version extension in `data/build/collection.json` just before the upload. Re-stamp after any rebuild (G1, O2).
- [x] `bash scripts/s3_sync.sh` in the background, logged (95 min in 0.3.0). Read the log's own totals, not the wrapper's exit.
- [x] `bash scripts/s3_sync.sh --dryrun` again: expect uploading 0, `collection.json no`, 0 unbuilt, which proves the bucket holds the build (G2). Keep the scratch copy of the 0.3.0 bodies until the final verify (G7).

## Phase 5: Register
- [x] Confirm the host's pypgstac is in 0.9.6–0.10.0 (stacs reads its private `_db`, G5): `ssh root@geopro 'cd /opt/geoserv/scripts && /root/.local/bin/uv pip show pypgstac'`, gated on what it prints.
- [ ] `PYTHONUNBUFFERED=1 uv run stacs register --config stacs.toml --mode drift --dryrun`, logged, in place of the first verify (the same comparison, no write; G5). Expect published = registered = built, missing = new items, orphaned 0, changed = the compare's count, collection changed, queryables 1 missing (G6).
- [ ] `PYTHONUNBUFFERED=1 uv run stacs register --config stacs.toml --mode drift`, logged (65 min in 0.3.0). This is the first queryables load on this database.
- [ ] `stacs verify` again: `IN SYNC` with `1 declared queryable(s) served as declared`.
- [ ] Live checks: collection `version` 0.4.0; `/collections/stac-pointcloud-bc/queryables` lists `lidarbc:delivery`; a served item's coordinates have at most 8 decimals; a `lidarbc:delivery` filter returns items.
- [ ] Edit #5's body to tick its queryable box; it closes from this PR. #22 stays open until the dispatch below passes (O1).

## Phase 6: Record and PR
- [ ] `NEWS.md`: `## Unreleased` (the queryable and stacs v0.2.0) becomes `## 0.4.0`, with what was published and its verification, measured from the logs (not this issue).
- [ ] After the final verify (O3), re-render `README.md` and `index.html` with the `build` chunk, so the page names catalogue version 0.4.0. Review the diff: expect only the version/date line and cache files (S1).
- [ ] Archive the PWF with `Measurement` and `Evidence` (logs prefix), then `/gh-pr-push`. The PR closes #5 and relates to #22.
- [ ] After the merge, which is your call: tag v0.4.0 on main as 0.3.0 was (release commit bumping `pyproject.toml`/`uv.lock` to 0.4.0, then the tag), and dispatch `update.yml` with `dryrun`. `gh workflow run update.yml --ref main -f dryrun=true`. Pass: `publish_plan.json` built = the release's count, upload 0, unbuilt 0, collection false; the job log's "k of k items that differ by digest match their published body". `update.yml` has never run, so a red run may be infrastructure: read which step failed (A2). Then close #22. The dispatch pushes the build cache, so pull before any later local push (A3).

## Validation

- [ ] Tests pass
- [ ] `/code-check` clean (each commit, or once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
