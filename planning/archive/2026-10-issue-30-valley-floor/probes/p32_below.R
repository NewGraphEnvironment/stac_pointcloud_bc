# Where height above the stream bed is negative, and why.
source("scripts/readme_functions.R")
sys.source("scripts/readme_rem.R", envir = e <- new.env())
for (n in ls(e)) assign(n, get(n, e))
main_dbg <- main
body(main_dbg) <- parse(text = sub("jsonlite::write_json\\(out, REM_JSON.*\\)", "assign('dbg', list(dem = dem, rem = rem, bed = bed, water = water, box = box), envir = .GlobalEnv)", paste(deparse(body(main)), collapse = "\n")))[[1]]
REM_PNG <- tempfile(fileext = ".png")
main_dbg()
r <- dbg$rem; w <- dbg$water
neg <- terra::ifel(w, NA, terra::ifel(r < -1, 1, NA))
p <- terra::patches(neg, directions = 8); f <- terra::freq(p); f <- f[order(-f$count), ]
for (v in head(f$value, 6)) {
  cc <- terra::xyFromCell(p, which(terra::values(p, mat = FALSE) == v))
  cr <- terra::values(r, mat = FALSE)[which(terra::values(p, mat = FALSE) == v)]
  ctr <- colMeans(cc); d <- sqrt((dbg$bed$x - ctr[1])^2 + (dbg$bed$y - ctr[2])^2)
  near5 <- order(d)[1:5]
  cat(sprintf("patch %d: %.1f ha, centre %.0f,%.0f m from SW, min rem %.1f, ground %.1f; nearest beds %s at %s m\n",
      v, nrow(cc) * 16 / 1e4, ctr[1] - dbg$box[1], ctr[2] - dbg$box[2], min(cr),
      mean(terra::extract(dbg$dem, rbind(ctr))[[1]]),
      paste(round(dbg$bed$z[near5], 1), collapse = "/"), paste(round(d[near5]), collapse = "/")))
}
