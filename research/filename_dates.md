# What the dates in a LidarBC file name mean

**Verified:** 2026-10-11 · **Issues:** #1 (the rule), #2 (two-day names) · **Produced by:**
GPS-time probes (a 20,000-point read at 0%, 25%, 50%, 75% and 95% of each file, GPS adjusted
standard time taken in UTC), run against the 0.3.0 build's listing; the rule is
`laz_item.date_parse` and `catalogue_build.groups_with_untrusted_dates`. The probe scripts were
not committed; the numbers below are the record.

A LidarBC file name ends in a date token: `yyyy`, `yymmdd`, `yyyymmdd`, or two `yyyymmdd`
(`bc_094j045_3_3_4_xyes_8_utm10_20240531_20250510.laz`).

## Two days are the first and last day flown over the tile

76 of the 77 deliveries from 2023 on (109,327 files) name every file with two days. In every
file probed, every sampled point's day lay between them, and most files showed both ends:

| probe | files | deliveries | result |
|---|---:|---:|---|
| pairs within one year | 16 | 8 | all points between the two days |
| pairs ending in a later year | 14 | 7 | all points between; `093c/2023` `_20230921_20251001` holds points from 2023, 2024 and 2025 |
| the same day twice | 12 | 6 | all points on that day |

So the **year directory is the year of the first day**, and the last can fall in a later year.
The build publishes a pair as `start_datetime` (the first day, 00:00:00Z) and `end_datetime`
(the last day, 23:59:59Z), and the same day twice as that day's `datetime`. Before this was
measured, the build gave a pair its last day as a single `datetime` (10,603 items) or, where
the last day's year was later, distrusted the whole delivery (33 deliveries, 80,337 files).

## A date in another year is a processing date

From #1: `082k/2017` files are named `_180827` while their GPS times fall in October 2017, and
`092g/092h/092j 2016` names carry 2017 dates that match the header's creation date. So a
delivery in which any name's date (a pair's first day) is in another year than its directory
is untrusted, and every file in it gets the directory year. In 0.3.0 that is 9 deliveries.

## Counts (0.3.0, 174,282 items)

64,372 items carry a day, 44,744 a range of days, and 65,166 a year (year-only names, the
untrusted deliveries, and 866 names whose token the parser cannot read, #25). Each says which in `lidarbc:datetime_source`, and keeps the name's last
date token in `lidarbc:filename_date`.

## Not established

- Whether the tokens are UTC or Pacific days. The GPS days, taken in UTC, matched; a point
  flown after 17:00 PDT on the last day would fall after `end_datetime`.
- Single-day names were probed only as same-day pairs, in deliveries from 2024.
