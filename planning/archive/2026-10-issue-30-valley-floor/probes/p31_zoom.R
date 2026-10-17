# Full-resolution (0.5 m) crops of the south forest strip and the NW block's lake edge, ground only
# (no canopy) beside the figure's drawing, with BC roads.
source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]
bx <- readRDS(file.path(S, "box.rds")); box <- bx$box
dem <- terra::rast(file.path(S, "dem05_tin.tif")); chm <- terra::rast(file.path(S, "chm05.tif"))
dem <- terra::crop(dem, terra::ext(box[1], box[3], box[2], box[4])); terra::crs(dem) <- terra::crs(chm)
lay <- readRDS(file.path(S, "bc_layers.rds"))
crop_png <- function(x0, y0, x1, y1, name, relief = 5, level = 712.72) {
  e <- terra::ext(box[1] + x0, box[1] + x1, box[2] + y0, box[2] + y1)
  d <- terra::crop(dem, e); h <- terra::crop(chm, e)
  bare <- pc_readme_relief(d, terra::ifel(is.na(h), NA, 0), level, relief = relief)
  can <- pc_readme_relief(d, h, level, relief = relief)
  png(file.path(S, paste0("zoom_", name, ".png")), width = 2 * terra::ncol(d) + 20, height = terra::nrow(d) + 40, res = 110)
  par(mfrow = c(1, 2), mai = c(0, 0.05, 0.35, 0.05))
  for (r in list(list(bare, "ground only"), list(can, "with canopy"))) {
    a <- terra::as.array(r[[1]]); a[is.na(a)] <- 255
    plot.new(); plot.window(c(x0, x1), c(y0, y1), asp = 1, xaxs = "i", yaxs = "i")
    rasterImage(as.raster(a, max = 255), x0, y0, x1, y1, interpolate = FALSE)
    if (nrow(lay$roads)) for (g in sf::st_geometry(sf::st_cast(lay$roads, "LINESTRING"))) { xy <- sf::st_coordinates(g); lines(xy[, 1] - box[1], xy[, 2] - box[2], col = "red", lwd = 1.5) }
    axis(1, line = -1.5, cex.axis = 0.7); title(paste(name, "-", r[[2]], "(m from window SW corner)"), cex.main = 0.9)
  }
  dev.off()
}
crop_png(0, 0, 700, 250, "south")
crop_png(250, 350, 600, 1000, "lakeedge")
# Profiles across the NW block's east (lake) edge, west to east, at three northings.
for (y in c(500, 700, 900)) {
  x <- seq(250, 520, by = 1)
  z <- terra::extract(dem, cbind(box[1] + x, box[2] + y))[[1]]
  cat(sprintf("y=%d: ", y), paste(sprintf("%d:%.2f", x[seq(1, length(x), 10)], z[seq(1, length(x), 10)]), collapse = " "), "\n")
}
