# dem_alignment_probe.R — where LidarBC's published DEM sits against its own ground returns (#30).
#
# Reads the window of the canopy figure (scripts/readme_chm.R) from the 2019 DEM tile, builds a
# 1 m TIN of the ground returns in the cached .laz (data/readme_laz/, written by readme_chm.R),
# and compares the two with the DEM moved by each half-cell. Prints the table in
# research/dem_alignment.md. From the repo root:
#
#     Rscript scripts/dem_alignment_probe.R

DEM <- "https://nrs.objectstore.gov.bc.ca/gdwuts/093/093l/2019/dem/bc_093l040_xli1m_utm09_2019.tif"
LAZ_DIR <- "data/readme_laz"
# The canopy figure's window, from Maxan Creek's mouth, with its margin (scripts/readme_chm.R).
MOUTH <- c(-126.1256, 54.3814)
BOX <- c(-730, -630, 530, 430)
# Land only: the published DEM flattens the lake to 712.54 m.
LAND_ABOVE <- 712.9

xy <- sf::st_coordinates(sf::st_transform(sf::st_sfc(sf::st_point(MOUTH), crs = 4326), 3156))
rb <- c(xy[1], xy[2], xy[1], xy[2]) + BOX
# The DEM's window, whole cells only.
win <- c(floor(rb[1]), floor(rb[2]), ceiling(rb[3]), ceiling(rb[4])) + 0.5
pub_file <- tempfile(fileext = ".tif")
sf::gdal_utils("translate", paste0("/vsicurl/", DEM), pub_file,
               c("-projwin", win[1], win[4], win[3], win[2]))
pub <- terra::rast(pub_file)
if (terra::ncell(pub) == 0L) stop("no DEM read from ", DEM, call. = FALSE)
cat("published origin as GDAL reads it:", terra::xmin(pub), terra::ymax(pub), "\n")

laz <- list.files(LAZ_DIR, pattern = "\\.laz$", full.names = TRUE)
if (length(laz) == 0L) stop("no .laz in ", LAZ_DIR, ": run scripts/readme_chm.R first", call. = FALSE)
las <- lidR::readLAS(laz, select = "xyzc",
                     filter = paste("-keep_class 2 -drop_withheld -keep_xy", paste(rb, collapse = " ")))
# Cells with whole-metre edges, 3 m inside the read, so the TIN has no edge in them.
e <- terra::ext(ceiling(rb[1]) + 3, floor(rb[3]) - 3, ceiling(rb[2]) + 3, floor(rb[4]) - 3)
tin <- lidR::rasterize_terrain(las, terra::rast(e, resolution = 1, crs = terra::crs(pub)), lidR::tin())
terra::crs(tin) <- terra::crs(pub)
land <- terra::values(tin, mat = FALSE) > LAND_ABOVE

cat("shift_x shift_y median_abs_m p95_abs_m cells\n")
for (dx in c(-0.5, 0.5)) for (dy in c(-0.5, 0.5)) {
  # Moved by half a cell, the DEM's cells land on the TIN's: "near" only picks them up.
  p <- terra::resample(terra::shift(pub, dx, dy), tin, method = "near")
  v <- abs(terra::values(tin, mat = FALSE) - terra::values(p, mat = FALSE))[land %in% TRUE]
  v <- v[!is.na(v)]
  cat(sprintf("%+.1f %+.1f %.3f %.3f %d\n", dx, dy, stats::median(v),
              stats::quantile(v, 0.95, names = FALSE), length(v)))
}
