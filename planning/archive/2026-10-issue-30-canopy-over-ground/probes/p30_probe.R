# #30 Phase 1 probe: cache the slow products once. Run from the repo root.
source("scripts/readme_functions.R")
out <- commandArgs(TRUE)[1]
t0 <- Sys.time()
laz <- list.files("data/readme_laz", pattern = "laz$", full.names = TRUE)
crs <- "EPSG:3156"
xy <- sf::st_coordinates(sf::st_transform(sf::st_sfc(sf::st_point(c(-126.1256, 54.3814)), crs = 4326), crs))
box <- c(xy[1] - 700, xy[2] - 600, xy[1] + 500, xy[2] + 400)
rb <- box + 30 * c(-1, -1, 1, 1)
saveRDS(list(box = box, rb = rb), file.path(out, "box.rds"))
las <- lidR::readLAS(laz, select = "xyzrc", filter = paste("-drop_withheld -keep_xy", paste(rb, collapse = " ")))
cat("read", format(Sys.time() - t0), "\n")
# Ground DEM, 1 m, on cells aligned to the published DEM's (corners on .5 m).
snap <- function(v, f) f(v - 0.5) + 0.5
g <- lidR::filter_ground(las)
gb <- c(snap(rb[1] + 2, ceiling), snap(rb[2] + 2, ceiling), snap(rb[3] - 2, floor), snap(rb[4] - 2, floor))
grid1 <- terra::rast(terra::ext(gb[1], gb[3], gb[2], gb[4]), resolution = 1, crs = lidR::st_crs(las)$wkt)
dem1 <- lidR::rasterize_terrain(g, grid1, lidR::tin())
terra::writeRaster(dem1, file.path(out, "dem1_tin.tif"), overwrite = TRUE)
# Same at 0.5 m on the CHM's grid (exactly box, +2 cells), for the figure.
b <- box + 2 * 0.5 * c(-1, -1, 1, 1)
grid05 <- terra::rast(terra::ext(b[1], b[3], b[2], b[4]), resolution = 0.5, crs = lidR::st_crs(las)$wkt)
dem05 <- lidR::rasterize_terrain(g, grid05, lidR::tin())
terra::writeRaster(dem05, file.path(out, "dem05_tin.tif"), overwrite = TRUE)
# Median and min z of every non-noise return per 0.5 m cell: the water surface where there is no ground.
keep <- !las$Classification %in% NOISE_CLASSES
cell <- terra::cellFromXY(grid05, cbind(las$X[keep], las$Y[keep]))
ok <- !is.na(cell)
zmed <- tapply(las$Z[keep][ok], cell[ok], stats::median)
zr <- terra::setValues(grid05, NA_real_); zr[as.integer(names(zmed))] <- as.numeric(zmed)
terra::writeRaster(zr, file.path(out, "zmed05.tif"), overwrite = TRUE)
cat("dem", format(Sys.time() - t0), "\n")
rm(g)
chm <- pc_readme_chm(las, box, res = 0.5, ground_gap = 5)
terra::writeRaster(chm, file.path(out, "chm05.tif"), overwrite = TRUE)
cat("chm", format(Sys.time() - t0), "\nDONE\n")
