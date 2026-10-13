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
