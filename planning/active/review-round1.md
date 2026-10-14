# Code-check round 1: staged `scripts/catalogue_compare.py` + `tests/test_catalogue_compare.py` (#22)

Reviewed 2026-10-14 (UTC). Applied code-check-python.md and the Mechanisms section of code-check.md.

## Verdict

No defect that passes a wrong build or fails the real rounding. Two low findings, both about
what the tests cannot see.

## Findings

- **[low] tests/test_catalogue_compare.py — `main()` and `items_load()` are untested, so the gate's exit code can be broken and the suite stays green.**
  I mutated a scratch copy and ran the suite against each mutation. These all left it at 22 passed:
  - `return 1 if (bad or only_pub or problems) else 0` changed to `return 0`;
  - `only_pub` dropped from that condition;
  - the `f != "collection.json"` filter removed from `items_load`;
  - `body.pop("links", None)` removed;
  - the `bool` exclusion in `rounding_diff` removed.

  The last three fail loudly against the real bucket (spurious only-published or differs-in-links), so a run would show them.
  The first two do not show: they turn a failing gate into exit 0, and this script is the only check before the full republish.
  The fix is one test that writes a two-item published dir and a build dir to `tmp_path` and asserts `main()` returns 1 when an item is only in the bucket and 0 for the rounding alone.

- **[low] scripts/catalogue_compare.py:107-110 — with any new item, every extent difference becomes a printed "change" and none is a problem.**
  `if ext and new:` moves all of `rounding_diff(extent)` into `changes`. A new item can only grow the spatial extent and the temporal interval, because items missing from the build already fail. Yet with `new > 0`, all of these pass silently:
  - a shrunk bbox;
  - a dropped temporal interval;
  - a changed extent structure.

  `catalogue_build.py` is unchanged since v0.3.0, so this is latent rather than live. It matters only if this release's build finds new LidarBC files, which a 2026-10-10 listing would not have.
  A tighter rule: when `new > 0`, require the built extent to contain the published one (to within TOLERANCE) and the temporal interval's structure to be unchanged.

## Checked and sound (the brief's questions)

- **`round(built, 8) != built` as the "at most 8 decimals" test.**
  - `round(round(x, 8), 8) == round(x, 8)` for doubles: the result is the double nearest an 8-place decimal, far closer to it than 0.5e-8.
  - `json` writes `repr`, which round-trips, so the test is sound after serialisation.
  - Ints pass unchanged: `round(int, 8)` is an int.
- **TOLERANCE against the real rounding, measured rather than reasoned.**
  - Method: rebuilt every item's footprint with the current `laz_item.item_create` from the cached headers (`data/build/headers.jsonl`, read only) and ran `cc.rounding_diff` on `geometry` and `bbox` against the 0.3.0 items in `data/build/items`. That copy is the published one: an item fetched from the bucket matched its local copy.
  - Results: 174,282 of 174,282 pass, 0 diffs, every bbox moved. The largest bbox shift is 4.999996860988176e-09, so the real margin under TOLERANCE is about 3e-15 plus the 1e-12 slack.
  - Cross-platform noise: the #4 measure was at most 5.7e-14 between macOS arm64 and linux/amd64, which is about 18x inside the slack. A last-bit straddle of a rounding boundary therefore cannot exceed TOLERANCE.
- **bbox and corners.**
  - The bbox is the min/max of the rounded corners. Because rounding is monotone, it equals `round(published bbox, 8)` for all 174,282 items (checked in the same run).
  - The collection's spatial extent is the min/max of the item bboxes (`collection_build`), so with no new items it is the published extent rounded, and it passes.
- **Published collection (live, read 2026-10-14).**
  - Non-item links are root, self and related, from unchanged `catalogue_build.py` code.
  - `stac_extensions` is `[lidarbc, version]`, and with `VERSION_EXT` removed it equals the build's `[lidarbc]`.
  - `version` is "0.3.0" and is free. Description, keywords, providers, summaries, title and license all come from code unchanged since v0.3.0.
  - Nothing there fails spuriously.
- **Bucket root.**
  - Measured with an authenticated `aws s3 ls`: the root holds only `collection.json`, the item JSONs and `build-cache/`. There is no `queryables.json` or other stray `.json`.
  - So `items_load` on the sync, with `--exclude 'build-cache/*'`, sees exactly the items.
- **The rest of the item.** Since v0.3.0 the only change under `scripts/` is the 7-line rounding in `laz_item.py`, so "everything else equal" matches what the build will produce.
- **code-check-python.md.**
  - No stdlib-shadowing name.
  - The tests make no network access (they use local fixtures).
  - The conftest guard is unaffected.
  - The mkdocs rule does not apply.

## Scratch

- Emulation script: `/private/tmp/claude-501/-Users-airvine-Projects-repo-stac-pointcloud-bc/a0167601-a578-4737-8609-55e8143028ee/scratchpad/cr1/emulate.py`, 14 min.
- Mutations were made in the scratch copy only. The repo was not touched beyond this file.
