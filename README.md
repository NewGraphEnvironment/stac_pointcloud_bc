stac-pointcloud-bc
================

<!-- README.md is generated from README.Rmd. Please edit that file -->

![status](https://img.shields.io/badge/status-province--wide-green)
![api](https://img.shields.io/badge/api-images.a11s.one-orange)

[`stac_pointcloud_bc`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc) is a searchable index of British Columbia’s lidar point clouds, served as the `stac-pointcloud-bc` collection.

Lidar measures the shape of the land and everything standing on it. The province’s [LidarBC](https://lidar.gov.bc.ca/) program publishes lidar flown across BC since 2012, and each flight records the land as it was when it was flown.

- A **bare-earth model** (DEM) shows the ground beneath the trees: floodplains, side channels and old channels, terraces, and the roads and embankments built across a river’s path. It shows where water goes, and where it used to go.
- A **surface model** (DSM) is the top of whatever stands there. With the ground subtracted, it becomes a **canopy height model** (CHM): how tall the streamside forest is, where it shades the water, and where it has been cleared or is coming back.
- Where a place has been flown more than once, comparing flights turns change into something that can be measured and shown to others: a channel moving, forest lost or regrowing, a floodplain filled or reconnected. Flights differ in density and in how their points were classified, so a comparison starts by checking that the two can be compared.

**Why the point clouds.** The ready-made products are uneven. LidarBC publishes DEMs for most deliveries, surface models for most tiles but not all, and canopy height models for only a few hundred tiles, all from 2023 and 2024. Each comes at the resolution and by the method LidarBC chose. The point clouds are the common source. From them you choose the product, its resolution and which returns go into it, and you can apply one method to every flight, which comparing years needs. They also give products LidarBC does not publish, such as height above the channel to map a floodplain, or the density and layering of vegetation.

**Two sources.** Every file is LidarBC’s, on the province’s objectstore. For a minority of them, Natural Resources Canada’s [CanElevation](https://open.canada.ca/data/en/dataset/7069387e-9986-4297-9f55-0288e9676947) series publishes a cloud-optimised copy (COPC). A COPC carries a spatial index, so a program can read one area of it over the internet. A plain LAZ file, as almost all of LidarBC’s files are, has none, so reading one area of it means reading the whole file. Each item links the LidarBC file and, where there is one, its COPC.

**An index, not a copy.** The catalogue holds one small record per file: where the file is, the area it covers, when it was flown, its coordinate system and its point count. No point data is copied. The index is rebuilt each month from the province’s listing, and the API at <https://images.a11s.one> serves the new records once they are registered. People search it by place and time from R ([`rstac`](https://brazil-data-cube.github.io/rstac/)), Python (`pystac-client`), QGIS 3.42+ or any other [STAC](https://stacspec.org/) tool, and applications can be built on the same API. The records are public: the bucket’s [collection.json](https://stac-pointcloud-bc.s3.us-west-2.amazonaws.com/collection.json) links every one, and [stacs](https://github.com/NewGraphEnvironment/stacs), the tool that loads them into this API’s PostgreSQL database (pgstac), can load them into anyone else’s. The DEM and DSM rasters LidarBC publishes for the same deliveries are a sister collection on the same endpoint, [`stac-elevation-bc`](https://github.com/NewGraphEnvironment/stac_dem_bc).

## Bare earth: a DEM read from the cloud-optimised copies

<img src="fig/kanaka_dem.png" alt="A hillshaded bare-earth elevation model of the lower Kanaka Creek where it meets the Fraser River at Maple Ridge, built from lidar ground returns: the creek's meander, the terrace escarpment above the floodplain, and the highway and rail embankments, with water in light blue." width="100%" />

The lower Kanaka Creek where it meets the Fraser at Maple Ridge, with the trees and buildings taken away. The creek meanders across its floodplain below a terrace escarpment, and the highway and rail embankments cross it. Light blue is where no ground was returned, which here is the water.

Only the area shown was read, not the whole files, because every tile here has a CanElevation COPC. Most tiles do not have one, and for those a workflow has to download each file whole, as the canopy height model below does. That may change if LidarBC publishes cloud-optimised files itself.

**How it was made.** One STAC search for a 1.6 × 1.2 km window returned 8 items, because the place has been flown more than once; the 4 flown in 2016 were used. Reading only that window from each of those items’ `copc` asset transferred 74 MB of the 434 MB in those files: 6.8 million points, 1.5 million of them ground returns, gridded at 2 m. One of these 4 items returned ground points only in this window, so trees and buildings cannot be measured from it here (see [Which classes a file holds](#which-classes-a-file-holds)).

<details>

<summary>

The code
</summary>

``` python
client = Client.open(API)
# Several deliveries can cover one place. Take the earliest item at the mouth that has a
# copc (ids sort by sheet, then year), and read only its delivery: two flights averaged
# into one grid would be neither.
at_mouth = sorted((i for i in client.search(
    collections=[COLLECTION],
    intersects={"type": "Point", "coordinates": [MOUTH_LON, MOUTH_LAT]}).items()
    if "copc" in i.assets), key=lambda i: i.id)
if not at_mouth:
    sys.exit("no item with a copc asset covers the mouth")
year = flight_year(at_mouth[0].properties)
crs = at_mouth[0].properties["proj:code"]
x0, y0 = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(MOUTH_LON, MOUTH_LAT)
found, box = window_items(client, crs, x0, y0)
items = [i for i in found if flight_year(i.properties) == year]
if any("copc" not in i.assets for i in items):
    # A laz-only tile would have to be downloaded whole; this demo is the windowed read.
    sys.exit("an item in the window has no copc asset: " +
             ", ".join(i.id for i in items if "copc" not in i.assets))
if any(i.properties["proj:code"] != crs for i in items):
    sys.exit("items in the window do not share one CRS")

xs, ys, zs, cls = [], [], [], []
fetched = size = 0
ground_only = []
for it in items:
    f = HttpRangeFile(it.assets["copc"].href)
    with CopcReader(f) as rd:
        # Only the COPC octree nodes that meet the window are fetched.
        pts = rd.query(bounds=Bounds(mins=np.array(box[:2]), maxs=np.array(box[2:])))
    xs.append(np.asarray(pts.x))
    ys.append(np.asarray(pts.y))
    zs.append(np.asarray(pts.z))
    cls.append(np.asarray(pts.classification))
    fetched += f.bytes_fetched
    size += f.size
    if len(pts) and np.all(cls[-1] == GROUND):
        ground_only.append(it.id)
x, y, z, c = (np.concatenate(a) for a in (xs, ys, zs, cls))
```

The whole script, with the gridding, is [`scripts/readme_dem.py`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/readme_dem.py).

</details>

## Canopy height: the forest along a stream

<img src="fig/maxan_chm.png" alt="Canopy height drawn over the bare ground of the Maxan Creek delta where the creek enters Bulkley Lake, built from lidar point clouds. The ground is coloured by its height above the lake, from dark blue at the lake's level through purple and orange to yellow at 5 m and above, and shaded to show its shape. The creek meanders across the delta to the lake, and narrow channels show as dark threads across the low ground of the delta, under a light green tint of shrubs. Stands of trees up to 40 m tall are dark green on the delta, the forested slope along the south edge is green over yellow, and curving lows mark the higher ground in the northwest. The lake on the east is light blue." width="100%" />

The Maxan Creek delta, where the creek enters Bulkley Lake. Along a stream, canopy height is the forest that shades the water, holds the banks and drops wood into the channel. The forest grows on ground that the creek has shaped, so the canopy is drawn over the bare ground, coloured by the ground’s height above the lake and shaded to show its relief. The creek meanders across the delta, and narrow channels thread the low ground between the stands of trees, under shrubs that are drawn as a light tint so the ground shows through them. Curving lows also mark the higher ground to the northwest. Two rough roads in BC’s Digital Road Atlas cross the forest on the slope to the south: the straight line, and a curve along the forest’s upper edge. The curved lows running down that slope are gullies. Of the cells on land, 37% stand at least 2 m and 12% at least 10 m; the tallest 1% exceed 27.8 m, to a maximum of 39.5 m. Light blue, 41% of the window, is the lake and the creek’s channel.

**How it was made.** A STAC search for a 1.2 × 1 km window, plus a 30 m margin, returned the 2 items covering it, both from the 093/093l/2019 delivery. None of them has a `copc` asset, so each `laz` was downloaded whole, once: 532 MB holding 107.8 million points, 23.4 million of them in the window. 33% of those are ground returns (class 2) and 67% are class 1, unclassified, which is where LidarBC leaves most of its vegetation. Only noise and withheld points are left out; nothing is chosen by vegetation class. With [lidR](https://r-lidar.github.io/lidRbook/), heights are measured above a triangulated surface of the ground returns, and the first returns are rasterised pit-free at 0.5 m. A cell with no ground return within 5 m, or no return at all, is left empty. The lake’s surface returns are class 1 and level with its shore, so without that test the lake would read 0 m like the meadow.

**The ground under it** is the same triangulated surface of the ground returns, on the same 0.5 m grid. Its colour is its height above the lake’s surface, 712.72 m, which is the median height of the returns over the water: from 0 at the lake to 5 m, which holds the delta, while the slope to the south runs past it. It is shaded as if lit from the northwest, with its relief exaggerated 4 times. Canopy of 2 m and up is drawn over it in greens, more opaque the taller it stands up to 15 m, and the ground’s shading runs through the canopy too. Each pixel of the figure is the average of the 0.5 m cells in its 1 m square, so a thin channel is not lost to sampling. LidarBC publishes a DEM for this delivery, and above the lake’s shore it is the same surface, but read as published it sits half a metre west and half a metre south of the points (see [research/dem_alignment.md](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/research/dem_alignment.md)), so the ground here is built from the points.

<details>

<summary>

The code
</summary>

``` r
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
# The bare ground on the same grid, and the lake's surface from the returns over the water,
# so the ground can be coloured by its height above the lake.
ground <- pc_readme_ground(las, box, res = CELL)
level <- round(pc_readme_water_level(las, chm), 2)
```

`pc_readme_chm()`, from [`scripts/readme_functions.R`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/readme_functions.R):

``` r
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
```

`pc_readme_ground()` and `pc_readme_water_level()`, from the same file:

``` r
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
#' Those cells have no ground return near them (`pc_readme_chm()`), so their other returns
#' (noise left out) are the water's surface, with the odd crown overhanging the shore, which the
#' median ignores. NA when the window holds no water.
pc_readme_water_level <- function(las, chm) {
  keep <- !las$Classification %in% c(2L, 9L, NOISE_CLASSES)
  if (!is.null(las$Withheld_flag)) keep <- keep & !las$Withheld_flag
  cell <- terra::cellFromXY(chm, cbind(las$X[keep], las$Y[keep]))
  wet <- !is.na(cell) & is.na(terra::values(chm, mat = FALSE)[cell])
  if (!any(wet)) return(NA_real_)
  stats::median(las$Z[keep][wet])
}
```

The whole script, with the figure, is [`scripts/readme_chm.R`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/readme_chm.R).

</details>

## The valley floor: old channels upstream

<img src="fig/maxan_rem.png" alt="The valley floors of Maxan Creek, Crow Creek and the Bulkley River around the west end of Bulkley Lake, from LidarBC's bare-earth elevation model, coloured by height above the nearest stream bed: dark blue at or below the bed through purple and orange to yellow at 3 m and above, and shaded to show the ground's shape. Maxan Creek's wide floodplain at the bottom left is crossed by meander scars and cut-off loops, Crow Creek winds along a narrower valley floor on the left, and the Bulkley River runs along the top. Curving old channels cross the cleared field west of the delta. Hills and terraces are yellow; Bulkley Lake on the right is light blue." width="100%" />

The delta in the canopy figure is the right-hand part of this 3.1 × 2.3 km view, where Maxan Creek meets Bulkley Lake. Further up the valley the old channels are clearer: Maxan Creek’s floodplain (bottom left) is crossed by meander scars and cut-off loops, Crow Creek winds along a narrower valley floor (left), and the Bulkley River runs along the top. Curving old channels also cross the cleared field west of the delta. The colour is height above the nearest stream bed, from 0 to 3 m, so one scale shows a valley floor that rises upstream; 48% of the land here lies less than 3 m above a stream bed.

**How it was made.** This view is wider than a demo should download point clouds for, so it reads the elevation model LidarBC made from the same 093/093l/2019 delivery, from the sister collection on the same API: the `stac-elevation-bc` item 093-093l-2019-dem-bc_093l040_xli1m_utm09_2019. Only the rows of the window and a 500 m margin around it were read, over HTTP, from the 638 MB file; its 1 m cells are averaged to 4 m. The streams are the Freshwater Atlas’s (Bulkley River, Crow Creek, Maxan Creek, Wiggins Creek and unnamed streams of Strahler order 2 and up). Every 10 m along each, the lowest ground within 15 m stands in for its bed, and open water, which the elevation model flattens to one level (found as level ground over 1 ha or more), counts as bed at its own level: 8,097 samples. A triangulated surface through them is the bed under 93% of the window; outside the samples, at its edges (1%), it is the inverse-distance mean of the three nearest samples. Both are built over that margin too, so the surface does not end at the window’s edge. Where either stands more than 1 m over the highest sample within about 150 m (taken on 40 m blocks), as where a stream on the high ground beyond a valley wall pulls it up over the valley floor, it is held there (6.3% of the window). The colour is each cell’s height above that bed; 5.3% of the land lies up to 2.6 m below it and is drawn with the bed. The shading is the elevation model’s own, with its relief exaggerated 4 times. The model sits half a metre west and half a metre south of the points (see [research/dem_alignment.md](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/research/dem_alignment.md)), which does not show at this scale and is not corrected here.

<details>

<summary>

The code
</summary>

``` r
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
# The window and a buffer around it, as far as the file reaches; only those rows are read
# from the file, over HTTP.
read <- c(max(box[1] - BUFFER, bb[1]), max(box[2] - BUFFER, bb[2]),
          min(box[3] + BUFFER, bb[3]), min(box[4] + BUFFER, bb[4]))
tif <- tempfile(fileext = ".tif")
sf::gdal_utils("translate", paste0("/vsicurl/", item$assets$dem$href), tif,
               c("-projwin", read[1], read[4], read[3], read[2]))
dem <- terra::rast(tif)

dem <- terra::aggregate(dem, CELL, mean)
water <- pc_readme_flat_water(dem, min_area = WATER_AREA)
# The streams, from the Freshwater Atlas.
# In BC Albers before the query: bcdata cannot translate a transform inside its filter.
aoi <- sf::st_as_sfc(sf::st_bbox(setNames(read, c("xmin", "ymin", "xmax", "ymax")),
                                 crs = sf::st_crs(crs))) |>
  sf::st_transform(3005)
streams <- bcdata::bcdc_query_geodata("WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP") |>
  bcdata::filter(bcdata::INTERSECTS(aoi)) |>
  bcdata::select(GNIS_NAME, STREAM_ORDER) |>
  bcdata::collect() |>
  sf::st_transform(crs)
streams <- streams[streams$STREAM_ORDER >= MIN_ORDER, ]
bed <- pc_readme_stream_bed(dem, streams, water = water, spacing = SPACING, reach = REACH)
rem <- pc_readme_rem(dem, bed, coarse = COARSE, above = ABOVE, near = NEAR)
source_bed <- terra::crop(attr(rem, "bed_source"), win)
# The figure is the window; the buffer only set the bed.
dem <- terra::crop(dem, win)
rem <- terra::crop(rem, win)
water <- terra::crop(water, win)
```

`pc_readme_stream_bed()`, `pc_readme_flat_water()` and `pc_readme_rem()`, from [`scripts/readme_functions.R`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/readme_functions.R):

``` r
pc_readme_stream_bed <- function(dem, lines, water = NULL, spacing = 10, reach = 15) {
  geom <- sf::st_cast(sf::st_geometry(sf::st_zm(lines)), "LINESTRING")
  pts <- sf::st_coordinates(sf::st_cast(sf::st_line_sample(geom, density = 1 / spacing), "POINT"))
  # A circle of `reach` m: 1 inside, NA outside, so the minimum is taken over the circle only.
  circle <- terra::focalMat(dem, reach, "circle")
  circle[circle > 0] <- 1
  circle[circle == 0] <- NA
  low <- terra::focal(dem, w = circle, fun = "min", na.rm = TRUE)
  bed <- data.frame(x = pts[, 1], y = pts[, 2],
                    z = terra::extract(low, pts[, 1:2, drop = FALSE])[[1]])
  if (!is.null(water)) {
    k <- which(terra::values(water, mat = FALSE) %in% TRUE)
    k <- k[(seq_along(k) - 1L) %% spacing == 0L]
    xy <- terra::xyFromCell(dem, k)
    bed <- rbind(bed, data.frame(x = xy[, 1], y = xy[, 2], z = terra::values(dem, mat = FALSE)[k]))
  }
  bed[!is.na(bed$z), ]
}

#' Open water in a hydro-flattened DEM: patches of exactly level ground of `min_area` m² or more
#'
#' A DEM made from lidar flattens each lake to one level, while no ground is level to the
#' millimetre over a hectare. Returns a logical raster on the grid of `dem`.
pc_readme_flat_water <- function(dem, min_area = 1e4) {
  span <- terra::focal(dem, w = 3, fun = \(x) max(x) - min(x))
  flat <- terra::classify(span == 0, cbind(0, NA))
  p <- terra::patches(flat, directions = 8)
  f <- terra::freq(p)
  big <- f$value[f$count * prod(terra::res(dem)) >= min_area]
  # On values: a SpatRaster's `%in%` does not dispatch unless terra is attached.
  terra::setValues(dem, terra::values(p, mat = FALSE) %in% big)
}

#' Height above the stream bed: `dem` minus a TIN through the bed samples
#'
#' The TIN is linear between samples, so between two streams the bed surface runs as a plane
#' rather than jumping at the line halfway between them. lidR leaves the cells beyond the
#' samples' hull empty, so there the bed is the inverse-distance mean of the three nearest
#' samples, on a grid `coarse` times the DEM's cell and interpolated back. Either surface can
#' rise far above the streams beside a cell, where a stream on the high ground beyond a valley
#' wall pulls it up over the valley floor; so a cell's bed is held to no more than `above` m over
#' the highest sample within `near` m, where there is one. Returns the height above the bed, with
#' an attribute `bed_source`: a raster on the grid of `dem`, 1 where the bed is the TIN, 2 the
#' nearest samples' mean, 3 either one held down.
pc_readme_rem <- function(dem, bed, coarse = 10, above = 1, near = 150) {
  pts <- data.table::data.table(X = bed$x, Y = bed$y, Z = bed$z, Classification = 2L)
  las <- suppressMessages(lidR::LAS(pts, crs = sf::st_crs(terra::crs(dem))))
  base <- suppressWarnings(lidR::rasterize_terrain(las, dem, lidR::tin()))
  g <- terra::rast(terra::ext(dem), resolution = coarse * terra::res(dem), crs = terra::crs(dem))
  from_far <- is.na(terra::values(base, mat = FALSE))
  if (any(from_far)) {
    v <- terra::vect(cbind(bed$x, bed$y), crs = terra::crs(dem))
    v$z <- bed$z
    diag <- sqrt(diff(terra::ext(dem)[1:2])^2 + diff(terra::ext(dem)[3:4])^2)
    far <- terra::interpIDW(g, v, "z", radius = diag, power = 1, maxPoints = 3)
    base <- terra::cover(base, terra::resample(far, dem, method = "bilinear"))
  }
  # The highest sample within `near` m: samples' maximum on the coarse grid, then a circle,
  # interpolated back smoothly so the cap has no steps.
  highest <- terra::rasterize(cbind(bed$x, bed$y), g, values = bed$z, fun = max)
  circle <- terra::focalMat(highest, near, "circle")
  if (nrow(circle) >= 2 * min(dim(highest)[1:2])) {
    # A window as wide as the grid (a small test grid): every cell takes the highest sample.
    highest <- terra::setValues(highest, max(bed$z))
  } else {
    circle[circle > 0] <- 1
    circle[circle == 0] <- NA
    highest <- terra::focal(highest, w = circle, fun = "max", na.rm = TRUE)
  }
  highest <- terra::resample(highest, dem, method = "bilinear")
  b <- terra::values(base, mat = FALSE)
  cap <- terra::values(highest, mat = FALSE) + above
  held <- !is.na(cap) & !is.na(b) & b > cap
  b[held] <- cap[held]
  rem <- dem - terra::setValues(dem, b)
  attr(rem, "bed_source") <- terra::setValues(dem, ifelse(held, 3L, ifelse(from_far, 2L, 1L)))
  rem
}
```

The whole script, with the figure, is [`scripts/readme_rem.R`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/readme_rem.R).

</details>

## What an item holds

| asset | what it is |
|----|----|
| `laz` | the province’s file, on `nrs.objectstore.gov.bc.ca`. Every item has one, and it is the source of record |
| `copc` | the [Cloud Optimized Point Cloud](https://copc.io/) that Natural Resources Canada’s [CanElevation](https://open.canada.ca/data/en/dataset/7069387e-9986-4297-9f55-0288e9676947) series publishes under the same file name. A minority of items have one, from four CanElevation projects |

**A `copc` asset is linked only after its header has been checked**, not on the file name alone: it must have the same point count, the same horizontal CRS, and a box within 0.05 m of the LidarBC file’s. That test cannot see a reclassified re-delivery published under the same name. A COPC can also be a different LAS version and point format from its source, so the item’s `pc:schemas` describe the `laz`, and the `copc` asset carries its own `las:version` and `las:point_format`. Which CanElevation projects republish LidarBC, and how that was measured, is in [`research/canelevation_overlap.md`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/research/canelevation_overlap.md).

Items carry the [pointcloud](https://github.com/stac-extensions/pointcloud), [projection](https://github.com/stac-extensions/projection) and [file](https://github.com/stac-extensions/file) extensions. They also carry `las:` fields for facts about the LAS format and `lidarbc:` fields for LidarBC’s paths and file names. An item with a class list also carries the [classification](https://github.com/stac-extensions/classification) extension.

An item’s date comes from its file name wherever the build can read the date and trust it: the day (`datetime`); the first and last day flown, where the name carries two (`start_datetime` / `end_datetime`); or the year, where the name carries only a year. Otherwise the item spans the year of its directory, for example where a delivery’s file names carry processing dates. `lidarbc:datetime_source` says whether the date came from the file name or the directory, and [`research/filename_dates.md`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/research/filename_dates.md) has the rules and how they were measured.

Each item names its delivery in `lidarbc:delivery` (`<block>/<sheet>/<year>`, such as `092/092g/2016`), which keeps one delivery apart from another where several cover the same place. Every [stac-elevation-bc](https://github.com/NewGraphEnvironment/stac_dem_bc) item from a LidarBC delivery carries the same key (its province-wide mosaics do not), and this collection links it as `related`.

### Which classes a file holds

A LAS header does not say which classes a file holds, and a few files lack what you would assume. Some have no ground returns at all, so they give no bare-earth surface, and some have only ground. The build samples the points of every file and reads in full each one the sample flags. Those items list every class present, with its point count, in the `laz` asset’s `classification:classes`. A sample can miss a class but never add one, so an item without a list holds ground and at least one class besides ground, noise and water, except for a few files the sampler cannot read. It says nothing about how much of each: look at the points before relying on their ground or vegetation classes. Most of LidarBC’s vegetation is unclassified (class 1). Water can be class 1 too, as at Bulkley Lake above. The method and what it found are in [`research/laz_classes.md`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/research/laz_classes.md).

## What is indexed

Every point-cloud file LidarBC publishes under `<block>/<sheet>/<year>/pointcloud/`, with two exceptions:

- a few files whose header is faulty, or that lie outside the mapsheet they are filed under
- eight 2017 deliveries that state no coordinate system

Each exception is named, with its reason, in [`scripts/catalogue_build.py`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/catalogue_build.py) (`EXCLUDE`, `EXCLUDE_DELIVERIES`).

The `.laz` files under `dsm/` are not indexed. In every tile compared, they were an RGB-colourised copy of the point cloud, not a surface model ([`research/laz_header_read.md`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/research/laz_header_read.md)).

Each month the catalogue is rebuilt from the province’s listing and any new files are published; the API serves them once they are registered. [NEWS.md](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/NEWS.md) says what each release published.

This page was rendered from catalogue version 0.5.0 on 2026-10-19.

## Query it

Use [`bcdata`](https://github.com/bcgov/bcdata) for an area of interest and `rstac` to search the collection for the items intersecting it. Below: every indexed point cloud in the Similkameen River watershed group.

``` r
# Freshwater Atlas watershed groups, by the record's permanent id.
aoi <- bcdata::bcdc_query_geodata("51f20b1a-ab75-42de-809d-bf415a0f9c62") |>
  bcdata::filter(WATERSHED_GROUP_CODE == "SIML") |>
  bcdata::collect() |>
  sf::st_transform(crs = 4326)

r <- rstac::stac("https://images.a11s.one/") |>
  rstac::stac_search(
    collections = "stac-pointcloud-bc",
    intersects = jsonlite::fromJSON(
      geojsonsf::sf_geojson(aoi, atomise = TRUE, simplify = FALSE),
      simplifyVector = FALSE
    )$geometry,
    limit = 1000
  ) |>
  rstac::post_request() |>
  rstac::items_fetch()
```

A sample of what it returns is below, 5 items with a copc asset and 5 without. Every item it returned, with download links for both assets, is in the table at <https://www.newgraphenvironment.com/stac_pointcloud_bc/>.

| item | points | laz | copc |
|:---|---:|:---|:---|
| 082-082e-2019-pointcloud-bc_082e002_1_2_1_xyes_8_utm11_2019 | 12,568,291 | [bc_082e002_1_2_1_xyes_8_utm11_2019.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2019/pointcloud/bc_082e002_1_2_1_xyes_8_utm11_2019.laz) | [bc_082e002_1_2_1_xyes_8_utm11_2019.copc.laz](https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/BC/Riverine_Floodplain_UTM11_2019/bc_082e002_1_2_1_xyes_8_utm11_2019.copc.laz) |
| 082-082e-2019-pointcloud-bc_082e002_1_2_2_xyes_8_utm11_2019 | 41,779,961 | [bc_082e002_1_2_2_xyes_8_utm11_2019.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2019/pointcloud/bc_082e002_1_2_2_xyes_8_utm11_2019.laz) | [bc_082e002_1_2_2_xyes_8_utm11_2019.copc.laz](https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/BC/Riverine_Floodplain_UTM11_2019/bc_082e002_1_2_2_xyes_8_utm11_2019.copc.laz) |
| 082-082e-2019-pointcloud-bc_082e002_1_2_3_xyes_8_utm11_2019 | 18,773,358 | [bc_082e002_1_2_3_xyes_8_utm11_2019.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2019/pointcloud/bc_082e002_1_2_3_xyes_8_utm11_2019.laz) | [bc_082e002_1_2_3_xyes_8_utm11_2019.copc.laz](https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/BC/Riverine_Floodplain_UTM11_2019/bc_082e002_1_2_3_xyes_8_utm11_2019.copc.laz) |
| 082-082e-2019-pointcloud-bc_082e002_1_2_4_xyes_8_utm11_2019 | 45,334,959 | [bc_082e002_1_2_4_xyes_8_utm11_2019.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2019/pointcloud/bc_082e002_1_2_4_xyes_8_utm11_2019.laz) | [bc_082e002_1_2_4_xyes_8_utm11_2019.copc.laz](https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/BC/Riverine_Floodplain_UTM11_2019/bc_082e002_1_2_4_xyes_8_utm11_2019.copc.laz) |
| 082-082e-2019-pointcloud-bc_082e002_1_4_1_xyes_8_utm11_2019 | 15,093,616 | [bc_082e002_1_4_1_xyes_8_utm11_2019.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2019/pointcloud/bc_082e002_1_4_1_xyes_8_utm11_2019.laz) | [bc_082e002_1_4_1_xyes_8_utm11_2019.copc.laz](https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/BC/Riverine_Floodplain_UTM11_2019/bc_082e002_1_4_1_xyes_8_utm11_2019.copc.laz) |
| 082-082e-2018-pointcloud-bc_082e002_4_4_4_xyes_12_utm11_2018 | 110,649,896 | [bc_082e002_4_4_4_xyes_12_utm11_2018.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2018/pointcloud/bc_082e002_4_4_4_xyes_12_utm11_2018.laz) |  |
| 082-082e-2018-pointcloud-bc_082e003_1_2_2_xyes_12_utm11_2018 | 44,603,740 | [bc_082e003_1_2_2_xyes_12_utm11_2018.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2018/pointcloud/bc_082e003_1_2_2_xyes_12_utm11_2018.laz) |  |
| 082-082e-2018-pointcloud-bc_082e003_1_2_3_xyes_12_utm11_2018 | 59,624,858 | [bc_082e003_1_2_3_xyes_12_utm11_2018.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2018/pointcloud/bc_082e003_1_2_3_xyes_12_utm11_2018.laz) |  |
| 082-082e-2018-pointcloud-bc_082e003_1_2_4_xyes_12_utm11_2018 | 53,470,524 | [bc_082e003_1_2_4_xyes_12_utm11_2018.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2018/pointcloud/bc_082e003_1_2_4_xyes_12_utm11_2018.laz) |  |
| 082-082e-2018-pointcloud-bc_082e003_1_3_4_xyes_12_utm11_2018 | 56,097,375 | [bc_082e003_1_3_4_xyes_12_utm11_2018.laz](https://nrs.objectstore.gov.bc.ca/gdwuts/082/082e/2018/pointcloud/bc_082e003_1_3_4_xyes_12_utm11_2018.laz) |  |

<details>

<summary>

Read a file’s header without downloading it
</summary>

A LAS file starts with a public header, at most 375 bytes, holding its version, point format, point count and bounding box. One HTTP range request reads it from either asset, whatever the file’s size. `pc_readme_header()` in [`scripts/readme_functions.R`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/scripts/readme_functions.R) does it with `httr2` and base R, with no LAS library, and checks the result against the item:

``` r
it <- r$features[order(vapply(r$features, \(f) f$id, ""))] |>
  Filter(f = \(f) !is.null(f$assets$copc)) |>
  (\(x) x[[1]])()

h_laz <- pc_readme_header(it$assets$laz$href)
h_copc <- pc_readme_header(it$assets$copc$href)

# Same point count as the item's `pc:count`, and a box within 0.05 m of its `proj:bbox`.
off_laz <- pc_readme_header_check(h_laz, it)
off_copc <- pc_readme_header_check(h_copc, it)
```

| field                          |                   laz |                  copc |
|:-------------------------------|----------------------:|----------------------:|
| LAS version                    |                   1.4 |                   1.4 |
| point format                   |                     6 |                     6 |
| points                         |            12,568,291 |            12,568,291 |
| min x, y                       | 300151.00, 5431033.85 | 300151.00, 5431033.85 |
| max x, y                       | 300746.43, 5432444.86 | 300746.43, 5432444.86 |
| offset from the item’s box (m) |                 0.000 |                 0.000 |
| bytes read / file size         |      375 / 51,835,294 |      375 / 77,720,976 |

The item is 082-082e-2019-pointcloud-bc_082e002_1_2_1_xyes_8_utm11_2019. Both files are LAS 1.4 point format 6, with the same count and box: CanElevation’s copy of the province’s file, reorganised as a COPC so that one region or one level of detail can be read without the rest.

</details>

## Sister collections on the same endpoint

- [`stac_dem_bc`](https://github.com/NewGraphEnvironment/stac_dem_bc) — the DEM and DSM rasters of the same LidarBC deliveries (`stac-elevation-bc`)
- [`stac_floodplains_bc`](https://github.com/NewGraphEnvironment/stac_floodplains_bc) — floodplain land-cover change (`stac-floodplains-bc`)
- [`stac_airphoto_bc`](https://github.com/NewGraphEnvironment/stac_airphoto_bc) — historic airphoto thumbnails, 1967–2019 (`stac-airphoto-bc`)
- [`stac_uav_bc`](https://github.com/NewGraphEnvironment/stac_uav_bc) — UAV imagery, organized by watershed (`stac-imagery-uav-bc`)

## Build and maintain

The catalogue is built in Python. Items are created by pure functions (`scripts/laz_item.py`) from a file’s href and header, and what the build found about its delivery, its CanElevation copy and its classes. The item JSON is published to `s3://stac-pointcloud-bc`, and [stacs](https://github.com/NewGraphEnvironment/stacs) registers and verifies it (`stacs.toml`).

``` bash
uv sync
uv run pytest tests/ -q
bash scripts/cache_sync.sh pull                                     # the shared read caches
PYTHONPATH=scripts uv run python scripts/catalogue_build.py        # -> data/build/
bash scripts/cache_sync.sh push
uv run python scripts/collection_version.py --version X.Y.Z        # release only
bash scripts/s3_sync.sh --dryrun && bash scripts/s3_sync.sh        # changed items, then collection.json
uv run stacs verify --config stacs.toml
uv run stacs register --config stacs.toml --mode drift            # from a tailnet machine
```

A [monthly GitHub Actions run](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/.github/workflows/update.yml) rebuilds the catalogue on the 6th and publishes what changed. Registration is not in CI: it is run by hand from a machine that can reach the host. [`maintaining.md`](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/maintaining.md) covers the rest: what makes a build refuse, the shared caches, and how to re-render this page.

## Licence

The scripts are [MIT](https://github.com/NewGraphEnvironment/stac_pointcloud_bc/blob/main/LICENSE). The catalogue is published as `CC-BY-4.0`, with the Province of British Columbia as producer and licensor, NRCan as a host and New Graph Environment as processor (the collection’s `license` and `providers`, in its [collection.json](https://stac-pointcloud-bc.s3.us-west-2.amazonaws.com/collection.json)). Each `copc` asset is distributed by NRCan under the Open Government Licence – Canada, as its description says.
