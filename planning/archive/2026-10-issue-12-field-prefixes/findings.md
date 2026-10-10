# Findings — Rename the nge: item fields to a prefix that names the source (lidarbc:) (#12)

## Issue context

**If we do it:** every custom field an item carries names the data it describes, and a reader (or a later stactools package) does not have to learn what an organisation's initials mean. **If we never do:** the fields stay readable only to people who already know `nge` is New Graph Environment.

## What is there

Six item fields use the `nge:` prefix (New Graph Environment):

| field | where | standard alternative? |
|---|---|---|
| `nge:product` | properties | none |
| `nge:datetime_source` | properties | none |
| `nge:filename_date` | properties | none |
| `nge:las_version` | properties, `copc` asset | none in `pc` |
| `nge:point_format` | properties, `copc` asset | none in `pc` |
| `nge:delivery` (proposed) | #5 | none |

STAC's convention for fields no extension covers is a prefix naming the **source** (`landsat:`, `sentinel:`, as stactools packages do). Here that is `lidarbc:`. Each field should also be checked against the published extensions before it is renamed, because a standard field beats any prefix (#10 found `classification:classes` that way).

## When

Renaming changes every published item. #2's build rebuilds and re-registers all of them, so the rename belongs before it, as with #5 and #10. #5's key should take the new prefix rather than ship as `nge:delivery`.

## Not in scope

The prefix is also used in stac_dem_bc, stac_airphoto_bc, stac_floodplains_bc and stac_uav_bc. Each is its own catalogue and decides for itself. #5's key is shared with stac-elevation-bc, so the two have to agree on that one.

## Plan-gate decisions (2026-10-10)

- Split prefixes: `lidarbc:` for facts about LidarBC's paths and names (`product`,
  `datetime_source`, `filename_date`, #5's `delivery`); `las:` for LAS-format facts
  (`las:version`, `las:point_format`), which are true of NRCan's COPC too and of any later
  non-LidarBC source.
- Schemas for each custom prefix go in crate (NGE's schema/data-dictionary repo), filed as a
  crate issue; items list them in `stac_extensions`. #2 waits on both.
- The sibling catalogues' `nge:` fields migrate too, one issue per repo (user, at the gate).
  Standard extension first: `processing:datetime` / `processing:software` look like the
  home for the produced-datetime and version/sha fields.

## Errors Encountered

| Error | Resolution |
|-------|------------|
