# Quick stand-in CHM for drawing experiments: max z per 0.5 m cell minus the ground TIN.
source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]
bx <- readRDS(file.path(S, "box.rds")); rb <- bx$rb
laz <- list.files("data/readme_laz", pattern = "laz$", full.names = TRUE)
las <- lidR::readLAS(laz, select = "xyzc", filter = paste("-drop_withheld -keep_xy", paste(rb, collapse = " ")))
dem <- terra::rast(file.path(S, "dem05_tin.tif")); terra::crs(dem) <- "EPSG:3156"
keep <- !las$Classification %in% NOISE_CLASSES
cell <- terra::cellFromXY(dem, cbind(las$X[keep], las$Y[keep])); ok <- !is.na(cell)
zx <- tapply(las$Z[keep][ok], cell[ok], max)
dsm <- terra::setValues(dem, NA_real_); dsm[as.integer(names(zx))] <- as.numeric(zx)
chm <- terra::clamp(dsm - dem, lower = 0, values = TRUE)
water <- terra::rast(file.path(S, "water05.tif")); terra::crs(water) <- "EPSG:3156"
chm <- terra::mask(chm, water, maskvalues = 1)
terra::writeRaster(chm, file.path(S, "chmq05.tif"), overwrite = TRUE)
