# Code-check round 3: branch `6-canelevation-overlap` (#6)

Reviewer: subagent, 2026-10-09. Read in full: the branch diff, scripts/catalogue_build.py,
the diff's laz_item.py / probe / tests / research hunks, the uncommitted NEWS.md, README.md
and CLAUDE.md drafts, s3_sync.sh, stacs.toml, and logs/20261009_catalogue_build_v0.2.0.log.
Checked against data/build/ (read only). Test suite: 97 passed. Every mutation below was run
in a scratch copy, never in the repo.

## The mechanism behind R1 and R2

**What the 2026-10-09 snapshot showed was written down as what the code guarantees.** The
property "this COPC is the LAZ's copy, and every copy is linked" is decided in one place: the
pairing join (`copc_pairs`) and the three comparisons in `copc_asset_add`. Every restatement
of it was written from the observed population, or from an upstream proxy, rather than from
the comparison the code makes. That is code-check.md's "One fact derived twice" plus "A proxy
is not the property":

| instance | observed or upstream proxy | written as | what the code enforces |
|---|---|---|---|
| R1 asset text | horizontal CRS agreed | "same CRS" | horizontal EPSG only (full CRS differs in all 1,964) |
| R2 asset/README text | boxes within 1 cm | "same extent" | box within 0.05 m |
| R2 collection text | research summary: 4 projects matched | "republishes four projects" | file-level name matches (139 LM files are not) |
| R2 guard | listing count complete | "a moved or shrunk project stops the build" | count only; the join downstream unguarded |

Nothing re-derives the restatements from the code, so each drifts toward the stronger,
observed claim. Below is every place it still reaches.

## Findings

- **[severity: fragile, published text in the durable record]** research/canelevation_overlap.md:43-45
  (and the same claim in scripts/canelevation_overlap_probe.py:9-10, "differs there and nowhere
  else"). "Apart from coordinates re-quantised by up to 0.01 m, the only difference is format
  ... which is why a whole-header comparison fails for that project and nowhere else." This
  is R1's CRS instance, surviving in the research file. The R2 fix added the box caveat to this
  sentence and left the CRS one out. The same file's lines 447-449 of the diff say the full CRS
  never matches. Re-derived from data/build/headers.jsonl and copc_headers.jsonl (header
  fields other than file_size that differ, per pair):

  | project | pairs | fields that differ |
  |---|---:|---|
  | Riverine_Floodplain_UTM11_2019 | 285 | `crs_wkt` only |
  | Riverine_Floodplain_UTM11_2019 | 104 | `crs_wkt` + `mins`/`maxs` |
  | Lower_Mainland_2016 | 1,575 | `crs_wkt`, `dimensions`, `las_version`, `point_format` (+ box in 1,489) |

  So a whole-header comparison fails for **every** UTM11 pair too, and the format is not the
  only difference: the vertical CRS is added (LM) or dropped (UTM11, CGVD2013) in all 1,964.
  This is the durable verdict file a later reader trusts, and the paragraph contradicts the
  section below it. Suggested wording: "Apart from coordinates re-quantised by up to 0.01 m and
  the vertical CRS (below), the difference is format ... which is why a comparison of LAS
  version and point format fails for that project and nowhere else."

- **[severity: published text, minor]** CLAUDE.md draft line 38 ("**13,996 of the
  `pointcloud/*.laz` have a copy in NRCan's CanElevation series**"), NEWS.md draft line 16
  ("CanElevation republishes 13,996 LidarBC files in all"), and the research heading at line 22
  ("13,996 LidarBC files are republished"). 13,996 is the count of **name matches**. Header
  checks have been made on 1,964 pairs (the build) plus 40 (the probe sample). The code states
  the rule itself: "A matching file name is how a copy is found, not proof that it is one"
  (laz_item.py, `copc_asset_add` docstring). The research body keeps the qualifier ("A matching
  name has been the same points wherever it was checked"). CLAUDE.md and NEWS drop it, and they
  are the two files most likely to be quoted. Wording that holds: "13,996 have a same-named
  COPC in CanElevation; the 2,004 compared by header are the same points". Also, the
  CLAUDE.md bullet sits under "## Source facts (measured 2026-10-06, live walk of 575,438
  keys)", but it was measured 2026-10-09 in another bucket. Give the bullet its own date.

- **[severity: fragile]** scripts/catalogue_build.py:79-84 and :185-192 (`COPC_PAIRS`,
  `copc_pairs_check`). The R2 fix reproduces the R2 mechanism inside itself in two ways:
  1. **The tolerance is borrowed.** The 90% slack was copied from the listing floors, where
     it absorbs listing noise. Pairing is a deterministic join against a known published
     state, so the slack only hides loss. Up to 115 assets in `092g/2016`, 42 in `092h/2016`,
     33 in `082e/2019` and 5 in `082l/2019` can go while the build exits 0. Example: CanElevation
     reprocesses or renames a few hundred Lower_Mainland tiles. The comment says the guard
     stops "the publish would drop its `copc` assets without a word"; up to 10% per group is
     dropped without a word. (`stacs verify` would then list those bodies as changed, so the
     loss is visible at registration. It is not visible at build or sync.) Floor at
     the measured count, or at 100% less a stated number, unless there is a known reason for
     legitimate shrinkage.
  2. **"Groups not named here have no copy" is a snapshot of today's INCREMENT.** Nothing
     enforces it. CLAUDE.md and NEWS both say later increments will link more of the 13,996.
     A group added to INCREMENT that pairs is unguarded until someone remembers COPC_PAIRS.
     A cheap way to enforce the comment: raise when `pairs` contains a group not in
     COPC_PAIRS.
  Neither affects the v0.2.0 build, which paired 1,964 of 1,964 (log: 332/57/1155/420).

- **[severity: bug if published as-is; already noted in R2 and still open]** data/build/ is
  the pre-fix build. It was built at 08:07, before b810750 (08:11) and ab4c052 (08:18).
  **All 1,964** item bodies carry "same point count, CRS and extent" (grep: 1,964 files).
  collection.json carries "republishes four LidarBC projects ... checked to have the same point
  count and extent". So the published JSON is where the mechanism lands. s3_sync.sh uploads
  data/build verbatim and checks only the link set. Rebuild before the sync, then confirm
  mechanically: `grep -l 'CRS and extent' data/build/items/*.json | wc -l` must print 0,
  `grep -c 'horizontal CRS' data/build/collection.json` must print 1, and 1,964 items must
  carry "horizontal CRS". The research header's cited log
  (`logs/20261009_catalogue_build_v0.2.0.log`) is this pre-fix build. Its counts still hold,
  because only text changed. But the name will mislead unless the rebuild's log replaces it.
  The same applies to NEWS ("published items compared to the build as sets before upload"):
  re-run that comparison against the rebuild.

## Review of the round-2 fixes

- `copc_pairs_check` grouping: `key_parse(u)["key"].split("/")[:3]` yields `082/082e/2019`,
  the same form as COPC_PAIRS and `group()`. The COPC_PAIRS values match the build log
  exactly (sum 1,964). Mutations: removing the call from `main()` turns 1 test red, and a
  zero floor turns 2 red. **Fires.**
- `--limit` skip: the direction is correct, and inverting it turns 1 test red. **Removing the
  skip altogether stays green (97 passed)**, because every limited-build test also patches
  `COPC_PAIRS = {}`. If the skip were lost, every real `--limit` build would fail loudly. That
  is not a fail-toward-pass, so this is a note, not a finding.
- Autouse `no_live_listing` fixture: it fires. With the `copc_listing` patches removed, 3 tests
  go red with "a test reached a live bucket listing". It covers only the two listers bound in
  `catalogue_build`, not header reads through `headers_fetch`'s default `reader`. I ran the
  whole suite with the objectstore, CanElevation and amazonaws hosts blocked at `getaddrinfo`:
  97 passed. So no current test reaches a live bucket by any route. Note only.
- `copc_asset_add` / collection DESCRIPTION / README / CLAUDE.md / NEWS wording of the check
  ("same point count and horizontal CRS, and a header box within 5 cm / 0.05 m") matches the
  code. "5 cm" is still a literal restating `COPC_BOX_TOLERANCE_M` in the asset text and the
  collection DESCRIPTION, so one fact is derived twice. It agrees today, and a tolerance change
  would silently desync 1,964 bodies. Building the string from the constant would close it. Not
  a defect now.

## Checked and found sound

- No test reaches a live bucket (suite run with live hosts blocked: 97 passed).
- The probe's `ce_list`/`ce_project` slicing is consistent with `canelevation_keys_list`'s url
  form.
- `copc_pairs` duplicate checks are scoped to matched names. The EXCLUDE file is not paired
  (pairing is over `kept`).
- A failed COPC read and any mismatch both return 1 before the staged swap. The pair-count
  check raises before any write (the test confirms that items/ is absent).

---

## Disposition (parent session, 2026-10-09)

All four fixed in the round-3 commit: research and probe wording, "copies" made "file names"
(and the CLAUDE.md bullet dated 2026-10-09), COPC_PAIRS made exact with unrecorded groups
refused, and the tolerance text in both descriptions derived from COPC_BOX_TOLERANCE_M.
data/build is rebuilt before publish, and the set check against the published items is re-run.

## Enumeration (ends the loop for this mechanism)

Mechanism: an observation from the 2026-10-09 snapshot restated as what the code guarantees.
Candidate set = every restatement on the branch of (a) the copy check, (b) the pairing scope,
(c) an observed count used as a guard. Each with its source of truth:

| where | claim | source of truth | state |
|---|---|---|---|
| laz_item.py COPC_BOX_TOLERANCE_M comment | count, horizontal CRS, x/y/z box within tol | copc_asset_add | matches |
| laz_item.py copc_asset_add docstring | same | copc_asset_add | matches |
| copc asset description (published) | count, horizontal CRS, box within {tol} | derived from constant | enforced |
| collection DESCRIPTION (published) | four projects, same names, check | CANELEVATION_PROJECTS + constant | enforced / derived |
| README draft | count, horizontal CRS, box within 5 cm | constant 0.05 | matches (literal in prose) |
| CLAUDE.md draft | name not proof; count, horizontal CRS, 0.05 m | copc_asset_add | matches |
| NEWS draft | 1,964 and per-group counts | rebuilt build log | re-derive after rebuild |
| research | sample 40 at < 1 m; build all pairs at 0.05 m; header differences | probe `same()`; build cache | matches (re-measured) |
| CANELEVATION_PROJECTS | .laz counts, 90% floor | live listing; rationale in comment | floor documented |
| COPC_PAIRS | pairs per group, exact; unrecorded refused | copc_pairs_check | enforced |
| COPC_BOX_TOLERANCE_M | 0.05 vs measured 0.01 max | build cache | documented |
