S <- commandArgs(TRUE)[1]
bx <- readRDS(file.path(S, "box.rds")); box <- bx$box
aoi <- sf::st_transform(sf::st_as_sfc(sf::st_bbox(setNames(box, c("xmin","ymin","xmax","ymax")), crs = sf::st_crs(3156))), 3005)
s <- bcdata::bcdc_query_geodata("WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP") |>
  bcdata::filter(bcdata::INTERSECTS(aoi)) |>
  bcdata::select(GNIS_NAME, BLUE_LINE_KEY, STREAM_ORDER, EDGE_TYPE) |> bcdata::collect()
print(table(s$GNIS_NAME, useNA = "ifany")); print(table(s$EDGE_TYPE))
s <- sf::st_transform(s, 3156)
saveRDS(s, file.path(S, "fwa.rds"))
