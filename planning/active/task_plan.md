# Task: Draw the canopy height figure over the delta's ground, so its old channels show (#30)

## Problem

The landing page's canopy height figure (`fig/maxan_chm.png`, #19) shows the Maxan Creek delta as trees on a flat 0 m meadow. The ground under it is not flat: a quick draft of the ground returns from the same two 2019 tiles shows a looped low in the northwest that looks like an old meander, narrow channels under the forest on the south edge, and faint threads between the stands on the delta. The figure could show the forest *and* the old channels it grows among, which is what a floodplain reader comes for.

The draft (ground hillshade, ground below its ~100 m median in blues clamped at −1.5 m, canopy 2 m and up on top) came out washed out, for reasons in how it was drawn, not in the data:

- Only the low ground was coloured, over a grey hillshade, under a 60%-opaque canopy layer, so every colour was diluted twice.
- The elevations' 1st–99th percentiles span 712.7–743.4 m, but the floodplain sits within about a metre of its median (713.7 m); the south slope takes most of any min–max stretch.
- The lake has no ground returns, so the triangulation fills it with flat grey and fans of artifacts.

A turbo-type ramp stretched over the floodplain's own range is known to bring these channels out in QGIS on the overlapping LidarBC DEM.

## Phase 1: Measure the ground (explore, scratch only)
- [ ] One background run of a probe script (scratchpad, not committed) over the cached `.laz`:
      write the CHM, a 1 m ground TIN aligned to the published DEM's cells, the water mask, and the
      water cells' returns to scratch `.tif`/`.rds`, so every later draw takes seconds, not 40 min
- [ ] Read the published DEM's window (`gdal_translate -projwin` over `/vsicurl/`; assert the cell
      count; download whole if the strip read misbehaves); difference it with our TIN over land
      cells: median, p1/p99, and where they differ
- [ ] Draw both, same stretch and hillshade, and say which shows the channels better
- [ ] Record numbers and the DEM verdict in `findings.md`. Default: our TIN, unless the published
      one is clearly better (it keeps the page's "products from the points" point and adds no STAC read)

## Phase 2: Choose the surface, stretch and blend (scratch renders)
- [ ] Elevation stretched to the floodplain's percentiles vs an REM: DEM minus a water surface
      interpolated from the water cells' returns; report the water surface's fall across the delta,
      which says whether the REM is needed
- [ ] Define "the floodplain" for the stretch from measurement (e.g. cells within N m of the water
      surface) and record its percentiles
- [ ] Ramp (blues vs turbo) stretched to those percentiles; hillshade multiplied into the colour,
      not laid under a transparent layer; lake/channel masked with the existing water mask
- [ ] Canopy treatment that leaves the ground legible, including under the south forest (opaque
      ≥ 2 m, a tint multiplied in, or two panels); judge each at the README's rendered width
- [ ] Record the choice and why in `findings.md`; one figure replaces `fig/maxan_chm.png` (the issue's
      "or a second figure" kept as fallback only if one panel cannot carry both)

## Phase 3: Build it (tests first)
- [ ] Failing tests in `tests/readme_functions_test.R` on synthetic LAS for each new helper
      (ground DEM on the CHM's grid; water surface / REM if chosen; the stretch-and-multiply blend:
      percentile clamp, NA water stays the water colour, hillshade darkens, canopy layer placement)
- [ ] Implement the helpers in `scripts/readme_functions.R`, inside a landing-page marker where the
      page shows them; restore-the-bug check that each test goes red
- [ ] `scripts/readme_chm.R`: build the ground surface from the same `las`, rewrite `plot_chm()`,
      add to `data/readme_chm.json` every number the caption will quote (stretch limits, floodplain
      definition, DEM source, water-surface fall, DEM difference if quoted)

## Phase 4: The page
- [ ] README.Rmd: caption, alt text and "How it was made" describe what is shown (straight lows
      that may be ditches or a road are not called channels); code excerpts updated
- [ ] Re-render README.md then index.html (`update_query = TRUE`, background, `PYTHONUNBUFFERED=1`);
      check the PNG at page width and that both outputs embed the new figure

## Validation
- [ ] `Rscript -e 'testthat::test_file("tests/readme_functions_test.R")'` and `uv run pytest` pass
- [ ] `/code-check` clean (once over the branch)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion, then `/gh-pr-push`

