# CLAUDE.md - stac_pointcloud_bc

## What this repo is

The STAC catalogue of LidarBC point clouds (`.laz`) as the `stac-pointcloud-bc`
collection. Sibling of [stac_dem_bc](https://github.com/NewGraphEnvironment/stac_dem_bc),
which indexes the raster products of the same deliveries (DEM, DSM) as
`stac-elevation-bc`. The `.laz` stay on the province's objectstore; this repo publishes
item JSON to `s3://stac-pointcloud-bc` and registers it with
[stacs](https://github.com/NewGraphEnvironment/stacs) (`stacs.toml`).

**The repo holds discovery and item creation only.** Registration and verification are
`stacs`. Change them there, not here.

## Decisions this repo starts from (#35, decided 2026-09-30)

- **Its own collection, one item per `.laz` file.** The `.laz` tiles have different,
  usually smaller footprints than the raster tiles, so as assets of a raster item they
  would misstate their geometry (rtj#229).
- **Its own repo and bucket.** Write authority is per bucket. `stac-dem-bc` holds the
  elevation catalogue at its root, and stac_dem_bc's registration requires a `dem` asset
  on every item there. The bucket (`stac-pointcloud-bc`, us-west-2, public read,
  versioned) and the CI role (`stac_pointcloud_bc_update`) are IaC in rtj (rtj#362).
- **Item creation is stactools-shaped:** a pure function from an href and a header to a
  `pystac.Item`, with nothing about the bucket, host or CI in it. That keeps a later
  stactools contribution a lift rather than a rewrite.

## Source facts (measured 2026-10-06, live walk of 575,438 keys)

- 181,708 `.laz`: 175,317 under `<block>/<sheet>/<year>/pointcloud/` and 6,391 under
  `.../dsm/`. Four have `copc` in the name; the rest are plain LAZ.
- 11 mapsheet-years publish their surface model **only** as `dsm/*.laz` (6,067 files).
  In stac_dem_bc they leave 1,211 DEM tiles reported as `no_raster_dsm`. Those files
  are the first increment indexed here.
- **Source URLs are `https://`.** `ngr::ngr_s3_keys_get()` returned `https:/` before ngr
  0.0.3 (ngr#38). Anything that reads a URL list refuses the one-slash form; never
  repair it silently (stac_dem_bc#51).

## Hazards inherited from stac_dem_bc

- **Never verify a registration by a count.** Compare id sets in both directions, and
  bodies by digest (`stacs verify`).
- **Register the collection before its items, and never delete-then-load.**
  `pgstac.items.collection` is `ON DELETE CASCADE`.
- Concatenating many item JSONs uses `find -exec cat {} +`, never a glob (ARG_MAX).
