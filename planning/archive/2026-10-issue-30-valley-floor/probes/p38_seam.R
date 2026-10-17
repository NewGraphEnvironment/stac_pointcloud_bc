source("scripts/readme_functions.R"); e <- new.env(); sys.source("scripts/readme_rem.R", envir = e)
REM_JSON <- tempfile(); e$REM_PNG <- tempfile(fileext = ".png")
o <- e$main()
R <- terra::as.matrix(o$rem, wide = TRUE); Z <- terra::as.matrix(o$dem, wide = TRUE); W <- terra::as.matrix(o$water, wide = TRUE) == 1
seam <- function(dr, dc) { nr <- nrow(R); nc <- ncol(R); a <- R[1:(nr - dr), 1:(nc - dc)]; b <- R[(1 + dr):nr, (1 + dc):nc]
  za <- Z[1:(nr - dr), 1:(nc - dc)]; zb <- Z[(1 + dr):nr, (1 + dc):nc]; wa <- W[1:(nr - dr), 1:(nc - dc)] | W[(1 + dr):nr, (1 + dc):nc]
  sum(abs(a - b) > 1.5 & abs(za - zb) < 0.3 & !wa & pmin(a, b) < 3, na.rm = TRUE) }
cat("seam pairs (rem jumps > 1.5 m where ground changes < 0.3 m):", seam(0, 1) + seam(1, 0), "\n")
