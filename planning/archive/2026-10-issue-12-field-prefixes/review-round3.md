# Review round 3 (#12), branch 12-rename-the-nge-item-fields-to-a-prefix-t at ef42d0c

Scope: `git diff 46f6b61...HEAD`, focused on ef42d0c (ITEM_PATHS / COLLECTION_PATHS pinned
from two fixture builds). Probed in a copy (`/tmp/spc_r3`); suite there: 149 passed. The repo
was not modified apart from this file.

## The mechanism behind rounds 1 and 2

The guard's scope is a set the author enumerated, and the expected answer is copied from that
same enumeration. In rounds 1 and 2 the author enumerated **places** (properties, then asset
tops, then summaries), so a key written anywhere else passed. ef42d0c moves the enumeration
from places to **inputs**: the pinned sets are the paths of two fixture builds, and the test
asserts that those same two builds still produce them. That closes every *place*. It does not
close the mechanism, because the equality only shows that the fixture builds are unchanged.
A key that main() writes only on a branch neither fixture takes can never reach the
comparison. Both fixture builds run one file, `PC`, with one header (EPSG:3157, token
`20170713` under `/2016/`, so `datetime_source == "path"`). Every branch that depends on the
input file therefore sits outside the guard. The relevant headings are "A fixture that cannot
reach the failure mode" and "Verification that reads its own output".

## Findings

- **[severity: fragile]** tests/test_laz_item.py:988-1066 (`ITEM_PATHS`,
  `test_every_key_the_build_writes_is_pinned`): the pinned set is not "every key the build
  writes" (comment at 988, docstring at 1047: "so every optional key is written by one of
  them"). The real build writes a path that neither fixture produces. I took the local
  `data/build/items` (9,649 items, built 2026-10-10 before the rename), mapped `nge:*` to the
  new names, and compared its path set with ITEM_PATHS:
  - real but not pinned: **`properties.proj:wkt2`**. 197 real items have no EPSG code (a
    UTM 11 WKT), so `item_create` takes its `wkt2=` branch (laz_item.py:280-285).
  - pinned but not real: none. The collection paths match exactly.

  Branches the fixtures never take, each measured by mutation in the copy and restored after:

  | branch the fixtures never take | real items on it | mutation | suite |
  |---|---|---|---|
  | no EPSG (`if not epsg`), laz_item.py:281 | 197 | `item.properties["nge:crs_name"] = horiz.name` | 149 passed (escapes) |
  | `datetime_source == "filename"` | 6,475 | `item.properties["nge:filename_date"] = ...` when `source == "filename"` | 149 passed (escapes) |

  In both rows the mutation writes a literal `nge:` key, which is the exact defect class #12
  exists to remove. It lands on 197 or 6,475 published items, and every test stays green. No
  test calls `item_create` with a trusted filename date. Line 241's
  `PC.replace("/2016/", "/2016/")` is a no-op, so it also yields `path`. Other branches that are
  unexercised but reachable: a `{"datetime": ...}` item (a trusted 6- or 8-digit token, which is
  in no current delivery), a `dsm` product (not in INCREMENT), and a COPC whose CRS has no
  EPSG (`crs[0].equals` branch). Excluded files and refused COPCs or class reads write
  nothing, so they cannot leak.

  The diff is not wrong today. The real build's only unpinned path is the standard
  `proj:wkt2`, and nothing in the current code writes a bad key on these branches. The defect
  is the guard's claimed scope. A fix: give `_main_with_copc` / `_main_with_classes` (or a
  third arm) a second file whose header has no EPSG code (the real UTM11 WKT from the 197
  items) and whose name carries a token that agrees with its directory year, so it is
  `filename`-sourced. Add `properties.proj:wkt2` to ITEM_PATHS. Then restore both mutations
  above and confirm they go red. Where `data/build/items` exists locally, comparing its path
  set with ITEM_PATHS (the probe above) is the check that sees the population rather than the
  fixture. That cache is gitignored, so it can only be an opt-in or skip-if-absent test.

## Other writers and values (reach, not defects)

- `scripts/collection_version.py` adds `version` and a `stac_extensions` entry to
  `data/build/collection.json` at release time. So the published collection carries two paths
  that COLLECTION_PATHS does not hold, and the guard never sees this writer. Both are the
  Version Extension's own fields, unprefixed by its design, so nothing is wrong today. A key
  added there would escape.
- The guard checks keys, not values. Prose values that name fields are not checked: the
  collection DESCRIPTION, which names `classification:classes`, and the asset descriptions. A
  stale `nge:` in one of them would pass. A grep of `scripts/`, `tests/`, `stacs.toml` and
  `README.Rmd` finds `nge:` only in the README's intended sentence about releases up to 0.2.0
  and in the guard's own asserts.
- No reader of the old item keys remains. `readme_functions.R`, `copc_pairs_measure.py` and
  `laz_classes_probe.py` read the header-record keys `las_version`/`point_format`, which are
  unchanged. `classes_add` reads `las:version` from properties (the `laz` value).
