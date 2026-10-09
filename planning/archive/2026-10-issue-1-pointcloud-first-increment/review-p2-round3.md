# Review: Phase 2 staged diff, round 3 (defects inside the round-1/2 fixes)

I worked in a copy (`$SCRATCH/pc3`, `cp -r`). Nothing in this repo was modified except this file.
`uv run pytest -q` in the copy: **54 passed**.

Evidence: a fresh live listing (9,650 URLs, all 11 groups pass the 90% floor), then all **9,650 headers read**
(0 errors, 1 range request each, 1m35s at 24 workers), with extra fields recorded (creation date, global
encoding, extra-bytes dims, VLRs, EVLRs). Every record then went through `item_create` and `date_parse`.
For dates, GPS time was read from point chunks. Finally `catalogue_build.py` ran end to end in the copy
from that warm cache.

## The mechanism behind round 1's four bugs

**A value was trusted to mean what its name says, and the check was built from the same belief that
wrote the code.** `mins` was taken as the data extent, `num_bits // 8` as the byte size, `to_epsg()` as
the CRS's code and the filename token as the acquisition date. Each fixture was hand-built from the
author's model of the data, so it agreed with the code. `pystac.validate()` checks form, never truth.
The only check that found any of the four was a run over the whole population.

The fixes repeat that shape: each new guard encodes a belief about the data that the population was
never asked about. Where it reaches now:

## Findings

- **[severity: bug — blocks the build]** scripts/laz_item.py:40-42, :192-195 (`TILE_SIDE_M = (100, 20_000)`)
  — **104 real files have a header box with a side under 100 m. `item_create` raises on the first one,
  so the full build cannot complete.** I ran `catalogue_build.py` end to end in the copy. It died at
  `bc_082e020_4_3_2_xyes_12_utm11_2018.laz` ("sides 18 x 879 m"), and nothing was written.
  Over all 9,650: `item_create` refuses **105**, which is the EXCLUDEd file plus 104 real edge or partial
  tiles. Of those, 38 are under 100 m on both axes. The smallest are 1.4 x 0.8 m with 14 points
  (`092g068_4_2_1…20160725`) and 6.1 x 4.6 m with 196 points (`092h016_3_3_4`). They are spread across
  every group: 082e/2018, 082e/2019, 082f, 082k, 082l/2019 (31 files), 092g, 092h and 092j. All are
  inside BC and none has a zero coordinate. Their header box is simply small, because the delivery's
  coverage ends inside the tile.
  The comment on line 40-41 says "every file in the first increment but one" fits. That was never
  measured. Round 1's check was upper bounds only (width < 0.06°, height < 0.03°). The test at
  tests/test_laz_item.py:198 asserts that a 1 cm-wide box is *refused*, which writes the wrong belief
  into the contract.
  The guard also aborts on the **first** fault, so it would take ~104 fix-and-rerun cycles to see them
  all.
  Fix: drop the lower bound (require `> 0`) and keep the upper one. If a positional guard is wanted, use
  the property round 1 actually checked, the next finding.

- **[severity: fragile]** scripts/laz_item.py:37-39, :201-203 (`BC_BBOX`) — **BC_BBOX stands in for
  "the footprint is where this file is", and it passes the commonest header fault for this data, a
  wrong UTM zone.** Reproduced: the real 082e003 box (UTM 11 coordinates) labelled EPSG:3157 (UTM 10)
  is accepted, with bbox `[-125.55, 49.02, -125.52, 49.04]`. That is 6° west of the right place
  (`-119.55`) and still well inside BC.
  The research note claims "a new fault fails the build rather than publishing" a wrong footprint. That
  holds only for faults big enough to leave the province. This data has three CRS encodings, a BoundCRS
  wrapper and an Esri WKT with no code, so a mislabelled zone is plausible.
  The discriminating check is the one round 1 ran: the footprint centroid must fall inside the BCGS
  1:20k sheet in the filename (`bc_082e003_…`). All 9,650 but the EXCLUDEd file passed it. It needs no
  size bounds, so it also replaces the broken lower bound above.
  BC_BBOX itself is right for BC: the extent over all items is lon -123.32 to -115.60, lat 48.9994 to
  51.0006, comfortably inside it, and the east edge of -114.0 clears BC's easternmost point (~-114.05).

- **[severity: bug, 1 item]** scripts/laz_item.py:113-115 (`date_parse`, year-agrees branch) —
  **"the year agrees" stands in for "this token is an acquisition date". In 082k/2017 it publishes a
  precise day the data contradicts.** 266 of the 267 082k files are named `_180827`, which round 1
  showed is not an acquisition date. The remaining file, `bc_082k016_3_3_3_xyes_8_utm11_171015.laz`,
  matches the directory year, so it publishes `datetime: 2017-10-15`, `nge:datetime_source: filename`.
  Its points, sampled at six positions through the file (seek to 0/20/40/60/80/99.9%, adjusted-standard
  GPS time, global encoding 1), fall on **2017-10-06 and 2017-11-06** and never on 10-15.
  So one delivery's naming is known to be wrong, and the rule still trusts one token from that same
  delivery. Whether a token is a date is a property of the delivery, not of each token.
  At minimum, this group should publish the 2017 range. Better: list which groups' tokens are trusted,
  rather than inferring it per file.
  The other day-published items are 306 in 092g/2016 and 587 in 092h/2016. Every one of their tokens
  precedes the header creation date, which is consistent with a flight date. I found no counter-evidence
  there, but they use GPS week time and cannot be checked from the points.

  The other branches are correct:
  - 8-digit and 6-digit tokens whose year agrees publish a day.
  - A token whose year disagrees publishes the directory-year range with `source: path`.
  - A 4-digit token that agrees publishes the range with `source: filename`, which is the same interval
    as the path.
  - A 4-digit token that disagrees publishes the range of the **directory** year, with `source: path`
    and the token kept in `nge:filename_date`. None of these occur in the data.
  - No token gives the range with `source: path` and `filename_date: None`.
  - The end, `12-31T23:59:59Z`, is inclusive and correct.
  - An invalid 8- or 6-digit date (e.g. `20161315`) raises `ValueError` and fails the build loudly.
    None occur.

- **[severity: fragile]** scripts/catalogue_build.py:57-64, :225-228 (`EXCLUDE`) — **the exclusion is
  keyed by URL alone, so a corrected re-delivery is dropped silently, forever.** The cache is ETag-gated,
  so a fixed file at the same key is re-read and its correct header lands in `headers`. Then
  `u not in EXCLUDE` discards it, with only a log warning that repeats the stale reason.
  This is the same blind spot round 2 fixed for the cache (URL without ETag), one structure over.
  Two ways to fix it:
  - key the entry on `(url, etag)` and fail the build when the ETag no longer matches;
  - or keep the URL key and assert the recorded fault still holds (`mins == [0, 0, 0]`), failing if it
    does not.
  Related: the excluded file's header is still fetched every run, so if that file starts returning
  403/404, the build fails over a file it was going to drop anyway.

- **[severity: fragile]** scripts/catalogue_build.py:205-212, :240-257 (`--limit`) — **a `--limit`
  development run swaps a partial build into `data/build/`, and nothing marks it partial.** That is the
  state on disk now: `data/build/collection.json` links **40** items, with a spatial extent of a 0.2° box
  and a 2018-only temporal extent. When the full build then fails (the first finding), this partial build
  stays in place and looks like a build.
  Phase 3 syncs `data/build/` to S3. The module's own rule is that a collection published without a file
  "would read as complete". `--limit` produces exactly that, through the same swap.
  Fix: write a limited build to a different directory (e.g. `data/build-limit/`), or refuse to swap
  without `--full`.

## Checked and found correct

- **`_horizontal` / Esri WKT (197 files, 082k):** `PROJCRS["UTM_Zone_11_Northern_Hemisphere"]` on
  `D_NORTH_AMERICAN_1983_CSRS` / GRS 1980, metres. It transforms with a ballpark NAD83(CSRS) to WGS84
  step, and differs from EPSG:2955's transform by ~1.6 m at a corner. The footprint is right.
  `proj:code` is null and `proj:wkt2` is the horizontal WKT2, which is correct for a CRS pyproj cannot
  identify.
- **CRS population:** there are exactly 5 distinct WKTs:
  - 3,525 projected 2955
  - 1,342 compound 2955 + vertical
  - 1,678 compound whose horizontal is a BoundCRS with source 2955
  - 197 Esri
  - 2,908 projected 3157

  Every BoundCRS source is the expected 2955. No whole-CRS BoundCRS, and no BoundCRS wrapping a
  compound. All units are metres, so TILE_SIDE_M's metre assumption holds. The UTM zone in every filename
  matches its CRS, apart from the 197 Esri files, which have no code to compare.
- **`_schema`:** laspy's `DimensionKind` has exactly four members (Signed, Unsigned, Floating, BitField),
  and all four are mapped. **No file carries extra-bytes dimensions** (`point_format.extra_dimensions` is
  empty in all 9,650), so the array and scaled extra-bytes paths are not reached. If one were, an array
  dim would publish its total bytes as a single entry, and a scaled one would publish its raw integer
  type. Neither would crash.
- **Cache:** all of the following were tested and probed, and are sound:
  - ETag and `header_version` gating
  - a record with a missing ETag is re-read
  - a race where the file is replaced between listing and reading caches under the old ETag and
    self-heals on the next run
  - `cache_tail_repair`, including a file with no newline, which truncates to empty
  - an appended record lands on a fresh line

  `file:size` from HEAD equals the listing's `Size` for all 9,650.
- **Swap:** a failure anywhere before line 251 leaves the previous build whole; I verified this with
  the build that crashed above. `items.old` is deleted only after a new set is fully staged. Only a
  kill between the two `os.replace` calls (lines 255-256) leaves new items beside the old
  `collection.json`. That window is microseconds, and is noted rather than raised.

## Observations

- **GPS time is not a reliable acquisition clock in every group.** First-chunk GPS dates for all 215
  files of `082g/2018` (global encoding 17, adjusted standard) are:

  | GPS date | files |
  |---|---|
  | 2010-06 | 6 |
  | 2011-09 | 8 |
  | 2015-12 | 9 |
  | 2017-03 | 130 |
  | 2018-07 | 62 |

  The 2011-09 cluster is what week-seconds flagged as adjusted-standard would produce. The rest are
  unexplained.
  So the 082k evidence, which is consistent and in season, holds. But "GPS says" is not a general
  oracle, and should not be cited as one in research/ without a per-group sanity check.
- Header creation dates are also unreliable: 92 files in 082k/2017 report creation in **2013**.
- `pc:schemas` follows two conventions at once. Bit fields are expanded to 1-byte unsigned "as PDAL
  reports it", but X/Y/Z are published as raw `signed` size 4, where PDAL reports `floating` size 8.
  This is not wrong, but the comment's PDAL rationale does not cover the whole list.
