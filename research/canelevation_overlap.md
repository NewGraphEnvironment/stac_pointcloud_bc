# Which LidarBC point clouds NRCan's CanElevation series republishes

**Verified:** 2026-10-09 · **Issues:** #6 (opened from #1) · **Produced by:**
`scripts/canelevation_overlap_probe.py`; log `logs/20261009_*_canelevation_overlap_probe.log`;
the per-pair check by `scripts/catalogue_build.py` (`logs/20261009_catalogue_build_v0.2.0.log`),
measured by `scripts/copc_pairs_measure.py`
(gitignored; the numbers below are the record).

## Where CanElevation's point clouds are

The FTP tree #1 tried (`ftp.maps.canada.ca/pub/elevation/pointclouds_nuagespoints/`, served
from the `ftp-maps-canada-ca` bucket) now holds only a README saying the content moved to
`canelevation-lidar-point-clouds` (S3, `ca-central-1`). That bucket allows listing.
The dataset record (open.canada.ca `7069387e-9986-4297-9f55-0288e9676947`) also publishes
a project index and a tile index (`Index_LiDARprojects_projetslidar.gpkg`,
`Index_LiDARtiles_tuileslidar.gpkg`), and the stactools-canelevation package reads the
same record. Files are COPC (`.copc.laz`), grouped by `<provider>/<project>/`.

Nine CanElevation projects hold BC data: seven under `BC/` and two federal flood-mapping
(FHIMP) projects under `NRCAN/`. `BC/Skeena_Terrace_2023` is in the bucket but missing
from the project index, so a footprint query alone misses it.

## 13,996 LidarBC file names recur in CanElevation, from four projects

Matched by file name, with `.copc` and `.laz` stripped. No name maps to more than one
LidarBC file.

| CanElevation project | files | same name as a LidarBC file |
|---|---:|---:|
| `BC/Vancouver_Island_Sunshine_Coast_2018` | 7,873 | 7,873 |
| `BC/Riverine_Floodplain_UTM10_2019` | 3,866 | 3,866 |
| `BC/Riverine_Floodplain_UTM11_2019` | 682 | 682 |
| `BC/Lower_Mainland_2016` | 1,714 | 1,575 |
| `BC/Hope_TB_2023`, `BC/Shuswap_TB_2023`, `BC/Skeena_Terrace_2023` | 1,457 | 0 |
| `NRCAN/FHIMP_PICAI_BC_South_{East,West}_*_2023` | 6,285 | 0 |

That is 13,996 of LidarBC's 181,708 `.laz`, all `pointcloud/` and none `dsm/`, spread over
28 mapsheet-years (2016, 2018, 2019). Some groups are republished whole (`093g/2019`,
1,261 of 1,261) and some barely (`092j/2019`, 3 of 198). The probe log has the per-group table.

**Wherever a matching name was checked, it had the same point count and box.** A seeded
sample of 10 pairs per project (40 in total) read both headers: 40 of 40 have the same point
count and a bounding box within 1 m. The sample did not read the CRS. The build later
checked every pair in the first increment (below), all from two of the four projects. The
format differs for `Lower_Mainland_2016`: COPC requires LAS 1.4 point format 6–8, so those
files were converted from LAS 1.2 format 1. The sample says nothing finer than that, and the
other two projects' 11,739 files have not been compared beyond it. A
CanElevation copy is larger (one pair: 65 MB `.laz`, 93 MB `.copc.laz`), so file size
does not identify a pair.

**What this means for the published collection.** 1,964 of the 9,649 v0.1.0 items have a
CanElevation copy, all in four of the 11 mapsheet-years:

| group | republished |
|---|---:|
| `092/092g/2016` | 1,155 / 1,706 |
| `092/092h/2016` | 420 / 1,019 |
| `082/082e/2019` | 332 / 871 |
| `082/082l/2019` | 57 / 1,352 |

The other seven (`082e/2018`, `082f/2018`, `082g/2018`, `082j/2018`, `082k/2017`,
`082l/2018`, `092j/2016`) have none.

## What the collection does with it (decision A, v0.2.0)

The maintainer chose to link rather than note or drop (#6). From v0.2.0, each item whose
file name CanElevation publishes carries that file as a second asset, `copc`, and the collection
description names the four projects. The `laz` asset stays the source of record.

The build does not trust the name. For every pair it reads the CanElevation file's header
and links it only if the point count and horizontal CRS are the same and the box (x, y and z)
is within 0.05 m. The first increment's 1,964 pairs (1,575 `Lower_Mainland_2016`, 389
`Riverine_Floodplain_UTM11_2019`; `scripts/copc_pairs_measure.py` over the build's header
caches) all pass:

- The largest box offset is 0.01 m: 371 boxes are identical and 1,593 differ by up to
  0.01 m, which is coordinates re-quantised by the conversion.
- The full CRSs never match, so a whole-header comparison fails every pair: the 1,575 add an
  unknown vertical CRS to a horizontal-only source, and the 389 drop the source's CGVD2013.
  The horizontal EPSG agrees in every pair (3157 and 2955).

A check on header values cannot see a reclassified re-delivery under the same name.

## Same tile under another name is not the same points

The other 139 files in `BC/Lower_Mainland_2016` carry a LidarBC tile id with a `_2018`
date suffix (`bc_092g025_3_1_1_xyes_8_utm10_2018.copc.laz`). Each tile has a LidarBC file under another date
(`..._20170714.laz` in `092g/2016`, and some in `092g/2025` too). In a sample of 10, none
had a LidarBC file on that tile with the same point count and box. So CanElevation holds a version of those tiles
that LidarBC does not serve today. They are not duplicates of anything in this
collection.

## The 2023 projects

The five projects with no name match (`BC/Hope_TB_2023`, `BC/Shuswap_TB_2023`,
`BC/Skeena_Terrace_2023` and the two FHIMP projects, 7,742 files in all) were compared by
header against every LidarBC 2022–2024 `pointcloud/` file on the NTS sheets they touch
(8,753 files on `082f/g/j/k/l/m`, `092g/h/i/j` and `103i`). None has a LidarBC file with
the same point count and box. One Shuswap file shares a point count only. No header read failed.

**What that test cannot see.** It finds a file-for-file copy, not a re-tiled one. The
FHIMP projects sit on a 1 km UTM grid (`..._1km_E5180_N54470_CLASS.copc.laz`) and the
provincial `TB` projects on their own numbering (`Hope_001`, `SHUS_00001`), while
LidarBC uses BCGS tiles. So the same flight, cut differently, would not match. The
filename dates point to different flights: FHIMP is dated 2023-07 and 2023-08, while
the LidarBC groups on those sheets are dated 2022, 2023-11, or 2024–2025. That is
supporting evidence, not proof. To settle it, compare GPS time ranges or point density
over a shared footprint.

## How to repeat it

`uv run python scripts/canelevation_overlap_probe.py OUTDIR`. The listings take a few minutes
(575k LidarBC keys, 313k CanElevation keys under `BC/` and `NRCAN/`). Step 4 reads about
16,500 headers, most of the run, because COPC reads from S3 are slower than the
objectstore's. The JSON written to OUTDIR (listings, pairs, headers) is enough to rerun a
comparison without listing again.
