# Review: commit 6be1d89 (landing-page revision, #24), round 2

Reviewed 2026-10-13 against `git show 6be1d89:README.Rmd`. Line numbers are that commit's.
Every probe was a read. No repo file was edited. The render ran in a scratch copy made with
`git archive 6be1d89`, using the working tree's caches. The live probes are against
`images.a11s.one` and the LidarBC objectstore, run 2026-10-13 around 13:20 PDT.

## Per-sentence table

| line | sentence | set walked / what was checked | verdict |
|---|---|---|---|
| 115 | "[`stac_pointcloud_bc`](…) is a searchable index of British Columbia's lidar point clouds, served as the `stac-pointcloud-bc` collection." | Scratch render: README.md:9 has the markdown link. index.html has `<a href="https://github.com/NewGraphEnvironment/stac_pointcloud_bc"><code>stac_pointcloud_bc</code></a>`. The collection name matches the API id. Edges: the 996 held-out files, and BC lidar that LidarBC does not publish. The next paragraph names LidarBC, which covers both | TRUE |
| 123 | "LidarBC publishes DEMs for most deliveries" | Round 1: 221 of the 233 pointcloud mapsheet-years have a DEM. Not re-measured | TRUE |
| 123 | "surface models for most tiles but not all" | stac_dem_bc README (fetched today): 95,888 of 102,460 items carry `dsm` | TRUE |
| 123 | "canopy height models for only some deliveries from 2023 and 2024" | Live objectstore walk of `<group>/chm/` for the 48 pointcloud mapsheet-years from 2023–24 (`data/pointcloud_groups.json`). 18 hold CHM tifs, 264 tifs in all, which matches stac_dem_bc#47. Inside those 18, CHM tiles are 264 of 23,293 DEM tiles (1.1%). No single delivery reaches 10%: the highest is `092/092o/2023` at 14 of 172 (8.1%), and `094/094g/2024` has 2 of 2,918 | TRUE as written, still misleading by grain. The clause before it counts surface models by **tile** ("most tiles"), and this one counts CHMs by **delivery**, so "some deliveries" reads as those deliveries being covered. None is more than 8.1% covered |
| 123 | "Each comes at the resolution and by the method LidarBC chose." | The unsupported "specifications differ" clause from round 1 is removed. Nothing left on the page depends on it | TRUE |
| 123 | "…and you can apply one method to every flight, which comparing years needs." | Stated as a necessary condition, the form round 1 asked for. It agrees with line 120 ("a comparison starts by checking that the two can be compared") | TRUE |
| 125 | "A COPC carries a spatial index, so a program can read one area of it over the internet." | `readme_dem.py` (CopcReader over HttpRangeFile). The COPC spec's octree hierarchy | TRUE |
| 125 | "A plain LAZ file has none, so reading one area of it means reading the whole file." | LAZ 1.4's chunk table lets a reader seek by **point index**: one 50,000-point chunk per seek (`laz_classes_probe.py:9,75`). That is how the class sample works. The chunks are in point order, not spatial order, and nothing in the file says which chunks hold an area, so every chunk has to be decoded to find the area's points. That means fetching the whole file. A LAStools `.lax` sidecar would give such an index, but none was found: three live prefix listings (`093c/2023`, `092g/2016`, `093l/2019`) hold only `.laz` and a folder marker. An EVLR-embedded index was not checked (the header cache keeps no VLRs). The one LidarBC file that really is a COPC (`093c058…copc.laz`) is not a "plain LAZ", so it is not a counter-example | TRUE (one edge left unmeasured: an index embedded in an EVLR) |
| 125 | (same sentence, how it reads) | "LAZ" appears here for the first time on the page. Nothing before it says LidarBC's files are LAZ: "Every file is LidarBC's" names no format. So the reader has to work out that "a plain LAZ file" means "the LidarBC file" in the sentence after it | New readability gap, minor |
| 127 | "No point data is copied." | The items hold hrefs and header facts. The page's caches hold derived numbers and figures, not points | TRUE |
| 127 | "The index is rebuilt each month from the province's listing, …" | `update.yml`: cron `17 10 6 * *`. `catalogue_build.py:4` lists every `pointcloud/*.laz` on the objectstore, so the rebuild works from the live listing. `gh run list --workflow update.yml` is empty: it has never run, and the first scheduled run is 2026-11-06. `s3_sync.sh:9` and `s3_publish.py:23`: "Nothing is deleted: an object the build no longer makes is reported and left." | Acceptable as a description of the schedule. The present tense describes how it is set up, and the first run is three weeks away. One edge: "rebuilt" can suggest that a file the province removes drops out of the index. The bucket keeps its item object, and only collection.json loses the link. Note only |
| 127 | "…and the API serves the new records once they are registered." | `update.yml:16-19`: registration is manual, from a tailnet machine. The qualifier from round 1 is now carried | TRUE. But "the API" is used here before the page introduces it: "its API at <https://images.a11s.one>" comes two sentences later. Minor ordering issue |
| 127 | "…a sister collection on the same endpoint, [`stac-elevation-bc`]…" vs the line-294 heading "Sister collections on the same endpoint" | Both now say "endpoint". The heading's list names stac_dem_bc first | TRUE, consistent |
| 189 | "The DEM and DSM items of [stac-elevation-bc](…) carry the same key, and this collection links it as `related`." | Live `/search`: `"lidarbc:delivery" = '092/092g/2016'` returns items carrying the key (`092-092g-2016-dem-bc_092g069413…`). `093/093a/2024` items with `['dem','dsm']` carry it, so DSM-bearing items do. I paged every `stac-elevation-bc` item with `"lidarbc:delivery" IS NULL`: **2,288 items, all `albers10k2m…` mosaics, all `dem`-only**. No item without the key has a `dsm`. The `related` link is live on the pointcloud collection (`https://stac-dem-bc.s3.amazonaws.com/collection.json`) | FALSE at the edge. Every DSM-bearing item carries the key, but 2,288 DEM items do not. The sister README's own sentence keeps the qualifier ("Every item **from a LidarBC delivery** carries `lidarbc:delivery`"), and this one drops it: the mechanism again. Also, "DEM and DSM items" names two kinds of item. There is one kind, which holds a `dem` asset and, on most items, a `dsm` |

## Findings

- **[claim]** README.Rmd:189: "The DEM and DSM items of stac-elevation-bc carry the same key"
  is false for 2,288 items. Paging every `stac-elevation-bc` item with `"lidarbc:delivery" IS NULL`
  on the live API returns 2,288, every one an `albers10k2m…` provincial mosaic with only a `dem`
  asset. Every item with a `dsm` carries the key. stac_dem_bc's README keeps the qualifier ("Every
  item from a LidarBC delivery carries…"), and this sentence drops it. The phrase "DEM and DSM
  items" also implies two item kinds; each item carries a `dem` and usually a `dsm`. Suggested:
  "Every stac-elevation-bc item from a LidarBC delivery tile carries the same key (its
  province-wide mosaics do not), and this collection links it as `related`."
- **[claim]** README.Rmd:123: "canopy height models for only some deliveries from 2023 and 2024"
  is true, 18 of the 48 mapsheet-years from 2023–24, but it changes grain from the clause before
  it. That clause counts surface models by tile; this one counts CHMs by delivery, so it reads as
  those deliveries being covered. They are not. A live walk found 264 CHM tiles against 23,293 DEM
  tiles in the same 18 deliveries (1.1%), and no delivery above 8.1% (`092/092o/2023`, 14 of 172).
  Suggested: "and canopy height models for a few hundred tiles in some deliveries from 2023 and
  2024".
- **[claim, minor]** README.Rmd:125: "A plain LAZ file has none" is the first time the page says
  LAZ, and nothing yet ties it to LidarBC's files. Suggested: "LidarBC's files are plain LAZ
  (a handful excepted), which has no index, so…". Or say "the LidarBC file" in place of "a plain
  LAZ file". The claim itself holds. The chunk table allows seeking by point index, not by area,
  and no `.lax` index was found in the three prefixes listed.
- **[claim, minor]** README.Rmd:127: "the API serves the new records once they are registered"
  comes before the page introduces the API ("its API at <https://images.a11s.one>", two
  sentences later). Either move the clause after that sentence, or name the endpoint here.
- **[note]** README.Rmd:127: "The index is rebuilt each month" is acceptable as a description of
  the schedule (cron on the 6th, a live listing walk). The workflow has never run: the first
  scheduled run is 2026-11-06. The publish never deletes (`s3_sync.sh:9`), so an item for a file
  the province removes stays in the bucket. This is not a defect in the sentence. It only means
  "rebuilt" does not cover removals.
- **[note]** The working-tree README.md (13:13) and index.html are older than README.Rmd (13:17).
  They differ from a scratch render of 6be1d89 at lines 17, 19, 21 and 211 of README.md, which
  still read "DEMs," and "will carry … once that catalogue publishes it". Re-render before
  committing the outputs.

Rendering: both targets rendered from the scratch copy with `update_query = FALSE`. There were no
errors and no "Error" text in the output. The inline repo link renders in both: README.md:9 and
index.html.
