S <- commandArgs(TRUE)[1]; source(file.path(S, "..", "p30_draw.R"))
chm_file <- if (length(commandArgs(TRUE)) > 1) commandArgs(TRUE)[2] else "chmq05.tif"
dem <- terra::rast(file.path(S, "dem05_tin.tif")); terra::crs(dem) <- "EPSG:3156"
water <- terra::rast(file.path(S, "water05.tif")); terra::crs(water) <- "EPSG:3156"
chm <- terra::rast(file.path(S, chm_file)); terra::crs(chm) <- "EPSG:3156"
chm <- terra::crop(chm, dem); dem <- terra::crop(dem, chm); water <- terra::crop(water, chm)
lake <- 712.72; lo <- lake; hi <- lake + 5
ramp <- function(v, lo, hi, pal) { t <- pmin(pmax((v - lo) / (hi - lo), 0), 1); t(grDevices::col2rgb(pal(256))[, round(t * 255) + 1]) / 255 }
hsv <- terra::values(shade(dem), mat = FALSE); hsv[is.na(hsv)] <- stats::median(hsv, na.rm = TRUE)
f <- pmin(0.45 + 0.55 * hsv / stats::median(hsv) * 0.8, 1.15)
z <- terra::values(dem, mat = FALSE); h <- terra::values(chm, mat = FALSE)
wv <- terra::values(water, mat = FALSE) %in% 1
tree <- !is.na(h) & h >= 2
draw <- function(gpal, cpal, name, cshade = 1) {
  m <- ramp(z, lo, hi, gpal)
  m[tree, ] <- ramp(h[tree], 2, 30, cpal)
  m <- m * ifelse(tree, 1 - cshade * (1 - f), f)
  m <- pmin(pmax(m, 0), 1) * 255
  m[wv, ] <- matrix(c(199, 219, 240), sum(wv), 3, byrow = TRUE)
  r <- terra::rast(dem, nlyrs = 3); terra::values(r) <- m
  save_rgb(r, file.path(S, paste0("cv_", name, ".png")))
}
greens <- \(n) grDevices::hcl.colors(n, "Greens 3", rev = TRUE)[round(seq(n * 0.25, n, length.out = n))]
draw(viridisLite::turbo, greens, "turbo_greens")
draw(viridisLite::plasma, greens, "plasma_greens")
draw(\(n) rev(grDevices::hcl.colors(n, "Blue-Yellow 2")), greens, "blueyellow_greens")
draw(\(n) grDevices::hcl.colors(n, "Lajolla", rev = FALSE), greens, "lajolla_greens")
# Translucent canopy: opacity grows with height, so shrubs tint the ground and tall trees cover it.
draw_mix <- function(gpal, cpal, name, a0 = 0.25, a1 = 0.9, h1 = 15) {
  m <- ramp(z, lo, hi, gpal)
  a <- ifelse(tree, pmin(pmax(a0 + (a1 - a0) * (h - 2) / (h1 - 2), a0), a1), 0)
  cm <- m; cm[tree, ] <- ramp(h[tree], 2, 30, cpal)
  m <- (m * (1 - a) + cm * a) * f
  m <- pmin(pmax(m, 0), 1) * 255
  m[wv, ] <- matrix(c(199, 219, 240), sum(wv), 3, byrow = TRUE)
  r <- terra::rast(dem, nlyrs = 3); terra::values(r) <- m
  save_rgb(r, file.path(S, paste0("cv_", name, ".png")))
}
draw_mix(viridisLite::plasma, greens, "mix_plasma")
draw_mix(viridisLite::turbo, \(n) grDevices::hcl.colors(n, "Grays")[1:n] , "mix_turbo_grey")
