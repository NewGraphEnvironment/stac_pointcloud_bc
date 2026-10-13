# Progress — Monthly update in GitHub Actions with the rtj#362 role (#4)

## Session 2026-10-12

- Plan-mode exploration — phases approved by user (cache in `build-cache/` prefix; run
  summary as the register cue)
- Created branch `4-monthly-update-in-github-actions-with-the` off main
- Scaffolded PWF baseline from issue #4 with approved phases
- Next: start Phase 1
- Phase 1: `scripts/s3_publish.py` (plan by digest), `s3_sync.sh` uploads only the plan,
  `tests/test_s3_publish.py` (12 tests). Dry run against 0.3.0: 0 items, collection
  unchanged, 0 unbuilt, 9 min 17 s.
- Plan review (Plan agent, spawned 01:45Z): 2 blockers, 7 assumptions, 7 gaps; triaged in
  `review-plan.md`, corrections added to `task_plan.md`.
- A1 probed: linux/amd64 footprints differ from the Mac's in the last ulp for 75% of items.
  Asked the user (stored-data decision); continuing on Phases 2-4.
- Rounded footprints to 8 dp (user's choice); probe after: 0 of 8,713 differ. Test red without the rounding.
- Phase 2: `scripts/cache_sync.sh`; seeded `build-cache/` (20 MB); round trip identical; push guards exercised (findings.md). `s3_sync.sh` gained `MAX_UPLOAD`.
- Phase 3: `.github/workflows/update.yml` (role re-assumed before cache push and publish, MAX_UPLOAD 40,000 unless `rewrite`, summary under always()), `tests.yml` (pytest on pull_request); actionlint clean. `cache_sync.sh push` cuts an interrupted record first.
- Phase 4: README.Rmd 'Monthly update' (rendered from cache, update_query = FALSE, so only prose changed); CLAUDE.md monthly-update facts.
