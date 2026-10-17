# Research

What is known, kept current. One topic file each, revised in place; `git log --follow`
is the history.

| file | covers |
|---|---|
| [laz_header_read.md](laz_header_read.md) | Cost and yield of a remote header read; `dsm/*.laz` is an RGB copy of the point cloud |
| [laz_classes.md](laz_classes.md) | Which point clouds are ground-only or hold no ground, measured by reading points; the build's density screen, and the random audit of what it misses; water returned as class 1, not 9 (093l/2019) |
| [filename_dates.md](filename_dates.md) | What a file name's date tokens mean: two days are the first and last day flown, measured by GPS time |
| [canelevation_overlap.md](canelevation_overlap.md) | Which LidarBC point clouds NRCan's CanElevation series republishes as COPC, and where its index is |
| [build_reproducibility.md](build_reproducibility.md) | Whether a rebuild on another platform writes the same item bytes: unrounded footprints differ in their last bits (75%), and rounding leaves a few boundary cases; S3 ETags of items are their MD5 |
| [dem_alignment.md](dem_alignment.md) | A LidarBC DEM (093l/2019) is a TIN of its delivery's ground returns, but sits 0.5 m south-west of where GDAL reads it; found by differencing at half-cell shifts |

Naming: `<topic>.md`, revised in place.
