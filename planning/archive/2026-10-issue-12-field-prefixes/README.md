## Outcome

The five `nge:` item fields now carry prefixes that name what they describe:
- `lidarbc:product`, `lidarbc:datetime_source` and `lidarbc:filename_date` are facts about LidarBC's paths and file names.
- `las:version` and `las:point_format` are facts about the LAS format. They are true of NRCan's COPC copy as well as of the LidarBC file.

Three decisions were made at the plan gate:
- **The split prefixes**, instead of `lidarbc:` for all five.
- **JSON Schemas for each custom prefix go in crate** ([crate#23](https://github.com/NewGraphEnvironment/crate/issues/23)). #2 waits on them.
- **The sibling catalogues migrate off `nge:` too**, each in its own repo ([stac_airphoto_bc#47](https://github.com/NewGraphEnvironment/stac_airphoto_bc/issues/47), [stac_floodplains_bc#74](https://github.com/NewGraphEnvironment/stac_floodplains_bc/issues/74), [stac_uav_bc#38](https://github.com/NewGraphEnvironment/stac_uav_bc/issues/38)). Standard extensions come first; the processing extension covers the produced-datetime and version fields.

Nothing was published. The 0.2.0 bucket still carries `nge:` until #2's full rebuild. #2's body now requires the crate schemas before that publish, NEWS entries naming each old → new pair, and a published-vs-build check that maps the old names.

What was learned is how a "no field outside the declared set" guard has to be built:
- Each of three review rounds found the guard missing one more place, and rounds 2 and 3 found it inside the previous fix.
- The cause was a guard whose expected answer came from the same enumeration as its scope: first hand-picked locations, then a fixture that took only one branch.
- What ended it was pinning every key path the build writes (`ITEM_PATHS`, `COLLECTION_PATHS`), from fixture builds that take every branch that writes a key, and then measuring that set against the real population.

## Measurement

On 2026-10-10 at 19:36Z, a full rebuild from the cached headers, written to a scratch directory rather than `data/build`, produced 9,649 items: 1 excluded, 1,964 with a COPC copy, 73 class lists. Its key paths equal the pinned sets exactly in both directions.

That replaced an earlier, weaker check. A `--limit 40` build (0 `"nge:` keys) had looked like enough, but it exercised no COPC pair, no EPSG-less CRS and no trusted filename date. Round 3 showed those last two branches cover 197 and 6,475 real items. Each guard extension was proved by mutation: an `nge:` or bare key restored on each branch turned the pinned test red.

Closed by: PR (opened from branch `12-rename-the-nge-item-fields-to-a-prefix-t`)
