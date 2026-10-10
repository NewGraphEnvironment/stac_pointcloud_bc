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
- `data/build` no longer holds `headers.jsonl`, so every header is read cold. At 16 workers
  that is about 30 min.
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

## Errors Encountered

| Error | Resolution |
|-------|------------|
