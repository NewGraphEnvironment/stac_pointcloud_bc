S <- commandArgs(TRUE)[1]; source(file.path(S, "..", "p30_draw.R"))
pub <- terra::rast(file.path(S, "dem_pub.tif")); tin <- terra::rast(file.path(S, "dem1_tin.tif"))
cat("pub ext", as.vector(terra::ext(pub)), "\ntin ext", as.vector(terra::ext(tin)), "\n")
terra::crs(tin) <- terra::crs(pub); tin <- terra::crop(tin, pub); pub <- terra::crop(pub, tin)
stopifnot(terra::compareGeom(tin, pub))
d <- tin - pub
lake <- pub <= 712.55
land <- d; land[lake] <- NA
q <- function(r) round(terra::global(r, quantile, probs = c(.01, .05, .25, .5, .75, .95, .99), na.rm = TRUE), 3)
cat("land cells", terra::global(!is.na(land), "sum")[[1]], "\n"); print(q(land))
cat("abs>0.1m share on land", terra::global(abs(land) > 0.1, "mean", na.rm = TRUE)[[1]], "\n")
cat("abs>0.5m share on land", terra::global(abs(land) > 0.5, "mean", na.rm = TRUE)[[1]], "\n")
wl <- d; wl[!lake] <- NA; cat("over lake:\n"); print(q(wl))
saveRDS(list(land = q(land), lake = q(wl)), file.path(S, "diff.rds"))
png(file.path(S, "diff.png"), width = 1350, height = 1135, res = 150)
terra::plot(terra::clamp(d, -0.5, 0.5), col = hcl.colors(100, "RdBu"), axes = FALSE, mar = c(1, 1, 1, 5))
dev.off()
save_rgb(blend(tin, 712.6, 718, viridisLite::turbo, water = lake), file.path(S, "tin_turbo_718.png"))
