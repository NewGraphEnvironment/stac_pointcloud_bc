## Outcome

Part 2 of #30 (part 1: `../2026-10-issue-30-canopy-over-ground/`). An investigation outside the delta window answered the user's questions: the south forest's straight line is a rough road in BC's Digital Road Atlas (with a second along the forest's upper edge), the curved lows down that slope are gullies, the ground under that forest is real (ground returns dense), and the hayfield's lake edge is cleared to a straight line with a 0.3-0.5 m ridge at the water, no dike. The old channels were clearest upstream, so a second landing-page figure was added: the valley floor up Maxan Creek as height above the nearest stream bed (`fig/maxan_rem.png`, `scripts/readme_rem.R`), read from LidarBC's DEM of the same delivery through `stac-elevation-bc` (one window and a 500 m margin over HTTP), with Freshwater Atlas streams. The bed surface between streams at different heights was the hard part: a TIN over a buffer, capped at 1 m over the highest sample within about 150 m, in a window the user trimmed 900 m from the west to leave out Crow Creek's upper valley and Wiggins Lake, where no method tried held. The delta caption now names the roads and gullies.

## Measurement

- Visible seams (adjacent cells' height above the bed jumping > 1.5 m where the ground changes < 0.3 m, one side under 3 m), trimmed window: round 1's rule 445 pairs; plain TIN 0 but 1.2 ha at -5.3 m; capped TIN 3 (round 3 counted 1).
- Methods tried and dropped, with why, are in `findings.md`: nearest-sample REM (blotches), local-minimum REM (halos), IDW and plane fits, range clamps (Voronoi seams), lowest-bed-within-1-km (overshoot), HAND by D8 after a Planchon-Darboux fill (90.7% of land reaches a stream, but floodplains read 3 m+), a lake fringe (grew to 512k samples).
- Final figure: 3.1 x 2.3 km at 4 m, 0.69 MB; the script runs in about 40 s and reruns byte-identical. index.html 6.5 MB with both new figures.

Closed by: PR #31
