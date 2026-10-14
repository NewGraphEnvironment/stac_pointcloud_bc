# Release 0.4.0: publish the rounded footprints (#22)

## Outcome

Republished all 174,282 items with footprints rounded to 8 decimals (#4), so the monthly update's
linux build writes the same bytes as the published catalogue, and registered them with stacs v0.2.0,
which also loaded the `lidarbc:delivery` queryable (#5, declared in #27). The release changed nothing
else, and the work was to prove that before writing anything: `scripts/catalogue_compare.py` was
rewritten as a gate that accepts the rounding and nothing more, and holds the build to itself.

What was learned about the gate: three review rounds, two of them finding a defect inside the
previous fix. The mechanism round 3 named was that the gate compared each built artifact with its
published twin but never the build with itself (its `items/` against its own collection links, its
extent against its items' envelope), and took the published set from whatever files a local copy
held, so an interrupted copy read as new items. It ended by enumeration: 30 failure sites and
conditions mutated one at a time, each caught by a test (`findings.md`, "The compare's
cross-checks"). The plan review caught that nothing asserted the uploaded collection was stamped, and
proposed `register --dryrun` in place of the first verify; one of its claims (that the dryrun reaches
pypgstac) was checked against stacs' README and was wrong.

Still to do, after the merge (task_plan Phase 6, last box): the v0.4.0 release commit and tag, and
the `update.yml` dryrun dispatch, which is the release's acceptance test. #22 closes when it plans 0
uploads.

## Measurement

- **Build**: 1,259 s (21 min, against 53 for 0.3.0, since every cache was warm and nothing was read),
  peak RSS 3.54 GB. 175,278 files in 233 groups, 174,282 items, 13,970 with a COPC copy, 17,552
  screened, 349 read whole: every count equal to 0.3.0's.
- **Compare** against a copy of the 0.3.0 bucket (27 min to copy 174,283 objects): 2,439,948
  coordinates, all equal to the published value rounded to 8 decimals; largest shift 5e-9 degrees
  (under 1 mm); 0 items differing beyond the rounding. Confirmed the expected, and turned "nothing
  else changes" from a reading of the diff into a measurement.
- **Upload**: 174,282 items and collection.json in 36 min (0.3.0: 95). A dryrun after it planned 0.
- **Register dryrun**: 25 min; registered 174,282, changed 174,282, queryable 1 missing.
- **Register**: 42 min (0.3.0: 65). **Final verify**: 26 min, `IN SYNC`, queryable served as declared.
- Host pypgstac 0.9.9.

## Evidence

`logs/20261014_*` (local; `logs/*.log` is gitignored, as in 0.3.0). Reviews: `review-plan.md`,
`review-round1.md` to `review-round3.md`.

Closed by: PR (this branch); #22 stays open until the post-merge dispatch.
