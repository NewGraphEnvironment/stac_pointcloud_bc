source("scripts/readme_functions.R"); e <- new.env(); sys.source("scripts/readme_rem.R", envir = e)
REM_JSON <- tempfile(); e$REM_PNG <- tempfile(fileext = ".png")
o <- e$main(); r <- terra::values(o$rem, mat = FALSE)
neg <- terra::ifel(o$water, NA, terra::ifel(o$rem < -1, 1, NA)); p <- terra::patches(neg, directions = 8)
f <- terra::freq(p); f <- f[order(-f$count), ]; b <- as.vector(terra::ext(o$rem)); pv <- terra::values(p, mat = FALSE)
cat("cells below -1:", sum(!is.na(pv)), " below -2:", sum(r < -2, na.rm = TRUE), "\n")
for (v in head(f$value, 6)) { k <- which(pv == v); cc <- terra::xyFromCell(p, k)
  cat(sprintf("patch: %.2f ha at %.0f,%.0f m from SW, min %.1f\n", length(k) * 16 / 1e4, mean(cc[,1]) - b[1], mean(cc[,2]) - b[3], min(r[k]))) }
