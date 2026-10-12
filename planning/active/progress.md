# Progress — README render: read the 35 MB collection.json to a file, not through R's 60 s URL timeout (#18)

## Session 2026-10-12

- Plan-mode exploration — phases approved by user
- Created branch `18-readme-render-read-the-35-mb-collection-json` off main
- Scaffolded PWF baseline from issue #18 with approved phases
- Next: start Phase 1
- Phase 1: two tests for `pc_readme_bucket_json()`; both fail on main (13: function absent; 14: regexp miss, then `file.exists(NULL)`)
