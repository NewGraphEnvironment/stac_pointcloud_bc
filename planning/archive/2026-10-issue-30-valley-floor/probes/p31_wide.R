# Overview of the published DEM around the Maxan delta, offset corrected, drawn like the figure.
source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]; agg <- as.numeric(commandArgs(TRUE)[2]); relief <- as.numeric(commandArgs(TRUE)[3])
d <- terra::shift(terra::rast(file.path(S, "dem_wide.tif")), 0.5, 0.5)
lake <- abs(d - 712.54) < 1e-4
chm <- terra::ifel(lake, NA, 0)
rgb <- pc_readme_relief(d, chm, level = 712.72, relief = relief)
if (agg > 1) rgb <- terra::aggregate(rgb, agg, mean, na.rm = TRUE)
out <- file.path(S, sprintf("wide_%gm_r%g.png", agg, relief))
pc_readme_relief_png(rgb, out, scale = agg, legend = list(relief = relief, tree = 2, top = 30), bar_m = 1000)
# The landing page window, drawn on top.
bx <- readRDS(file.path(S, "box.rds"))$box
cat("window in px:", (bx[c(1,3)] - terra::xmin(d)) / agg, (bx[c(2,4)] - terra::ymin(d)) / agg, "\n")
