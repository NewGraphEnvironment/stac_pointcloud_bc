# stac_pointcloud_bc

STAC catalogue of [LidarBC](https://lidar.gov.bc.ca/) point clouds (`.laz`), published as
the `stac-pointcloud-bc` collection at
<https://images.a11s.one/collections/stac-pointcloud-bc>.

The `.laz` stay on the province's objectstore (`nrs.objectstore.gov.bc.ca/gdwuts`). This
repo builds one STAC item per file from its LAS header, publishes the item JSON to
`s3://stac-pointcloud-bc`, and registers it with
[stacs](https://github.com/NewGraphEnvironment/stacs). The raster products of the same
deliveries (DEM, DSM) are the `stac-elevation-bc` collection, built by
[stac_dem_bc](https://github.com/NewGraphEnvironment/stac_dem_bc).

## What is indexed

| | files | indexed |
|---|---|---|
| `pointcloud/*.laz` in the 11 mapsheet-years with no raster DSM | 9,650 | 9,649 (one faulty header excluded) |
| the rest of `pointcloud/*.laz` | 165,667 | not yet |
| `dsm/*.laz` (in the tiles compared, an RGB copy of the point cloud; #3) | 6,391 | no |

See [NEWS.md](NEWS.md) for what each release published and
[research/](research/README.md) for how the source was measured.

## Build, publish, register

```bash
uv sync
uv run pytest tests/ -q
PYTHONPATH=scripts uv run python scripts/catalogue_build.py        # -> data/build/
uv run python scripts/collection_version.py --version X.Y.Z        # release only
bash scripts/s3_sync.sh --dryrun && bash scripts/s3_sync.sh        # items, then collection.json
uv run stacs verify --config stacs.toml
uv run stacs register --config stacs.toml --mode drift            # from a tailnet machine
```

`catalogue_build.py --limit N` writes to `data/build-limit/`, never `data/build/`, so a
development build cannot be published.
