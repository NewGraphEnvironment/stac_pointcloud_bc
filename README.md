# stac_pointcloud_bc

STAC catalogue of [LidarBC](https://www2.gov.bc.ca/gov/content/data/geographic-data-services/lidarbc)
point clouds (`.laz`), published as the `stac-pointcloud-bc` collection at
<https://images.a11s.one/collections/stac-pointcloud-bc>.

The `.laz` stay on the province's objectstore (`nrs.objectstore.gov.bc.ca/gdwuts`). This
repo builds one STAC item per file, publishes the item JSON to `s3://stac-pointcloud-bc`,
and registers it with [stacs](https://github.com/NewGraphEnvironment/stacs).

The raster products from the same deliveries (DEM, DSM) are the `stac-elevation-bc`
collection, built by [stac_dem_bc](https://github.com/NewGraphEnvironment/stac_dem_bc).
