# readme_functions.R — sourced by README.Rmd (#9).
#
# Everything the landing page shows comes from two caches, written when the page is rendered
# with `update_query = TRUE`: data/readme_cache.rds (the published items reduced to counts,
# the example's search result, two header reads) and data/readme_dem.json (written by
# scripts/readme_dem.py). A render with `update_query = FALSE` reads only those, so it needs
# no network.

API_ROOT <- "https://images.a11s.one"
COLLECTION <- "stac-pointcloud-bc"
BUCKET_URL <- "https://stac-pointcloud-bc.s3.us-west-2.amazonaws.com"
CACHE <- "data/readme_cache.rds"
DEM_JSON <- "data/readme_dem.json"

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
  pc_readme_header_parse(raw[seq_len(min(length(raw), LAS_HEADER_BYTES))])
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


# ---- the collection, fetched whole -------------------------------------------------------

#' The item ids the bucket's collection.json links, and its version
#'
#' The API sends no `numberMatched` (measured 2026-10-09: only `numberReturned`), so the
#' independent side of the completeness check is the bucket's own collection.json, written by
#' the release from the same build. Ids are read the way scripts/s3_sync.sh and stacs read
#' them: the file name of each `rel: item` link, `%20` decoded. `simplifyVector = FALSE`, or
#' `links` comes back as a data.frame.
pc_readme_bucket <- function(api_root = API_ROOT, collection = COLLECTION) {
  coll <- rstac::stac(paste0(api_root, "/")) |>
    rstac::collections(collection) |>
    rstac::get_request()
  s3 <- jsonlite::fromJSON(paste0(BUCKET_URL, "/collection.json"), simplifyVector = FALSE)
  hrefs <- vapply(Filter(\(l) identical(l$rel, "item"), s3$links), \(l) l$href, character(1))
  list(ids = sub("\\.json$", "", gsub("%20", " ", basename(hrefs))),
       version = s3$version, api_version = coll$version)
}

#' Every published item, reduced to what the counts need
#'
#' Refuses anything short of the whole collection: the fetched ids must equal the ids the
#' bucket links, as sets in both directions, and the API and the bucket must serve the same
#' catalogue version. A truncated page would otherwise report a smaller collection.
pc_readme_fetch <- function(api_root = API_ROOT, collection = COLLECTION) {
  r <- rstac::stac(paste0(api_root, "/")) |>
    rstac::stac_search(collections = collection, limit = 1000) |>
    rstac::post_request() |>
    rstac::items_fetch(progress = FALSE)
  ids <- vapply(r$features, \(f) f$id, character(1))
  if (length(ids) == 0L) stop("search returned no items", call. = FALSE)
  if (anyDuplicated(ids)) stop("search returned duplicate ids", call. = FALSE)

  b <- pc_readme_bucket(api_root, collection)
  missing <- setdiff(b$ids, ids)
  extra <- setdiff(ids, b$ids)
  if (length(missing) > 0L || length(extra) > 0L) {
    stop("the API and the bucket disagree: ", length(missing), " linked in the bucket but ",
         "not served, ", length(extra), " served but not linked", call. = FALSE)
  }
  if (is.null(b$api_version) || !identical(b$api_version, b$version)) {
    stop("the API serves version ", b$api_version %||% "none", " but the bucket's ",
         "collection.json says ", b$version %||% "none", call. = FALSE)
  }

  fp <- rstac::items_as_sf(r)
  stopifnot(nrow(fp) == length(ids))
  laz <- vapply(r$features, \(f) f$assets$laz$href, character(1))
  copc <- vapply(r$features, \(f) f$assets$copc$href %||% NA_character_, character(1))
  items <- sf::st_sf(
    id = ids,
    # gdwuts/<block>/<sheet>/<year>/pointcloud/<file>
    group = sub("^.*/gdwuts/[^/]+/([^/]+)/([0-9]{4})/.*$", "\\1/\\2", laz),
    copc = !is.na(copc),
    points = as.numeric(fp[["pc:count"]]),
    geometry = sf::st_geometry(fp)
  )
  if (any(!grepl("^[0-9]{3}[a-p]/[0-9]{4}$", items$group))) {
    stop("an item's laz href is not under gdwuts/<block>/<sheet>/<year>/", call. = FALSE)
  }
  list(items = items[order(items$id), ], version = b$version, fetched_at = Sys.Date())
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
