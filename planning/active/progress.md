# Progress — Index LidarBC point clouds as stac-pointcloud-bc (#1)

## Session 2026-10-07

- Plan approved in stac_dem_bc's session (repo creation, dsm/*.laz first); "Go all phases to PR"
- Created repo, scaffold (77e35db), CLAUDE.md conventions (0735683); transferred stac_dem_bc#35 → #1
- Created branch `1-index-lidarbc-point-clouds-175k-laz-as-s`; scaffolded PWF baseline
- Next: Phase 1 probes
- Phase 1: header probe (64 KB/0.15 s per file); dsm/*.laz is an RGB copy, not a DSM → user re-chose pointcloud/*.laz (9,650); CanElevation unresolved
- Phase 2: laz_item.py (pure item_create + header_read + keys_list), catalogue_build.py, 33 tests; 7 guard mutations each turn a test red
- Phase 2 code-check rounds 1+2: 4 metadata bugs (corrupt header box, bit-field schema size 0, BoundCRS proj:code null, filename dates ≠ acquisition) and 5 runtime fragilities fixed; 54 tests, 14 guard mutations each red
- Phase 2 round 3: 1 inside-fix defect (100 m lower bound) + sheet check, delivery-level date trust, EXCLUDE recheck, --limit dir; 69 tests, every guard mutation red
- Phase 2 round 4: 1 fragile inside a fix (global OUT) fixed; enumeration of all 9,650 headers through the build's own logic: 9,649 built, 1 excluded, 0 refused; NTS grid checked against NRCan for 128 sheets. Loop ended on that enumeration
