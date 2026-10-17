# Water cells as pc_readme_chm() defines them (no ground return within 5 m), and their returns' z.
source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]
bx <- readRDS(file.path(S, "box.rds")); box <- bx$box; rb <- bx$rb
laz <- list.files("data/readme_laz", pattern = "laz$", full.names = TRUE)
las <- lidR::readLAS(laz, select = "xyzrc", filter = paste("-drop_withheld -keep_xy", paste(rb, collapse = " ")))
b <- box + 2 * 0.5 * c(-1, -1, 1, 1)
grid <- terra::rast(terra::ext(b[1], b[3], b[2], b[4]), resolution = 0.5, crs = "EPSG:3156")
g <- las$Classification == 2L
n <- tabulate(terra::cellFromXY(grid, cbind(las$X[g], las$Y[g])), terra::ncell(grid))
near <- terra::focal(terra::setValues(grid, n), w = 21, fun = "sum", na.rm = TRUE)
water <- near == 0
keep <- !las$Classification %in% NOISE_CLASSES & !g
cell <- terra::cellFromXY(grid, cbind(las$X[keep], las$Y[keep]))
wv <- terra::values(water, mat = FALSE)
sel <- !is.na(cell) & wv[cell] %in% TRUE
z <- tapply(las$Z[keep][sel], cell[sel], stats::median)
wz <- terra::setValues(grid, NA_real_); wz[as.integer(names(z))] <- as.numeric(z)
terra::writeRaster(water, file.path(S, "water05.tif"), overwrite = TRUE)
terra::writeRaster(wz, file.path(S, "waterz05.tif"), overwrite = TRUE)
cat("water cells", sum(wv, na.rm = TRUE), "with returns", length(z), "\n")
print(round(quantile(z, c(0, .01, .05, .5, .95, .99, 1)), 2))
