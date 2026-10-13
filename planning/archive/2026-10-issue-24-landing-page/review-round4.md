# Code-check round 4: the sentences ab5f15d changed, walked member by member

Reviewed 2026-10-13. Scope: only the sentences commit ab5f15d changed (README.Rmd 117, 156, 186,
188, 297, 302; maintaining.md 15, 17; CLAUDE.md 60). Evidence: a full scan of the local 0.3.0
build (data/build/items, 174,282 item JSONs: name, date token shape by `laz_item._DATE`, item date
kind, `datetime_source`, `filename_date`, per delivery), `laz_item.date_parse`,
`catalogue_build.groups_with_untrusted_dates`, `item_create` / `copc_asset_add` / `classes_add`
signatures, every `raise` / `return 1` in catalogue_build.py and laz_item.py, update.yml's steps,
cache_sync.sh's exits, data/build/classes.jsonl (ground in samples per delivery), the live
stac-airphoto-bc collection and its first and last item by datetime, GitHub docs'
`data/reusables/actions/scheduled-workflows-disabled.md`, and `git ls-tree origin/main research/`
plus an HTTP fetch of the linked research URL.

## Mechanism, one level down

Round 3's "866 items whose names carry no date token" was a count of names **the parser does not
match**, not of names that carry no date. The fix wrote that parser output into two sentences as a
fact about the names. Read by name, the 866 are:

| tail | items | deliveries | what the name carries |
|---|---:|---|---|
| `_2019_pa.laz` | 726 | 092b/c/f/g/k/l 2019 | the directory year, then `_pa` |
| `_2021_1.laz` | 5 | 092i/2021 | the directory year, then `_1` |
| `_201701024.laz` | 127 | 092p/2017 | nine digits, not a date |
| `_2016721.laz` | 7 | 092h/2016 (untrusted) | seven digits, not a date |
| `_20230902_20230902.copc.laz` | 1 | 093c/2023 | a same-day pair, before `.copc` |

`_DATE` requires `.laz` (or `_dsm`, or ` (n)`) straight after the token, so `_pa`, `_1` and `.copc`
all hide it. Effect: 731 year names publish the same year they would have, but as
`datetime_source: path` with no `filename_date`; the one `.copc.laz` file publishes 2023 where its
name says 2023-09-02.

## Findings

- **[claim] CLAUDE.md:60.** "`092p/2017` and `093c/2023` (one file) mix a day token with no token
  and keep each file's own precision." The 093c/2023 member is
  `bc_093c058_1_1_1_xyes_8_utm10_20230902_20230902.copc.laz`. Its name has a day token that the
  parser misses, and its item spans 2023 (`path`). So it does **not** keep its own precision; it
  loses it. The membership is right: of the deliveries that mix a day token with an unparsed name,
  only 092p/2017 and 093c/2023 are trusted (092h/2016 is the other mix, and it is untrusted).
  092p/2017's 127 unparsed names are the nine-digit `_201701024`. Suggest: "`092p/2017` (127
  nine-digit `_201701024` names) mixes day tokens with names the parser cannot read, and keeps each
  file's own precision; in `093c/2023` one `.copc.laz` name hides its day pair from the parser, so
  that item spans its year."
- **[claim] README.Rmd:186, sentence 1.** "An item's date is when its tile was flown, as precisely
  as the file name says: the day, …, or the year." There are two counter-members:
  (a) the `.copc.laz` item above. Its name says 2023-09-02 and its item says 2023, so the date is
  not as precise as the name.
  (b) "when its tile was flown" is unestablished for the **2,612 single-day items** (yymmdd 628,
  yyyymmdd 1,984). They are in 11 trusted deliveries from 2016–2017: 093l/2016 549, 092h/2017 471,
  082e/2017 359, 092j/2017 319, 082l/2017 269, 092g/2017 209, 092p/2017 208, 103i/2016 125,
  093m/2016 84, 092a/2016 17 and 092i/2017 2. research/filename_dates.md, "Not established", says
  "Single-day names were probed only as same-day pairs, in deliveries from 2024". In #1, the
  082k/2017 `_171015` names were same-year day tokens that were not the flight day. The trust rule
  cannot catch a processing date in the same year.
  The old text also said "the day flown", but the fix made it the definition of every item's date.
  Suggest: "An item's date comes from its file name, as precisely as the build can read it: …" and
  keep "flown" for the two-day names, which were probed.
- **[claim, low] README.Rmd:186, sentence 3.** "Those items, and any whose name carries no date,
  span the directory's year." The outcome holds for all 9,628 members (8,762 untrusted + 866
  unparsed). But "whose name carries no date" describes none of the 866: 731 carry their directory
  year, 134 carry a malformed token, and 1 carries a day pair (table above). Suggest "and any whose
  name's date the build cannot read". Grammar, low: "Those items" has no noun antecedent, because
  the sentence before it names a delivery, not items. "That delivery's items" would fix it.
- **[claim, low] README.Rmd:302.** "Each item is created by a pure function (`scripts/laz_item.py`)
  from a file's href and header, and what the build measured about its delivery and its CanElevation
  copy." Three pure functions in laz_item.py build an item:
  - `item_create(url, header, collection_href, trust_filename_date)`
  - `copc_asset_add(item, href, copc_header, laz_header)`
  - `classes_add(item, full)`
  The sentence names the first two's inputs and omits `full`, the whole-file class read that gives
  349 items their class lists. "A pure function" in the singular also reads as `item_create`, and
  `item_create` takes neither the copy nor the classes. Suggest "by pure functions in
  `scripts/laz_item.py`, from a file's href and header, whether its delivery's file-name dates are
  trusted, its CanElevation copy's header, and, where the build read the whole file, its classes."
- **[bug, low] scripts/laz_item.py:101 (`_DATE`), not page text.** The parser misses a date token
  followed by `_pa`, `_1` or `.copc`. The cost is one item's day (the `.copc.laz` above), plus 731
  `datetime_source: path` labels where `filename` would describe the source. The build does not
  refuse it, and `groups_with_untrusted_dates` never sees these tokens. All of them agree with their
  directory year, so no delivery's trust would change if they were parsed. This is outside the
  branch's scope; it is for an issue.
- **[claim, low] the new link, README.Rmd:186.** The link resolves: `research/filename_dates.md` is
  on origin/main (blob 3ff27be) and the URL returns HTTP 200. But the page now sends readers to the
  file whose "Counts" line round 3 found wrong: "65,166 a year (year-only names and the untrusted
  deliveries)", where those two sets are 64,300 and the other 866 are the unparsed names. That line
  should be fixed (naming the unparsed names as above) before or with this link.

## Per-sentence verdicts

| file:line | changed sentence | members walked | verdict |
|---|---|---|---|
| CLAUDE.md:60 | `092p/2017` and `093c/2023` (one file) mix a day token with no token and keep each file's own precision | every delivery with more than one token shape (80); trusted mixes of a day token and an unparsed name: 092p/2017 (208 + 127), 093c/2023 (2,968 + 1); the 1 is `…_20230902_20230902.copc.laz`, published as year | FALSE (the 093c member keeps no precision; its name has a day) |
| README.Rmd:117 | each flight records the land as it was when it was flown | definitional | TRUE |
| README.Rmd:156 | the same method can be applied to every flight | method needs class 2; all 225 indexed deliveries have class 2 in ≥1 density-screen sample (lowest 103h/2019, 1 of 4) | TRUE |
| README.Rmd:186 s1 | an item's date is when its tile was flown, as precisely as the file name says: day / first and last day / year | day 64,372 (61,760 same-day pairs, 2,612 single tokens); range 44,744; year from a `yyyy` token 55,538; `.copc.laz` day pair → year (1) | FALSE (1 member); UNVERIFIABLE for "flown" at 2,612 single-day items |
| README.Rmd:186 s2 | any name's date (a pair's first day) in another year → no file-name date in that delivery used | untrusted 9, each with ≥1 disagreeing member (082f/2017 1,705; 082k/2017 266; 092b/2023 184; 092b/2024 44; 092f/2023 8; 092f/2024 24; 092g/2016 1,400; 092h/2016 426; 092j/2016 182); 0 trusted deliveries with a disagreeing parsed date; the `d1 <= dt` arm has 0 members; every unparsed token's year equals its directory | TRUE |
| README.Rmd:186 s2 | often because it is a processing date | 4 of 9 shown (accepted in round 3) | TRUE |
| README.Rmd:186 s3 | those items, and any whose name carries no date, span the directory's year | 8,762 untrusted + 866 unparsed, all year/path; none of the 866 lacks a date-like token | TRUE in effect; description FALSE (low) |
| README.Rmd:186 s4 | `datetime_source` says which; the research file has how it was measured | `filename`/`path` on all 174,282; link 200, on main; the file describes the GPS probes | TRUE (linked file carries a known-wrong count) |
| README.Rmd:188 | keeps one delivery apart from another where several cover the same place | key = `<block>/<sheet>/<year>`, `DELIVERY` regex, unique per mapsheet-year by construction | TRUE |
| README.Rmd:297 | airphoto thumbnails, 1967–2019 | live extent 1967-07-11 to 2019-09-18; first and last item by datetime match | TRUE |
| README.Rmd:302 | a pure function from href and header, and what the build measured about its delivery and its CanElevation copy | `item_create` + `copc_asset_add` + `classes_add`; `classes_add`'s whole-file read (349 items) not named | FALSE (low, one input omitted) |
| maintaining.md:15 | usually the build; tests, a missing cache, the build's time limit and `stacs audit` can also fail it | update.yml: Tests, Pull (cache_sync.sh `not building cold`, exit 1), Build `timeout-minutes: 240`, Audit; none continue-on-error. Install, OIDC and Publish can also fail, which "usually" covers | TRUE |
| maintaining.md:15 | the refusal list, with the new "a CanElevation name matched by two files on either side" | every item maps to code: groups_check, blocks_list:294, pointcloud_select:320/328, groups_with_untrusted_dates:560, duplicate ids:795, header read return 1 + items_create faults, exclusions_check 517/525/536, copc_listing:401, copc_pairs:427/430, copc_pairs_check 442/447 + copc_not_copy_check 457 (+ "not a copy" 862), validate_all 825/929, classes_check/classes_attach 916. Not listed: listing OSErrors (the "network error" sentence), schemas_check/fields_check, "not a copy" (loosely "pairing"). No listed refusal is fictitious | TRUE |
| maintaining.md:17 | 60 days without repository activity | GitHub docs: "automatically disabled when no repository activity has occurred in 60 days" | TRUE |
