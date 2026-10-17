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

## Below the bed (review p2 round 1, 2026-10-17)

The TIN bed between Crow Creek's upstream end (745 m) and Maxan Creek (728 m) ran over a hillside:
4.5% of land below the bed, to -8.9 m. Patches below -1 m (probe `p32_below.R`): 3.6 ha at -3.6 m
370 m from any mapped stream (a hollow on Maxan's floodplain), 0.6 ha at -9.0 m on the south edge
(nearest samples 640 m away, the artifact), and four of 0.2 ha or less.

| rule (bed above ground by > ABOVE, replaced by lowest sample within NEAR) | below bed | min | replaced |
|---|---|---|---|
| none | 4.5% | -8.94 m | 0 |
| ABOVE 0.5, NEAR 300 | 3.7% | -9.01 m | 1.7% (no sample within 300 m of the artifact) |
| ABOVE 0.5, NEAR 1000 | 2.9% | -0.5 m | 2.3%, but real floodplain hollows jumped to the lake's level: yellow patches inside the valley floors |
| **ABOVE 2, NEAR 1000** | 4.9% | -2.0 m | 0.5%; floors clean, the artifact corner yellow |

## Round 2's findings, and what ended the iteration (2026-10-17)

Round 2 (`review-p2-round2.md`) found round 1's rule (lowest sample within 1 km) overshot: about
1 km downstream on a falling valley, a 7 m step across flat floodplain; and the opposite error at
Wiggins Lake's level. Tried and dropped, each fixing one artifact and making another:
range clamp to the 5 nearest samples (76% of cells held, Voronoi seams across the field); a 1 m
slack on 10 nearest (30% held, the hillside artifact untouched); IDW of the nearest samples below
the ground plus whole-shore sampling (bottom-edge seam 2-3 m, Wiggins flat unchanged); HAND by
D8 flow after a Planchon-Darboux fill (90.7% of land reaches a stream, but floodplains read 3 m+,
measured to where their flow meets the channel far downstream); a 500 m buffer with a lake fringe
(the fringe grew to 512k samples). Patch of the window's west end causing both: Crow Creek's upper
valley and Wiggins Lake. User chose (2026-10-17) to trim the window 900 m from the west.

In the trimmed window (3.1 x 2.3 km), visible seams (adjacent cells whose height above the bed
jumps > 1.5 m where the ground changes < 0.3 m, one side under 3 m), probe `p38_seam.R`:

| bed | seams | deepest below bed |
|---|---|---|
| committed rule (lowest within 1 km) | 445 pairs | -2.0 m |
| plain TIN, 500 m buffer | 0 | -5.3 m (1.2 ha on Crow Creek's floor, the TIN pulled up by a plateau stream 300 m west) |
| **TIN, 500 m buffer, capped at 1 m over the highest sample within 150 m** | 3 | -3.3 m (scratch), -2.6 m as committed |

Dropping samples on stream reaches steeper than 2 degrees removed 273 samples and changed nothing.
