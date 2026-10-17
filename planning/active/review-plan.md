# Plan review (Plan agent, 2026-10-17)

Returned as reply text (Plan agents cannot write); summarised here with the disposition of each.

| id | finding | disposition |
|---|---|---|
| B1 | Phase 1's published-lattice grid and the CHM grid do not nest; a resample jags the water mask | Figure's DEM is built on the CHM's own grid (box + 2 cells, cropped); the published lattice is probe-only. Box not snapped, so #19's numbers do not move |
| B2 | `terra::plot()`/`plotRGB()` thin to `maxcell = 5e5`; the 4.8 M-cell CHM is drawn from ~1 cell in 3, aliasing thin channels | Adopted: composite at 0.5 m, averaged to 1 m, drawn 1 cell per device pixel with `maxcell = ncell` |
| G1 | Caption numbers from JSON, computed once, rounded; README fails loudly on a missing key | Adopted |
| G2 | Raw `shade()` dims flat ground by 43% | Adopted: normalised so flat = 1; exaggeration chosen and recorded |
| G3 | Shading a DEM with NA water darkens the banks | Already so in probe: shade the unmasked TIN, paint water after; test added |
| G4 | The water mask may not see the creek | Confirmed: the mask is one patch, the lake. REM fallback measured (findings) |
| G5 | TIN facets under sparse forest ground look like straight lows | Measure distance to ground; caption names only features on returns |
| G6 | Two legends drawn by hand | Adopted |
| G7 | turbo needs viridisLite | `grDevices::hcl.colors("Plasma")`, no new dependency |
| G8 | Colour collisions (green canopy vs turbo green; water vs blues) | Ground ramp with no green (plasma), canopy greens, water light blue |
| G9 | Markers: ground helper gets its own span; test every README marker resolves; stale text listed | Adopted |
| G10 | PixelIsPoint half-cell check; datum offset; hydro-flattening | Shift test run; hydro-flattening found (findings) |
| G11 | Tests: plane values at cell centres, stretch clamps, flat unchanged, layer order, PNG size | Adopted (snapping tests dropped with B1's choice) |
| O1 | Decide B1 before the long run | Done: no snap |
| O2 | Judge the code that ships | Helpers written and tested first, scratch only sets parameters |
| O3 | `update_query = TRUE` refreshes unrelated caches | Run `readme_chm.R` once, then both renders with `update_query = FALSE` |
| O4 | Provisional stretch for the DEM comparison | Noted |
| A1 | PNG bytes machine-dependent | Plot twice, compare md5; record |
| A2 | Deterministic percentiles | All cells, no sampling |
| A4 | REM may be unneeded | Measured: elevation stretch chosen |
| A5 | Page weight | Stated in PR |
| S1 | Published-DEM comparison stays probe-only, recorded in research/ | Adopted |
| AC1-5 | Legibility at ~880 px, pinned delivery, index.html embeds new PNG (md5), every caption number traces to JSON | Adopted into Validation |
