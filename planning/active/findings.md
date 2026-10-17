# Findings — #30 part 2: the valley floor upstream

## Investigation (2026-10-17, scratch probes `p31_*.R`)

- **South forest's straight line:** BC Digital Road Atlas (`WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP`)
  has 7 segments in the window, all `ROAD_SURFACE` rough, `ROAD_CLASS` unclassified, unnamed: one
  along the straight line across the south forest, one along the foot of the slope. The other dark
  features on the slope are curved gullies. A CN railway runs along the far (north) shore.
- **Not TIN artifacts:** ground returns are dense under the south forest; the distance to the
  nearest ground return is under 1 m almost everywhere on land; the gaps are the creek and the lake.
- **Lake edge of the hayfield:** cleared to a straight edge, ~30 m of rough uncleared ground left at
  the shore; profiles at 500, 700, 900 m north of the window's south edge show the field sloping
  gently to the lake and a 0.3-0.5 m ridge at the waterline. No dike.
- **Zoomed out (published DEM, 9 x 6.7 km window read over HTTP in 75 s):** height above the lake
  saturates upstream (the valley floor is 8+ m above it). Height above the nearest FWA stream bed
  (order >= 2, lowest ground within 6 m, 2,350 samples, nearest-sample + 150 m smoothing) shows
  Maxan Creek's meander scars and oxbows upstream and the Bulkley River's floodplain; the
  nearest-sample surface leaves blotches in the field west of the delta.
- The DEM tile's coverage ends on a curve at its south: a window must avoid its nodata.

## The figure as built (2026-10-17)

- Window 4.0 x 2.3 km west of the mouth (WEST 3400, EAST 600, SOUTH 1550, NORTH 750 m); SOUTH 1750
  reached the tile's nodata corner (3,766 cells), 1600 was the first clear value, 1550 keeps a margin.
- Read in ~30 s; whole script ~1 min. Drawn at 4 m (2 m gave a 3.5 MB PNG and a 10.2 MB index.html;
  4 m: 0.9 MB, 6.8 MB). Two runs, same md5.
- Fixes found by looking: lidR's TIN leaves cells beyond the samples' hull empty whatever its
  `extrapolate` (a 50 x 50 test: 2,406 of 2,500 NA with `knnidw(3, 1, Inf)`), drawn white: filled by
  `terra::interpIDW()` on a 10x coarser grid. Water as the most common value missed a second lake
  (6.8 ha, flattened at 748.55 m): water is now any level patch of 1 ha or more. Shading the REM drew
  the bed surface's triangle edges as lines: shading now comes from the DEM (`shape =`).
- A SpatRaster `%in%` failed inside `terra::ifel()` (terra imported, not attached): on values instead.
