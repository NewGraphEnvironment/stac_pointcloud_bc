# Scratch renderer for #30: colour(stretch(surface)) * hillshade, written as an RGB PNG.
shade <- function(dem, z = 1) {
  hs <- terra::shade(terra::terrain(dem * z, "slope", unit = "radians"),
                     terra::terrain(dem * z, "aspect", unit = "radians"), 35, 315)
  terra::clamp(hs, 0, 1)
}
blend <- function(surf, lo, hi, pal, dem = surf, water = NULL, k = 0.45, z = 1) {
  hs <- terra::values(shade(dem, z), mat = FALSE)
  hs[is.na(hs)] <- stats::median(hs, na.rm = TRUE)
  t <- pmin(pmax((terra::values(surf, mat = FALSE) - lo) / (hi - lo), 0), 1)
  i <- round(t * 255) + 1
  cols <- grDevices::col2rgb(pal(256)) / 255
  f <- pmin(k + (1 - k) * hs / stats::median(hs, na.rm = TRUE) * 0.8, 1.15)
  m <- t(cols[, i]) * f
  m <- pmin(pmax(m, 0), 1) * 255
  if (!is.null(water)) { w <- which(terra::values(water, mat = FALSE) %in% TRUE); m[w, ] <- matrix(c(199, 219, 240), length(w), 3, byrow = TRUE) }
  r <- terra::rast(surf, nlyrs = 3); terra::values(r) <- m; r
}
save_rgb <- function(rgb, path, w = 1350) {
  png(path, width = w, height = round(w * terra::nrow(rgb) / terra::ncol(rgb)), res = 150)
  on.exit(dev.off())
  terra::plotRGB(rgb, r = 1, g = 2, b = 3, scale = 255, mar = 0, axes = FALSE)
}
