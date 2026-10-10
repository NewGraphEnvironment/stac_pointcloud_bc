# Progress — Rename the nge: item fields to a prefix that names the source (lidarbc:) (#12)

## Session 2026-10-10

- Plan-mode exploration — phases approved by user (prefix split and crate schemas decided at the gate; sibling migration added by the user)
- Created branch `12-rename-the-nge-item-fields-to-a-prefix-t` off main
- Scaffolded PWF baseline from issue #12 with approved phases
- Next: start Phase 1
- Phase 1: assertions renamed; `test_every_prefixed_field_is_a_standard_one_or_declared` walks an item (copc + class lists) and its collection. Red for the right reason: 5 failed, 142 passed, the guard listing the five `nge:` keys.
