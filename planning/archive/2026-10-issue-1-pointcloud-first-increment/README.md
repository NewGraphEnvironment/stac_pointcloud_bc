## Outcome

The repo was created and NewGraphEnvironment/stac_dem_bc#35 transferred here as #1. Then
the first increment of `stac-pointcloud-bc` was published: **9,649 items** from the
`pointcloud/*.laz` of the 11 mapsheet-years whose `dsm/` holds no raster. It is registered,
and `stacs verify` reports IN SYNC.

The approved plan indexed `dsm/*.laz` first. The Phase 1 probe showed those files are an
RGB-colourised copy of the same-tile point cloud, not a surface model, so the user re-chose
`pointcloud/*.laz`.

Items take their geometry and properties from the LAS header, read with one 64 KB range
request. Four review rounds read all 9,650 real headers and found what `validate()` and
hand-written fixtures could not:
- one corrupt header (excluded by name, and its fault rechecked on every run)
- bit-field schemas published with size 0
- BoundCRS horizontals publishing no `proj:code`
- filename dates that are not acquisition dates (trust is now decided per delivery)

Two guards written during the work were themselves wrong, and the population caught both:
- a 100 m minimum tile side refused 104 real edge files
- a BC-wide box could not catch a wrong UTM zone; it was replaced by an NTS-sheet check,
  verified against NRCan for all 128 sheets

## Measurement

- **Header read:** one 64 KB request, 0.11–0.22 s, no EVLRs (10 files). Listing the 11
  groups takes about 2 s. Reading 9,650 headers with 16 threads takes about 2 min.
  Building and validating 9,649 items takes 14–16 min (pystac validation dominates).
- **`dsm/*.laz` vs `pointcloud/*.laz` for the same tile:** identical bounds; point counts
  30,202,168 vs 30,202,170 and 58,432,776 vs 58,466,790 (the difference is noise class 7);
  point format 3/7 vs 1. 5,710 of 6,067 have a same-id `pointcloud/` tile. This changed
  the increment and stac_dem_bc's DSM-gap wording (stac_dem_bc#53).
- **Tile sides:** median 1,829 x 1,418 m, maximum 1,878 m. 104 files are under 100 m, the
  smallest 1.4 x 0.8 m with 14 points.
- **Dates:**
  - 266 `082k/2017` files are named `_18xxxx`, and GPS time puts them in October 2017.
  - 2,008 files in `092g/h/j 2016` carry 2017 processing dates.
  - So all 4 of those deliveries publish their directory year. The other 7 name only the
    year.
- **CRS:** 5 distinct WKTs. 1,678 BoundCRS compounds resolve to EPSG:2955. 197 Esri WKTs
  cannot be identified and publish `proj:wkt2`.
- **Registration:** 1 collection and 9,649 items; payload 22.2 MB. Verify: 9,649 / 9,649,
  0 missing, 0 orphaned, 0 changed.

## Evidence

`logs/20261007_*` (gitignored). The probe, build, sync, register and verify logs are there;
the numbers above are the record. Review findings are in `review-*.md` in this directory.
`research/laz_header_read.md` is the durable write-up.

Closed by: PR (to be opened from branch `1-index-lidarbc-point-clouds-175k-laz-as-s`)
