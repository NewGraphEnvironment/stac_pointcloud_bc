# Whether two builds of the catalogue write the same bytes

**Verified:** 2026-10-13 · **Issues:** #4 (found and fixed), #22 (the release that publishes
the fix) · **Produced by:** `item_create` over every 20th url of the 0.3.0 header cache
(8,713 items), run on macOS arm64 and in `python:3.12` under `--platform linux/amd64` (QEMU)
from the same `uv.lock`; a `Decimal` distance-to-half-way pass over all 174,282 published
footprints; S3 `head-object` and listings of `s3://stac-pointcloud-bc`. Method and numbers in
`planning/archive/2026-10-issue-4-monthly-update/findings.md`.

The monthly update publishes only the items whose bytes the bucket does not already hold
(`scripts/s3_publish.py`). That works only if a rebuild of an unchanged file writes the same
bytes on whatever machine builds it.

- **Unrounded footprints are not portable.** With PROJ 9.8.1 from the same pyproj wheel
  version on both platforms, **6,559 of 8,713** items (75%) differed between macOS arm64 and
  linux/amd64: in `geometry` in every one, in `bbox` in 4,560, and in `proj:*` in none. The
  largest difference was **5.68e-14 degrees**, the last bits of a double (for example,
  latitude 49.05009440869304 against 49.05009440869303). `proj:bbox` is copied from the
  header, not computed, so it agrees.
- **Rounding to 8 decimals** (`laz_item.LONLAT_DECIMALS`, about 1 mm; a header box is stored
  to 1 cm) brought the sample to **0 of 8,713** different.
- **Rounding still leaves boundary cases.** A value within a few ulp of a half-way point can
  round one step apart on the two platforms. Over all 174,282 published footprints, values
  within 1 ulp of an 8-dp half-way point occur in **5 items**, and within 4 ulp in **9**. A
  1-in-20 sample expects about 0.25 of them, so the 8,713-item probe could not show them.
  `s3_publish.same_items` therefore fetches the published body of each item that differs by
  digest (up to 2,000) and leaves one that differs only by one grid step in `geometry` or
  `bbox`.
- **An item's S3 ETag is the MD5 of its file.** Items are 2.5 to 4 KB, so they are uploaded
  as single parts (SSE-S3, `AES256`). `collection.json` (35 MB) is multipart (`-5`), so it
  is compared by body. The emulated amd64 run is not the GitHub runner itself; the first
  dry-run dispatch is the check on real hardware.

Anything else a build computes in floating point and writes to an item or the collection has
the same hazard. The collection extent is the min and max of item bboxes, so it inherits
their rounding.
