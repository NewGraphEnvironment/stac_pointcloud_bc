# Findings — Index the rest of pointcloud/*.laz (165,667 files) (#2)

## Issue context

**If we do it:** the collection covers every LidarBC point cloud, not just the 11 mapsheet-years of the first increment. **If we never do:** stac-pointcloud-bc stays a partial index of 9,649 of 175,317 files.

The first increment (#1) built the pipeline and checked it against every real header in those 11 groups. Before widening:
- `INCREMENT` in `scripts/catalogue_build.py` becomes a full listing. That is one walk; the per-group 90% floor needs a whole-bucket equivalent.
- At about 0.15 s and 64 KB per header, 165,667 files is about 10 GB of range reads. Validation costs about 0.1 s per item, so the whole build is hours, not minutes.
- `date_parse`'s trust is decided per delivery. Re-check which deliveries mix naming styles.
- The NTS sheet check knows the blocks 082/083/092/093/094/102/103/104. A key in any other block raises.
- **Every item carries a delivery key** (`"<block>/<sheet>/<year>"`, from the `laz` href), and the collection gets a `related` link to stac-elevation-bc. Decided in #5; the key is `lidarbc:delivery` (#12), and must agree with stac-elevation-bc's (NewGraphEnvironment/stac_dem_bc#55). This build is where it lands, so the full re-registration happens once.
- **Point classes (decided in #10, PR #13; merged 2026-10-10 but not published).** The bucket is still v0.2.0. The 73 class lists and the new collection description reach it with this build, in the same re-registration. A file a point sample calls ground-only or groundless is read whole, and its `laz` asset lists every class present with its point count in `classification:classes`. Do not sample every file. In the first increment, a header density check at or below the 5th percentile of the mapsheet-year caught all 58 such files, so the build samples only the low-density tail (about 10% for margin), then reads whole what the sample flags (`research/laz_classes.md`). Two gaps to close here:
  - **The check has to move into the build.** Today `scripts/laz_classes_probe.py` runs separately, and `CLASSES_READ` pins per-group counts, which will not scale to every group.
  - **The 5th-percentile rate is measured only on the first increment.** Those mapsheet-years are the ones with no raster DSM, not a random sample, so re-measure it before relying on it.

- **Field names (#12, merged before this build).** Items carry `lidarbc:product`, `lidarbc:datetime_source`, `lidarbc:filename_date`, `las:version` and `las:point_format`, where 0.2.0 has `nge:`. This build is the first to publish them, so:
  - **Blocked on NewGraphEnvironment/crate#23**: the `lidarbc` and `las` JSON Schemas at a stable URL, listed in every item's `stac_extensions`. Do not publish a build without them; nothing in the build refuses one yet.
  - **NEWS names each old → new pair**, because a saved filter on an `nge:` name stops matching.
  - **The published-vs-build check has to map the names.** `scripts/copc_pairs_measure.py --published` compares bodies; against 0.2.0 every item now differs. Map the published `nge:` keys to their new names before comparing, so the proof is still "these changes and nothing else".

## Plan-mode exploration (2026-10-10)

### Context

stac-pointcloud-bc publishes 9,649 of the 175,317 `pointcloud/*.laz` files: the 11
mapsheet-years of #1. This build indexes all of them. It is also the one full
re-registration where three changes that are merged but not yet published land together:
- the class lists (#10),
- the renamed fields (#12),
- the `lidarbc:delivery` key with a `related` link to stac-elevation-bc (#5, stac_dem_bc#55).

**Blocker cleared:** crate#23's schemas answer 200, after a 301 that pystac follows:
- `https://newgraphenvironment.github.io/crate/stac/lidarbc/v1.0.0/schema.json`
- `https://newgraphenvironment.github.io/crate/stac/las/v1.0.0/schema.json`

**Decided at this gate:**
- The density screen is checked on a random 5% of the files it does not pick.
- The publish runs on this branch, but only after your explicit go.

**What exploration found:**
- `catalogue_build.py` is built around three per-group pins:
  - `INCREMENT`, the listing floor per mapsheet-year;
  - `COPC_PAIRS`, the number of COPC pairs per group;
  - `CLASSES_READ`, the number of whole-file class reads per group.
- The class check lives in a separate script (`laz_classes_probe.py`), and the build only
  consumes its cache.
- `groups_with_untrusted_dates` already works per delivery over whatever URLs it is given, so
  it scales as it is. What it decides still needs re-measuring and recording.
- stac_dem_bc's `urls_list.txt` shows only blocks 082, 083, 092, 093, 094, 102, 103 and 104.
  Those are exactly `NTS_BLOCKS`, so the sheet check should hold. Phase 1 confirms it on the
  `.laz` listing itself.
- ~~`data/build` no longer holds `headers.jsonl`~~ — wrong (plan review A1): it holds 9,650 at
  `HEADER_VERSION` 2, so about 165.6k headers remain to read.
- Validation at about 0.1 s per item is about 5 h if run serially. It needs a process pool.
- `copc_pairs_measure.py --published` assumes that the only difference is the `copc` asset.
  That no longer holds.
- Collection queryables wait on stacs#8, and are out of scope here.

Branch: `2-index-the-rest-of-pointcloud-laz-165-667`

### Verification end to end

- `uv run pytest`, including the pinned key-path sets and the mutation proofs for each new
  guard.
- The full build exits 0, and its log shows:
  - the per-group listing,
  - the COPC pairs,
  - the screened, sampled and read-whole counts.
- `copc_pairs_measure.py --published` shows no difference beyond the expected ones.
- `stacs verify` reports IN SYNC after the publish.
- A filter on `lidarbc:delivery` returns items from both collections, once stac_dem_bc#55 has
  published. Otherwise this is noted as pending in #5.

## Whole-bucket walk (2026-10-10 23:35Z, scratchpad walk of the 8 block prefixes)

- The root's directories: the 8 NTS blocks (082 083 092 093 094 102 103 104), plus `albers10k2m`,
  `index`, `intensity_plots`, `metadata`, `monthly_bulletin`, `temp`, `test`, `transfer_summary`.
  `blocks_list` keeps the three-digit ones and refuses one `NTS_BLOCKS` lacks.
- 409,449 keys under the blocks; 181,669 `.laz` (2026-10-06: 181,708); **175,278 under
  `pointcloud/`** (2026-10-06: 175,317, so 39 fewer). The 11 first-increment groups are unchanged
  (9,650 in all, each equal to its `INCREMENT` count). Where the 39 went was not measured: the
  2026-10-06 walk kept no per-group record. From now on `data/pointcloud_groups.json` is that record.
- Every `.laz` parses: no key off the pattern, no product directory but `pointcloud`/`dsm`, no
  sheet letter outside A–P, no file name outside `[A-Za-z0-9_.() -]`, no duplicate id.
- **233 mapsheet-years**, from 2012 to 2026. Smallest: `094/094o/2026` 1 file; `092/092i/2017`,
  `093/093c/2019`, `103/103j/2021` 2 each.
- 145 file names carry a ` (2)` copy marker (the increment's handling already covers them).

### Dates (issue: "re-check which deliveries mix naming styles")

- **42 deliveries are untrusted** (some filename date's year disagrees with the directory), up
  from the increment's 4 (`082k/2017`, `092g/092h/092j 2016`, all still there). Most of the new
  ones are 2023/2024 directories.
- Token length per delivery: 125 deliveries name only `yyyy`, 94 only `yyyymmdd`, 3 only
  `yymmdd`; **11 mix styles**: `082f/2017` (6-digit 1,709, 4-digit 1,063); seven 2019/2021
  deliveries mixing `yyyy` with no token (`092b`, `092c`, `092f`, `092g`, `092k`, `092l` 2019,
  `092i/2021`); `092h/2016` and `093c/2023` (8-digit plus a few with none, both untrusted anyway);
  `092p/2017` (8-digit 208, none 127).
- Decision (mechanism, not a stored-data fork): a trusted delivery that mixes a day token with no
  token keeps each file's own precision: a day `datetime` where the file names one, the year
  range where it names none. Each item says which in `lidarbc:datetime_source`. Only `092p/2017`
  is in that case.

## A compound CRS written vertical-first (full build, 2026-10-11)

- The first full build read 173,270 new headers and refused on 2,008 (`logs/20261011_0014_catalogue_build_full.log`):
  every one `CRSError: components of the compound CRS do not belong to one of the allowed
  combinations` (PROJ 9.8.1, pyproj 3.8.0, laspy 2.7.0).
- All 2,008 are in seven 2021 deliveries: `082l` 132, `092h` 277, `092i` 156, `092p` 157,
  `093a` 156, `093i` 428, `093p` 702. Their WKT, in an EVLR (`LASF_Projection` 2112, no
  GeoKeys), is `COMPD_CS["CGVD2013 height + NAD83(CSRS) / UTM zone 10N" (1,876) or 11N (132),
  VERT_CS[...], PROJCS[...]]`: the vertical part first, which OGC 01-009 and PROJ refuse.
- Not triaged into `EXCLUDE` (one fault across 2,008 files). Read instead with the two parts
  swapped (`laz_item.compound_reorder`, `header_crs`). The swap changes the order only: each part
  keeps its own definition and EPSG authority (3157 / 2955 horizontal, 6647 vertical). Any other
  parse failure still raises. Logged once per distinct WKT.

## item_create refusals on the full listing (2026-10-11)

`logs/20261011_0250_catalogue_build_full.log`: 995 of 175,277 files refused, in two kinds.

- **985 with no CRS at all**: every file of eight 2017 deliveries (`093e` 37, `103b` 114,
  `103c` 37, `103f` 156, `103g` 33, `103h` 576, `103j` 6, `103k` 26). The only VLR is LASzip; no
  WKT, no GeoKeys (TerraScan, LAS 1.4 format 6). One DEM tile per delivery declares NAD83(CSRS) /
  UTM 9N (`093e`, `103b`, `103c`, `103h`; EPSG:3156) or 8N (`103f`, `103g`, `103j`, `103k`;
  EPSG:3155), matching the `utm0N` in the file names. Not every DEM tile was read.
  **Decided by the user 2026-10-11:** keep them out of 0.3.0; indexing them from the DEM CRS is #15.
  (Was: a stored-data decision, so the user's.) In-branch default,
  reversible before the publish: `EXCLUDE_DELIVERIES`, which refuses if any file there gains a CRS.
  Alternative: take each file's CRS from its delivery's DEM (zone and datum), with the CRS
  source noted in NEWS.
- **10 single-file faults**, each its own `EXCLUDE` entry with its reason: three with 0 points
  or 1 point, two impossible boxes (`082j/2022` from easting 0; `092h/2021` 2,685 km wide), one
  copy of a 093C tile filed under both `092b/2023` and `092n/2023`, a `093n/2021` file whose header
  declares UTM 9N while its name and data are UTM 10N, and a 6 x 130 m sliver at the west edge of
  082M whose centre is 0.86 m outside the sheet.
- The build now logs every refused file, not only three examples per class.

## CanElevation name matches that are not copies (2026-10-11)

`logs/20261011_0436_catalogue_build_full.log`: of 13,996 name matches, **26 fail the header check**,
all in `Vancouver_Island_Sunshine_Coast_2018` (groups `092b/092c/092e/092f/092g/092l/102i` 2019).
Every one has fewer points than the LidarBC file: 37.1M vs 41.2M, down to 8.45M vs 93.1M. 20 of
the 26 COPC counts are multiples of 50,000 (58,550,000; 15,000,000; ...), which looks like conversions
cut short, though that was not measured. Recorded in `data/copc_not_copies.json` with both counts.
Those items carry no `copc` asset and are not sampled through it. The build refuses if either
count changes. So 13,970 items carry a `copc` asset.

## The 5% audit of the density screen (2026-10-11, `logs/20261011_0900_*`, `_1005_*`)

`laz_classes_probe.py --audit 0.05 --seed 2`: a uniform 5% of the 156,730 files the 10th-percentile
screen leaves out, 7,836 files. 7,834 sampled; 2 cannot be read by the sampler at all, every time
(`LazrsError: no chunks available in chunk table`): `082e075_1_4_3` (082e/2024, 166 M points,
1.08 GB) and `094j045_3_3_4` (094j/2024, 95 M points, 0.62 GB). Both LAS 1.4 format 6, about 6.5
bytes a point, so not obviously truncated; not investigated further. 9 flagged; whole reads
confirm **2 misses**:

| file | whole read | density percentile in its mapsheet-year |
|---|---|---|
| `082-082g-2016-..._082g002_2_2_2_xyes_6_utm11_2016` | no ground: class 1 2,394,812, class 7 116 (las2las, 2022-04-26) | 95.9 (n=2,149) |
| `102-102i-2019-..._102i090_2_1_4_xyes_8_utm10_2019` | 29,724 class 7 and 2 class 2: "ground-only" by the definition, in fact a noise tile | 17.7 (n=373) |

The other 7 flags were mixed (5 in `093g/2019`, where the COPC levels or the laz sample showed no
ground in a mostly-vegetation tile). **The first miss breaks the plan's fallback** ("widen the
screen to the smallest percentile that catches them all"): at the 96th percentile, that is
sampling nearly every file, about 20 h and 400 GB at the audit's pace. Point estimate of the miss rate outside the screen:
2 / 7,834 = 0.026% (exact binomial 95% interval about 0.003% to 0.092%), so roughly 38 such files
among the 148,894 neither screened nor audited (5 to 137; corrected from 40 over 156,730 by the
docs fact-check, `review-docs.md`). Put to the user with the PR; the build meanwhile publishes
the screen's lists plus the audit's 9 reads (recorded in `data/classes_required.json`).

## Two-day file names are the first and last day flown (2026-10-11)

The docs fact-check found 10,603 items dated by the second of two day tokens; the date-rule
review (`review-round5.md`) found 9,278 more pairs whose last day is in a later year, which made
33 deliveries (80,337 files) untrusted. GPS times (a 20,000-point read at 0/25/50/75/95% of each
file; scratchpad probes, not committed) settle it:
- 16 in-year pairs from 8 deliveries and 14 cross-year pairs from 8 deliveries: every sampled
  point's day lies between the two tokens; most files show both ends. `093c/2023`
  `_20230921_20251001` holds points from 2023, 2024 and 2025.
- 12 same-day pairs from 6 newly trusted deliveries: every point on the named day.

So the directory year is the year of the first day, and the pair is `start_datetime` /
`end_datetime`. Untrusted deliveries fall from 42 to 9. Items: 64,372 single days, 44,744 ranges
of days, 65,166 years. Not checked: whether the tokens are UTC or Pacific days (the GPS days were
taken in UTC and matched); `end_datetime` is 23:59:59Z of the last day.

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `ConnectionError: RemoteDisconnected` on a CanElevation listing page, after a 9-min walk | `laz_item.page_get`: 4 attempts with backoff on connection errors, timeouts and 5xx |
| `CRSError` on 2,008 headers: compound CRS written vertical-first | Read swapped (`compound_reorder`); see the section above |
| 34 of 12,032 COPC header reads `RemoteDisconnected` on the CanElevation bucket (`logs/20261011_0335_*`) | Transient: re-run, which reads only the uncached 34 (`logs/20261011_0436_*`) |
| 6 of 17,552 screened point samples `RemoteDisconnected` on the LidarBC objectstore after a 3 h 10 min sample pass (`logs/20261011_0525_*`, which is named for a mislabelled start: it ran 05:05Z to 08:55Z) | Transient, and the build refused as designed (`classes_check`): re-run, which samples only the 6 |
