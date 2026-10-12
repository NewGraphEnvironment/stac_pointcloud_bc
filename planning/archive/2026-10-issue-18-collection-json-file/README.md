## Outcome

The README's `update_query = TRUE` render read the bucket's 35 MB `collection.json` through an R URL
connection, which stops at `getOption("timeout")` (60 s), and failed on a slow link after the
19-minute API fetch. `pc_readme_bucket_json()` now downloads it to a tempfile with
`pc_readme_fetch_file()`, the httr2 helper #19 added (no total timeout; a 10 kB/s-for-120 s stall
abort; raises on an HTTP error status), parses the copy and deletes it. The issue had prescribed
`curl::curl_fetch_disk()` and a new dependency; reusing the existing helper made that unnecessary,
and the issue body says so. The plan review caught that the planned live check compared ids with
`data/readme_cache.rds`, which holds none; the first live run failed on exactly that, and the check
was rerun against the old read instead.

## Measurement

- Under `options(timeout = 5)`: the new read succeeded (92 s and 117 s for 35 MB on this link); the
  old `fromJSON(<url>)` failed with the incident's `Timeout of 5 seconds was reached` /
  `cannot read from connection`. Round 2 of the code check reproduced both under `timeout = 3`.
- New read against old read (`timeout = 1800`): 174,282 ids each, 0 in either set and not the
  other, no duplicates; version 0.3.0 in both, in the API and in the cache, whose per-group item
  counts sum to 174,282. Confirms the change moved the transfer and nothing else.
- Removing `on.exit(unlink(tmp))` turns both cleanup assertions red; round 2's five mutations of
  the new function each turned test 13 red.
- `/code-check branch`: three rounds, all Clean.

Closed by: PR #21
