# Code review, round 3: catalogue_compare.py (#22)

Reviewed the staged diff (`scripts/catalogue_compare.py`, `tests/test_catalogue_compare.py`) on
2026-10-13. The probes and mutants ran in `scratchpad/cr3/` (`tests/test_probe_r3.py`, `mut.py`).
The repo's `scripts/catalogue_compare.py` was compared with `cmp` after the sweep and is unchanged.

## The mechanism

The gate checks each artifact **against its published twin** and never checks the build
**against itself**. The published side is now cross-checked: the local copy against the published
collection's links (fix 4). The build side has three artifacts:

- the files in `items/`;
- `collection.json`'s item links;
- `collection.json`'s extent.

The gate assumes these agree because one script writes all three. Two things lean on that
assumption without checking it:

- `new`, a count taken from `items/`, relaxes the check on a different artifact, the collection's
  extent;
- the item-link check (`pi - bi`) is the only place the build's links are read, and it looks in one
  direction only.

Findings 2 to 4 of rounds 1 and 2 came from this. Each check ran over a set it assumed equal to
another set: the local files and the published set; the extent's latitude and longitude edges and
the minx edge. Each time, the inference was one direction or one member wide.

## Where it reaches, checked one by one

| pair the gate assumes agree | checked? | probe result |
|---|---|---|
| published local files vs published collection links | yes (`not_copied`, `unlinked`) | — |
| published hrefs (`pi`) vs published ids (`linked`) | same function of the same href | agree |
| build `items/` files vs build collection links | **no** | A, B: exit 0 |
| `new` (from `items/`) vs build links minus published links | **no** | A: exit 0 |
| build collection extent vs build item bboxes | **no** (only vs published) | C, E: exit 0 with new > 0 |
| new items vs the rounding rule | **no** (only shared items are compared) | F: exit 0 |
| `main`'s `new` vs `collection_diff`'s relaxation | untested | mutant survives |

## Findings

- **[low]** scripts/catalogue_compare.py:188-216 (`main`). The build's `items/` is never checked
  against the build's `collection.json` links.
  - `new` is `built.keys() - linked`, read from `items/`. `collection_diff` reads the build's links
    only through `pi - bi`, and nothing compares `bi` with `built.keys()`.
  - **Probe A.** `items/` holds x and y; the build collection links only x. Result: `new: y`,
    `item links 1 -> 1`, **exit 0**.
  - **Probe B.** `items/` holds x; the build collection links x and w. Result: `item links 1 -> 2`,
    **exit 0**.
  - Neither case can be published, because `s3_sync.sh`'s linked-vs-files check refuses both before
    it uploads anything. So the harm is a wrong acceptance verdict, not data loss.
  - Both are real states. `catalogue_build.py` replaces `items/` before `collection.json` (lines
    961-962), so a failure between those two calls leaves new items beside the old collection.
    That collection can also carry 0.3.0's unrounded extent: the C case below, which then passes
    whenever `items/` holds anything new.
  - **Fix:**
    - in `main`, fail unless `linked_ids(bc) == built.keys()` (the check `s3_sync.sh` makes);
    - then pass `len(linked_ids(bc) - linked)` as `new`, or assert it equals `len(new)`;
    - add a `_tree` test for each direction.

- **[low]** scripts/catalogue_compare.py:155-162 (`collection_diff`, `ext and new` branch). With
  any new item, the extent is checked only for containing the published one. That drops both the
  rounding test and any upper bound.
  - **Probe C.** One new item, and the build collection keeps the published unrounded extent
    (`-124.9999999963`). Result: printed as `extent widened ... carries more than 8 decimals`,
    **exit 0**. Probe C0 is the same with no new item, and it exits 1.
  - **Probe E.** One new item, and the built extent is `[-180, -90, 180, 90]`. Result: **exit 0**.
  - `s3_sync.sh` does not look at the extent, so either would be published.
  - Today this is latent: `collection_build` derives the extent from the rounded item bboxes. It
    becomes the live path as soon as the 0.4.0 build lists any LidarBC file added since 2026-10-10,
    because from then on `new > 0`.
  - **Fix:** the gate already holds every built item. When `new > 0`, require the built spatial
    extent to equal the envelope of the built items' bboxes, and the temporal interval to equal
    their min and max datetimes. Then keep `extent_widened`'s containment check as the check
    against the published extent. That makes the new-item branch exact instead of open-ended.

- **[low]** scripts/catalogue_compare.py:193-199 (`main`). A new item is never checked against the
  release's own rule, that every coordinate carries at most `LONLAT_DECIMALS` decimals.
  - Only `pub & built` goes through `item_expected_diff`.
  - **Probe F.** The build holds a new item y whose footprint is unrounded (the 0.3.0 form). Result:
    `new: y`, **exit 0**.
  - Latent: every item goes through `item_create`.
  - **Fix:** one line. For each id in `new`, run `rounding_diff(b[k], b[k], k)` over `ROUNDED` and
    count anything it returns in `bad`. Comparing a value with itself checks only the decimals.

- **[low]** tests/test_catalogue_compare.py: no `main()` test has a new item or an extent problem.
  - So the mutant `collection_diff(pc, bc, len(new))` → `collection_diff(pc, bc, 1)` **survives**
    all 42 tests. That mutant always relaxes the extent to containment.
  - Equivalently: a `main` that miscounts `new`, as in the first finding, is invisible to the suite.
  - **Fix:** add a `main()` test where the build's extent widens beyond the rounding with no new
    item, asserting exit 1, and one with a new item, asserting exit 0 and the `new:` line.

## Other mutants (decision points outside the earlier sweep)

Killed: the `rel == "item"` filter in `linked_ids` removed; the `ext and new` branch disabled;
`start_ok` forced; a published open end accepted; the dict and list structure branches of
`rounding_diff`; the `bbox` half of `ROUNDED` dropped.

Survived, each harmless:

- `new = built - pub.keys()`. Equivalent, because `not_copied` fails first.
- The `.json` filter in `items_load` removed. A non-JSON file crashes `json.load`, which exits 1.
- `links` not popped. That fails louder, not quieter.
- `b[0] <= p[0]` when the published start is `None`. A TypeError is caught and reported as
  "unreadable".
- `except Exception`.
- Extra exemptions added to the generic key loop (`summaries`, `license`) or to `exts`. These are
  pinned only by the `description` and appended-extension rows. That is a weak pin, but it is not a
  defect in the code.

## Checked and sound

- `pi - bi` (hrefs) and `linked` (ids) agree: the ids are a function of the hrefs, and
  `item_link_href` encodes only the space. A host or format change in the build's hrefs makes
  `pi - bi` non-empty, so it fails.
- A file present in both copies but holding a different body `id` fails, because `id` is in the
  `p != b` comparison.
- Every crash path (missing `bbox`, malformed collection, missing `collection.json`) exits 1.
- code-check-python.md:
  - no script name shadows a stdlib module;
  - the suite passes with `socket.getaddrinfo` and `connect` denied and `NO_PROXY=*` (42 passed), so
    it is offline;
  - there is no root `conftest.py`, but nothing in this diff relies on a session guard;
  - the mkdocs rule does not apply.
