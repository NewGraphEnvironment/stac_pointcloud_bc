# readme_functions.R — sourced by README.Rmd (#9).
#
# Everything the landing page shows comes from one cache, written when the page is rendered
# with `update_query = TRUE`: the published items reduced to what the figure and the example
# need, the example's search result, and two header reads. A render with
# `update_query = FALSE` reads only the cache, so it needs no network.

API_ROOT <- "https://images.a11s.one"
COLLECTION <- "stac-pointcloud-bc"
CACHE <- "data/readme_cache.rds"


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
  if (length(raw) < 227L || !identical(rawToChar(raw[1:4]), "LASF")) {
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
#' without advertising `Accept-Ranges` (scripts/laz_remote.py); anything other than a 206 is
#' refused, because a 200 would be the whole file.
pc_readme_header <- function(url) {
  resp <- httr2::request(url) |>
    httr2::req_headers(Range = paste0("bytes=0-", LAS_HEADER_BYTES - 1L)) |>
    httr2::req_timeout(30) |>
    httr2::req_perform()
  if (httr2::resp_status(resp) != 206L) {
    stop(url, ": expected a 206 partial response, got ", httr2::resp_status(resp),
         call. = FALSE)
  }
  pc_readme_header_parse(httr2::resp_body_raw(resp))
}
