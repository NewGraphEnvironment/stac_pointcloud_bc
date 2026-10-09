# Findings — README.Rmd landing page served on GitHub Pages, like stac_dem_bc (#9)

## Issue context

**If we do it:** the collection has a landing page like its sisters, with a write-up, a working example and a figure. Someone arriving from images.a11s.one or a sister repo can see what `stac-pointcloud-bc` holds and query it in a minute. **If we never do:** the README stays a build manual, and the GitHub Pages URL does not exist, so nothing links here.

## Model: stac_dem_bc

- `README.Rmd` renders twice from one source:
  - `github_document` → `README.md` (`rmd_on = FALSE`);
  - `html_document` → `index.html` (`rmd_on = TRUE`).
- A `build` chunk with `eval = FALSE` holds both render calls.
- An `update_query` param gates the live API query, and its results are saved so a rebuild does not need the network.
- Pages serves `main` at `/`, at https://www.newgraphenvironment.com/stac_dem_bc/, and the repo's About carries that URL. No workflow renders it; it is re-knit by hand.
- Figures live in `fig/`.

## Scope

- [ ] **`README.Rmd`, rendering to `README.md` and `index.html`.** Same params and build chunk as stac_dem_bc.
  - **Write-up:** what the collection is (one item per LidarBC `.laz`, footprint, count and CRS from the header), what is indexed so far (link NEWS.md rather than restating counts or versions), and the `copc` asset (CanElevation's COPC under the same file name, header-checked; `research/canelevation_overlap.md`).
- [ ] **Sister collections on images.a11s.one:** `stac-elevation-bc` (the DEM/DSM rasters of the same deliveries), `stac-floodplains-bc`, `stac-airphoto-bc`, `imagery-uav-bc-prod`.
- [ ] **Simple example:**
  1. Search `stac-pointcloud-bc` for an area of interest with `rstac`, as the sisters do.
  2. Tabulate the items with their `laz` and `copc` hrefs.
  3. Read one header remotely.

  Results are saved under `update_query`.
- [ ] **Figure.** Item footprints for the indexed mapsheet-years, with the items carrying a `copc` asset marked. Built by a script, saved to `fig/`.
- [ ] **Pages:** enable from `main` at `/`, check the page serves, and set the repo's About URL and description.
- [ ] **stac_dem_bc:** add `stac-pointcloud-bc` to its sister list. That is a PR there, not here.

## Open questions for the plan

- **R toolchain in a Python repo.** The example and the render are R (`rstac`, `rmarkdown`), as in every sister. The repo currently has no R dependencies. Pin them (e.g. `renv`), or document `install.packages()` and accept drift?
- **Build manual.** The current README content (build, publish, register) moves to a section of the Rmd, or to `docs/`.

## Plan-mode exploration (2026-10-09)

- **stac_floodplains_bc is the better model than stac_dem_bc** for mechanics, at
  `40b75ca`: `rmd_on` defaults FALSE (an accidental knit can't put a widget in README.md),
  `set.seed` + `htmlwidgets::setWidgetIdSeed` so a re-render is a no-op, badges md-only
  (`self_contained` would fetch them), helpers in `scripts/readme_functions.R` with
  `my_dt_table`/`my_tab_caption_rmd` copied in (no staticimports), one cache rds, figure
  written by a helper under `update_query`, and a render that stops on a missing cache.
  stac_dem_bc contributes the page shape (write-up, query, table, sisters).
- **R available here:** rstac 1.0.1, rmarkdown, DT, sf, ggplot2, bcdata, bcmaps,
  geojsonsf, httr2. **No lidR/rlas, no PDAL.** So the header read is a `Range: bytes=0-374`
  request with `httr2` and the LAS public header parsed with `readBin` — which is also the
  point the page makes: no download, no LAS library. The objectstore answers ranges with
  206 without advertising them (`scripts/laz_remote.py`).
- **Live:** 5 collections on images.a11s.one, matching the issue's four sisters plus this
  one. stac_orthophoto_bc is private and not on the endpoint — left out.
- **Indexed (build):** 9,649 items in 11 mapsheet-years; `copc` on 1,964 in four of them
  (`092g/2016` 1,155, `092h/2016` 420, `082e/2019` 332, `082l/2019` 57).
- Repo About today: description set, homepage empty. Pages: not enabled.

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `las_u32` failed on `0x80000000`: `readBin(size = 4)` returns `NA_integer_` for exactly 2^31, so `if (v < 0)` errored | Sum the four bytes as doubles; pinned by a test at 2^31 |

## Phase 1: header reader (2026-10-09)

- Fixtures are the first 375 bytes of three real files, fetched with `curl -r 0-374`
  (all three answered 206): LAS 1.2 format 1 LAZ (`092g005_1_2_2`, 2016), its CanElevation
  COPC (LAS 1.4 format 6, legacy count 0, 64-bit count 3,957,849), and a LAS 1.4 format 1
  LAZ (`082e003_1_4_1`, 2018) whose legacy and 64-bit counts agree.
- Expected values are laspy's, from `data/build/headers.jsonl` and `copc_headers.jsonl`.
- Restored bugs: reading the legacy count on 1.4 fails 1 test (the COPC; the 1.4 format-1
  file carries both counts, so only the COPC fixture can see it); the unmasked format byte
  fails 3.

## Plan review (Plan agent, 2026-10-09, returned 21:07Z)

Folded in, each checked before acting:

- **The API sends no `numberMatched`** (probed: `POST /search` returns `numberReturned` only).
  The completeness guard compares the fetched ids with the bucket's collection.json
  `rel: item` links as sets, both ways, plus API vs bucket version (`pc_readme_fetch()`).
  `items_fetch()` pages: 9,649 in ~36 s, 251 MB in memory; only a slim summary is cached
  (`data/readme_cache.rds`, 6 KB).
- **A root DESCRIPTION would reroute releases** — confirmed in
  `soul/skills/gh-pr-merge/SKILL.md`: `Type: Project` selects the manifest route
  (`SKIP_BUMP=1 SKIP_TAG=1`, "the release script cuts the tag"), and this repo has no
  release script, so catalogue releases would stop being tagged. The manifest moved to
  `scripts/DESCRIPTION` (`pak::local_install_dev_deps("scripts")`); the user's decision —
  a DESCRIPTION, no renv — stands.
- `pc_readme_header()` now reads the status before the body (`req_perform_connection`), so a
  200 is refused without downloading the file; probed against `images.a11s.one/collections`
  (answers 200 to a range): refused.
- `.nojekyll`; knitr intermediates in `.gitignore`; absolute GitHub links for `.md` targets
  (Pages serves `.md` as `text/markdown`).
- Figure: copc drawn last (082e/082l years overlap), one label per mapsheet.
- Not taken: a BC inset map (the axes carry lat/long, and the extent is the point);
  printing the reader inline (the page links the function file instead).

## Example AOI (2026-10-09)

Items per watershed group, from all 9,649 footprints (`st_intersects`): every group with copc
also has laz-only items. Chosen: **Similkameen River (SIML)**, 306 items, 213 with `copc`
(082e/2018 and 082e/2019). The render `stopifnot`s that the result holds both kinds.
Runners-up: Fraser Canyon 283/89, Squamish 334/72, Kettle River 369/119.

## Render determinism

md (`update_query = TRUE`) → html (FALSE) → md (FALSE) → html (FALSE): README.md and
index.html byte-identical between the two cache-only passes. DT ids seeded.
