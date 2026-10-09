# Review: Phase 2 staged diff, round 4 (defects inside the round-3 fixes)

Worked in a copy (`rsync` of the repo minus `data/` and `.venv`, plus a copy of
`data/build/headers.jsonl`), running the repo's `.venv` python read-only. Nothing in the repo was
modified except this file. `pytest -q` in the copy: **69 passed**.

## Findings

- **[severity: fragile]** scripts/catalogue_build.py:245-247 — **`global OUT` is set for `--limit`
  and never reset, so it leaks across `main()` calls in one process.** Proven in the copy: `main()`
  with `--limit 1`, then `main()` with no `--limit`, writes the *full* build to `data/build-limit/`
  and leaves `data/build/` absent (`OUT after full run: data/build-limit`). The CLI runs one `main()`
  per process, so a production run is not affected. Both current tests that pass `--limit`
  monkeypatch `OUT`, so the suite is not affected today either. But a future test that calls
  `main(--limit)` without that monkeypatch would leave `OUT` changed for every later test.
  `test_the_build_refuses_when_any_header_failed` (line 460) does not pin `OUT`. If it ran after such
  a test, its two `not (tmp_path / "data/build/...").exists()` assertions would pass vacuously.
  Fix: use a local, e.g. `out = "data/build-limit" if args.limit else OUT`, and use it throughout
  `main()`.

No other defects found inside the round-3 fixes. The four specific checks:

1. **`nts_sheet_bounds` matches NRCan's own index.** I checked all 128 sheets in the 8 blocks
   (A-P x 082/083/092/093/094/102/103/104) against NRCan's NTS delimitation service
   (`https://geogratis.gc.ca/services/delimitation/en/nts/<id>`), comparing bboxes:
   - **110 match exactly.** These include every letter that is absent from the data: 082I, 082M-P,
     083A-P, 093A-P, 094A-P, 103I/J/P, 104A/B/G-K/M-P, 102I/J/K and others.
   - **13 differ, but only because NRCan clips the sheet to the land or the border it publishes.**
     Each NRCan bbox lies inside the code's nominal cell and shares its grid edges. Examples:
     - 082A-D and 092A: lat 48.75-49, i.e. the US border
     - 092B Victoria: -124 to -123
     - 103K Dixon Entrance, 104F Sumdum, 104L Juneau

     None of the 13 is a lettering or origin error.
   - **5 do not exist (404):** 102D, 103M, 103N, 104D and 104E, which are ocean or Alaska.

   So the snake (`ABCD`, `HGFE`, `IJKL`, `PONM`, each written east to west) and the `NTS_BLOCKS`
   origins are right. Because the cells are nominal, the check is slightly looser than the published
   clipped sheets. That is harmless for a centre-in-sheet test.
   **Margin:** the closest of the 9,649 footprint centres is 0.002 deg (~140-220 m) inside its sheet
   edge, at `bc_082l081_1_1_3…2019`. That is two orders of magnitude above the ~1 m difference
   between NAD83 and WGS84, so no real file sits on a knife edge.
2. **`groups_with_untrusted_dates` matches the evidence exactly.** It distrusts 4 groups:
   - `082k/2017`: 266 tokens `_18xxxx`, 1 `_171015`
   - `092g/2016`: 1,400 `2017…`, 306 `2016…`
   - `092h/2016`: 426 `2017…`, 586 `2016…`, 7 seven-digit `2016721`
   - `092j/2016`: 182 `2017…`

   The 2017 tokens total 1,400 + 426 + 182 = 2,008, and 082k has 266 `_18xxxx` tokens. Both match the research note exactly. No group is
   distrusted without a disagreeing token, and none with one is missed. All 7 trusted groups carry
   only 4-digit year tokens that agree with the directory.
   - **The 7-digit / absent case does not mark a group, and that is right.** It parses as no date,
     so it can only produce the directory year and never a wrong day. In the data it occurs only in
     092h, which is already distrusted.
   - **A 4-digit token that disagrees does mark the group, and that is also right.** It shows the
     delivery's naming is not about acquisition, which is the same reasoning as the other cases.
3. **`--limit` and the cache.** A limited run caches to `data/build-limit/headers.jsonl`, separate
   from the full cache:
   - It costs N extra 64 KB range reads, about 0.2 s each, which is negligible.
   - It never pollutes or reads the full cache.
   - The leak is the finding above.
   - Side note: in a limited run, `groups_with_untrusted_dates` sees only the first N URLs. So a
     limited build can trust a delivery that the full build distrusts. That is acceptable, because
     the limited build is not where a publish reads.
4. **The exact float comparison in `exclusions_check` is safe.** laspy's `mins` are float64 read
   straight from the header bytes, not computed, and Python's JSON float repr round-trips exactly.
   `0 == 0.0 == -0.0`. Proven live: I re-read the excluded file's header just now (one range
   request) and round-tripped it through JSON. It still reads `[0.0, 0.0, 0.0]` and is excluded.
   The cache has no URL with more than one v2 record, so there was no historical re-read to compare.

## Enumeration (all 9,650 cached v2 headers, the build's own `exclusions_check` / `groups_with_untrusted_dates` / `item_create`)

| | count |
|---|---|
| headers (v2, latest per url) | 9,650. Matches the 11 `INCREMENT` groups exactly: none missing, none extra |
| excluded (EXCLUDE, fault re-confirmed) | 1 (`092h003_2_3_1…20160913`) |
| refused by `item_create` | **0** |
| built | **9,649** |
| duplicate ids | 0 |

- 200 sampled items `validate()`.
- The collection `validate()`s.
- Spatial extent: [-123.3176, 48.9994, -115.5997, 51.0006].
- Temporal extent: 2016-01-01 to 2019-12-31T23:59:59Z.

| group | trust | day `datetime` | year range | `nge:datetime_source` |
|---|---|---|---|---|
| 082/082e/2018 | trusted | 0 | 1,995 | filename (4-digit year) |
| 082/082e/2019 | trusted | 0 | 871 | filename |
| 082/082f/2018 | trusted | 0 | 1,061 | filename |
| 082/082g/2018 | trusted | 0 | 215 | filename |
| 082/082j/2018 | trusted | 0 | 207 | filename |
| 082/082k/2017 | **untrusted** | 0 | 267 | path |
| 082/082l/2018 | trusted | 0 | 774 | filename |
| 082/082l/2019 | trusted | 0 | 1,352 | filename |
| 092/092g/2016 | **untrusted** | 0 | 1,706 | path |
| 092/092h/2016 | **untrusted** | 0 | 1,019 | path |
| 092/092j/2016 | **untrusted** | 0 | 182 | path |

Other checks over the same headers:
- The comment's tile figures hold: max side 1,877.65 m, median 1,829 x 1,418 m, 104 files with a
  side under 100 m, smallest 1.41 x 0.84 m.

## Observations (decisions or docs, not defects)

- **No item in the increment now publishes a day.** Every trusted group carries only year tokens,
  and every group with day tokens is distrusted. Until round 3, 892 built items published a day (306 in
  092g and 586 in 092h, `2016…` tokens; the 587th is the EXCLUDEd file). They now publish the 2016 range. Round 3 found no
  counter-evidence for those tokens: each precedes its header creation date, and GPS week time cannot
  test them. So the distrust rests on the delivery mixing two naming conventions, not on those tokens
  being shown wrong. A year range is never false, so this is a defensible call. It is a precision
  choice the user may want stated in NEWS or the collection description.
- research/laz_header_read.md:76-78 still says `item_create` "refuses any box that is not tile-sized
  or not inside BC". The guards are now `0 < side <= 5 km` and the NTS-sheet centre check. The last
  bullet of the same section states the new rule correctly, so the note contradicts itself.
- Unchanged from round 3: the EXCLUDEd file's header is still fetched every run. If that one URL
  starts returning 403/404, the build fails over a file it would drop.
- Cost: running `item_create` over 9,649 items took about 20 min wall clock here. It shared the CPU
  with the running build, and builds two `Transformer`s per item (mine plus the margin pass). Expect
  the real build's item phase to take minutes, not seconds.
