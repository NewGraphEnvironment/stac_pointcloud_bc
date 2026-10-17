# Height above the nearest stream bed, over the wide DEM window: FWA streams sampled every 10 m for
# the lowest ground within 6 m, spread to every cell from the nearest sample, smoothed.
source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]
d <- terra::shift(terra::rast(file.path(S, "dem_wide.tif")), 0.5, 0.5)
e <- terra::ext(682500, 689500, 6027000, 6031500)
d <- terra::crop(d, e)
d2 <- terra::aggregate(d, 2, mean, na.rm = TRUE)
lake <- abs(d2 - 712.54) < 0.01
aoi <- sf::st_transform(sf::st_as_sfc(sf::st_bbox(e, crs = sf::st_crs(3156))), 3005)
s <- bcdata::bcdc_query_geodata("WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP") |>
  bcdata::filter(bcdata::INTERSECTS(aoi)) |> bcdata::select(GNIS_NAME, EDGE_TYPE, STREAM_ORDER) |> bcdata::collect()
s <- sf::st_transform(s, 3156); print(table(s$GNIS_NAME, s$EDGE_TYPE, useNA = "ifany"))
main <- s[s$EDGE_TYPE %in% c(1000, 1050, 1100, 1150) & s$STREAM_ORDER >= 2, ]
pts <- sf::st_cast(sf::st_line_sample(sf::st_cast(sf::st_geometry(main), "LINESTRING"), density = 1 / 10), "POINT")
dmin <- terra::focal(d2, w = 7, fun = "min", na.rm = TRUE)
z <- terra::extract(dmin, terra::vect(pts))[[2]]
xy <- sf::st_coordinates(pts); ok <- !is.na(z)
cat("samples", sum(ok), "bed range", round(range(z[ok]), 2), "\n")
g10 <- terra::rast(e, resolution = 10, crs = "EPSG:3156")
pv <- terra::vect(cbind(xy[ok, 1], xy[ok, 2]), crs = "EPSG:3156"); pv$z <- z[ok]
base <- terra::interpNear(g10, pv, "z", radius = 5000)
base <- terra::focal(base, w = 15, fun = "mean", na.rm = TRUE)
base <- terra::resample(base, d2, method = "bilinear")
rem <- d2 - base
terra::writeRaster(rem, file.path(S, "rem_wide2.tif"), overwrite = TRUE)
saveRDS(main, file.path(S, "fwa_wide.rds"))
for (rel in c(3, 5)) {
  rgb <- pc_readme_relief(rem, terra::ifel(lake, NA, 0), 0, relief = rel)
  # hillshade from the DEM itself, not the REM: draw the REM colour over the DEM's shape
  rgbd <- pc_readme_relief(d2, terra::ifel(lake, NA, 0), 0, relief = 1e9)
  pc_readme_relief_png(terra::aggregate(rgb, 2, mean, na.rm = TRUE), file.path(S, sprintf("rem_wide_r%g.png", rel)), scale = 4,
                       legend = list(relief = rel, tree = 2, top = 30), bar_m = 1000)
}
