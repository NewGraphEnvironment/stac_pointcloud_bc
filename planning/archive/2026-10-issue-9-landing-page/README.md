## Outcome

`stac-pointcloud-bc` has a landing page: `README.Rmd` renders `README.md` and `index.html`,
served by GitHub Pages from `main` at <https://www.newgraphenvironment.com/stac_pointcloud_bc/>.
It leads with what the collection is for, as the user redirected mid-run: a STAC search for a
window on the lower Kanaka Creek, a read of only that window from each item's CanElevation COPC,
and a hillshaded bare-earth DEM from the ground returns (`scripts/readme_dem.py`). Below that are
an rstac search of a watershed group, a 375-byte LAS header read in R with no LAS library, and the
build manual. A coverage map was built and dropped (the province is about to be registered).
Houston was asked for first; it is not indexed yet (#2) and has no COPC. R dependencies are a
manifest in `scripts/DESCRIPTION`, not at the root, because a root `Type: Project` DESCRIPTION
moves `/gh-pr-merge` onto a release route that never tags this repo. The review lesson repeated
#6's: the defects that survived longest were sentences stating a number their code did not
produce, and the loop ended on an enumeration of every claim on the page (findings.md,
"Code-check").

## Measurement

- Full fetch of the collection with rstac: 9,649 items, ~36 s, 251 MB in memory; the API sends
  no `numberMatched`, so completeness is the id set against the bucket's collection.json.
- Kanaka window (1.6 × 1.2 km, 4 items, 2016): 74 MB read of 434 MB (17%), 6.8 M points,
  1.5 M ground, ~2 min (`data/readme_dem.json`). One of the four tiles is ground-only (#10).
- Renders: md from the live query == md from the cache; two cached renders byte-identical.
- Declared environment sufficient, measured by code-check round 3 in a library holding only
  `scripts/DESCRIPTION`'s packages (109; no reticulate): all renders and tests pass.

Durable versions: `research/canelevation_overlap.md` ("Reading a window from a COPC over
HTTPS"), `research/laz_header_read.md` ("some deliveries are ground-only").

## Evidence

The plan review and three code-check rounds in this directory (`review-*.md`).

Closed by: PR (to be opened from branch 9-readme-rmd-landing-page-served-on-github)
