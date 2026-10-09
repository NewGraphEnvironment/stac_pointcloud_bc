# Findings — Check whether NRCan CanElevation republishes these LidarBC projects (#6)

## Issue context

**If we do it:** we know whether part of this collection duplicates the national point cloud series, and can link to it or drop the overlap. **If we never do:** a user may find the same flights twice, in two catalogues, with no note that they are the same.

## Answered (2026-10-09): yes, for 13,996 files from four projects

Measured in [`research/canelevation_overlap.md`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/6-canelevation-overlap/research/canelevation_overlap.md) (producer: `scripts/canelevation_overlap_probe.py`).

- **Where the index is.** #1's FTP route is dead. The content moved to the listable S3 bucket `canelevation-lidar-point-clouds` (ca-central-1), and open.canada.ca publishes project and tile indexes (GPKG). `BC/Skeena_Terrace_2023` is in the bucket but not in the project index.
- **What is republished.** CanElevation republishes four LidarBC projects as COPC under LidarBC's own file names: `Vancouver_Island_Sunshine_Coast_2018`, `Riverine_Floodplain_UTM10_2019`, `Riverine_Floodplain_UTM11_2019` and `Lower_Mainland_2016`. That is 13,996 of LidarBC's 181,708 `.laz`, all `pointcloud/`, over 28 mapsheet-years. In a sample of 40 pairs, every header had the same point count and bounding box. The only difference is format: LAS 1.2 was converted to 1.4, because COPC requires it.
- **In the published collection (v0.1.0):** 1,964 of 9,649 items have a copy, in `092g/2016` (1,155), `092h/2016` (420), `082e/2019` (332) and `082l/2019` (57). The other seven mapsheet-years have none.
- **No file-level copy found:** CanElevation's five other BC projects (2023, three provincial and two federal FHIMP). Compared by header against 8,753 LidarBC 2022–24 files on the same sheets, none of their 7,742 files has a copy. That test cannot see a re-tiled copy, but the filename dates point to different flights.
- **Not a copy:** 139 `Lower_Mainland_2016` tiles dated `_2018`, which hold different points from LidarBC's file on the same tile.

## Decision (2026-10-09): A, link

Decided by the maintainer: link the CanElevation COPC from each matching item and name the overlap in the collection description. The options considered:

What to do about the 13,996 files, which this collection will reach in later increments, including the 1,964 already published:

- **A. Link (recommended).** Add the CanElevation COPC as a second asset (or an `alternate` link) on each matching item, and name the overlap in the collection description. COPC is the cloud-optimised form, so linking adds value; LidarBC stays the source of record; and nothing is lost for the four mapsheet-years CanElevation covers only in part.
- **B. Note only.** Name the four projects in the collection description, and leave the items unchanged.
- **C. Drop.** Leave the matching files out of this collection. This splits mapsheet-years such as `092g/2016` (1,155 of 1,706) between two catalogues.

A changes item JSON, so the build goes through `/planning-init 6`, on branch `6-canelevation-overlap`.

## Build wiring (2026-10-09)

- CanElevation ETags are multipart (`"<md5>-7"`), stable per object, so the COPC header
  cache keys on them as the LidarBC cache does.
- `stacs audit` (v0.1.1) checks only the required `laz` key; a second asset on another
  host passes (40 items, limited build).

## Errors Encountered

| Error | Resolution |
|-------|------------|
