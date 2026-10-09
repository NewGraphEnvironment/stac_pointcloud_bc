# Review — Phase 2, round 2 (runtime)

Scope: HttpRangeFile, headers_fetch concurrency/cache, failure handling, catalogue_build
main, and whether the tests reach what they claim. Metadata correctness was out of scope.
Worked in a copy (`cp -r` to the scratchpad); the staged repo was not touched.

`uv run pytest -q` in the copy: **33 passed**.

## Findings

- **[severity: fragile]** tests/test_laz_item.py:216-222 (`test_a_header_read_transfers_one_block_not_the_file`)
  — the fixture cannot reach the failure it names. The served LAZ is **32,618 bytes**, under
  one 64 KB block, so "1 request, <= BLOCK bytes" holds whatever laspy reads. Mutation proof:
  with `_ = r.header.point_count` replaced by `_ = r.read()` (decompress every point) the
  test still **passes**. A regression that made header reads pull the whole file (e.g. a
  laspy upgrade reading the LAZ chunk table on open) would not be caught. Fix: a fixture
  larger than BLOCK. 1,000,000 random points (format 1) gives 6.3 MB and still reads in
  1 request / 65,536 bytes on laspy 2.7.0, so the assertion keeps holding and starts to mean
  something. (`__globals__["BLOCK"]` resolves to laz_remote.BLOCK correctly; it is only odd.)

- **[severity: fragile]** scripts/catalogue_build.py:192-202 — destructive step runs before
  the collection is built and validated. Items are validated first (good), but then
  `items/*.json` is deleted and rewritten, and only after that do `collection_build()` and
  `c.validate()` run. Any exception there, or a disk-full on the item writes, leaves
  `data/build/items/` holding the new set (or part of it) beside the **previous build's
  collection.json**, whose item links name a different set. Publishing is a separate step,
  and it would ship that mismatched pair. Fix: build and validate the collection before
  deleting anything (or write to a temp dir and swap).

- **[severity: fragile]** scripts/catalogue_build.py:86-93, 96-120 — the header cache never
  invalidates. It is keyed by URL only, and `keys_list` discards the `Size`/`ETag`/
  `LastModified` the listing already returns. A file re-delivered under the same key keeps
  its old `file:size`, point count and footprint in every later build, silently. Same
  mechanism: a change to the fields `header_read` returns is not seen by a warm cache
  (missing key -> KeyError at build, loud). Storing the listing's size/ETag with each
  record and re-reading on mismatch closes both.

- **[severity: fragile]** scripts/catalogue_build.py:91 — a partial last line in
  `headers.jsonl` (a crash/SIGKILL/disk-full mid-write) makes `json.loads` raise
  `JSONDecodeError` (reproduced), so every subsequent run dies at load until the file is
  edited by hand. That contradicts "an interrupted run loses nothing". Skipping (and
  logging) an unparseable trailing line would let the re-run converge.

- **[severity: fragile]** tests/ — the build's own guards have no test: nothing exercises
  `headers_fetch` (cache append, retry-on-rerun, error collection) or `main`'s refusal when
  any header failed, though the test module docstring says it covers "the build's guards".
  Probed by hand in the copy: one failed read is recorded, not cached, and a re-run reads
  only it and converges (2 lines in the cache); a cached header round-trips through JSON to
  an item dict identical to a fresh one. So the code is right today, and nothing would
  catch it going wrong.

## Checked and found sound

- **Live listing** of the 11 groups: 9,650 keys, all pass `key_parse`, all `.laz`
  lowercase, no case-insensitive id collisions (relevant on APFS), 15 with ` (2)` spaces and
  parens, no `%#?+&` or non-ASCII.
- **Live header reads** (13 sampled, including 3 ` (2)` files): LAS 1.4 and 1.2,
  0 EVLRs, **1 range request each**, ~0.1 s per file, so 9,650 at 16 workers is minutes.
- **LAS 1.4 with EVLRs**: laspy seeks to the tail on open; HttpRangeFile serves it (2
  requests, the last block short and correct). Handled.
- **Short 206 body**: urllib3 enforces Content-Length and raises, so it becomes a recorded
  error, not a silently short block. Missing Content-Length on HEAD -> KeyError -> recorded
  error. A 200 to a Range GET -> refused (tested). Read at/after EOF returns `b""`.
- **Memory**: one HttpRangeFile per file, released when `header_read` returns; futures hold
  only small header dicts.
- **Concurrency**: cache is appended from the main thread only (inside the `as_completed`
  loop), flushed per line; the shared Session's pool is sized to the workers.
- **No swallowed failures**: header errors fail the build; `item_create` raises loudly;
  duplicate ids and missing `laz` asset are checked before any deletion.
- **pystac validation**: schemas are cached in-process (`schema_cache`), no per-item network
  fetch observed; ~20-50 ms per item, so 9,650 is roughly 3-8 minutes of CPU. Slow but not
  a failure.

Low, not raised as a finding: no retry on a transient error (a re-run converges, measured
above); a key that persistently 403s has no exclusion path, so the build can never complete
for it — consistent with the stated "refuse" design; Ctrl-C leaves `ThreadPoolExecutor`
running every pending read before exit (`shutdown(wait=True)`), about a minute here.
