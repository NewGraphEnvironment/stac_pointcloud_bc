# Plan review — #17 (Plan agent, 2026-10-17, condensed by the parent session)

Blocker
- B1: a whole read uses the same LazrsParallel backend as the sampler, so it is no test of the
  two chunk-table files; a sequential (LazBackend.Lazrs) or laszip read would be. No command reads
  them whole as is; a trial must write to a scratch file, not classes_full.jsonl. -> dropped from
  this issue; carve-out kept.
- B2: catalogue_compare.py (0.4.0-only) fails any new classification:classes, stac_extensions or
  description change. -> added to Phase 3.

Gap
- G1: screen wording in catalogue_build comments/logs/--limit reason, laz_classes_probe
  comments, README.Rmd:236 (and README.md/index.html), maintaining.md cache size (~95 MB
  uncompressed classes.jsonl after the sweep) and refusal list, cache_sync.sh "3 h of samples".
  -> code wording done; docs added to Phase 4.
- G2: tests that assume the screen (1423, 1501, message asserts, GROUP11 comment). -> done.
- G3: EXCLUDE's shape does not refuse a departed file; a carve-out not sampled can never show it
  reads; key each entry by ETag. -> done (ETags 056c28d7...-9, 54247648...-5).
- G4: expect about 38 more unreadable files in the sweep (2 of 7,834); each needs an entry, or
  a sequential-backend fallback. -> open; decide on what the sweep finds.
- G5: an empty good sample passes unflagged. -> refused now.
- G6: a flagged file that cannot be read whole refuses every build with "re-run" advice. -> open.

Ordering
- O1: pushing the swept cache before merge reddens a main run (flags unrecorded); merging first
  sends a monthly run into ~148k samples. Push and merge back to back; check OIDC (#22).
- O2: the carve-out set comes from the sweep's errors. O4: expect classes_required.json == []
  after --classes-record --force (all 11 ids have flagging samples).

CI cost: ~124 samples/min locally; a 240-min step leaves ~180 min, so ~20k new or re-delivered
files a month is the ceiling (was 40k by MAX_UPLOAD). Log samples per minute.

Scope: no release steps in the plan (S1). S2: --limit's unrecorded=False needs a new reason.
Acceptance: the 349 0.4.0 lists unchanged; description states the carve-out count.
Default-mode laz_classes_probe writes records the build reuses (checked: same probe, ETags,
COPC encoding).
