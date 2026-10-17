# Progress — Draw the canopy height figure over the delta's ground (#30)

## Session 2026-10-17

- Plan-mode exploration — phases approved by user ("go all phases to PR")
- Created branch `30-draw-the-canopy-height-figure-over-the-d` off main
- Scaffolded PWF baseline from issue #30 with approved phases
- Next: start Phase 1

- Phase 1 (09:53-10:05Z): probe cached CHM, 0.5 m and 1 m ground TINs, water mask in 12 min
  (not 42: the issue's figure included its own plotting). Published DEM window read in 12 s.
  Our TIN chosen; the published tile is the same TIN misplaced 0.5 m SW as GDAL reads it.
- Phase 2: three REMs tried and dropped (artifacts); elevation above the lake's surface, 0-5 m,
  plasma, canopy tinted by height, ground hillshade x4 multiplied through. Plan review folded in
  (`review-plan.md`): B2 (`maxcell` thinning) is why the drawing now goes through `rasterImage()`.
