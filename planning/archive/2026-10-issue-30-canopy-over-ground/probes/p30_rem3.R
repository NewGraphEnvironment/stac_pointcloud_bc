S <- commandArgs(TRUE)[1]; source(file.path(S, "..", "p30_draw.R"))
dem <- terra::rast(file.path(S, "dem05_tin.tif")); terra::crs(dem) <- "EPSG:3156"
water <- terra::rast(file.path(S, "water05.tif")); terra::crs(water) <- "EPSG:3156"
pr <- readRDS(file.path(S, "creekbed.rds"))
fit <- lm(z ~ x + y, data = pr); print(summary(fit)$coef); cat("resid sd", sd(resid(fit)), "\n")
xy <- terra::xyFromCell(dem, seq_len(terra::ncell(dem)))
base <- terra::setValues(dem, pmax(predict(fit, data.frame(x = xy[,1], y = xy[,2])), 712.72))
rem <- dem - base
rl <- terra::mask(rem, water, maskvalues = 1)
fp <- terra::mask(rl, rl > 4, maskvalues = 1)
qf <- unlist(terra::global(fp, quantile, probs = c(.02, .98), na.rm = TRUE)); cat("C p2/p98", round(qf, 2), "\n")
terra::writeRaster(rem, file.path(S, "remC.tif"), overwrite = TRUE)
save_rgb(blend(rem, qf[1], qf[2], viridisLite::turbo, dem = dem, water = water), file.path(S, "remC_turbo.png"))
