# readme_chm.R — from a STAC search to a canopy height model, for the landing page (#19).
#
# Finds the items covering a window over the Maxan Creek delta at Bulkley Lake, downloads each
# item's `laz` asset whole (these have no `copc` to read a window from), and builds a pit-free
# canopy height model with noise and withheld points left out. Writes fig/maxan_chm.png and
# data/readme_chm.json, which README.Rmd reads. Run by README.Rmd when it renders with
# `update_query = TRUE`, from the repo root:
#
#     Rscript scripts/readme_chm.R
#
# The downloads stay in data/readme_laz/ (gitignored), so a second run fetches nothing.

source("scripts/readme_functions.R")

# Maxan Creek's mouth on Bulkley Lake: the BC Geographical Names point for the creek. Not the
# Freshwater Atlas stem's downstream end, which the atlas routes on to the lake's centreline.
MOUTH_LON <- -126.1256
MOUTH_LAT <- 54.3814
# The one delivery read. Pinned, so a flight indexed later over the delta cannot change the
# figure; only 2019 covers this reach (NewGraphEnvironment/floodplains#121).
DELIVERY <- "093/093l/2019"
# The window, in metres from that point.
WEST <- 700
EAST <- 500
SOUTH <- 600
NORTH <- 400
CELL <- 0.5     # m
MARGIN <- 30    # m read beyond the window, so the ground TIN has no edge inside it
GROUND_GAP <- 5 # m. A cell with no ground return this near is water (pc_readme_chm())
# Refused before anything is downloaded: a window moved onto more tiles than this is a mistake.
MAX_ITEMS <- 2L
MAX_BYTES <- 600e6
LAZ_DIR <- "data/readme_laz"
CHM_PNG <- "fig/maxan_chm.png"

main <- function() {
  # --- shown on the landing page: begin
  api <- rstac::stac(paste0(API_ROOT, "/"))
  # The CRS of the delivery's tiles, from the one at the mouth.
  at_mouth <- api |>
    rstac::stac_search(collections = COLLECTION, limit = 100,
                       intersects = list(type = "Point", coordinates = c(MOUTH_LON, MOUTH_LAT))) |>
    rstac::post_request()
  at_mouth <- Filter(\(f) identical(f$properties[["lidarbc:delivery"]], DELIVERY),
                     at_mouth$features)
  if (length(at_mouth) == 0L) stop("no ", DELIVERY, " item covers the mouth", call. = FALSE)
  crs <- at_mouth[[1]]$properties[["proj:code"]]

  xy <- sf::st_sfc(sf::st_point(c(MOUTH_LON, MOUTH_LAT)), crs = 4326) |>
    sf::st_transform(crs) |>
    sf::st_coordinates()
  box <- c(xy[1] - WEST, xy[2] - SOUTH, xy[1] + EAST, xy[2] + NORTH)
  read_box <- box + MARGIN * c(-1, -1, 1, 1)
  # Search for the window and its margin: every point read has to come from a found item.
  aoi <- sf::st_as_sfc(sf::st_bbox(setNames(read_box, c("xmin", "ymin", "xmax", "ymax")),
                                   crs = sf::st_crs(crs))) |>
    sf::st_transform(4326)
  found <- api |>
    rstac::stac_search(collections = COLLECTION, limit = 100,
                       intersects = jsonlite::fromJSON(geojsonsf::sfc_geojson(aoi),
                                                       simplifyVector = FALSE)) |>
    rstac::post_request() |>
    rstac::items_fetch(progress = FALSE)
  items <- Filter(\(f) identical(f$properties[["lidarbc:delivery"]], DELIVERY), found$features)
  items <- items[order(vapply(items, \(f) f$id, ""))]
  size <- vapply(items, \(f) as.numeric(f$assets$laz[["file:size"]]), 0)
  if (length(items) > MAX_ITEMS || sum(size) > MAX_BYTES) {
    stop(length(items), " items, ", round(sum(size) / 1e6), " MB: more than this demo downloads",
         call. = FALSE)
  }
  if (any(vapply(items, \(f) f$properties[["proj:code"]] != crs, logical(1)))) {
    stop("items in the window do not share one CRS", call. = FALSE)
  }
  # And they must cover all of it: a tile missing from the delivery would leave part of the
  # window empty, drawn as if it were water.
  rect <- \(b) sf::st_as_sfc(sf::st_bbox(setNames(b, c("xmin", "ymin", "xmax", "ymax")),
                                         crs = sf::st_crs(crs)))
  tiles <- sf::st_union(do.call(c, lapply(items, \(f) rect(unlist(f$properties[["proj:bbox"]])))))
  if (!sf::st_covers(tiles, rect(read_box), sparse = FALSE)[1, 1]) {
    stop("the items found do not cover the window and its margin", call. = FALSE)
  }

  # No `copc` asset, so no window read: each file is downloaded whole, once. Refused if a
  # release pairs one with a COPC, since the page then says something false.
  if (any(vapply(items, \(f) !is.null(f$assets$copc), logical(1)))) {
    stop("an item in the window now has a copc asset: read the window from it", call. = FALSE)
  }
  laz <- vapply(seq_along(items), \(i) {
    pc_readme_laz_get(items[[i]]$assets$laz$href, size[i], LAZ_DIR)$path
  }, "")
  # LASlib reads only the points inside the window and its margin. pitfree() needs the
  # return number: it rasterises first returns.
  las <- lidR::readLAS(laz, select = "xyzrc",
                       filter = paste("-drop_withheld -keep_xy", paste(read_box, collapse = " ")))
  chm <- pc_readme_chm(las, box, res = CELL, ground_gap = GROUND_GAP)
  # --- shown on the landing page: end

  # The returns inside the window (the margin left out), noise included.
  inside <- las$X >= box[1] & las$X < box[3] & las$Y >= box[2] & las$Y < box[4]
  cls <- las$Classification[inside]
  # Heights over the cells that have one; NA cells (open water) are left out.
  h <- terra::values(chm, mat = FALSE)
  h <- h[!is.na(h)]
  plot_chm(chm, box)
  out <- list(
    items_found = vapply(found$features, \(f) f$id, ""),
    delivery = DELIVERY,
    items = vapply(items, \(f) f$id, ""),
    laz = vapply(items, \(f) f$assets$laz$href, ""),
    crs = crs,
    window_m = c(WEST + EAST, SOUTH + NORTH),
    cell_m = CELL,
    margin_m = MARGIN,
    ground_gap_m = GROUND_GAP,
    # The files as published, downloaded whole once: their `file:size` and `pc:count`.
    bytes_files = sum(size),
    points_files = sum(vapply(items, \(f) as.numeric(f$properties[["pc:count"]]), 0)),
    points_window = sum(inside),
    share_ground = mean(cls == 2L),
    share_class1 = mean(cls == 1L),
    share_noise = mean(cls %in% NOISE_CLASSES),
    classes = as.list(table(cls)),
    cells = terra::ncell(chm),
    cells_na = terra::ncell(chm) - length(h),
    share_2m = mean(h >= 2),
    share_10m = mean(h >= 10),
    height_m = setNames(as.list(round(stats::quantile(h, c(0.5, 0.9, 0.99, 1), names = FALSE), 1)),
                        c("p50", "p90", "p99", "max"))
  )
  jsonlite::write_json(out, CHM_JSON, auto_unbox = TRUE, pretty = TRUE, digits = NA)
}

plot_chm <- function(chm, box, path = CHM_PNG) {
  # In metres from the window's corner, as the DEM figure is.
  r <- terra::shift(chm, dx = -box[1], dy = -box[2])
  top <- ceiling(terra::global(r, "max", na.rm = TRUE)[[1]] / 5) * 5
  w <- 1350
  png(path, width = w, height = round(w * (box[4] - box[2]) / (box[3] - box[1])), res = 150)
  on.exit(grDevices::dev.off())
  terra::plot(r, col = grDevices::hcl.colors(100, "YlGn", rev = TRUE), range = c(0, top),
              colNA = "#C7DBF0", axes = FALSE, box = FALSE, mar = c(1, 1, 1, 5),
              plg = list(title = "canopy\nheight (m)", cex = 0.9))
  terra::sbar(500, xy = c(50, 60), type = "line", lwd = 2, label = "500 m", cex = 0.8)
}

if (sys.nframe() == 0L) main()
