# Plan review (Plan agent, 2026-10-14) — summary, written by the session (the agent cannot write)

Verdict: no blockers. Q1 the rounding is the only item change (diff since v0.3.0; build log so far:
175,278 files in 233 groups, 175,278 headers cached / 0 to read, same 9 untrusted deliveries, CanElevation
counts as measured). bbox comes from rounded corners; extent from item bboxes. Tolerance 5e-9 + 1e-12
accepts the rounding (half-way ties covered) and rejects anything else. Q2 collection: only version and
its extension URL can differ. Q5: the 0.3.0 README timeout no longer applies.

Gaps / ordering folded into task_plan.md:
- G1/O2 nothing asserts the uploaded collection.json is stamped 0.4.0; stamp last, re-stamp after any rebuild.
- G2 re-run s3_sync.sh --dryrun after the upload: expect uploading 0, collection.json no, 0 unbuilt.
- G3a compare should print how many coordinates equal round(p, 8) exactly, and max |b - p|.
- G3b a test where published sits exactly half-way (bare TOLERANCE = 5e-9 would otherwise pass every test).
- G3c with new items, any extent change is accepted (new items expected 0 this release).
- G4 dryrun wording: uploading ≈ compare's changed count, 0 unbuilt, collection.json yes; MAX_UPLOAD unset.
- G5 stacs v0.2.0 reads pypgstac's private `_db` (documented for 0.9.6–0.10.0); use
  `stacs register --mode drift --dryrun` as the before-check (full comparison, no write), saves ~45 min.
- G6 exact numbers for the before-check: published = registered = 174,282, missing 0, orphaned 0,
  changed = compare's count, collection changed, queryables 1 missing.
- G7 keep the scratch copy of 0.3.0 bodies until IN SYNC; bucket versioning is the other way back.
- G8 tell /gh-pr-merge the version is 0.4.0 and NEWS already has its section.
- O1 do not close #22 on merge: its acceptance (the update.yml dryrun dispatch) runs after the merge.
- O3 render README only after the final verify. O4 cache push before the dispatch.
- A2 update.yml has never run: a red dispatch may be infrastructure; read which step failed.
- A3 the dryrun dispatch still pushes the build cache: pull before any later local push.
- Acceptance for the dispatch: publish_plan.json built 174,282, upload 0, unbuilt 0, collection false;
  job log "k of k items that differ by digest match their published body" (k ≈ 5, ≤ 9).
  Command: gh workflow run update.yml --ref main -f dryrun=true.
- S1 README render re-runs the demos: review its diff, expect only version/date and cache files.
- S2 fold NEWS `## Unreleased` (queryable, stacs v0.2.0) into `## 0.4.0`.
