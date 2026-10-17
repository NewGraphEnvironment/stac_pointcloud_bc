# Profiles across Maxan Creek's north-running reach, west to east, from the 1 m DEM (offset corrected).
S <- commandArgs(TRUE)[1]
d <- terra::shift(terra::rast(file.path(S, "dem_wide.tif")), 0.5, 0.5)
st <- readRDS(file.path(S, "hand_streams.rds"))
mx <- sf::st_union(st[st$GNIS_NAME %in% "Maxan Creek", ])
for (y in seq(6028850, 6029450, by = 100)) {
  # where the FWA line crosses this northing
  ln <- sf::st_sfc(sf::st_linestring(cbind(c(685000, 687000), c(y, y))), crs = sf::st_crs(st))
  xc <- sf::st_coordinates(sf::st_intersection(mx, ln))[, 1]
  if (!length(xc)) next
  x <- seq(min(xc) - 60, min(xc) + 120, by = 4)
  z <- terra::extract(d, cbind(x, y))[[1]]
  cat(sprintf("N %d (FWA at E %.0f): ", y, min(xc)), paste(sprintf("%+d:%.1f", round(x - min(xc)), z), collapse = " "), "\n")
}
