source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]
bx <- readRDS(file.path(S, "box.rds")); box <- bx$box
img <- png::readPNG("fig/maxan_chm.png")[, 1:1200, 1:3]
lay <- readRDS(file.path(S, "bc_layers.rds"))
dist <- terra::rast(file.path(S, "ground_dist1.tif"))
px <- function(g) { xy <- sf::st_coordinates(g); cbind(xy[, 1] - box[1], xy[, 2] - box[2], xy[, ncol(xy)]) }
draw_lines <- function(g, col, lty = 1, lwd = 2) if (!is.null(g) && nrow(g)) {
  g <- sf::st_cast(sf::st_zm(sf::st_geometry(g)), "LINESTRING")
  for (i in seq_along(g)) { xy <- sf::st_coordinates(g[i]); lines(xy[, 1] - box[1], xy[, 2] - box[2], col = col, lty = lty, lwd = lwd) } }
png(file.path(S, "overlay.png"), width = 2400, height = 1000, res = 110)
par(mfrow = c(1, 2), mai = c(0, 0, 0.3, 0))
plot.new(); plot.window(c(0, 1200), c(0, 1000), asp = 1, xaxs = "i", yaxs = "i")
rasterImage(img, 0, 0, 1200, 1000, interpolate = FALSE)
draw_lines(lay$roads, "red"); draw_lines(lay$rail, "black", 2, 3)
title("figure + BC road atlas (red) + railway (black dashed)")
plot.new(); plot.window(c(0, 1200), c(0, 1000), asp = 1, xaxs = "i", yaxs = "i")
d <- terra::values(dist, mat = FALSE); m <- matrix(pmin(d, 10) / 10, terra::nrow(dist), byrow = TRUE)
rasterImage(as.raster(1 - m), 0, 0, 1200, 1000, interpolate = FALSE)
draw_lines(lay$roads, "red"); draw_lines(lay$rail, "black", 2, 3)
title("distance to the nearest ground return (white 0, black 10+ m)")
dev.off()
for (k in c("roads", "rail")) if (!is.null(lay[[k]])) print(sf::st_drop_geometry(lay[[k]])[, intersect(c("ROAD_NAME_FULL","ROAD_SURFACE","ROAD_CLASS","TRACK_NAME","OPERATOR_ENGLISH_NAME","USE_TYPE"), names(lay[[k]]))])
