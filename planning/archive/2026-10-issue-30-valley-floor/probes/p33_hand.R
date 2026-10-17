# HAND prototype: follow D8 flow down to a stream or lake cell; height above that cell's bed.
source("scripts/readme_functions.R")
e <- new.env(); sys.source("scripts/readme_rem.R", envir = e); for (n in ls(e)) assign(n, get(n, e))
REM_PNG <- tempfile(fileext = ".png"); REM_JSON <- tempfile(fileext = ".json")
S <- commandArgs(TRUE)[1]
if (!file.exists(file.path(S, "hand_in.rds"))) {
  dbg <- main()
  aoi <- sf::st_transform(sf::st_as_sfc(sf::st_bbox(dbg$dem)), 3005)
  st <- bcdata::bcdc_query_geodata("WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP") |> bcdata::filter(bcdata::INTERSECTS(aoi)) |>
    bcdata::select(GNIS_NAME, STREAM_ORDER) |> bcdata::collect() |> sf::st_transform(terra::crs(dbg$dem))
  terra::writeRaster(dbg$dem, file.path(S, "hand_dem.tif"), overwrite = TRUE)
  terra::writeRaster(dbg$water, file.path(S, "hand_water.tif"), overwrite = TRUE)
  saveRDS(st, file.path(S, "hand_streams.rds")); saveRDS(TRUE, file.path(S, "hand_in.rds"))
}
dem <- terra::rast(file.path(S, "hand_dem.tif")); water <- terra::rast(file.path(S, "hand_water.tif")) == 1
suppressPackageStartupMessages(library(sf)); st <- readRDS(file.path(S, "hand_streams.rds")); st <- st[st$STREAM_ORDER >= 2, ]
t0 <- Sys.time()
nc <- terra::ncol(dem); nr <- terra::nrow(dem); n <- nc * nr
z <- terra::values(dem, mat = FALSE)
line <- !is.na(terra::values(terra::rasterize(terra::vect(st), dem, touches = TRUE), mat = FALSE))
wet <- terra::values(water, mat = FALSE) %in% TRUE
circle <- terra::focalMat(dem, 15, "circle"); circle[circle > 0] <- 1; circle[circle == 0] <- NA
low <- terra::values(terra::focal(dem, w = circle, fun = "min", na.rm = TRUE), mat = FALSE)
sink <- line | wet
drain <- ifelse(wet, z, low)
# Planchon-Darboux fill: water level W falls from +Inf to max(z, lowest neighbour + eps),
# held at z on streams, lakes and the window's edge, so every cell drains to one of them.
Z <- matrix(z, nr, nc, byrow = TRUE); SK <- matrix(sink, nr, nc, byrow = TRUE)
edge <- row(Z) %in% c(1, nr) | col(Z) %in% c(1, nc)
W <- ifelse(SK | edge, Z, Inf); eps <- 1e-3
shift <- function(M, a, b) { out <- matrix(Inf, nr, nc)
  rs <- max(1, 1 + a):min(nr, nr + a); cs <- max(1, 1 + b):min(nc, nc + b)
  out[rs, cs] <- M[rs - a, cs - b]; out }
for (k in 1:5000) {
  mn <- pmin(shift(W,1,0), shift(W,-1,0), shift(W,0,1), shift(W,0,-1), shift(W,1,1), shift(W,1,-1), shift(W,-1,1), shift(W,-1,-1))
  W2 <- ifelse(SK | edge, Z, pmax(Z, pmin(W, mn + eps)))
  if (isTRUE(all(W2 == W))) break
  W <- W2
}
cat("fill iterations", k, " max fill", round(max(W - Z), 2), " share filled >1cm", round(mean(W - Z > 0.01), 3), "\n")
filled <- terra::setValues(dem, as.vector(t(W)))
fd <- terra::values(terra::terrain(filled, "flowdir"), mat = FALSE)
# ESRI D8 codes to row/col steps.
code <- c(1, 2, 4, 8, 16, 32, 64, 128); dr <- c(0, 1, 1, 1, 0, -1, -1, -1); dc <- c(1, 1, 0, -1, -1, -1, 0, 1)
i <- seq_len(n); r0 <- (i - 1) %/% nc + 1; c0 <- (i - 1) %% nc + 1
m <- match(fd, code)
r1 <- r0 + dr[m]; c1 <- c0 + dc[m]
nxt <- ifelse(is.na(m) | r1 < 1 | r1 > nr | c1 < 1 | c1 > nc, i, (r1 - 1) * nc + c1)
nxt[sink] <- i[sink]
for (it in 1:40) { n2 <- nxt[nxt]; if (identical(n2, nxt)) break; nxt <- n2 }
reach <- sink[nxt]
cat("ends: stream/lake", round(mean(sink[nxt][!wet]), 3), " edge", round(mean(!sink[nxt][!wet]), 3), "\n")
hand <- ifelse(reach, z - drain[nxt], NA)
land <- !wet
cat(sprintf("iterations %d; land reaching a stream or lake %.1f%%; %s\n", it, 100 * mean(reach[land]), format(Sys.time() - t0)))
cat("hand quantiles on land:", round(quantile(hand[land], c(.01, .05, .25, .5, .75, .95), na.rm = TRUE), 2), "\n")
saveRDS(list(hand = hand, reach = reach), file.path(S, "hand_out.rds"))
h <- terra::setValues(dem, hand)
# Draw: unreached cells grey-ish via NA -> treated as land with ground NA (blank).
rgb <- pc_readme_relief(h, terra::ifel(water, NA, 0), 0, relief = 3, shape = dem)
pc_readme_relief_png(rgb, file.path(S, "hand.png"), scale = 4, legend = list(relief = 3), bar_m = 1000, ground_label = "HAND (m)")
