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
