# Plan review (Plan agent, 2026-10-10) — triage

The full review was returned as reply text (Plan agents cannot write); this is its triage.

| id | finding | disposition |
|---|---|---|
| B1 | circular import build <-> probe | fixed: `cache_tail_repair`, `CLASS_TARGETS` moved into `laz_classes_probe.py`; the probe no longer imports the build |
| B2 | screen definition | fixed: strict-below share <= SCREEN_PERCENTILE, the research's definition, `density` imported from the probe |
| G1 | whole-group groundless deliveries escape a within-group screen | decide from the 5% audit: clustered misses -> sample those groups whole; scattered -> widen; recorded in findings |
| G2 | audit has no acceptance criterion | pass = zero confirmed misses; report the 95% upper bound; save seed and id list |
| G3 | derived check scoped to the screen fails toward pass | every good current sample that flags needs a whole read, screened or not; no `--limit` skip |
| G4 | collection description, CLAUDE.md, NEWS claim every file was sampled | rewrite in Phase 5 |
| G5 | item_create refusals raise one at a time | aggregate per fault class, refuse once |
| G6 | date_parse errors name no file | aggregate with G5 |
| G7 | mixed naming styles unchecked | report token-length mix per delivery in Phase 4 |
| G8 | published diff drops keys instead of asserting | assert values, map asset-level `nge:` too, compare collection, exit non-zero |
| G9 | related link shape | fixed: stac_dem_bc's shape, S3 collection.json, before item links |
| G10 | file name characters vs item_link_href | refuse outside a conservative set at listing |
| G11a | pointcloud_select drops misnamed product dirs | key_parse every .laz; unknown product raises |
| G11b | --groups-record lowers floors blindly | log deltas, refuse a lowering without --force |
| G12 | COPC_PAIRS literal | committed JSON beside GROUPS, recorded by the same flag |
| O1 | listing-only checks run late | move before header read |
| O2 | validation first meets crate schemas at the end | validate one item per shape early; pool validates dicts |
| O3/O4 | ordering of re-measure vs build | build caches headers before refusing; audit runs on its class_targets |
| O5 | re-runs costly | cache CRS/Transformer by WKT |
| A1 | headers.jsonl exists (9,650) | noted; findings corrected |
| A2 | crate lidarbc v1.1.0 404s; stac_dem_bc names it | pinned v1.0.0 here; tell stac_dem_bc (comment on its #55) |
| A3 | TILE_SIDE_MAX_M measured on 11 groups | covered by G5's aggregated report |
| A4 | key_parse does not tie sheet to block | add the check |
| A5 | mixed density regimes within a group | report audit misses by group |
| A6 | stacs verify duration at 175k | note expected duration in Phase 6 |
| S1-S3 | leftover pins, counts in comments, asset-level schema keys | S3 already: guard walks every key; S1/S2 in Phase 5 |
| AC1-AC5 | pass/fail gates | adopted |
