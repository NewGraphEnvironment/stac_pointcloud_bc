S <- commandArgs(TRUE)[1]; source(file.path(S, "..", "p30_draw.R"))
dem <- terra::rast(file.path(S, "dem05_tin.tif")); terra::crs(dem) <- "EPSG:3156"
water <- terra::rast(file.path(S, "water05.tif")); terra::crs(water) <- "EPSG:3156"
land <- terra::mask(dem, water, maskvalues = 1)
# A: the lowest ground within ~100 m, from a 5 m grid, smoothed.
a5 <- terra::aggregate(land, 10, fun = "min", na.rm = TRUE)
lo <- terra::focal(a5, w = 41, fun = "min", na.rm = TRUE)
lo <- terra::focal(lo, w = 21, fun = "mean", na.rm = TRUE)
baseA <- terra::resample(lo, dem, method = "bilinear")
remA <- dem - baseA
# B: the creek bed sampled along the FWA line plus the lake surface, interpolated (IDW).
pr <- readRDS(file.path(S, "creekbed.rds"))
lk <- terra::as.points(terra::aggregate(water, 20, fun = "max"))
lk <- lk[lk[[1]][[1]] == 1, ]
lxy <- terra::crds(lk)
p <- terra::vect(rbind(cbind(pr$x, pr$y), lxy), crs = "EPSG:3156")
p$z <- c(pr$z, rep(712.72, nrow(lxy)))
r5 <- terra::aggregate(dem, 10)
baseB <- terra::interpIDW(r5, p, "z", radius = 2000, power = 2, maxPoints = 12)
baseB <- terra::resample(baseB, dem, method = "bilinear")
remB <- dem - baseB
for (nm in c("A", "B")) {
  rem <- get(paste0("rem", nm)); rl <- terra::mask(rem, water, maskvalues = 1)
  q <- terra::global(rl, quantile, probs = c(.01, .05, .25, .5, .75, .9, .95), na.rm = TRUE)
  cat(nm, round(unlist(q), 2), "\n")
  fp <- terra::mask(rl, rl > 4, maskvalues = 1)
  qf <- unlist(terra::global(fp, quantile, probs = c(.02, .98), na.rm = TRUE))
  cat(nm, "floodplain (<4 m) p2/p98", round(qf, 2), "\n")
  terra::writeRaster(rem, file.path(S, paste0("rem", nm, ".tif")), overwrite = TRUE)
  save_rgb(blend(rem, qf[1], qf[2], viridisLite::turbo, dem = dem, water = water), file.path(S, paste0("rem", nm, "_turbo.png")))
}
