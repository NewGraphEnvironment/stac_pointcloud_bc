# Findings — Monthly update in GitHub Actions with the rtj#362 role (#4)

## Issue context

**If we do it:** new LidarBC deliveries reach the collection without a local run, as stac_dem_bc's `update.yml` does for rasters. **If we never do:** the collection is as current as the last time someone built it by hand.

The bucket and the OIDC role `stac_pointcloud_bc_update` exist (NewGraphEnvironment/rtj#362). The trust names this repo. Registration still needs the tailnet, as it does for stac_dem_bc.


## Exploration (2026-10-12)

- Build caches in `data/build` (not committed): `headers.jsonl` 384 MB, `copc_headers.jsonl`
  28 MB, `classes.jsonl` 18 MB, `classes_full.jsonl` 228 KB. Cold build: headers 9,028 s at
  about 20/s and 16 workers; class samples 3 h 10 min; warm build 53 min (#2 archive README).
- Role: `role_gha_stac_pointcloud_bc` (module `stac_pointcloud_bc_update`, rtj
  `env/prod/main.tf`). Get/Put bucket-wide, ListBucket, no delete, trust `ref:refs/heads/main`.
- S3 ETag of an item equals the MD5 of the local file (probed one item: f11596f9...,
  SSE AES256, application/json). `collection.json` ETag is multipart (`-5`, 35,271,165 B).
- Published `collection.json` carries `version` 0.3.0; so does local `data/build/collection.json`.

## Errors Encountered

| Error | Resolution |
|-------|------------|

## Digest publish dry run (2026-10-13, 01:47Z to 01:56Z)

`bash scripts/s3_sync.sh --dryrun` against `data/build` as published at 0.3.0: 174,282 built,
174,283 objects in the bucket; **0 to upload, collection unchanged, 0 unbuilt**, in 9 min 17 s
(the full `aws s3 sync` publish was 95 min). The 0 unbuilt proves the listing decodes the 143
names with a space.

## Footprints are not byte-identical across platforms (A1, 2026-10-13)

Probe: `item_create` over every 20th url of `data/build/headers.jsonl`, sorted (8,713 items),
writing geometry, bbox and `proj:*` as JSON, on the Mac (arm64, PROJ 9.8.1 from the
pyproj wheel) and in `python:3.12` under `--platform linux/amd64` (QEMU, same uv.lock,
PROJ 9.8.1). The probe reproduces the built items on the Mac: 0 of the first 2,000 differ
from `data/build/items`.

- **6,559 of 8,713 differ** (75%): geometry in all of them, bbox in 4,560, `proj:*` in none.
- Largest difference **5.68e-14 degrees**: the last bits of a double (e.g. lat
  49.05009440869304 vs 49.05009440869303).
- So the first CI build would upload about 130k of 174k items and an unstamped collection,
  and Mac and CI builds would then rewrite each other's items. Caveat: amd64 was emulated;
  the first dry-run dispatch measures the real runner.
- **Decision (user, 2026-10-13): round lon/lat to 8 decimals** (`laz_item.LONLAT_DECIMALS`,
  about 1 mm; header boxes are stored to 1 cm). Same probe after the change: **0 of 8,713
  differ**. Every published item's geometry and bbox change once, so it ships as a release
  (rebuild, publish, verify, register), before the first scheduled run publishes it unstamped.

## Build cache seeded (2026-10-13, 02:48:50Z to 02:49:03Z)

`scripts/cache_sync.sh push` from this Mac's `data/build`: headers 175,318 lines (15.7 MB gz),
COPC headers 13,996 (1.3 MB), class samples 35,055 (3.1 MB), whole reads 349 (37 KB). Pulled
into an empty scratch tree: all four byte-identical to the local files. Guards exercised there:
an unchanged push uploads nothing; a cache cut to 100 lines is refused; a tree that never
pulled is refused; a pull over a local cache merges (175,318 + 175,318 -> 175,318).
