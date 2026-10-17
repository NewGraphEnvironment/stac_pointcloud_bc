# readme_functions.R — sourced by README.Rmd (#9).
#
# Everything the landing page shows comes from three caches, written when the page is rendered
# with `update_query = TRUE`: data/readme_cache.rds (the catalogue version, the example's
# search result, two header reads) and data/readme_dem.json (written by
# scripts/readme_dem.py) and data/readme_chm.json (scripts/readme_chm.R). A render with `update_query = FALSE` reads only those, so it needs
# no network.

API_ROOT <- "https://images.a11s.one"
COLLECTION <- "stac-pointcloud-bc"
CACHE <- "data/readme_cache.rds"
DEM_JSON <- "data/readme_dem.json"
CHM_JSON <- "data/readme_chm.json"

#' The lines of a file between `# --- <marker>: begin` and `# --- <marker>: end`
#'
#' So the page shows the script's own code rather than a copy of it. Refuses a missing or
#' doubled marker rather than showing nothing, or the wrong span.
pc_readme_lines <- function(path, marker) {
  x <- readLines(path)
  b <- grep(paste0("# --- ", marker, ": begin"), x, fixed = TRUE)
  e <- grep(paste0("# --- ", marker, ": end"), x, fixed = TRUE)
  if (length(b) != 1L || length(e) != 1L || e <= b + 1L) {
    stop(path, ": expected one '", marker, "' begin/end pair around some code", call. = FALSE)
  }
  # Dedent by the begin marker's own indent, so the excerpt reads at the left margin.
  ind <- nchar(sub("#.*", "", x[b]))
  sub(paste0("^ {0,", ind, "}"), "", x[(b + 1L):(e - 1L)])
}


# ---- the LAS header, read remotely -------------------------------------------------------

# The public header block of LAS 1.4 is 375 bytes; earlier versions use a prefix of it.
LAS_HEADER_BYTES <- 375L

#' Little-endian unsigned integers out of a raw vector, as doubles
#'
#' R has no unsigned 32-bit or any 64-bit integer type, and `readBin(size = 4)` cannot stand
#' in for one: it goes negative above 2^31 and returns NA for exactly 2^31, R's NA_integer_
#' bit pattern. So the bytes are summed as doubles, which hold a u64 exactly up to 2^53,
#' far above any point count.
las_u32 <- function(raw, offset) {
  sum(as.numeric(raw[offset + 1:4]) * 256^(0:3))
}
las_u64 <- function(raw, offset) {
  las_u32(raw, offset) + las_u32(raw, offset + 4L) * 2^32
}
las_f64 <- function(raw, offset, n = 1L) {
  readBin(raw[offset + seq_len(8L * n)], "double", size = 8L, n = n, endian = "little")
}

#' Parse a LAS public header block
#'
#' Offsets are the ASPRS LAS 1.4 R15 specification's, which keeps 1.0–1.3 as a prefix.
#' Two traps a reader of LAZ and COPC must not fall into:
#' - the point format byte carries the LAZ compression flags in its top two bits (0x81 is
#'   format 1, compressed), so it is masked;
#' - from 1.4 the point count is the 64-bit field at 247, and point formats 6–10 leave the
#'   legacy 32-bit field at 107 as zero. A COPC is LAS 1.4 format 6, so reading the legacy
#'   field reports it as empty.
pc_readme_header_parse <- function(raw) {
  # Compared as bytes: rawToChar() errors on an embedded nul, which binary input has.
  if (length(raw) < 227L || !identical(raw[1:4], charToRaw("LASF"))) {
    stop("not a LAS header: no LASF signature in the first bytes", call. = FALSE)
  }
  major <- as.integer(raw[25])
  minor <- as.integer(raw[26])
  if (major != 1L || minor > 4L) {
    stop("LAS ", major, ".", minor, " is not a version this reader knows", call. = FALSE)
  }
  if (minor >= 4L && length(raw) < LAS_HEADER_BYTES) {
    stop("LAS 1.4 header needs ", LAS_HEADER_BYTES, " bytes, got ", length(raw), call. = FALSE)
  }
  count <- if (minor >= 4L) las_u64(raw, 247L) else las_u32(raw, 107L)
  # Stored order is max x, min x, max y, min y, max z, min z.
  ext <- las_f64(raw, 179L, 6L)
  list(
    las_version = paste0(major, ".", minor),
    point_format = bitwAnd(as.integer(raw[105]), 0x3F),
    point_count = count,
    scale = las_f64(raw, 131L, 3L),
    offset = las_f64(raw, 155L, 3L),
    mins = ext[c(2, 4, 6)],
    maxs = ext[c(1, 3, 5)]
  )
}

#' Read a LAS/LAZ/COPC header over HTTPS with one range request
#'
#' Transfers 375 bytes, whatever the file's size. The objectstore answers a range with 206
#' without advertising `Accept-Ranges` (scripts/laz_remote.py). The status is read before the
#' body, so a server that ignores the range and answers 200 is refused without the whole file
#' (up to ~270 MB here) being downloaded first.
pc_readme_header <- function(url) {
  resp <- httr2::request(url) |>
    httr2::req_headers(Range = paste0("bytes=0-", LAS_HEADER_BYTES - 1L)) |>
    httr2::req_timeout(30) |>
    httr2::req_perform_connection()
  on.exit(close(resp))
  if (httr2::resp_status(resp) != 206L) {
    stop(url, ": expected a 206 partial response, got ", httr2::resp_status(resp),
         call. = FALSE)
  }
  raw <- raw(0)
  while (length(raw) < LAS_HEADER_BYTES && !httr2::resp_stream_is_complete(resp)) {
    raw <- c(raw, httr2::resp_stream_raw(resp, kb = 1))
  }
  raw <- raw[seq_len(min(length(raw), LAS_HEADER_BYTES))]
  # What was actually transferred, so the page states a measurement rather than the request.
  c(pc_readme_header_parse(raw), bytes = length(raw))
}

#' Check a header read against the item that describes the file
#'
#' The item's `pc:count` and `proj:bbox` were read by laspy at build time; this reader is
#' independent of it. A `copc` asset is held to the build's own pairing test: same count, box
#' within 0.05 m (research/canelevation_overlap.md).
pc_readme_header_check <- function(h, item, tol = 0.05) {
  p <- item$properties
  bbox <- unlist(p[["proj:bbox"]])
  # A 2D proj:bbox (xmin, ymin, xmax, ymax), as laz_item.py writes it. A 3D one would
  # recycle silently against four values, so it is refused rather than misread.
  if (length(bbox) != 4L) stop(item$id, ": proj:bbox is not 2D", call. = FALSE)
  off <- max(abs(c(h$mins[1:2], h$maxs[1:2]) - bbox))
  if (!identical(h$point_count, as.numeric(p[["pc:count"]])) || off > tol) {
    stop(item$id, ": header read (", h$point_count, " points, box offset ", signif(off, 3),
         " m) disagrees with the item (", p[["pc:count"]], " points)", call. = FALSE)
  }
  off
}


# ---- the catalogue version ---------------------------------------------------------------

#' The `version` the API's collection carries, or NA when it carries none
#'
#' A monthly run that adds items publishes a collection with no `version` until the next
#' release stamps one (#4), so a missing version is a state of the catalogue, not an error.
pc_readme_version <- function(api_root = API_ROOT, collection = COLLECTION) {
  coll <- rstac::stac(paste0(api_root, "/")) |>
    rstac::collections(collection) |>
    rstac::get_request()
  coll$version %||% NA_character_
}


# ---- the example -------------------------------------------------------------------------

#' The example's search result as one row per item
pc_readme_rows <- function(features) {
  rows <- tibble::tibble(
    item = vapply(features, \(f) f$id, character(1)),
    points = vapply(features, \(f) as.numeric(f$properties[["pc:count"]]), numeric(1)),
    laz = vapply(features, \(f) f$assets$laz$href, character(1)),
    copc = vapply(features, \(f) f$assets$copc$href %||% NA_character_, character(1))
  )
  rows[order(rows$item), ]
}

#' A link to an asset, or an empty cell
pc_readme_link <- function(href) {
  ifelse(is.na(href), "",
         paste0('<a href="', href, '" target="_blank">', basename(href), "</a>"))
}


# ---- the canopy height model (scripts/readme_chm.R, #19) ---------------------------------

# ASPRS classes dropped before the CHM: low and high noise. Nothing is chosen by vegetation
# class, because LidarBC leaves most vegetation in class 1 (research/laz_classes.md).
NOISE_CLASSES <- c(7L, 18L)

#' Download a `laz` asset whole, once
#'
#' A file already in `dir` at the item's `file:size` is used as it is. One at any other size
#' is refused rather than overwritten: the download goes to a `.part` name and is renamed only
#' once its size matches, so a wrong size there was not left by this function and is worth a
#' look before it is deleted. `fetch(url, path)` is the transfer, swappable in tests.
pc_readme_laz_get <- function(href, size, dir, fetch = pc_readme_fetch_file) {
  dest <- file.path(dir, basename(href))
  if (file.exists(dest)) {
    if (!identical(as.numeric(file.size(dest)), as.numeric(size))) {
      stop(dest, " is ", file.size(dest), " bytes, but the item says ", size,
           ": delete it to download again", call. = FALSE)
    }
    return(list(path = dest, downloaded = FALSE))
  }
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  part <- paste0(dest, ".part")
  on.exit(unlink(part))
  fetch(href, part)
  if (!identical(as.numeric(file.size(part)), as.numeric(size))) {
    stop(href, ": downloaded ", file.size(part), " bytes, but the item says ", size,
         call. = FALSE)
  }
  if (!file.rename(part, dest)) stop("could not move ", part, " to ", dest, call. = FALSE)
  list(path = dest, downloaded = TRUE)
}

#' The whole file at `url`, written to `path`; an HTTP error status raises
#'
#' No total timeout: the objectstore served these files at about 0.5 MB/s (2026-10-12), so a
#' 0.6 GB file takes 20 minutes. A transfer that falls under 10 kB/s for two minutes is
#' abandoned instead.
pc_readme_fetch_file <- function(url, path) {
  httr2::request(url) |>
    httr2::req_options(low_speed_limit = 10000, low_speed_time = 120) |>
    httr2::req_perform(path = path)
  invisible(path)
}

#' A canopy height model over `box` from a point cloud read with a margin around it
#'
#' Heights are above a TIN of the ground returns (`normalize_height()`; lidR takes classes 2
#' and 9 as ground). Every other return except noise and withheld points stands on it,
#' class 1 included, and the ground returns stay in at height 0, so open ground reads 0 m
#' rather than empty. Pit-free rasterising (Khosravipour et al. 2014) onto a grid of `res`
#' over exactly `box` (xmin, ymin, xmax, ymax); a triangle with an edge over `max_edge` m is
#' dropped, so a gap in the returns stays NA rather than being bridged, and a cell with no
#' ground return within about `ground_gap` m is NA: open water.
#' Read `las` with a margin beyond `box`: the ground TIN is unreliable at its own edge.
# --- the CHM, shown on the landing page: begin
pc_readme_chm <- function(las, box, res = 0.5, max_edge = c(2, 1.5), ground_gap = 5) {
  keep <- !las$Classification %in% NOISE_CLASSES
  if (!is.null(las$Withheld_flag)) keep <- keep & !las$Withheld_flag
  las <- lidR::filter_poi(las, keep)
  las <- lidR::normalize_height(las, lidR::tin())
  # Rasterised two cells beyond `box` and then cropped to it: the cells along the edge of a
  # triangulation come out NA. rasterize_canopy() refuses a point outside its grid.
  b <- box + 2 * res * c(-1, -1, 1, 1)
  las <- lidR::filter_poi(las, X > b[1] & X < b[3] & Y > b[2] & Y < b[4])
  grid <- terra::rast(terra::ext(b[1], b[3], b[2], b[4]), resolution = res,
                      crs = lidR::st_crs(las)$wkt)
  chm <- lidR::rasterize_canopy(
    las, grid, lidR::pitfree(thresholds = c(0, 2, 5, 10, 15, 20, 25, 30), max_edge = max_edge)
  )
  # Water: where no ground return lies within about `ground_gap` m. A lake's surface returns
  # are unclassified and sit at the height of the ground TIN across it, so they read 0 m,
  # the same as a meadow; a meadow returns ground and a lake does not.
  g <- las$Classification == 2L
  n <- tabulate(terra::cellFromXY(grid, cbind(las$X[g], las$Y[g])), terra::ncell(grid))
  # Every cell whose centre is within `ground_gap` m along x and y: that many cells each way.
  w <- 2L * as.integer(ceiling(ground_gap / res)) + 1L
  near <- terra::focal(terra::setValues(grid, n), w = w, fun = "sum", na.rm = TRUE)
  chm <- terra::mask(chm, near, maskvalues = 0)
  chm <- terra::crop(chm, terra::ext(box[1], box[3], box[2], box[4]))
  # A return a few cm under the interpolated ground is not a negative height.
  terra::clamp(chm, lower = 0, values = TRUE)
}
# --- the CHM, shown on the landing page: end


# ---- the ground under the canopy (scripts/readme_chm.R, #30) ------------------------------

#' The bare ground over `box`: a TIN of the ground returns, on the CHM's grid
#'
#' The same grid as `pc_readme_chm(las, box, res)`, so the two overlay cell for cell. The TIN
#' runs across water too, where it has no ground to stand on; the figure paints water over it.
# --- the ground, shown on the landing page: begin
pc_readme_ground <- function(las, box, res = 0.5) {
  keep <- las$Classification %in% c(2L, 9L)
  if (!is.null(las$Withheld_flag)) keep <- keep & !las$Withheld_flag
  g <- lidR::filter_poi(las, keep)
  b <- box + 2 * res * c(-1, -1, 1, 1)
  grid <- terra::rast(terra::ext(b[1], b[3], b[2], b[4]), resolution = res,
                      crs = lidR::st_crs(las)$wkt)
  dem <- lidR::rasterize_terrain(g, grid, lidR::tin())
  terra::crop(dem, terra::ext(box[1], box[3], box[2], box[4]))
}

#' The water's surface: the median height of the returns in the cells the CHM calls water
#'
#' Those cells have no ground return near them (`pc_readme_chm()`), so their unclassified
#' returns are the water's surface, with the odd crown overhanging the shore, which the median
#' ignores. NA when the window holds no water.
pc_readme_water_level <- function(las, chm) {
  keep <- !las$Classification %in% c(2L, 9L, NOISE_CLASSES)
  if (!is.null(las$Withheld_flag)) keep <- keep & !las$Withheld_flag
  cell <- terra::cellFromXY(chm, cbind(las$X[keep], las$Y[keep]))
  wet <- !is.na(cell) & is.na(terra::values(chm, mat = FALSE)[cell])
  if (!any(wet)) return(NA_real_)
  stats::median(las$Z[keep][wet])
}
# --- the ground, shown on the landing page: end

# The figure's colours. The ground ramp is Plasma without its last tenth, which turns
# yellow-green: what is left has no hue between yellow and blue, so it cannot be read as canopy.
GROUND_PAL <- function(n) grDevices::hcl.colors(ceiling(n / 0.9), "Plasma")[seq_len(n)]
CANOPY_PAL <- function(n) grDevices::hcl.colors(n, "Greens 3", rev = TRUE)[ceiling(seq(n / 4, n, length.out = n))]
WATER_COL <- "#C7DBF0"

#' Canopy height over the ground, as an RGB raster (0-255)
#'
#' Ground is coloured by its height above the water's surface `level`, from 0 to `relief` m
#' (below and above that, the ramp's ends). Canopy of `tree` m and up is drawn in greens by its
#' height up to `top` m, more opaque as it rises: a light tint at `tree` m, `opacity[2]` from
#' `full` m. Both are multiplied by a hillshade of the ground, normalised so flat ground keeps
#' its colour, so the ground's shape shows through the canopy. Water (NA in `chm`) is
#' `WATER_COL`. `ground` and `chm` must share one grid.
pc_readme_relief <- function(ground, chm, level, relief = 5, tree = 2, full = 15, top = 30,
                             opacity = c(0.15, 0.9), exaggeration = 4, sun = c(35, 315)) {
  if (!terra::compareGeom(ground, chm, crs = FALSE, stopOnError = FALSE)) {
    stop("the ground and the CHM are not on one grid", call. = FALSE)
  }
  ramp <- function(v, lo, hi, pal) {
    i <- round(pmin(pmax((v - lo) / (hi - lo), 0), 1) * 255) + 1
    t(grDevices::col2rgb(pal(256))[, i, drop = FALSE]) / 255
  }
  # The hillshade, divided by what flat ground gets, so flat ground is 1. Unknown (the grid's
  # edge) counts as flat.
  e <- ground * exaggeration
  hs <- terra::shade(terra::terrain(e, "slope", unit = "radians"),
                     terra::terrain(e, "aspect", unit = "radians"), sun[1], sun[2])
  f <- terra::values(hs, mat = FALSE) / sin(sun[1] * pi / 180)
  f[is.na(f)] <- 1
  f <- pmin(pmax(f, 0), 1.25)
  z <- terra::values(ground, mat = FALSE)
  h <- terra::values(chm, mat = FALSE)
  rgb <- ramp(z, level, level + relief, GROUND_PAL)
  can <- which(!is.na(h) & h >= tree)
  a <- opacity[1] + diff(opacity) * pmin((h[can] - tree) / (full - tree), 1)
  rgb[can, ] <- rgb[can, ] * (1 - a) + ramp(h[can], tree, top, CANOPY_PAL) * a
  rgb <- pmin(rgb * f, 1) * 255
  # No ground under land is drawn blank; water is water whether or not the TIN reaches it.
  rgb[is.na(z), ] <- NA
  wet <- which(is.na(h))
  rgb[wet, ] <- matrix(grDevices::col2rgb(WATER_COL), length(wet), 3, byrow = TRUE)
  out <- terra::rast(ground, nlyrs = 3, names = c("red", "green", "blue"))
  terra::values(out) <- rgb
  out
}

#' Draw `rgb` (from pc_readme_relief()) to a PNG, one cell to one pixel, with its two scales
#'
#' Drawn with `rasterImage()`, not `terra::plot()`, whose `maxcell` would thin the raster
#' and break thin channels. `scale` is the cell size of `rgb` in m; `legend` the numbers the
#' scales are labelled with: `level`, `relief`, `tree`, `top`.
pc_readme_relief_png <- function(rgb, path, scale, legend, bar_m = 500) {
  nc <- terra::ncol(rgb)
  nr <- terra::nrow(rgb)
  key <- 330  # px for the scales, right of the map
  grDevices::png(path, width = nc + key, height = nr, res = 150, type = "cairo")
  on.exit(grDevices::dev.off())
  graphics::par(mai = c(0, 0, 0, 0), xaxs = "i", yaxs = "i", family = "sans")
  graphics::plot.new()
  graphics::plot.window(c(0, nc + key), c(0, nr))
  a <- terra::as.array(rgb)
  a[is.na(a)] <- 255
  graphics::rasterImage(grDevices::as.raster(a, max = 255), 0, 0, nc, nr, interpolate = FALSE)
  # Scale bar, bottom left, on a white ground so it reads over the forest.
  bx <- 40 + c(0, bar_m / scale)
  graphics::rect(bx[1] - 14, 20, bx[2] + 14, 80, col = "white", border = NA)
  graphics::segments(bx[1], 34, bx[2], 34, lwd = 3, lend = 1)
  graphics::text(mean(bx), 34, paste(bar_m, "m"), pos = 3, cex = 0.9)
  # Two colour scales, drawn from the same ramps and numbers as the map.
  bar <- function(x, pal, lab, at, ticks) {
    y <- nr * c(0.12, 0.88)
    graphics::rasterImage(grDevices::as.raster(rev(pal(100))), x, y[1], x + 34, y[2])
    graphics::rect(x, y[1], x + 34, y[2], lwd = 0.5)
    yy <- y[1] + diff(y) * at
    graphics::segments(x + 34, yy, x + 42, yy, lwd = 0.5)
    graphics::text(x + 44, yy, ticks, adj = 0, cex = 0.8)
    graphics::text(x, y[2] + 18, lab, adj = c(0, 0), cex = 0.8)
  }
  r <- legend$relief
  bar(nc + 30, GROUND_PAL, "ground above\nthe lake (m)",
      seq(0, 1, length.out = r + 1), c(0:(r - 1), paste0(r, "+")))
  ct <- unique(c(legend$tree, seq(10, legend$top, by = 10)))
  bar(nc + 190, CANOPY_PAL, "canopy\nheight (m)",
      (ct - legend$tree) / (legend$top - legend$tree), c(ct[-length(ct)], paste0(ct[length(ct)], "+")))
  invisible(path)
}


# ---- table helpers, copied from the sister repos (staticimports) -------------------------

my_tab_caption_rmd <- function(
    caption_text,
    tip_flag = TRUE,
    tip_text = " <b>NOTE: To view all columns in the table - please click on one of the sort arrows within column headers before scrolling to the right.</b>") {
  cat(
    '<div style="text-align: center; font-weight: bold; margin-bottom: 10px;">',
    caption_text,
    if (tip_flag) tip_text,
    '</div>',
    sep = "\n"
  )
}
my_dt_table <- function(dat,
                        cols_freeze_left = 3,
                        page_length = 10,
                        col_align = 'dt-center',
                        font_size = '11px',
                        ...) {
  dat |>
    DT::datatable(
      ...,
      class = 'cell-border stripe',
      filter = 'top',
      extensions = c("Buttons", "FixedColumns", "ColReorder"),
      rownames = FALSE,
      options = list(
        scrollX = TRUE,
        columnDefs = list(list(className = col_align, targets = "_all")),
        pageLength = page_length,
        dom = 'lrtipB',
        buttons = c('excel', 'csv'),
        fixedColumns = list(leftColumns = cols_freeze_left),
        lengthMenu = list(c(5, 10, 25, 50, -1), c(5, 10, 25, 50, "All")),
        colReorder = TRUE,
        initComplete = htmlwidgets::JS(glue::glue(
          "function(settings, json) {{ $(this.api().table().container()).css({{'font-size': '{font_size}'}}); }}"
        ))
      )
    )
}
