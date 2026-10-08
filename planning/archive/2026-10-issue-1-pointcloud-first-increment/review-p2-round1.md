# Review: Phase 2 staged diff, round 1 (published-metadata correctness)

Reviewer worked in a copy (`$SCRATCH/pcrepo`); nothing in this repo was modified except this file.
Evidence: a real listing of the increment (9,650 URLs, all 11 groups passed the 90% floor), then
`catalogue_build.headers_fetch` over **all 9,650** headers (0 errors, 2m10s at 24 workers), then
`item_create` on every header. Spot point reads (20k–50k points) for GPS time.

## Findings

- **[bug]** scripts/laz_item.py:149-154 (and catalogue_build.py:216-218) — **one real file publishes a
  footprint from the equator to 49°N, and drags the collection extent with it.**
  `092/092h/2016/pointcloud/bc_092h003_2_3_1_xyes_7_utm10_20160913.laz` has header
  `mins = [0.0, 0.0, 0.0]`, `maxs = [611484.67, 5432744.76, 1847.61]` (84,489,826 points, so not an empty
  file — the header min is simply wrong). `item_create` gives bbox
  `[-129.817, -4.8e-08, -121.475, 49.0375]`, and `collection_build` takes the min over items, so the
  published collection spatial extent becomes ~`[-129.8, 0.0, …]`. Nothing guards it: there is no
  plausibility check on the header box (no "inside BC", no tile-size bound, no `mins != 0`). Every other
  file passed an independent check (bbox centroid inside its BCGS 1:20k sheet from the filename, width
  < 0.06°, height < 0.03°): exactly 1 of 9,650 failed, this one. Needs a guard that refuses (or
  routes to a fallback footprint) a box outside BC / larger than a tile, with a test using these real
  numbers.

- **[bug]** scripts/laz_item.py:108 and :122-128 — **every item's `pc:schemas` publishes the bit-field
  dimensions with `size: 0` and `type: "signed"`.** laspy 2.7.0 reports bit fields with
  `num_bits` 1–5 and `kind = BitField`; `num_bits // 8` is 0, and `_schema_type("BitField")` falls through
  to `SIGNED`. Measured over all 9,650 headers: format 1 (6,363 items) has 8 zero-size fields
  **including `classification`** (5 bits in format 1); formats 6/7 (3,287 items) have 9 (return_number,
  number_of_returns, scanner_channel, flags…). The extension schema only requires `size` to be an
  integer, so `validate()` passes, but the values are wrong (a byte size of 0; flags typed signed) and
  the schema list no longer sums to the record length. The test fixture cannot reach this:
  tests/test_laz_item.py:111-112 hand-writes `("classification", 1, "UnsignedInteger")`, which
  `header_read` never produces for format 1 (it produces `("classification", 0, "BitField")`). Map
  BitField to unsigned and a whole byte (PDAL's convention: uint8, size 1), and build the fixture from
  `laspy.PointFormat(1).dimensions` rather than by hand.

- **[bug]** scripts/laz_item.py:147, :183-186 — **1,678 items whose horizontal CRS is EPSG:2955 publish
  `proj:code: null` and a BOUNDCRS WKT2 instead.** CRS distribution over all headers:
  3,525 Projected EPSG:2955; 2,908 Projected EPSG:3157; 1,342 Compound → EPSG:2955;
  **1,678 Compound whose `sub_crs_list[0]` is a `BoundCRS`** (`SOURCECRS` = PROJCRS … `ID["EPSG",2955]`,
  `TARGETCRS` WGS 84, `ABRIDGEDTRANSFORMATION` TOWGS84) — groups 082f/2018, 082g/2018, 082j/2018 and the
  format-6 part of 082e/2018; 197 Projected Esri-style "UTM_Zone_11_Northern_Hemisphere" (082k/2017,
  unidentifiable by pyproj even at `min_confidence=1`, so `wkt2` there is acceptable).
  `BoundCRS.to_epsg()` is `None`, so the code falls to `wkt2=horiz.to_wkt()` and writes the whole
  BOUNDCRS (WGS84 target + Helmert params) as the item's CRS. Same CRS, two different published forms
  across adjacent tiles; anything filtering or grouping on `proj:code` loses those 1,678. Fix: unwrap
  `if horiz.is_bound: horiz = horiz.source_crs` before both the transformer and `to_epsg()`. (The
  footprint itself is fine: BoundCRS vs plain 2955 differ by 1.26 m at a corner.) The test fixture
  `EPSG:2955+6647` (tests/test_laz_item.py:141) builds a compound with no BoundCRS, so it cannot reach
  the real shape — take the WKT from a real header (e.g. `bc_082f021_3_3_2_xyes_12_utm11_2018.laz`).

- **[bug]** scripts/laz_item.py:35-37, :81-98 — **the filename date is not reliably the acquisition date,
  and 266 items are published a year late.** Directory year vs parsed year over all 9,650:
  `082k/2017` → 266 files `_180827` (published `datetime` 2018-08-27) + 1 `_171015`. Adjusted-standard
  GPS time in the points (global encoding = 1) puts those 266 in **October 2017** — 5 sampled
  `_180827` files: 2017-10-09 … 2017-10-27; the `_171015` file: 2017-10-06. So the directory year is
  right and the filename `datetime` is ~10 months wrong, in the wrong year, and published as a precise
  instant with `nge:datetime_source: filename`. Also suspect: 2,008 items in `092g/2016`, `092h/2016`,
  `092j/2016` parse to **2017** (`20170601`, `20170713`, `20170714`); for `20170601` and `20170713` the
  filename date equals the LAS header creation date **exactly** (2017-06-01, 2017-07-13), which is what
  a processing/export date looks like, whereas every 2016 token precedes its creation date as a flight
  date would. Those files use GPS week time (encoding 0), so the year cannot be read from the points;
  unproven either way, but the same mechanism as 082k. At minimum: when the filename year disagrees
  with the directory year, do not publish the filename instant (fall back to the directory-year range,
  or widen to cover both), and record the 082k finding in research/. The `_DATE` comment "is the
  acquisition date" is a claim the data contradicts.

## Checked and found correct (no finding)

- **href_encode / asset hrefs**: HEAD on
  `…/082l/2018/pointcloud/bc_082l024_2_4_3_xyes_12_utm11_2018%20(2).laz` → 200, and the `%28`/`%29` form
  → 200 too. Listing keys arrive decoded from the XML, `header_read` and `item_create` each encode the
  raw URL exactly once, so the docstring ("not idempotent; pass the raw URL once") is accurate. Only 15
  of 9,650 names have any character outside `[a-z0-9_./-]` — all ` (2).laz`.
- **Item ids / item-link hrefs vs stacs**: `_href_to_id` decodes only `%20`; `item_link_href` encodes only
  the space and the item file is written as `<id>.json` with the literal space, so an `aws s3 sync` key,
  the link href and the decoded id agree. 0 duplicate ids over the 9,650.
- **date_parse regex on real names**: tokens are 4-digit (6,475), 8-digit (2,901), 6-digit (267:
  `171015`, `180827` only), none (7: `_2016721`, falls back to path with `source: path` — correct and
  labelled). No 4-digit token outside 1990-2030. `%y` century is right for these. Year-range end
  `12-31T23:59:59Z` is fine.
- **Geometry otherwise**: the 4-corner transform is adequate at 2 km (edge curvature well under 1 m);
  every file except the one above lands inside its own 1:20k sheet, so CRS and axis order are right
  for all three CRS shapes. `proj:bbox` is the 2D native box in the same CRS as `proj:code`/`proj:wkt2`.
  0 files with `point_count == 0`, 0 with any `min > max`. (971 files have z mins below -100 m — noise
  points; does not affect the 2D footprint.)

## Observations (not code defects, but they touch what gets published)

- research/laz_header_read.md says "`pointcloud/` files are format 1, with no colour". Over the full
  increment, 3,275 `pointcloud/` files are format 6 and **12 are format 7 (RGB)**; only 6,363 are format 1.
  The research verdict that point format is what distinguishes `dsm/` from `pointcloud/` needs revising.
- The 15 ` (2).laz` files each coexist with the un-suffixed original of the same tile, and they are not
  copies: e.g. `bc_082l024_2_4_3…2018.laz` 73,414,950 pts / 1,548 m wide vs the ` (2)` 83,548,760 pts /
  1,824 m wide. The build publishes both as separate items over the same tile; whether that is intended
  is a decision, not a bug.
