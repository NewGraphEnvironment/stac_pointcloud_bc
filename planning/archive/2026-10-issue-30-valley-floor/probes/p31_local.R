# The current window: ground-return density, roads/rails/streams from BC layers, a crop of the south strip.
source("scripts/readme_functions.R")
S <- commandArgs(TRUE)[1]
bx <- readRDS(file.path(S, "box.rds")); box <- bx$box; rb <- bx$rb
laz <- list.files("data/readme_laz", pattern = "laz$", full.names = TRUE)
las <- lidR::readLAS(laz, select = "xyzc", filter = paste("-keep_class 2 -drop_withheld -keep_xy", paste(box, collapse = " ")))
g1 <- terra::rast(terra::ext(box[1], box[3], box[2], box[4]), resolution = 1, crs = "EPSG:3156")
n <- tabulate(terra::cellFromXY(g1, cbind(las$X, las$Y)), terra::ncell(g1))
dens <- terra::setValues(g1, n)
terra::writeRaster(dens, file.path(S, "ground_density1.tif"), overwrite = TRUE)
# Distance to the nearest ground return, at 1 m: where the TIN is guessing.
has <- terra::ifel(dens > 0, 1, NA)
dist <- terra::distance(has)
terra::writeRaster(dist, file.path(S, "ground_dist1.tif"), overwrite = TRUE)
aoi <- sf::st_transform(sf::st_as_sfc(sf::st_bbox(setNames(rb, c("xmin","ymin","xmax","ymax")), crs = sf::st_crs(3156))), 3005)
get <- function(id) tryCatch(sf::st_transform(bcdata::collect(bcdata::filter(bcdata::bcdc_query_geodata(id), bcdata::INTERSECTS(aoi))), 3156), error = function(e) { message(id, ": ", conditionMessage(e)); NULL })
lay <- list(roads = get("WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP"),
            rail = get("WHSE_BASEMAPPING.GBA_RAILWAY_TRACKS_SP"),
            trans = get("WHSE_BASEMAPPING.GBA_TRANSMISSION_LINES_SP"))
for (k in names(lay)) cat(k, if (is.null(lay[[k]])) "error" else nrow(lay[[k]]), "\n")
if (!is.null(lay$roads)) print(table(lay$roads$ROAD_SURFACE, lay$roads$ROAD_CLASS))
saveRDS(lay, file.path(S, "bc_layers.rds"))
