# Progress — Check whether NRCan CanElevation republishes these LidarBC projects (#6)

## Session 2026-10-09

- Research landed first (443b88d): measurement and probe, decision A taken in the issue
- Plan-mode exploration — phases approved by user; "go all phases to pr"
- Branch `6-canelevation-overlap` already existed (pushed with the research); no new branch cut
- Scaffolded PWF baseline from issue #6 with approved phases
- Next: start Phase 1

### Phase 1 — item function and lister
- `copc_asset_add()` (pure) and `canelevation_keys_list()` in `laz_item.py`; probe now uses the shared lister
- 9 new tests; each of the five new guards (count, box, double add, non-200, truncated-without-token) shown red when removed, in a scratch copy
- Live: probe lister lists 682 `.laz` in `BC/Riverine_Floodplain_UTM11_2019`, as the research recorded

### Phase 2 — build wiring
- `copc_listing()` (four projects, 90% floor), `file_stem()`, `copc_pairs()` (a name on two files either side fails), COPC headers through `headers_fetch()` into `copc_headers.jsonl`; a read failure returns 1 before anything is written
- Collection description names the overlap; NRCan added as a `host` provider
- 7 new tests (91 total); five guards shown red when removed (short project, duplicate either side, COPC read error, the wiring itself)
- The two existing `main()` tests reached the live CanElevation bucket once wired; they now patch `copc_listing`
- Live `--limit 40` build over `092g/2016`: CanElevation projects listed at exactly the measured counts (7,873 / 3,866 / 682 / 1,714); 40 of 40 items got a `copc` asset; its href HEADs 200; `stacs audit` OK on all 40

### Plan review folded in (review-plan.md)
- The `--limit 40` slice of Phase 2 was made with a one-off that set `catalogue_build.INCREMENT = {"092/092g/2016": 1706}` before `main()`; `--limit` alone takes the URL-sorted head, which is `082e/2018`
- First full build (07:44-07:52 PDT): 9,649 items, 1,964 with `copc` (332 / 57 / 1,155 / 420). Measured on its cache: max box offset 0.01 m (x/y and z), all CRSs agree, 1,575 copies are LAS 1.4/6 from 1.2/1
- Fixes: z and CRS compared, tolerance 1 m -> 0.05 m, all mismatches reported (rc 1), COPC format on the asset, licence named, CanElevation listed first, duplicate check scoped to matched names, `data/build-limit/` ignored. 4 new tests (95); five guards shown red when removed

### Code-check (branch), four rounds — see review-round1..4.md
- R1: asset text said "same CRS" (only horizontal compared). R2: "same extent", whole projects, pair loss unguarded, a test listing the live bucket. R3 named the mechanism (snapshot restated as guarantee) and found it in R2's fix. R4 found it in R3's fix (one-sided floor) and in research scope; ended by a mechanical enumeration (60 hits classified, review-round4.md)
- Added `scripts/copc_pairs_measure.py` as the producer of the research and NEWS numbers

### Phase 3 — build, publish, register v0.2.0
- Final build at b73298a (`logs/20261009_catalogue_build_v0.2.0.log`): 9,649 items, 1,964 `copc` (332 / 57 / 1,155 / 420); exact COPC_PAIRS held
- Before upload: `copc_pairs_measure.py --published` against a copy of the bucket: changed ids == the 1,964 copc ids, none changed beyond the asset, no id gained or lost
- Synced (`logs/20261009_s3_sync_v0.2.0.log`); bucket read back byte-identical to the build (`/usr/bin/diff -rq`; `diff` here is a git wrapper)
- `stacs verify` before: changed 1,964, set-equal to the copc ids; `stacs register --mode drift` (`logs/20261009_stacs_register_v0.2.0.log`): collection then 1,964 items; `stacs verify` after: IN SYNC, 9,649
- Served `copc` hrefs HEAD 200 from both contributing projects (Lower_Mainland_2016, Riverine_Floodplain_UTM11_2019)
