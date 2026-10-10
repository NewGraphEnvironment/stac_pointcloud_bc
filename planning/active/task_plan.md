# Task: Rename the nge: item fields to a prefix that names the source (lidarbc:) (#12)

**If we do it:** every custom field an item carries names the data it describes, and a reader (or a later stactools package) does not have to learn what an organisation's initials mean. **If we never do:** the fields stay readable only to people who already know `nge` is New Graph Environment.

## Context

Five item fields use `nge:` (New Graph Environment), which names who built the catalogue, not
the data. Only a reader who already knows the initials can read them. #2's full rebuild
re-registers every item, so the rename has to land before it (#2 is blocked on this issue).

**Decided at the plan gate (2026-10-10):**
- **The prefixes split by what each field describes.**
  - `lidarbc:` for facts about LidarBC's paths and file names. An item from another
    source would simply not carry them:
    `lidarbc:product`, `lidarbc:datetime_source`, `lidarbc:filename_date`, and #5's
    `lidarbc:delivery` (that key is built in #2, not here).
  - `las:` for facts about the LAS format, which are true of any source, NRCan's
    COPC included: `nge:las_version` becomes `las:version`, and `nge:point_format`
    becomes `las:point_format`.
- **The JSON Schemas for these prefixes go in crate**, as a crate issue filed now. Items
  then list them in `stac_extensions`. #2 waits on both, so the full re-registration
  still happens once.
- **No published extension covers any of these fields.** I checked
  `pointcloud` v1.0.0 (`pc:count/type/encoding/schemas/density/statistics`),
  `projection`, `file` and `classification`.

Measured on main @ 46f6b61: the `nge:` keys are set only in `scripts/laz_item.py` (L260–268
properties, L332–334 the class-read check, L383–384 the `copc` asset's `extra_fields`) and in
`scripts/catalogue_build.py` L402 (the collection's summaries). Tests: `tests/test_laz_item.py`
L160, 242–243, 586, 620–621. Prose: `README.Rmd` L137 and L139, and `research/laz_header_read.md`
L88. No cache or registration config holds a key: `stacs.toml` requires only the `laz` asset.

## Phase 1: Tests first
- [x] `tests/test_laz_item.py`: change the existing assertions to the new names
      (`lidarbc:product`, `lidarbc:filename_date`, `lidarbc:datetime_source`, `las:version`,
      `las:point_format`, on the item and on the `copc` asset).
- [x] Add a guard test: walk an item built from a fixture, with a `copc` asset and class
      lists added, and its collection, recursively. No key starts with `nge:`. Every
      non-standard key is one of the declared set.
- [x] Run `uv run pytest` and confirm the new assertions fail for the right reason.

## Phase 2: Rename in the build
- [x] `scripts/laz_item.py`: the properties, `filename_date`, the LAS version comparison in
      the class read (`las:version`), and the `copc` asset's `extra_fields`. Update the
      docstrings that name the fields (n/a: none name a key, per the plan review).
- [x] `scripts/catalogue_build.py`: summaries key `lidarbc:product`.
- [x] `uv run pytest` is green. Confirm the guard goes red when one `nge:` key is restored.
- [x] Run a `catalogue_build.py --limit` build (to `data/build-limit/`). `grep '"nge:'` over
      it returns nothing, and pystac validation passes.

## Phase 3: Prose
- [x] `README.Rmd` L137/L139: the new names. Re-render both targets from the `build`
      chunk with `update_query = FALSE`, which uses the cache only and no network.
- [x] `research/laz_header_read.md` L88: the new name, plus a Verified line noting the
      rename.
- [ ] NEWS.md: the 0.1.0 and 0.2.0 entries stay as they are, because they describe what
      was published. The release that publishes the rename (#2) names old → new. That
      requirement goes into #2's body.

## Phase 3b: Plan-review follow-ups (planning/active/review-plan.md)
- [x] Guard covers unprefixed keys and what main() writes (COPC and class-read builds)
- [x] README names the `nge:` spelling of releases up to 0.2.0

## Phase 4: Migrate the sibling catalogues off nge:, by issue in each repo
You asked at the gate that the other catalogues' `nge:` fields also move to prefixes that
say what each field is. Each catalogue has its own bucket, build and re-registration, so
the migration is one issue per repo. Each issue carries that repo's field inventory and a
proposed mapping, standard extension first. Inventory on main, 2026-10-10:
- **stac_airphoto_bc:** `produced_datetime`, `pipeline_sha`, `fly_version`, `fly_sha`.
- **stac_floodplains_bc:** `flooded_version`, `link_version`/`link_sha`/`link_config_sha`/
  `link_run_uid`, `drift_version`, `produced_datetime`, the `landcover_*` group (`key`,
  `collection`, `source`, `stac_url`, `item_hash`), `probe`, `kept`.
- **stac_uav_bc:** `stream_name`, `watershed_group`, `wsg_code`, `region`, `site_id`,
  `project`, `alias`.
- **stac_dem_bc:** none today. stac_dem_bc#55 adds the shared key as `lidarbc:delivery`.

The likely standard fit: the **processing** extension. `processing:datetime` would replace
`produced_datetime`, and `processing:software` (a name → version map) the
`*_version`/`*_sha` fields. Each repo checks that fit field by field. Fields with no
standard home get a prefix naming what they describe: a Freshwater Atlas prefix for
`wsg_code`/`stream_name`, a landcover-source prefix, and so on. `nge:` stays only where
NGE genuinely is the subject.

- [x] File the crate issue: one versioned JSON Schema per custom prefix the family uses
      (`lidarbc`, `las` first, then whatever the sibling migrations settle), at a stable
      URL that items list in `stac_extensions`.
- [x] File a migration issue in stac_airphoto_bc, stac_floodplains_bc and stac_uav_bc, each
      linking #12 and the crate issue.
- [x] Edit the #12 body: the split decision; "Not in scope" becomes links to the three
      sibling issues and the crate issue.
- [x] Edit the #5 body: `nge:delivery` becomes `lidarbc:delivery`.
- [x] Edit the #2 body: `lidarbc:delivery`; blocked on the crate schemas; NEWS names the
      rename.
- [x] Edit the stac_dem_bc#55 body: the key is `lidarbc:delivery`, and the two
      collections must agree.

## Validation
- [x] Tests pass
- [ ] `/code-check` clean (each commit, or once over the branch with `/code-check branch`)
- [ ] PWF checkboxes match landed work
- [ ] `/planning-archive` on completion
