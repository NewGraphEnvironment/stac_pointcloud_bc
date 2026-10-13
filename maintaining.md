# Maintaining stac-pointcloud-bc

What a maintainer needs beyond the build commands on the [landing page](README.md#build-and-maintain). The source facts and the rules the build follows are in [`CLAUDE.md`](CLAUDE.md), and what is known about the source, and how it was measured, is in [`research/`](research/README.md).

## Building and publishing

`catalogue_build.py --limit N` writes to `data/build-limit/`, never `data/build/`, so a development build cannot be published.

`s3_sync.sh` uploads only the items whose digest the bucket does not already hold, and `collection.json` only when an item goes or the collection changed, so publishing an unchanged build sends nothing (9 minutes to check the 174,282 items of 0.3.0, measured 2026-10-11). It deletes nothing: an object the build no longer makes is reported and left.

## Monthly update

[`.github/workflows/update.yml`](.github/workflows/update.yml) runs on the 6th of each month, and on dispatch. It pulls the build's read caches from `s3://stac-pointcloud-bc/build-cache/` (headers and class samples, about 20 MB in October 2026), rebuilds the whole catalogue from them, saves them back, and publishes what changed. A month with nothing new publishes nothing, and the collection keeps its release `version`. A month that adds items publishes a `collection.json` with no `version` until the next release stamps one. More than 40,000 items in one run is refused as a rewrite, which is a release, published from a local build; dispatch with `dryrun` to plan without uploading. Registration is not in CI, because it needs the tailnet: run `stacs register --mode drift`, then `stacs verify`, from a machine that can reach the host. The run's summary gives the commands.

A red run is usually the build refusing something a person should look at (tests, a missing cache, the build's time limit and `stacs audit` can also fail it). It refuses a mapsheet-year listed under 90% of its recorded count, a block directory with no NTS grid, a key or file name it cannot place, a file name whose date is no date, two files with one item id, a header that cannot be read or makes no item, an `EXCLUDE` or `EXCLUDE_DELIVERIES` entry whose files no longer show their fault, a CanElevation project listed short, a COPC pairing or non-copy count that changed, a CanElevation name matched by two files on either side, an item that fails validation, and a class read the screen requires. That last one can follow growth in an existing mapsheet-year, which moves its density screen; record it with `catalogue_build.py --classes-record`. A network error is retried by re-running, which reads only what is missing. A new mapsheet-year is built, not refused, unless its file names match CanElevation COPC (the pairing check), and is recorded with `--groups-record` at the next release.

A local build shares the caches: `cache_sync.sh pull` before it and `push` after. `push` refuses to replace a cache the monthly run has written since this tree last pulled. A change to `laz_item.HEADER_VERSION` makes every header be read again (about 2.5 hours in October 2026), so build that once locally and push it before the next monthly run. GitHub disables the schedule of a public repository after 60 days without repository activity; re-enable it under Actions.

## The landing page

`README.md` and `index.html` (the GitHub Pages landing page) are generated from `README.Rmd`; edit that, never the outputs. The page is R. [`scripts/DESCRIPTION`](scripts/DESCRIPTION) lists its packages; it is a manifest, not a package.

```bash
Rscript -e 'pak::local_install_dev_deps("scripts")'
Rscript -e 'testthat::test_file("tests/readme_functions_test.R")'
```

The DEM demo is Python, in its own dependency group: `uv sync --group readme`. The CHM demo is R. Then run the two `rmarkdown::render()` calls in the `build` chunk at the top of `README.Rmd`. The `README.md` render with `update_query = TRUE` queries the API, runs `scripts/readme_dem.py` and `scripts/readme_chm.R`, and refreshes `data/readme_cache.rds`, `data/readme_dem.json`, `fig/kanaka_dem.png`, `data/readme_chm.json` and `fig/maxan_chm.png`; the `index.html` render reads them. The CHM demo's first run downloads about 0.5 GB of `.laz` into `data/readme_laz/` (not committed), and later runs reuse it.

The page prints no count of the collection, because the monthly update would make it stale (#24). The demos' own numbers describe the figures beside them, as of the render date the page states.
