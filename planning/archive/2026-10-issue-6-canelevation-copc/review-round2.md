# Code-check round 2: branch `6-canelevation-overlap` (#6)

Reviewer: subagent, 2026-10-09. I read these in full: scripts/laz_item.py,
scripts/catalogue_build.py, scripts/canelevation_overlap_probe.py, tests/test_laz_item.py
(the branch diff), research/canelevation_overlap.md, .gitignore, scripts/s3_sync.sh,
stacs.toml, and the uncommitted NEWS.md, README.md and CLAUDE.md drafts. Test suite: 95
passed. I checked the claims against data/build/ (read only) and against the live published
v0.1.0 items.

## Findings

- **[severity: fragile / published text, minor]** scripts/laz_item.py:334-337 (the `copc`
  asset `description`), repeated in the README.md draft ("same point count, horizontal CRS
  and extent"). The round-1 fix is correct for the CRS. It leaves the same kind of overclaim
  on the **extent**. The code accepts a box within `COPC_BOX_TOLERANCE_M` (0.05 m), and in the
  real build the boxes are not the same in most pairs. Re-derived from headers.jsonl and
  copc_headers.jsonl:

  | project | box identical | box differs by 0 < off ≤ 0.01 m |
  |---|---:|---:|
  | Lower_Mainland_2016 | 86 | 1,489 |
  | Riverine_Floodplain_UTM11_2019 | 285 | 104 |

  So 1,593 of the 1,964 item bodies would say "the same ... extent" for a box that differs by
  up to 1 cm. That also means the copy's coordinates were re-quantised. It is the same points,
  but not bit-identical XYZ. The consequence is far smaller than round 1's: a centimetre
  against a categorical CRS difference. But it is the same rule ("the asset claims what was
  checked and no more", in the function's own docstring), and it goes into 1,964 published
  bodies that stacs digests. If it is to change, change it before the v0.2.0 publish. One
  wording that matches the check: "the same point count and horizontal CRS, and an extent
  within 5 cm". The NEWS.md draft already states this precisely ("a box within 0.05 m"), and
  so does the CLAUDE.md draft.

- **[severity: published text, minor]** scripts/catalogue_build.py:100-102 (collection
  `DESCRIPTION`): "CanElevation series republishes four LidarBC projects as COPC under the
  same file names". `Lower_Mainland_2016` has 1,714 files, and only 1,575 of them carry a
  LidarBC file name. The other 139 have a `_2018` name, and LidarBC does not serve them
  (research/canelevation_overlap.md, "Same tile under another name is not the same points").
  So "republishes four projects under the same file names" claims the whole of each project.
  Also, the four names are CanElevation's project names, not LidarBC's. A wording that holds:
  "republishes LidarBC files, under the same file names, in four of its projects (...)".

- **[severity: fragile]** scripts/catalogue_build.py:352 (`pairs = copc_pairs(...)`) and the
  comment at :67-70. The comment says dropped assets must stop the build ("Dropping the assets
  instead would publish a catalogue that reads complete, so a moved or shrunk project stops
  the build"). Only the listing count is guarded, never the number of pairs. If CanElevation
  renames files in place (same count, new names), or LidarBC renames its side, every pair
  disappears. `copc_pairs` returns `{}` and the build exits 0. The next publish then drops up
  to 1,964 `copc` assets from a catalogue that still reads complete. That is the outcome the
  comment says is prevented. The same applies, partially, to a shrinkage under 10%. This does
  not affect the v0.2.0 build, which paired all 1,964. It is a guard that fails toward pass
  on future builds. A floor on `len(pairs)` (scaled or skipped under `--limit`), or a
  comparison against the previous build's copc set, would make it loud.

## Checked and found sound

- Round-1 fix (b810750): the text now says "horizontal CRS", which matches the
  `_horizontal()` + EPSG/`equals` comparison. Horizontal EPSG is equal in every real pair
  (3157 for 1,575, 2955 for 389).
- Every number in the NEWS.md draft, re-derived from data/build:
  - 1,964 items with `copc`.
  - Group counts: 092g/2016 1,155, 092h/2016 420, 082e/2019 332, 082l/2019 57.
  - Largest box offset 0.00999 m.
  - Lower_Mainland_2016: 1,575 copies, LAS 1.2/fmt 1 -> 1.4/fmt 6.
  - Riverine UTM11: 389 copies, 1.4/6 -> 1.4/6.
  - `file:size` equals the copy's header-read size in all 1,964.
  - No copc href needs percent-encoding.
- "Nothing else in any item changed": I fetched 25 live v0.1.0 item bodies from
  `stac-pointcloud-bc.s3.us-west-2.amazonaws.com` (15 with a copc asset in the build, 10
  random). All 25 equal the build body with the `copc` asset removed. `item_create` is
  untouched by the branch.
- `copc_asset_add`:
  - It raises before mutating the item.
  - A missing COPC CRS fails.
  - A NaN box fails (`not off < tol`).
  - A second `copc` is refused.
  - A pyproj `CRSError` from garbage WKT is not a `ValueError`, but it still aborts before
    the staged swap (fails loud).
- `copc_pairs`:
  - Duplicate names on either side raise.
  - `(2)` copies cannot pair.
  - It pairs over `kept`, so an EXCLUDE file gets no asset.
- `canelevation_keys_list`: a non-200 raises, and a truncated page with no token raises.
- The probe's header errors are counted, never silently read as matches.
- s3_sync.sh's set-equality check and the stacs `require = "laz"` are unaffected by the
  extra asset.

## Notes (not findings)

- **data/build/ must be rebuilt before `scripts/s3_sync.sh`.** The items on disk carry the
  pre-fix description ("same point count, CRS and extent"). s3_sync.sh uploads data/build
  verbatim and has no check that the build matches the current code. Publishing the tree as
  it stands would ship the overclaim round 1 removed into 1,964 bodies. A rebuild also
  re-lists both buckets. So the "no item added or removed" sentence in NEWS should be
  confirmed against the rebuilt set, as NEWS says it was, not against this one.
- The collection `license` (CC-BY-4.0) versus the copc asset's OGL-Canada was noted in
  round 1 and is out of scope here.
