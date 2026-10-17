# Render with the shipping helpers from the cached rasters; args: out dir, tag, then name=value overrides.
source("scripts/readme_functions.R")
a <- commandArgs(TRUE); S <- a[1]; tag <- a[2]
args <- if (length(a) > 2) lapply(strsplit(a[-(1:2)], "="), \(kv) setNames(list(as.numeric(kv[2])), kv[1])) else list()
args <- do.call(c, args); if (!is.null(args$op)) { args$opacity <- c(args$op, 0.9); args$op <- NULL }
ground <- terra::rast(file.path(S, "dem05_tin.tif")); chm <- terra::rast(file.path(S, "chm05.tif"))
box <- readRDS(file.path(S, "box.rds"))$box
ground <- terra::crop(ground, terra::ext(box[1], box[3], box[2], box[4]))
terra::crs(ground) <- terra::crs(chm)
t0 <- Sys.time()
rgb <- do.call(pc_readme_relief, c(list(ground, chm, 712.72), args))
rgb1 <- terra::aggregate(rgb, 2, mean, na.rm = TRUE)
pc_readme_relief_png(rgb1, file.path(S, paste0("fig_", tag, ".png")), scale = 1,
                     legend = list(relief = if (is.null(args$relief)) 5 else args$relief, tree = 2, top = 30))
cat(tag, format(Sys.time() - t0), "\n")
