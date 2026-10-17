# Tests for scripts/readme_functions.R, the R side of the landing page (#9).
#
#   Rscript -e 'testthat::test_file("tests/readme_functions_test.R")'
#
# The fixtures are the first 375 bytes of three real files. The expected values are what
# laspy read from the same files at build time (data/build/headers.jsonl and
# copc_headers.jsonl), so the R parser is checked against an independent reader.

source(file.path(testthat::test_path(".."), "scripts", "readme_functions.R"))

fixture <- function(name) {
  path <- file.path(testthat::test_path("fixtures"), paste0("header_", name, ".bin"))
  readBin(path, "raw", n = file.size(path))
}

test_that("a LAS 1.2 LAZ header reads as laspy read it", {
  # bc_092g005_1_2_2_xyes_8_utm10_20170714.laz (092g/2016)
  h <- pc_readme_header_parse(fixture("las12_laz"))
  expect_identical(h$las_version, "1.2")
  expect_identical(h$point_format, 1L)
  expect_identical(h$point_count, 3957849)
  expect_equal(h$mins, c(490856.09, 5427462.71, -2.23), tolerance = 1e-9)
  expect_equal(h$maxs, c(492686.14, 5428853.82, 22.06), tolerance = 1e-9)
})

test_that("a COPC header reads its 64-bit point count, not the empty legacy field", {
  # bc_092g005_1_2_2_xyes_8_utm10_20170714.copc.laz, CanElevation Lower_Mainland_2016:
  # LAS 1.4 point format 6, whose legacy count is zero.
  h <- pc_readme_header_parse(fixture("las14_copc"))
  expect_identical(h$las_version, "1.4")
  expect_identical(h$point_format, 6L)
  expect_identical(h$point_count, 3957849)
  expect_equal(h$mins, c(490856.091, 5427462.71, -2.23), tolerance = 1e-9)
  expect_equal(h$maxs, c(492686.14, 5428853.819, 22.06), tolerance = 1e-9)
})

test_that("a LAS 1.4 LAZ in a legacy point format reads as laspy read it", {
  # bc_082e003_1_4_1_xyes_12_utm11_2018.laz (082e/2018)
  h <- pc_readme_header_parse(fixture("las14_laz"))
  expect_identical(h$las_version, "1.4")
  expect_identical(h$point_format, 1L)
  expect_identical(h$point_count, 68821342)
  expect_equal(h$mins, c(313588.24, 5433307.36, 751.04), tolerance = 1e-9)
  expect_equal(h$maxs, c(315461.72, 5434757.25, 1248.91), tolerance = 1e-9)
})

test_that("a u32 above 2^31 and a u64 above 2^32 read unsigned", {
  raw <- as.raw(c(0x00, 0x00, 0x00, 0x80, 0x01, 0x00, 0x00, 0x00))
  expect_identical(las_u32(raw, 0L), 2^31)
  expect_identical(las_u64(raw, 0L), 2^31 + 2^32)
})

test_that("anything that is not a LAS header is refused", {
  expect_error(pc_readme_header_parse(charToRaw("<html>not a point cloud</html>")),
               "no LASF signature")
  expect_error(pc_readme_header_parse(fixture("las14_copc")[1:300]), "needs 375 bytes")
})

test_that("a header read is checked against its item's count and box", {
  item <- function(count, bbox) {
    list(id = "092-092g-2016-pointcloud-bc_092g005_1_2_2_xyes_8_utm10_20170714",
         properties = list(`pc:count` = count, `proj:bbox` = as.list(bbox)))
  }
  bbox <- c(490856.09, 5427462.71, 492686.14, 5428853.82)
  # The LAZ matches its item exactly; the COPC is 1 mm off, inside the build's 0.05 m.
  expect_lt(pc_readme_header_check(pc_readme_header_parse(fixture("las12_laz")),
                                   item(3957849L, bbox)), 1e-6)
  expect_equal(pc_readme_header_check(pc_readme_header_parse(fixture("las14_copc")),
                                      item(3957849L, bbox)), 0.001, tolerance = 1e-6)
  h <- pc_readme_header_parse(fixture("las12_laz"))
  expect_error(pc_readme_header_check(h, item(3957848L, bbox)), "disagrees")
  expect_error(pc_readme_header_check(h, item(3957849L, bbox + c(0, 0, 0.06, 0))),
               "disagrees")
  expect_error(pc_readme_header_check(h, item(3957849L, c(bbox, 0, 1))), "not 2D")
})

# ---- the canopy height model (#19) --------------------------------------------------------

# A 20 m square on a ground plane rising 0.5 m per metre east, sampled every 0.25 m; a 3 m
# square of class 1 returns standing 20 m above it; one class 7 (noise) return 80 m up.
synthetic_las <- function() {
  g <- expand.grid(X = seq(0.125, 19.875, by = 0.25), Y = seq(0.125, 19.875, by = 0.25))
  ground <- data.frame(g, Z = 100 + 0.5 * g$X, Classification = 2L)
  t <- expand.grid(X = seq(4.1, 6.9, by = 0.2), Y = seq(14.1, 16.9, by = 0.2))
  tree <- data.frame(t, Z = 100 + 0.5 * t$X + 20, Classification = 1L)
  noise <- data.frame(X = 15.5, Y = 5.5, Z = 100 + 0.5 * 15.5 + 80, Classification = 7L)
  d <- rbind(ground, tree, noise)
  d$ReturnNumber <- 1L
  d$NumberOfReturns <- 1L
  d$Withheld_flag <- FALSE
  las <- suppressMessages(lidR::LAS(data.table::as.data.table(d)))
  lidR::st_crs(las) <- 3156
  las
}

test_that("the CHM is height above ground, open ground reads 0, and noise is dropped", {
  box <- c(2, 2, 18, 18)
  chm <- pc_readme_chm(synthetic_las(), box, res = 1)
  expect_equal(as.vector(terra::ext(chm)), c(xmin = 2, xmax = 18, ymin = 2, ymax = 18))
  expect_equal(terra::res(chm), c(1, 1))
  at <- function(x, y) terra::extract(chm, cbind(x, y))[[1]]
  expect_equal(at(5.5, 15.5), 20, tolerance = 0.01)  # the tree, above a sloping ground
  expect_equal(at(12.5, 12.5), 0)                    # open ground: 0, not NA
  expect_equal(at(15.5, 5.5), 0)                     # where the noise return was
  expect_lt(max(terra::values(chm), na.rm = TRUE), 20.1)
  expect_false(anyNA(terra::values(chm)))
})

test_that("a gap with no returns stays NA rather than being bridged", {
  las <- synthetic_las()
  gap <- las@data$X > 11 & las@data$X < 16 & las@data$Y > 9 & las@data$Y < 14
  las <- lidR::filter_poi(las, !gap)
  chm <- pc_readme_chm(las, c(2, 2, 18, 18), res = 1)
  expect_true(is.na(terra::extract(chm, cbind(13.5, 11.5))[[1]]))
  expect_equal(terra::extract(chm, cbind(8.5, 8.5))[[1]], 0)
})

test_that("water, unclassified returns with no ground near them, is NA rather than 0 m", {
  las <- synthetic_las()
  d <- las@data
  lake <- d$X > 8 & d$X < 17.9 & d$Y > 6 & d$Y < 13.9
  # Its surface returns are class 1 at the height the ground TIN gives across it.
  d$Classification[lake & d$Classification == 2L] <- 1L
  las <- suppressMessages(lidR::LAS(d, crs = lidR::st_crs(las)))
  chm <- pc_readme_chm(las, c(2, 2, 18, 18), res = 1, ground_gap = 3)
  # The nearest ground cells are 4 or more cells away: water.
  expect_true(is.na(terra::extract(chm, cbind(13.5, 10.5))[[1]]))
  # Ground in the cell 3 m east (x 18-19) is within the gap: not water.
  expect_equal(terra::extract(chm, cbind(15.5, 10.5))[[1]], 0)
  expect_equal(terra::extract(chm, cbind(4.5, 4.5))[[1]], 0)  # open ground beside it
  expect_equal(terra::extract(chm, cbind(5.5, 15.5))[[1]], 20, tolerance = 0.01)
})

test_that("withheld returns are dropped like noise", {
  las <- synthetic_las()
  las@data$Withheld_flag[las@data$Classification == 7L] <- TRUE
  las@data$Classification[las@data$Classification == 7L] <- 1L
  chm <- pc_readme_chm(las, c(2, 2, 18, 18), res = 1)
  expect_lt(max(terra::values(chm), na.rm = TRUE), 20.1)
})

# ---- the ground under the canopy (#30) ----------------------------------------------------

test_that("the ground is the plane under the trees, on the CHM's grid, cell for cell", {
  las <- synthetic_las()
  box <- c(2.3, 2.1, 17.3, 17.1)  # an origin off the 0.5 m lattice, as the real window's is
  ground <- pc_readme_ground(las, box, res = 0.5)
  chm <- pc_readme_chm(las, box, res = 0.5)
  expect_true(terra::compareGeom(ground, chm, crs = FALSE))
  # At each cell centre, the plane Z = 100 + 0.5 X: a half-cell shift would be 0.125 m off.
  xy <- terra::xyFromCell(ground, seq_len(terra::ncell(ground)))
  expect_lt(max(abs(terra::values(ground, mat = FALSE) - (100 + 0.5 * xy[, 1]))), 0.01)
  # Under the tree, the ground, not the crown.
  expect_equal(terra::extract(ground, cbind(5.55, 15.55))[[1]], 100 + 0.5 * 5.55, tolerance = 0.01)
})

test_that("the water level is the median of the returns in the cells the CHM calls water", {
  las <- synthetic_las()
  d <- las@data
  lake <- d$X > 8 & d$X < 17.9 & d$Y > 6 & d$Y < 13.9
  d$Classification[lake & d$Classification == 2L] <- 1L
  d$Z[lake] <- 104
  # A few crowns over the water, which the median ignores.
  crown <- which(lake)[1:20]
  d$Z[crown] <- 125
  las <- suppressMessages(lidR::LAS(d, crs = lidR::st_crs(las)))
  chm <- pc_readme_chm(las, c(2, 2, 18, 18), res = 1, ground_gap = 3)
  expect_equal(pc_readme_water_level(las, chm), 104)
  # No water in the window: NA, not a number.
  dry <- pc_readme_chm(synthetic_las(), c(2, 2, 18, 18), res = 1)
  expect_true(is.na(pc_readme_water_level(synthetic_las(), dry)))
})

# Rasters for the drawing: a flat plane 2.5 m above a water level of 100 m.
relief_grids <- function(n = 20) {
  r <- terra::rast(ncols = n, nrows = n, xmin = 0, xmax = n, ymin = 0, ymax = n, crs = "EPSG:3156")
  list(ground = terra::setValues(r, 102.5), chm = terra::setValues(r, 0))
}
cell_rgb <- function(rgb, x, y) unname(unlist(terra::extract(rgb, cbind(x, y))))
ramp_rgb <- function(pal, t) as.vector(grDevices::col2rgb(pal(256)[round(t * 255) + 1]))

test_that("flat open ground keeps its ramp colour; the ramp's ends hold outside its range", {
  g <- relief_grids()
  rgb <- pc_readme_relief(g$ground, g$chm, level = 100, relief = 5)
  expect_equal(cell_rgb(rgb, 10.5, 10.5), ramp_rgb(GROUND_PAL, 0.5))
  low <- pc_readme_relief(g$ground - 10, g$chm, level = 100)
  high <- pc_readme_relief(g$ground + 10, g$chm, level = 100)
  expect_equal(cell_rgb(low, 10.5, 10.5), ramp_rgb(GROUND_PAL, 0))
  expect_equal(cell_rgb(high, 10.5, 10.5), ramp_rgb(GROUND_PAL, 1))
})

test_that("a slope facing away from the sun is darker than flat ground", {
  g <- relief_grids()
  xy <- terra::xyFromCell(g$ground, seq_len(terra::ncell(g$ground)))
  # Rising to the north-west, where the sun is (315 degrees), the ground faces south-east: away.
  away <- terra::setValues(g$ground, 102.5 + 0.2 * (xy[, 2] - xy[, 1]))
  dark <- pc_readme_relief(away, g$chm, level = 100, relief = 1e6)
  ref <- pc_readme_relief(away, g$chm, level = 100, relief = 1e6, exaggeration = 0)
  expect_lt(sum(cell_rgb(dark, 10.5, 10.5)), 0.5 * sum(cell_rgb(ref, 10.5, 10.5)))
  # Facing the sun is lighter than flat, within the cap.
  lit <- terra::setValues(g$ground, 102.5 + 0.2 * (xy[, 1] - xy[, 2]))
  bright <- pc_readme_relief(lit, g$chm, level = 100, relief = 1e6)
  expect_gt(sum(cell_rgb(bright, 10.5, 10.5)), sum(cell_rgb(ref, 10.5, 10.5)))
})

test_that("water wins, shrubs tint, trees cover, and a bank is not darkened by its water", {
  g <- relief_grids()
  chm <- g$chm
  chm[terra::cellFromXY(chm, cbind(15.5, 10.5))] <- NA    # water
  chm[terra::cellFromXY(chm, cbind(5.5, 5.5))] <- 1.9     # under the canopy threshold
  chm[terra::cellFromXY(chm, cbind(5.5, 10.5))] <- 3      # shrub
  chm[terra::cellFromXY(chm, cbind(5.5, 15.5))] <- 30     # tall tree
  rgb <- pc_readme_relief(g$ground, chm, level = 100, relief = 5)
  open <- ramp_rgb(GROUND_PAL, 0.5)
  expect_equal(cell_rgb(rgb, 15.5, 10.5), as.vector(grDevices::col2rgb(WATER_COL)))
  expect_equal(cell_rgb(rgb, 5.5, 5.5), open)
  expect_equal(cell_rgb(rgb, 14.5, 10.5), open)  # the bank beside the water
  green <- function(v) v[2] - mean(v[c(1, 3)])
  shrub <- cell_rgb(rgb, 5.5, 10.5)
  tree <- cell_rgb(rgb, 5.5, 15.5)
  expect_gt(green(shrub), green(open))
  expect_gt(green(tree), green(shrub))
  # A shrub is a tint: it stays nearer the ground's colour than its own canopy colour is.
  dist <- function(a, b) sqrt(sum((a - b)^2))
  expect_lt(dist(shrub, open), 0.5 * dist(ramp_rgb(CANOPY_PAL, 1 / 28), open))
  expect_error(pc_readme_relief(g$ground, terra::aggregate(chm, 2), level = 100), "one grid")
})

test_that("the figure is drawn one cell to one pixel, with room for its scales", {
  g <- relief_grids(120)  # taller than the scale bar's box, so row 5 is all map
  # Water in every other column: thinning or smoothing the raster would break the stripes.
  chm <- g$chm
  xy <- terra::xyFromCell(chm, seq_len(terra::ncell(chm)))
  chm[xy[, 1] %% 2 < 1] <- NA
  rgb <- pc_readme_relief(g$ground, chm, level = 100)
  path <- withr::local_tempfile(fileext = ".png")
  pc_readme_relief_png(rgb, path, scale = 1, bar_m = 10,
                       legend = list(relief = 5, tree = 2, top = 30))
  img <- png::readPNG(path)
  expect_identical(dim(img)[1:2], c(120L, 120L + 330L))
  row <- round(img[5, 1:120, 1:3] * 255)
  water <- as.vector(grDevices::col2rgb(WATER_COL))
  expect_true(all(t(row[c(TRUE, FALSE), ]) == water))
  expect_true(all(t(row[c(FALSE, TRUE), ]) == ramp_rgb(GROUND_PAL, 0.5)))
})

test_that("every code excerpt README.Rmd shows resolves to one marked span", {
  root <- file.path(testthat::test_path(".."))
  rmd <- readLines(file.path(root, "README.Rmd"))
  calls <- regmatches(rmd, regexpr('pc_readme_lines\\("[^"]+", "[^"]+"\\)', rmd))
  expect_gte(length(calls), 4L)
  for (cl in calls) {
    args <- regmatches(cl, gregexpr('"[^"]+"', cl))[[1]]
    args <- gsub('"', "", args)
    expect_gt(length(pc_readme_lines(file.path(root, args[1]), args[2])), 0L, label = cl)
  }
})

test_that("a laz asset is downloaded once, and a cached file of the wrong size is refused", {
  dir <- withr::local_tempdir()
  href <- "https://example.invalid/gdwuts/093/093l/2019/pointcloud/a.laz"
  calls <- 0L
  fake <- function(url, path) {
    calls <<- calls + 1L
    writeBin(as.raw(seq_len(10)), path)
  }
  r1 <- pc_readme_laz_get(href, 10, dir, fetch = fake)
  expect_true(r1$downloaded)
  expect_identical(r1$path, file.path(dir, "a.laz"))
  r2 <- pc_readme_laz_get(href, 10, dir, fetch = fake)
  expect_false(r2$downloaded)
  expect_identical(calls, 1L)
  expect_error(pc_readme_laz_get(href, 11, dir, fetch = fake), "delete it")
  expect_identical(calls, 1L)
})

test_that("a download of the wrong size is not kept", {
  dir <- withr::local_tempdir()
  href <- "https://example.invalid/b.laz"
  short <- function(url, path) writeBin(as.raw(1:9), path)
  expect_error(pc_readme_laz_get(href, 10, dir, fetch = short), "downloaded 9 bytes")
  expect_identical(list.files(dir), character(0))
})
