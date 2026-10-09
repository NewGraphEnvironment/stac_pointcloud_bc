# Task: Check whether NRCan CanElevation republishes these LidarBC projects (#6)

**If we do it:** we know whether part of this collection duplicates the national point cloud series, and can link to it or drop the overlap. **If we never do:** a user may find the same flights twice, in two catalogues, with no note that they are the same.

Measured in `research/canelevation_overlap.md` (443b88d). Decided 2026-10-09: **A, link** —
add the CanElevation COPC as a second asset on each matching item and name the overlap
in the collection description. 1,964 of the 9,649 v0.1.0 items have a copy.

## Shape of the change (from the code)

- `scripts/laz_item.py` stays stactools-shaped. Add a **pure**
  `copc_asset_add(item, href, copc_header)` that adds asset `copc` (media type
  `application/vnd.laszip+copc`, role `data`, `file:size`, title naming CanElevation)
  and **raises unless the COPC header has the item's point count and a box within 1 m**
  of its `proj:bbox`. A name match is the proxy; the header is the property.
- Move the CanElevation lister out of `scripts/canelevation_overlap_probe.py` (`ce_list`)
  into `laz_item.py` beside `keys_list` as `canelevation_keys_list()`, returning
  `{"url","etag","size"}` like `keys_list`, so the probe and the build share one copy.
- `scripts/catalogue_build.py`: a `CANELEVATION` dict of the four project prefixes with
  their measured `.laz` counts (7,873 / 3,866 / 682 / 1,714), refused under 90% as
  `INCREMENT` is. Name-match by stem (`.copc`/`.laz` stripped); a stem matching more
  than one file on either side fails the build. Read the matched COPC headers through
  the existing `headers_fetch()` with its own cache (`copc_headers.jsonl`, ETag-keyed),
  any read error fails the build, then `copc_asset_add()` per pair. Collection:
  `DESCRIPTION` names the overlap and the four projects; NRCan added to `PROVIDERS`
  with role `host`.
- `stacs.toml` unchanged (`require = "laz"` still holds; stacs has no href-host rule).

## Decisions taken at this gate (recommended defaults; say if any is wrong)
1. **Asset, not `alternate` link**, key `copc`. It is stored item shape.
2. **Every pair verified by header at build** (1,964 COPC header reads, cached), not
   trusted on the 40-pair sample. A mismatch fails the build rather than dropping the asset.
3. **Publish and register v0.2.0 on this branch**, as #1 did for v0.1.0.

## Phase 1: Item function and lister (tests first)
- [ ] Tests: `copc_asset_add` adds a `copc` asset that validates, with media type, `file:size` and the LidarBC `laz` asset untouched
- [ ] Tests: a COPC header with another point count, or a box off by > 1 m, raises
- [ ] Tests: `canelevation_keys_list` pages by continuation token, raises on non-200 and on truncated-without-token, carries ETag and size
- [ ] `laz_item.py`: `MEDIA_TYPE_COPC`, `ASSET_COPC = "copc"`, `CANELEVATION` base URL, `canelevation_keys_list()`, `copc_asset_add()`
- [ ] `canelevation_overlap_probe.py` imports the lister instead of its own `ce_list`
- [ ] Each new guard shown red with the guard removed

## Phase 2: Build wiring
- [ ] Tests: a CanElevation project listed short is refused; a stem matching two files fails the build; a COPC header read error fails the build
- [ ] `catalogue_build.py`: `CANELEVATION` projects + counts, `copc_pairs()`, COPC header fetch via `headers_fetch()`, assets added before validation
- [ ] `DESCRIPTION` names the overlap; NRCan in `PROVIDERS`; test that the collection still validates
- [ ] `--limit` build to `data/build-limit/` on a `092g/2016` slice: inspect one item's `copc` asset and HEAD its href (200)

## Phase 3: Build, publish, register v0.2.0
- [ ] Full build: 9,649 items, 1,964 with a `copc` asset, per-group counts match the research (1,155 / 420 / 332 / 57); log under `logs/`
- [ ] `collection_version.py --version 0.2.0`; `s3_sync.sh --dryrun` then sync
- [ ] `stacs verify` (expect 9,649 ids both ways, 1,964 + collection changed), `stacs register --mode drift` from the tailnet machine, `stacs verify` again: IN SYNC
- [ ] An item served by the API has a `copc` href that answers 200 on HEAD

## Phase 4: Close-out
- [ ] NEWS `0.2.0` entry (numbers derived from the build, not the issue); README "What is indexed" notes the COPC asset
- [ ] `research/canelevation_overlap.md`: section on what was done with the finding (decision A, v0.2.0); CLAUDE.md source-facts bullet
- [ ] Issue #6 body: mark the decision built, link the release

## Validation

- [ ] Tests pass (`uv run pytest tests/ -q`)
- [ ] `/code-check` clean (once over the branch with `/code-check branch`; covers 443b88d's probe too)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion, then `/gh-pr-push`
