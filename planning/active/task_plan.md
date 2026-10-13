# Task: Landing page: say why it is useful first, drop counts that go stale, trim reader-facing detail (#24)

The landing page (`README.Rmd` -> `README.md`, `index.html`) opens with what the catalogue is made of rather than why anyone would want it, prints counts the monthly update (#4) makes stale, says "client" where it means people and software, and carries maintainer detail a reader has to scroll past. Decided at the plan gate: drop the per-mapsheet-year table; keep a short build section at the end and move the rest to `maintaining.md`.

## Phase 1: Claim ledger
- [x] Write a findings table: each claim the page keeps, its source (code line, live API/bucket, research file, external doc), its verdict, and the date checked. Carry over the 2026-10-13 audit from #24.
- [x] Check the new opening's claims:
  - the year range comes from the collection's temporal extent and `data/pointcloud_groups.json`
  - "flown more than once" is shown at tile level for the two demo places (Kanaka 092g, Maxan 093l) from `data/readme_dem.json` and `data/readme_chm.json` items, not inferred from mapsheet-years
  - the CHM statement comes from stac_dem_bc#47
- [ ] Commit (findings + checkbox).

## Phase 2: Rewrite `README.Rmd`
- [ ] Opening: why it is useful (the draft above), then what it is, then how to reach it (endpoint, rstac / pystac-client / QGIS 3.42+). No "client" meaning a customer.
- [ ] Remove every count the monthly run can change:
  - the `items-` badge
  - `n_items`, the mapsheet-years and `n_copc` in prose
  - "9 minutes to check 174,282 items"
  - "253 … 38" in the class paragraph
  - the per-mapsheet-year table and its summary
  - the Similkameen result count
  - and any computation in the `query` chunk that only those used
- [ ] Describe the copc share in words: CanElevation republishes a minority of files, from four of its projects.
- [ ] DEM and CHM sections: lead each with what the figure shows and why it matters for a watershed. Keep the method and the demo's own numbers after that, shortened.
- [ ] Move the class-list caveat out of the DEM section into "What an item holds", cut to what a user needs: a header cannot say which classes a file holds; low-density files were screened, and the ones with no ground (or only ground) carry `classification:classes`; some unscreened files are like that too. Link `research/laz_classes.md`.
- [ ] Fix the three inaccuracies:
  - `lidarbc:delivery`: say the stac-elevation-bc items will carry the same key from stac_dem_bc's next full rebuild (stac_dem_bc#55)
  - the full list of extensions
  - "one item per point-cloud file", with the exclusions in one sentence
- [ ] Cut the `nge:` rename history (NEWS has it) and the 11-file breakdown (`catalogue_build.py` `EXCLUDE` has it), each linked once.
- [ ] Keep "Read a header without downloading the file", in a `<details>` block.
- [ ] End with a short "Build and maintain" section: the command block, one paragraph on the monthly update, and a link to `maintaining.md`.
- [ ] Commit.

## Phase 3: `maintaining.md`
- [ ] Move in from the page:
  - what makes the monthly build refuse
  - cache sync and the `push` refusal
  - the `HEADER_VERSION` re-read cost
  - the 60-day schedule disable
  - the `--limit` build directory
  - `s3_sync.sh`'s digest-only upload and that it deletes nothing
  - the README render instructions (DEM demo dependency group, CHM download)
- [ ] Text moves as it stands. Any number in it says when it was measured.
- [ ] Commit.

## Phase 4: Render and check
- [ ] `/code-check` on the diff (`README.Rmd`, `maintaining.md`).
- [ ] Render both targets with the `build` chunk (`README.md` with `update_query = TRUE`, then `index.html`). Run `tests/readme_functions_test.R`.
- [ ] Mechanical check: grep the rendered `README.md` and `index.html` for `174`, `13,970`, `mapsheet-years`, `client`, and badge counts. Expect nothing beyond the dated demo figures.
- [ ] Read the rendered `README.md` top to bottom against the claim ledger.
- [ ] Commit the renders.

## Phase 5: Out of scope, filed
- [ ] The collection's `related` link title ("match items on lidarbc:delivery") is not true until stac_dem_bc republishes. Note it on stac_dem_bc#55 or file a follow-up there, rather than republishing `collection.json` here.

## Validation

- [ ] Tests pass
- [ ] `/code-check` clean (each commit, or once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
