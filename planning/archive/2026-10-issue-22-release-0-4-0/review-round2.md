# Code review, round 2: catalogue_compare.py (#22)

Reviewed the staged diff (`scripts/catalogue_compare.py`, `tests/test_catalogue_compare.py`)
on 2026-10-14 UTC. Probes and mutants ran in a scratch copy; the repo was not touched.

## Findings

- **[medium]** scripts/catalogue_compare.py:155-156 (`main`, `new = sorted(built.keys() - pub.keys())`).
  A published item that is missing from the local copy of the bucket is counted as **new**, so it is
  never compared, and the gate exits 0. "Published" here means the files `aws s3 sync` happened to write,
  not what the published catalogue holds. `collection_diff` checks only that the published item links
  are a subset of the built ones, never that each published link has a local file. Reproduced: published
  collection links x and y, the local copy holds only x.json, the build has x and y. Output:
  `only published 0, new 1 ... new: y`, `collection: item links 2 -> 2`, exit **0**. An interrupted or
  partial sync (Phase 3 step 1 is ~174k objects) therefore passes, with the gaps shown as "new". This
  release expects some genuinely new items (new LidarBC files since 2026-10-10), so a non-zero `new`
  does not stand out. Fix: read the published ids from `pc`'s item links, decoding them the way
  `s3_sync.sh` and stacs do (`href.rsplit("/", 1)[1]`, `%20` -> space, drop `.json`). Fail when a linked
  id has no local file. Compute `new` as the build's ids minus the linked ids. Add a `_tree` test with
  `pub_links=["x", "y"]` and only x on disk.

- **[low]** tests/test_catalogue_compare.py: some mutants of the new code still pass all 30 tests. Each
  one weakens the gate toward accepting:
  - `return 1 if (bad or only_pub or problems)` -> `(bad or only_pub)`. No `main()` test fails on a
    collection problem alone.
  - `end_ok = True` in `extent_widened`. No test makes the built interval end earlier while new > 0.
  - `b[1] <= p[1] + TOLERANCE`, `b[2] >= ...`, `b[3] >= ...` each replaced by `True`. Only the bbox's
    minx shrinking (`[0]`) is tested.
  - the per-element `len(p) != 4 / len(b) != 4` and `len(p) != 2 / len(b) != 2` structure checks
    removed. Only an appended box or interval is tested, not one of a different length.

  The code is correct for each; the tests do not pin it. One parametrized row per edge, plus a `main()`
  test with matching items and a changed collection (e.g. `description`), would cover them.

- **[low]** scripts/catalogue_compare.py:131-138 (`collection_diff`, `ext and new` branch). When new > 0,
  `extent_widened` replaces `rounding_diff` for the whole extent. It reads only `spatial.bbox` and
  `temporal.interval`, so an added or removed key elsewhere in `extent` (or in `spatial`/`temporal`)
  goes into `changes` and does not fail. Probe: built `extent["extra"] = 1` with new=1 gives
  `problems == []`. pystac does not write such keys today, so this is a gap in the gate, not a live
  defect. Fix: compare key sets in `extent_widened`.

## Checked and sound

- The temporal ordering works on these strings. pystac writes whole-second `YYYY-MM-DDTHH:MM:SSZ`
  (published `['2012-01-01T00:00:00Z', '2026-05-06T00:00:00Z']`; the build matches). Every datetime
  `laz_item` makes is whole seconds, so lexicographic order is instant order. Fractional seconds would
  break this, because `.` sorts before `Z`, but no item has them. Open ends (`None`) are handled in both
  directions. A published `None` start against a built value is refused. A non-string value raises a
  TypeError, which is caught and reported as "unreadable".
- The try/except in `collection_diff`. A malformed extent raises KeyError or TypeError, which becomes
  a problem. Anything uncaught kills the process with exit 1. No failure path exits 0.
- `coords()` pairing. Both sides are flattened in the same order (dict keys sorted, lists in order).
  `zip` truncates silently when structures differ, but every such item is already in `bad` through
  `rounding_diff`'s length and key checks. The stats are printed only and gate nothing, so a misaligned
  pair cannot change the exit code.
- Cost over 174k items: about 2.4M coordinate pairs plus one deepcopy per item. Both are linear and
  small next to loading the JSON.
- The version stamp. `version_stamp` adds only `version` and `VERSION_EXT`, and both are exempt, so
  the stamped 0.3.0 collection against the unstamped build passes (tested). The non-item links in
  the published and built collection.json are identical (checked against the live bucket and
  data/build).
- The bucket root holds only item JSON, collection.json and `build-cache/` (`aws s3 ls`), so
  `items_load` sees no stray JSON.
