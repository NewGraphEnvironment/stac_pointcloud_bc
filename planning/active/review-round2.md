# Code-check round 2: branch 24-landing-page-say-why-it-is-useful-first (base 9c0a9f6, HEAD da58572)

Reviewed 2026-10-13. Scope: README.Rmd, maintaining.md, scripts/readme_functions.R,
tests/readme_functions_test.R, and the round 1 fixes in da58572. Claims were checked against
scripts/catalogue_build.py, scripts/laz_item.py, scripts/s3_publish.py, scripts/cache_sync.sh,
.github/workflows/update.yml, research/filename_dates.md, data/readme_dem.json, the local 0.3.0
build in data/build/items (174,282 items, which matches research/filename_dates.md's counts),
stac_dem_bc's main branch (via gh) and the live API.

## Findings

No bugs and no security issues. The R change is sound: `pc_readme_version()` falls back to
`NA_character_`, the inline text handles NA, and nothing still refers to the removed functions.
Five claims are stronger than the code or data support, and two maintainer pointers are stale.

- **[claim] README.Rmd:186.** This is the one that matters most. The date paragraph covers
  only day tokens. Measured over the 0.3.0 build:

  | date kind | `datetime_source` | items |
  |---|---|---:|
  | one day (`datetime`) | filename | 64,372 |
  | range of days | filename | 44,744 |
  | whole year, from a year-only name (`_2016.laz`) | filename | 55,538 |
  | whole year, untrusted delivery | path | 8,762 |
  | whole year, no date token at all | path | 866 |

  `laz_item.date_parse` turns a `yyyy` token into a 1 Jan to 31 Dec range with source
  `filename`. So 55,538 items (32%) have a date taken from the file name that is a year, not
  "the day flown". The page's only stated reason for a year span ("because some deliveries name
  files with processing dates") explains 8,762 of the 65,166 year-span items. A reader who sees
  `datetime_source: filename` on a whole-year item finds nothing on the page that explains it.
  The 866 items with no date token have a date that does not come from the file name, although
  no name in their delivery disagrees. Also, `research/filename_dates.md` ("Not established")
  says single-day names were probed only as same-day pairs, so "That is the day flown" is
  unmeasured for `yymmdd`/`yyyymmdd` single tokens. Suggested fix: the name's date is a day, two
  days or a year. A whole-year span also comes from a year-only name or a name with no date, as
  well as from an untrusted delivery. The same overstatement is in the intro at line 124 ("with
  the dates they were flown"): about 37% of items carry only a year.

- **[claim] README.Rmd:121.** "products nobody has published yet" is a universal that cannot be
  checked, and it is likely false for the first example. Lidar-derived relative-elevation and
  floodplain products for BC reaches are published by others. The issue's draft said "nobody has
  made yet". What the code and data support is "products LidarBC does not publish".

- **[claim] README.Rmd:117.** "each flight is a record of a watershed at one moment". Per tile,
  acquisition often spans months. Of the 44,744 day-range items, 16,949 span 31 to 365 days and
  1,295 span more than a year. The longest is 741 days (`093/093c/2023`, `092/092g/2023`).
  `research/filename_dates.md` records `093c/2023` holding points from 2023, 2024 and 2025. That
  matters because the change-over-time bullet at line 122 builds on the sentence: one "flight"
  of a tile can itself straddle two growing seasons. "at one time" or "a record of a watershed
  when it was flown" would not overstate it.

- **[claim] README.Rmd:188.** The page says stac-elevation-bc items "will carry the same key from
  that catalogue's next full rebuild". stac_dem_bc's main branch adds `lidarbc:delivery` through
  `scripts/footprint_apply.py`, an in-place rewrite of every published item. Its NEWS
  "Unreleased" says this is "published by dispatching `update.yml` with `footprint: true`". It
  is not a full rebuild. The live items still lack the key (`094-094o-2026-dem-bc_…`,
  `092-092k-2025-dem-bc_…` have no `lidarbc:` property, checked 2026-10-13). A reader expecting
  a rebuild would wait for the wrong event. "once stac_dem_bc publishes #55" is accurate.

- **[claim, low] README.Rmd:198.** The round 1 fix, "a few files with a faulty header, or filed
  under the wrong mapsheet", still leaves out one of the 11. `bc_082m081_3_3_3_…_2019.laz` has a
  sound header and is filed under its own sheet. It is a 6 x 130 m sliver whose centre is under
  a metre outside 082M (`catalogue_build.py` EXCLUDE reason), and the build's centre-in-sheet
  test refuses it. "a few files with a faulty header, or lying outside the mapsheet they are
  filed under" covers all three non-header cases, the two misfiled 093C tiles included.

- **[fragile, low] .github/workflows/update.yml:12.** The comment says "A red run is a build that
  refused something a person must look at (README, "Monthly update")". This branch moves that
  section and its refusal list to maintaining.md, so the pointer now names a heading that no
  longer exists. Point it at maintaining.md, "Monthly update".

- **[fragile, low] README.Rmd:37.** The build chunk comment still lists "the bucket" among what
  `update_query = TRUE` reads. This branch removed the bucket read (`BUCKET_URL`,
  `pc_readme_bucket_json`). The render now reads only the API, the two header reads, and the
  two demos.

## Round 1 fixes reviewed

- Line 192, "an item without a list was not read in full": this matches
  `catalogue_build.DESCRIPTION` and `classes_published` (lists for screened-and-flagged files
  plus `classes_required.json`). It is correct.
- Line 186, the trust rule: it now matches `groups_with_untrusted_dates`
  (`filename_date and source == "path"`). It is correct as far as it goes. The rest of that
  paragraph is the first finding above.
- Line 198, exclusions: see the 082m081 finding above.
- The ledger row for the removed id check is marked as removed. It is correct.

## Checked and fine

- "flown across BC since 2012": `pointcloud_groups.json` years run 2012 to 2026, and the
  collection's temporal extent starts 2012-01-01.
- "Every point-cloud file LidarBC publishes under `<block>/<sheet>/<year>/pointcloud/`":
  `blocks_list` takes every `\d{3}/` root prefix and raises on an unknown one, and
  `pointcloud_select` raises on any `.laz` it cannot place.
- Kanaka "because the place has been flown more than once": `readme_dem.py` keeps one delivery
  year, and the 4 dropped items are the same tiles in 2024 and 2025.
- The footprint, point count, point format and CRS come from the header (`laz_item.item_create`).
- The `related` link is live. A minority of items have a `copc` (13,970 of 174,282).
- In maintaining.md, the version behaviour (`s3_publish.collection_differs` / `_unstamped`),
  the 40,000 ceiling, `dryrun`, no registration in CI, the summary carrying the commands, the
  cache_sync push refusal by ETag, and the refusal list all match the code.
