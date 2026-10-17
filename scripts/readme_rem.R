# readme_rem.R — the valley floor up Maxan Creek, as height above the stream bed (#30).
#
# The canopy figure (scripts/readme_chm.R) shows the delta. Its old channels are clearest further
# up the valley, over more ground than a demo should download point clouds for, so this figure
# reads LidarBC's DEM of the same delivery from the sister collection, stac-elevation-bc: one
# window, read over HTTP from a 638 MB file. Each cell is drawn as its height above the nearest
# stream bed (pc_readme_rem()), so one colour scale covers a valley floor that rises upstream.
# Writes fig/maxan_rem.png and data/readme_rem.json, which README.Rmd reads. Run by README.Rmd
# when it renders with `update_query = TRUE`, from the repo root:
#
#     Rscript scripts/readme_rem.R

source("scripts/readme_functions.R")

ELEVATION <- "stac-elevation-bc"
# The same point and delivery as scripts/readme_chm.R: Maxan Creek's mouth on Bulkley Lake.
MOUTH_LON <- -126.1256
MOUTH_LAT <- 54.3814
DELIVERY <- "093/093l/2019"
# The window, in metres from that point: the delta and the valley up to 3.4 km west of it.
WEST <- 3400
EAST <- 600
SOUTH <- 1550
NORTH <- 750
CELL <- 4      # m, the figure's cell: the 1 m DEM averaged; about what the page width shows
# Streams of this Strahler order and up set the bed (FWA); the lowest ground within REACH m of
# each, every SPACING m. A smaller stream is a gully on a hillside, not a valley floor. Where the
# bed surface stands over ABOVE m above the ground, the lowest sample within NEAR m replaces it.
MIN_ORDER <- 2
SPACING <- 10
REACH <- 15
ABOVE <- 2
NEAR <- 1000
# Coloured from the bed to RELIEF m above it, which holds the valley floor.
RELIEF <- 3
EXAGGERATION <- 4
# The DEM flattens open water to one level: level patches of this many m² or more are water.
WATER_AREA <- 1e4
REM_PNG <- "fig/maxan_rem.png"

main <- function() {
  # --- shown on the landing page: begin
  api <- rstac::stac(paste0(API_ROOT, "/"))
  at_mouth <- api |>
    rstac::stac_search(collections = ELEVATION, limit = 100,
                       intersects = list(type = "Point", coordinates = c(MOUTH_LON, MOUTH_LAT))) |>
    rstac::post_request()
  items <- Filter(\(f) identical(f$properties[["lidarbc:delivery"]], DELIVERY) &&
                    !is.null(f$assets$dem), at_mouth$features)
  if (length(items) != 1L) stop(length(items), " ", DELIVERY, " DEM items at the mouth", call. = FALSE)
  item <- items[[1]]
  crs <- paste0("EPSG:", item$properties[["proj:epsg"]])
  xy <- sf::st_sfc(sf::st_point(c(MOUTH_LON, MOUTH_LAT)), crs = 4326) |>
    sf::st_transform(crs) |>
    sf::st_coordinates()
  # On the DEM's own cell edges, so the read is not resampled.
  tf <- unlist(item$properties[["proj:transform"]])
  snap <- \(v, o) o + round(v - o)
  box <- c(snap(xy[1] - WEST, tf[3]), snap(xy[2] - SOUTH, tf[6]),
           snap(xy[1] + EAST, tf[3]), snap(xy[2] + NORTH, tf[6]))
  bb <- unlist(item$properties[["proj:bbox"]])
  if (box[1] < bb[1] || box[2] < bb[2] || box[3] > bb[3] || box[4] > bb[4]) {
    stop(item$id, " does not cover the window", call. = FALSE)
  }
  # Only the window's rows are read from the file, over HTTP.
  tif <- tempfile(fileext = ".tif")
  sf::gdal_utils("translate", paste0("/vsicurl/", item$assets$dem$href), tif,
                 c("-projwin", box[1], box[4], box[3], box[2]))
  dem <- terra::rast(tif)
  # --- shown on the landing page: end
  if (terra::ncol(dem) != box[3] - box[1] || terra::nrow(dem) != box[4] - box[2]) {
    stop("the DEM read is not the window: ", terra::ncol(dem), " x ", terra::nrow(dem), call. = FALSE)
  }
  # The tile's coverage ends on a curve; a window past it would draw nodata as water.
  if (anyNA(terra::values(dem, mat = FALSE))) stop("the window reaches the DEM's nodata", call. = FALSE)
  # --- the valley floor, shown on the landing page: begin
  dem <- terra::aggregate(dem, CELL, mean)
  water <- pc_readme_flat_water(dem, min_area = WATER_AREA)
  # The streams, from the Freshwater Atlas.
  # In BC Albers before the query: bcdata cannot translate a transform inside its filter.
  aoi <- sf::st_as_sfc(sf::st_bbox(setNames(box, c("xmin", "ymin", "xmax", "ymax")),
                                   crs = sf::st_crs(crs))) |>
    sf::st_transform(3005)
  streams <- bcdata::bcdc_query_geodata("WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP") |>
    bcdata::filter(bcdata::INTERSECTS(aoi)) |>
    bcdata::select(GNIS_NAME, STREAM_ORDER) |>
    bcdata::collect() |>
    sf::st_transform(crs)
  streams <- streams[streams$STREAM_ORDER >= MIN_ORDER, ]
  bed <- pc_readme_stream_bed(dem, streams, water = water, spacing = SPACING, reach = REACH)
  rem <- pc_readme_rem(dem, bed, above = ABOVE, near = NEAR)
  # --- the valley floor, shown on the landing page: end

  rgb <- pc_readme_relief(rem, terra::ifel(water, NA, 0), level = 0, relief = RELIEF,
                          exaggeration = EXAGGERATION, shape = dem)
  pc_readme_relief_png(rgb, REM_PNG, scale = CELL, legend = list(relief = RELIEF), bar_m = 1000,
                       ground_label = "above the\nstream bed (m)")
  bed_from <- attr(rem, "bed_from")
  r <- terra::values(rem, mat = FALSE)[!terra::values(water, mat = FALSE)]
  if (anyNA(r)) stop("height above the stream bed is missing for ", sum(is.na(r)), " cells", call. = FALSE)
  out <- list(
    item = item$id,
    dem = item$assets$dem$href,
    delivery = DELIVERY,
    crs = crs,
    window_m = c(box[3] - box[1], box[4] - box[2]),
    dem_cell_m = abs(tf[1]),
    cell_m = CELL,
    bytes_file = as.numeric(item$assets$dem[["file:size"]]),
    streams = sort(unique(stats::na.omit(streams$GNIS_NAME))),
    min_order = MIN_ORDER,
    spacing_m = SPACING,
    reach_m = REACH,
    bed_samples = nrow(bed),
    above_m = ABOVE,
    near_m = NEAR,
    # Where each cell's bed came from: the TIN, beyond its hull the three nearest samples, or
    # the lowest sample within NEAR m where those stood above the ground.
    share_bed_tin = round(bed_from[["tin"]], 3),
    share_bed_nearest = round(bed_from[["nearest"]], 3),
    share_bed_lowest = round(bed_from[["lowest"]], 3),
    water_area_m2 = WATER_AREA,
    share_water = round(mean(terra::values(water, mat = FALSE)), 3),
    relief_m = RELIEF,
    exaggeration = EXAGGERATION,
    # Land less than RELIEF m above the stream bed, and the part of it below the bed: the
    # valley floor as drawn, all of it below the ramp's top.
    share_floor = round(mean(r < RELIEF), 3),
    share_below = round(mean(r < 0), 3),
    min_m = round(min(r), 2)
  )
  jsonlite::write_json(out, REM_JSON, auto_unbox = TRUE, pretty = TRUE, digits = NA)
}

if (sys.nframe() == 0L) main()
