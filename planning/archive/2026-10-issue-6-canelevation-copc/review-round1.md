# Code-check round 1 — branch `6-canelevation-overlap` (#6)

Reviewer: subagent, 2026-10-09. Read in full: scripts/laz_item.py, scripts/catalogue_build.py,
scripts/canelevation_overlap_probe.py, tests/test_laz_item.py, research/canelevation_overlap.md,
.gitignore; context scripts/laz_remote.py, scripts/s3_sync.sh, stacs.toml, the installed stacs
package. Test suite: 95 passed. Checked against the built data in data/build/ (read only).

## Findings

- **[severity: bug, minor — published text]** scripts/laz_item.py, `copc_asset_add`, the asset
  `description` ("checked at build to have the same point count, CRS and extent"). The code
  compares the **horizontal** CRS only, and in the real build the full CRS differs in **every one
  of the 1,964 pairs**:

  | pairs | LidarBC `laz` header CRS | CanElevation `copc` header CRS |
  |---:|---|---|
  | 1,575 | `NAD83(CSRS) / UTM zone 10N` | `NAD83(CSRS) / UTM zone 10N + unknown` |
  | 389 | `NAD83(CSRS) / UTM zone 11N + CGVD2013` | `NAD83(CSRS) / UTM zone 11N` |

  (measured from data/build/headers.jsonl and copc_headers.jsonl via pyproj `CRS.name`.)
  So the sentence written into 1,964 published item JSONs states a check that was not made and
  would fail if it were. The function's own docstring says "the asset claims what was checked
  and no more". Fix: say "horizontal CRS" (e.g. "the same point count, horizontal CRS and
  extent"). The Z box agrees to 0.01 m in every pair, so the points are the same; only the claim
  is wrong. Note that this changes every copc item body, so do it before the v0.2.0 publish, not
  after (stacs verify compares bodies by digest, and written data outlives the fix).

## Checked and found sound

- Every built item with a `copc` asset (1,964) re-derived independently from the two header
  caches: point count equal, `file:size` equals the copy's header-read size, max box offset
  0.00999 m (< 0.05), horizontal EPSG equal (3157/3157 and 2955/2955), no CanElevation href
  used twice, no cached COPC header unused.
- `copc_pairs`: duplicate names on either side raise; `(2)` copies cannot pair (stem keeps the
  marker); pairing is over `kept`, so an EXCLUDE file cannot gain an asset.
- `same_crs`: a COPC with no CRS fails; EPSG-less sides fall back to `CRS.equals`; NaN box
  offsets fail (`not off < tol`).
- Failure paths: a failed COPC header read and any mismatch both return 1 before anything is
  written; a pyproj `CRSError` from a garbage COPC WKT is not caught as `ValueError` but still
  aborts the build before the staged swap (fails loud, not toward pass).
- `canelevation_keys_list`: non-200 and truncated-without-token both raise; keys are joined with
  `/` and encoded once at asset construction via `href_encode`.
- Short CanElevation project listings stop the build (accepted tradeoff); `--limit` writes to
  data/build-limit, now gitignored.
- stacs.toml requires only `laz`; nothing in stacs inspects other assets, so the extra asset
  does not affect register/verify.

## Notes (not findings)

- The collection `license` is `CC-BY-4.0` (pre-existing) and items inherit it, while the `copc`
  asset description says the copy is under the Open Government Licence - Canada. The asset text
  states the right licence, so this is a metadata inconsistency rather than a defect in the
  diff; raising it only so it is a decision rather than an accident.
