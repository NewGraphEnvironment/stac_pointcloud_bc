# Code-check round 5: the sentences 16fe2a7 changed, walked member by member

Reviewed 2026-10-13. Scope: only what 16fe2a7 changed (README.Rmd 124, 186, 302; CLAUDE.md 60-61;
research/filename_dates.md 38-40). Evidence: a full scan of the local 0.3.0 build
(data/build/items, 174,282 item JSONs, built 2026-10-11 09:07 local time, after the last date-code
change 706ad76). For each item it records the delivery, the date shape (`datetime`, a
calendar-year span, or another span), `lidarbc:datetime_source`, `lidarbc:filename_date`,
`proj:code` and `proj:wkt2`. The name's token shape comes from `laz_item._DATE` on the
**URL-decoded** asset file name: the raw href percent-encodes ` (n)`, and matching it raw
misclassifies 143 names. Also read: `laz_item.date_parse`, `item_create` (and where it sets
`filename_date`), `classes_add`, `copc_asset_add`, `catalogue_build.groups_with_untrusted_dates` /
`items_create` / call sites, and gh issue 25.

## Measured sets

| date shape | `datetime_source` | name token (decoded) | items |
|---|---|---|---:|
| day | filename | same-day pair | 61,760 |
| day | filename | yyyymmdd | 1,984 |
| day | filename | yymmdd | 628 |
| range (not a calendar year) | filename | two different days | 44,744 |
| year | filename | yyyy (= directory year in all 55,538) | 55,538 |
| year | path | any token, in the 9 untrusted deliveries | 8,762 |
| year | path | unparsed (726 `_2019_pa`, 127 `_201701024`, 7 `_2016721`, 5 `_2021_1`, 1 `.copc.laz` pair) | 866 |

Of the 866 unparsed, 7 (`_2016721`) are in an untrusted delivery (092h/2016). So the 9 untrusted
deliveries hold 8,769 items. Every item has a date. Every range starts in its directory year, all
65 range deliveries are 2023 or later, and every range name is a two-day pair.

## Per-sentence verdicts

| # | file:line | sentence | members walked | verdict |
|---|---|---|---|---|
| 1a | README.Rmd:186 | the date comes from its file name wherever the build can read the date and trust it | 109,116 filename-sourced items with a non-year date + 55,538 filename-sourced year spans; every filename-sourced item has a parsed token in a trusted delivery that agrees with its directory | TRUE |
| 1b | README.Rmd:186 | "a day (`datetime`) or a range (`start_datetime` / `end_datetime`), which for a name carrying two days is the first and last day flown" | days 64,372, two-day ranges 44,744, **year-token spans 55,538 (source `filename`)** | TRUE as worded, but it hides the largest file-name category (finding 1) |
| 1c | README.Rmd:186 | "first and last day flown" | 44,744 ranges in 65 deliveries (2023+); the GPS probe covers 30 files in 15 deliveries | UNVERIFIABLE beyond the probe (accepted in round 4; unchanged) |
| 1d | README.Rmd:186 | "Otherwise the item spans the year of its directory" | 8,762 + 866 `path` items, all spanning the directory year | TRUE |
| 1e | README.Rmd:186 | "for example where a delivery's file names carry processing dates" | 092g/h/j 2016 (names = header creation date, research #1); 3 of 9 untrusted deliveries shown | TRUE (an example) |
| 1f | README.Rmd:186 | "`lidarbc:datetime_source` says which" | `filename` / `path` on all 174,282 | TRUE, but `filename` on a year span contradicts what a reader takes from 1b + 1d (finding 1) |
| 2 | README.Rmd:124 | files come back "with their dates and coordinate systems" | every item has a date (0 without); 171,371 carry `proj:code`, and the other 2,911 (082f/2017 1,690, 093p/2018 271, 093o/2018 241, 093j/2017 228, 093i/2018 222, 082k/2017 197, 093o/2017 58, 093i/2017 4) carry `proj:wkt2` | TRUE |
| 3 | README.Rmd:302 | "Items are created by pure functions (`scripts/laz_item.py`) from each file's href and header and what the build measured about it" | `item_create(url, header, collection_href, trust_filename_date)`, `copc_asset_add(item, href, copc_header, laz_header)`, `classes_add(item, full)`, all "Pure: no I/O". `full` is measured about the file. `copc_header` is measured about another file, the copy. `trust_filename_date` is `group_of(u) not in groups_with_untrusted_dates(...)`: it is parsed from **every other name in the delivery**, not measured, and not about this file | FALSE (low; finding 2) |
| 4a | CLAUDE.md:60-61 | 092p/2017: "those items carry the directory year, the rest their day" | 127 `_201701024` → year/path; 208 → day/filename; nothing else | TRUE |
| 4b | CLAUDE.md:60-61 | 093c/2023: "those items carry the directory year, the rest their day" | 1 `.copc.laz` → year/path; **1,812 days and 1,156 ranges** | FALSE: 1,156 members carry a range, e.g. the `_20230921_20251001` names cited in `date_parse`'s docstring (finding 3) |
| 4c | CLAUDE.md:60 | "some names carry a date the parser cannot read (`_201701024`, …)" | issue #25 itself calls the nine-digit token malformed, and its "Done when" leaves it to the path year | low: "date" is a characterisation (finding 3) |
| 5a | research/filename_dates.md:38 | 64,372 + 44,744 + 65,166 | = 174,282 | TRUE |
| 5b | research/filename_dates.md:38-39 | 65,166 = year-only names ∪ untrusted deliveries ∪ 866 unread | 55,538 (trusted yyyy) + 8,762 (untrusted, parsed) + 866 = 65,166. As named, though, "the untrusted deliveries" are 8,769 items and overlap the 866 by 7 (`_2016721`, 092h/2016). Yyyy names in untrusted deliveries (1,063) also fall in both "year-only names" and "untrusted" | TRUE as a union; not a disjoint decomposition (low) |
| 5c | research/filename_dates.md:39-40 | "Each … keeps the name's last date token in `lidarbc:filename_date`" | 0 of the 866 have `filename_date` (item_create sets it only `if when["filename_date"]`). 732 of them do carry a token (726 `_2019_pa`, 5 `_2021_1`, 1 `.copc.laz` pair) | FALSE: contradicts the clause the fix put just before it (finding 4) |

## Findings

- **[claim] README.Rmd:186: the fix dropped the year category.** The old sentence listed "the day …,
  the first and last day …, or the year". The new one lists only "a day … or a range, which for a
  name carrying two days is the first and last day flown", then says "Otherwise the item spans the
  year of its directory". **55,538 items (32% of the catalogue)** have a year-only name in a trusted
  delivery and carry `datetime_source: filename` with a calendar-year span. Such an item has a date
  from its file name that is neither a day nor a two-day range. A reader of this page would also
  file a year span under "otherwise" and expect `path`. The sentence is true as worded, since a year
  span is "a range", but it is written from the parser's return shapes, not the member list.
  Suggest: "… a day (`datetime`), the first and last day flown where the name carries two
  (`start_datetime` / `end_datetime`), or the year where it carries only a year. Otherwise …".
- **[claim, low] README.Rmd:302: "what the build measured about it" excludes the date-trust input.**
  `item_create`'s `trust_filename_date` is a property of the delivery. `groups_with_untrusted_dates`
  derives it from every other file name in the delivery, and it is parsed, not measured. Round 4's
  suggestion named it ("whether its delivery's file-name dates are trusted"). The pre-fix text had
  "its delivery", and the fix dropped it while adding the classes. The COPC input is a measurement
  of a different file, the copy, which "about it" stretches but can carry. Suggest: "… from each
  file's href and header, and what the build found about its delivery, its CanElevation copy and,
  where it read the whole file, its classes."
- **[claim] CLAUDE.md:61: "the rest their day" is false for 093c/2023.** Besides the one `.copc.laz`
  item, 093c/2023 holds 1,812 day items and **1,156 range items**. It is one of the deliveries whose
  `_20230921_20251001` names `date_parse`'s own docstring cites. Only 092p/2017 is "the rest their
  day". Low, on the same line: `_201701024` is nine digits, and #25 treats it as malformed, not as a
  date. Also, 8 other deliveries hold unread names (the 2019 `_pa` six, 092i/2021, 092h/2016). There
  every item carries the year whichever way the name is read, so their omission is harmless, but the
  sentence should not read as the full list. Suggest: "In `092p/2017` 127 names end in a malformed
  `_201701024` and carry the directory year, the other 208 their day; in `093c/2023` one
  `.copc.laz` name hides its day pair from the parser, so that item spans 2023 (#25)."
- **[claim] research/filename_dates.md:39-40: a new self-contradiction.** The fix added "866 names
  whose token the parser cannot read" to the sentence that ends "Each … keeps the name's last date
  token in `lidarbc:filename_date`". None of the 866 has `filename_date` (`item_create` writes it
  only when `date_parse` returns a token), and 732 of them do have a token in the name. Suggest:
  "… and keeps the last date token the parser reads in `lidarbc:filename_date` (none for the 866)."
  Low, on the same line: "Each says which in `lidarbc:datetime_source`". Here "which" follows
  day / range / year, but the field says `filename` / `path`: a year span can be either, and a day
  or range is always `filename`.
- **[claim, low] research/filename_dates.md:38-39: the parts of 65,166 overlap as named.** The total
  is right as a union (55,538 + 8,762 + 866). But "the untrusted deliveries" are 8,769 items, and 7 of
  them (`_2016721`, 092h/2016) are also among the 866. If the parenthetical is meant to be summed, say
  "the untrusted deliveries' other 8,762 items".

No new bug in code: 16fe2a7 touched prose only. README.md and index.html are not yet re-rendered on
this branch; that is Phase 4 in task_plan.md, so it is not a defect.
