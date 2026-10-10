# Progress — Rename the nge: item fields to a prefix that names the source (lidarbc:) (#12)

## Session 2026-10-10

- Plan-mode exploration — phases approved by user (prefix split and crate schemas decided at the gate; sibling migration added by the user)
- Created branch `12-rename-the-nge-item-fields-to-a-prefix-t` off main
- Scaffolded PWF baseline from issue #12 with approved phases
- Next: start Phase 1
- Phase 1: assertions renamed; `test_every_prefixed_field_is_a_standard_one_or_declared` walks an item (copc + class lists) and its collection. Red for the right reason: 5 failed, 142 passed, the guard listing the five `nge:` keys.
- Phase 2: keys renamed in `laz_item.py` (properties, class-read check, `copc` extra_fields) and `catalogue_build.py` (summaries). 147 passed. Guard mutation: restoring `nge:point_format` on the copc asset, or `nge:datetime_source` on the item, turns the guard red. `--limit 40` build at 19:15Z: 41 JSON files written, 0 `"nge:` keys, each new key on all 40 items, `lidarbc:product` in the collection summary too.
- Phase 3: README.Rmd's two field-name sentences and `research/laz_header_read.md` L88 (+ Verified line). Both targets re-rendered with `update_query = FALSE` (cache only); README.md and index.html each changed in exactly those two sentences. The NEWS requirement is carried in Phase 4's #2 body edit.
