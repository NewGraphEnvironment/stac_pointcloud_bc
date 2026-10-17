S <- commandArgs(TRUE)[1]; source(file.path(S, "..", "p30_draw.R"))
s <- readRDS(file.path(S, "fwa.rds")); print(s[, c("GNIS_NAME", "EDGE_TYPE")])
dem <- terra::rast(file.path(S, "dem05_tin.tif")); terra::crs(dem) <- "EPSG:3156"
water <- terra::rast(file.path(S, "water05.tif")); terra::crs(water) <- "EPSG:3156"
mx <- sf::st_union(s[s$GNIS_NAME %in% "Maxan Creek" & s$EDGE_TYPE == 1000, ])
mx <- sf::st_intersection(mx, sf::st_as_sfc(sf::st_bbox(dem)))
pts <- sf::st_cast(sf::st_line_sample(sf::st_cast(mx, "LINESTRING"), density = 1/10), "POINT")
cat("sample points", length(pts), "\n")
# Creek bed: the lowest ground within 6 m of each point.
dmin <- terra::focal(dem, w = 25, fun = "min", na.rm = TRUE)
v <- terra::extract(dmin, terra::vect(pts))[[2]]
onw <- terra::extract(water, terra::vect(pts))[[2]]
xy <- sf::st_coordinates(pts)
pr <- data.frame(x = xy[,1], y = xy[,2], z = v, water = onw)
pr <- pr[!(pr$water %in% 1), ]
print(round(quantile(pr$z, c(0,.1,.5,.9,1), na.rm=TRUE), 2))
print(pr[order(pr$x)[c(1:5, seq(10, nrow(pr), 15))], ])
saveRDS(pr, file.path(S, "creekbed.rds"))
