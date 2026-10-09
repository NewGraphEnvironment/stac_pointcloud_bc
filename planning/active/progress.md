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
