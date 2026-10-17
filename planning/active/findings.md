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
