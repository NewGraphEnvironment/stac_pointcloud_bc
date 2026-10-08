# Task: Index LidarBC point clouds (175k .laz) as stac-pointcloud-bc, in a new repo (#1)

Transferred from NewGraphEnvironment/stac_dem_bc#35. This branch is the **first increment**.

## Context

The objectstore holds 181,708 `.laz` that nothing indexes: 175,317 under `pointcloud/`
and 6,391 under `dsm/` (live walk, 2026-10-06). #35 decided on its own collection
(`stac-pointcloud-bc`), its own repo (`stac_pointcloud_bc`) and its own bucket. The
bucket and the CI role exist (rtj#362, closed), and the role's trust already names the
repo. The registration layer is `stacs` v0.1.1 (stacs#1, closed). So #35 is unblocked;
only the repo is missing.

Approved at this gate:
- **Create the repo.** Public `NewGraphEnvironment/stac_pointcloud_bc`, laid out like
  `stac_airphoto_bc` (uv, `pyproject.toml`, `stacs.toml`, `tests/`). Transfer #35 there
  and do all the work there.
- ~~First increment = `dsm/*.laz` (6,067 files)~~ **Changed after Phase 1 (user, 2026-10-07):
  `dsm/*.laz` is an RGB copy of the point cloud, not a surface model. First increment =
  `pointcloud/*.laz` in the 11 laz-only mapsheet-years: 9,650 files.** Original reasoning:
  These are the surface models whose absence leaves 1,211 DEM tiles reported as
  `no_raster_dsm` in stac_dem_bc's `data/dsm_pairing_report.md`. Each item records its
  product (`dsm` / `pointcloud`), so `pointcloud/*.laz` can join the same collection
  later with no id clash.

Measured per group, `dsm/*.laz` (`pointcloud/*.laz` alongside, not in this increment):

```
082/082e/2018 1546 (1995)   082/082e/2019 771 (871)    082/082f/2018 258 (1061)
082/082g/2018  215 (215)    082/082j/2018 183 (207)    082/082k/2017  29 (267)
082/082l/2018  752 (774)    082/082l/2019 321 (1352)   092/092g/2016 1394 (1706)
092/092h/2016  416 (1020)   092/092j/2016 182 (182)
```

## Phase 0: Repo bootstrap (in `~/Projects/repo/stac_pointcloud_bc`)
- [x] `gh repo create NewGraphEnvironment/stac_pointcloud_bc --public`, MIT, clone to `~/Projects/repo/`
- [x] Scaffold from `stac_airphoto_bc`'s shape:
  - `pyproject.toml`: python >= 3.12; pystac, laspy[lazrs], fsspec/requests, `stacs` @ v0.1.1 from git
  - `uv.lock`
  - `stacs.toml`: api `https://images.a11s.one`, collection `stac-pointcloud-bc`, bucket `https://stac-pointcloud-bc.s3.amazonaws.com`, transport copied from stac_dem_bc; asset rule set in Phase 2
  - `planning/`, `NEWS.md` (`## Unreleased`), `README.md`, `.gitignore`
- [x] `/claude-md-init`: repo CLAUDE.md carrying the decisions from #35 (collection, bucket, why separate) and a link back to stac_dem_bc
- [x] `gh issue transfer 35 NewGraphEnvironment/stac_pointcloud_bc`. Record the new number; stac_dem_bc's CLAUDE.md and #47 cross-references get a one-line pointer update in stac_dem_bc
- [x] Then `/planning-init <new N>` there: branch and PWF baseline with these phases

## Phase 1: Probes — the "open before building" questions, measured
- [x] **Remote header read cost.** On 5 `dsm/*.laz` and 5 `pointcloud/*.laz`, read the LAS header and VLRs with laspy over HTTP range requests (no point decompression). Record bytes transferred, wall time, point count, bounds, CRS (WKT/GeoTIFF VLR), point format and classification flags
- [x] **Decision rule, fixed now so the probe settles it without a stall:** if the header read is ≤ 64 KB and ≤ 2 s per file, items get their geometry and properties from the header (real bounds, point count, CRS). Otherwise they come from the filename (tile id → nominal footprint) and the cost goes in the issue
- [x] **Is `dsm/*.laz` a surface model?** No: an RGB copy of the same-tile `pointcloud/*.laz`. Increment re-asked → `pointcloud/*.laz`. Check classification and return info on 2 files. If they are not DSM points, stop and re-ask the increment question
- [x] **CanElevation overlap.** Unresolved: no point cloud collection in NRCan STAC, FTP listing 403. Follow-up issue. Query NRCan's CanElevation STAC for the 11 groups' bboxes and years; record any overlap. Overlap is recorded, not a blocker for the first increment
- [x] Write the results to `research/laz_header_read.md` (provenance header) and the issue body

## Phase 2: Item creation — stactools-shaped
- [x] `src/` or `scripts/laz_item.py`: pure `item_create(href, header) -> pystac.Item`, with no bucket, host or CI in it
  - `pointcloud` and `proj` extensions
  - id from the key path, as stac_dem_bc does (`082-082e-2018-dsm-<file>`)
  - `nge:product` = `dsm` / `pointcloud`
  - datetime from the filename date, as stac_dem_bc parses it
  - one asset, key `laz`, media type `application/vnd.laszip`, href = the objectstore URL (`https://`)
- [x] Listing: one bucket walk via `ngr` v0.0.3, or a Python walk; keep the `https://` scheme guard (stac_dem_bc#51) and a plausibility floor
- [x] `stacs.toml` `[assets] require = "laz"`
- [x] Tests: fixtures cover both products, a missing CRS VLR, a filename with no date, and an `https:/` input that must raise. Each guard is shown to fail its test when removed

## Phase 3: Build, publish, register the first increment
- [x] Build 9,650 items → 9,649 (1 excluded by name, header mins [0,0,0]) with `ThreadPoolExecutor` (I/O-bound, as stac_dem_bc), logging to `logs/`; validate with pystac (`stacs` validate)
- [x] Collection JSON: extent from the items, providers and keywords as in stac_dem_bc, STAC Version Extension
- [x] Sync to `s3://stac-pointcloud-bc/` with local credentials (CI publishing is a follow-up issue)
- [x] `stacs verify` then `stacs register --config stacs.toml --mode drift` from the tailnet machine; then verify again: id sets equal both ways, bodies digest-equal
- [x] Spot-check 3 items in QGIS/STAC Browser against the source footprint

## Phase 4: Close-out
- [x] README (what is indexed, what is not yet), NEWS `v0.1.0` entry, follow-up issues:
  - the rest of `pointcloud/*.laz` (175,317 − 9,650)
  - `dsm/*.laz` (6,391): RGB copies; index as a variant asset or not at all
  - CI monthly update with the rtj#362 role
  - elevation-item → point cloud link
- [x] stac_dem_bc: does `dsm_pairing_report.md` gain a pointer to the new collection for the 1,211 tiles? File it there, don't change it here

## Validation

- [x] `uv run pytest` green; each new guard turns its test red when removed
- [x] Probe numbers recorded with units in `research/laz_header_read.md`
- [x] After registration, `stacs verify` IN SYNC: 9,649 ids both ways, 0 changed bodies
- [x] An item served by the API has a `laz` href that resolves (HTTP 200 on HEAD)
- [x] `/code-check` clean on each commit
- [x] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
