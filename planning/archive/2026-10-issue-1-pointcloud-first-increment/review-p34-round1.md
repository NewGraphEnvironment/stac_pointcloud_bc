# Review: Phase 3-4 staged diff, round 1

Reviewed 2026-10-07 against the staged diff (`pc_p34.patch`), the live bucket and API, and
stacs v0.1.1 source. All probes ran in a copy of the repo (rsync to scratchpad, fake `aws` on PATH).

## Findings

- **[severity: fragile]** scripts/s3_sync.sh:12 — Any argument other than the exact string `--dryrun`
  is silently ignored, so the script does a real publish. Reproduced with a fake `aws`:
  `bash scripts/s3_sync.sh --dry-run` (the spelling most CLIs use; `aws` and `stacs` use
  `--dryrun`, so the two are easy to mix up) ran `aws s3 sync …` and `aws s3 cp …` with
  no `--dryrun`, then printed "Sync complete". This is the production bucket, and a preview flag
  that does not preview is the dangerous direction. Fix: reject any argument other than none or
  `--dryrun` (`case "${1:-}" in ""|--dryrun) ;; *) echo usage >&2; exit 2;; esac`, and refuse `$# > 1`).

- **[severity: fragile]** scripts/s3_sync.sh:18-21 — The guard comment says "The collection links
  exactly the items being uploaded, or nothing is published", but the check compares two counts,
  not two sets. Reproduced in the copy: renaming one item file to `not-linked-anywhere.json` leaves
  9,649 = 9,649 and the script proceeds to upload an unlinked item while the collection links a
  file that is not uploaded. The realistic way to reach this is catalogue_build.py being killed
  between `os.replace(stage, items)` and `os.replace(collection.json.new, collection.json)` on a
  rebuild whose item set changed but whose size did not (an EXCLUDE added, one file re-delivered
  under a new name): new items beside the old collection.json, which is the state the build's own
  comment says can never exist. Fix: compare the set of link basenames (with `%20` decoded, as
  stacs `_href_to_id` does) to the set of file names in `items/`, in the same python3 call.

- **[severity: bug, documentation]** NEWS.md "`dsm/*.laz` is not a surface model" and README.md
  table row `dsm/*.laz (an RGB copy of the point cloud, not a surface model) | 6,391` — stated for
  all 6,391 files, but the evidence in research/laz_header_read.md is two tile pairs compared
  (`092g026_1_4_2`, `082e084_4_1_4`) plus a 5-file header sample, all inside the 11 groups. The same
  note says only 5,710 of the 6,067 `dsm/*.laz` in those groups have a `pointcloud/` file with the
  same tile id, so for the other 357 "a copy of the same-tile `pointcloud/*.laz`" cannot be true as
  written, and the 324 `dsm/*.laz` outside the 11 groups were never examined. A reader acts on this
  (NEWS says the stac_dem_bc DSM gap "is real", and #3 decides whether to index them). Scope the
  claim to what was measured: "in the tiles compared", "of the 6,067 in the 11 groups, 5,710 share a
  tile id with a pointcloud file".

- **[severity: fragile, internal]** planning/active/task_plan.md Validation — the newly ticked line
  reads "`stacs verify` IN SYNC: 9,650 ids both ways"; the published and registered count is 9,649
  (Phase 3's line was corrected, this one was not). A ticked box asserting a number that is false.

## Checked and fine

- Counts: INCREMENT sums to 9,650; 175,317 − 9,650 = 165,667; `data/build/items` holds 9,649; the
  collection links 9,649; 15 item files carry a space and are counted correctly by `find | wc -l`.
- Live state: `s3://…/collection.json` is byte-identical to `data/build/collection.json`; served with
  `Content-Type: application/json`; API collection serves `version: 0.1.0` with the Version Extension.
- collection_version.py: the stamped collection validates with `pystac.validation.validate_dict`
  (core 1.1.0 + version v1.2.0); a non-string version is rejected by the schema; re-stamping is
  idempotent. A rebuild drops the stamp, which matches stac_dem_bc's deliberate rule (an
  appended catalogue's old version is false, absence is better), so not a defect.
- s3_sync.sh: `${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}` runs under `set -u` on /bin/bash 3.2.57; the
  `[ … ] && …` line does not trip `set -e`; `python3` uses only `json`; a missing `links` key fails
  the command substitution and exits.
- `aws s3 sync` without `--delete`: stacs reads the published set only from the collection's item
  links (`catalogue.collection_item_links`), so stale unlinked objects in the bucket are invisible to
  it; an item dropped from a later build would surface as `orphaned` (registered, not published) and
  nothing in stacs deletes it. No defect for this release (first publish); a known consequence of
  upsert-only.
- NEWS dates: every item has `datetime: null` and a directory-year range; the 7 non-delivery-year
  groups carry only 4-digit year tokens, so "every other delivery names only the year" holds; 7
  `092h/2016` items have no token at all.
- README commands: `stacs verify|register --config … --mode drift` exist in the installed stacs;
  `PYTHONPATH=scripts` is redundant (running `scripts/x.py` puts `scripts/` on sys.path) but harmless;
  `pytest tests/ -q` is 75 passed in the copy; `https://lidar.gov.bc.ca/` returns 200.
