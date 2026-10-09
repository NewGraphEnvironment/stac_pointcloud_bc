# Code-check round 4: branch `6-canelevation-overlap` (#6)

Reviewer: subagent, 2026-10-09. Read: the branch diff, 75a7876 in full, scripts/catalogue_build.py,
the copc parts of scripts/laz_item.py, scripts/canelevation_overlap_probe.py, the copc tests,
research/canelevation_overlap.md, the uncommitted NEWS.md / README.md / CLAUDE.md drafts,
scripts/s3_sync.sh, review-round3.md, and the probe log. Waited for the rebuild: the log has
`built 9649 items (1 excluded, 1964 with a COPC copy)` at 08:31:08, per-group 332/57/1155/420,
so the exact floor passes on real data. Suite in a scratch copy: 97 passed.

Re-derived from the rebuilt data/build (read only):
- all 1,964 copc assets carry the 0.05 m text; title "Point cloud (COPC), NRCan CanElevation copy";
- format: 1,575 pairs 1.2/1 -> 1.4/6, 389 pairs 1.4/6 -> 1.4/6 (NEWS's format bullet holds);
- box offset: max 0.00999 m, 371 identical, 1,593 non-zero (research numbers hold);
- CRS: 1,575 source horizontal-only -> copy compound; 389 source compound -> copy horizontal-only;
  full CRS equal in 0 pairs (research numbers hold).

## Findings

- **[severity: fragile]** scripts/catalogue_build.py:82-86 and :192 (`COPC_PAIRS`,
  `copc_pairs_check`). **The R3 mechanism, inside R3's fix.** The comment says "Pairing is a
  deterministic join, so there is no slack: a group pairing fewer than this is refused, since
  the publish would drop those `copc` assets without a word." That is true only while the
  published count equals the recorded one. The guard is one-sided (`n[g] < expected`), so a
  group that grows (LidarBC adds a file to an increment group that CanElevation holds by name,
  or CanElevation adds a same-named file) passes and publishes more assets, and a later loss
  back down to the recorded count also passes, dropping published `copc` assets with no word.
  The unrecorded-group refusal (:196-199) already takes the position that a new pairing must be
  recorded; a recorded group that pairs *more* is the same event and goes unrecorded. The
  deterministic-join argument applies in both directions. Fix: `if n[g] != expected` with the
  message saying which way; tests/test_laz_item.py:765-778 then needs a case for one extra pair.
  Mutation check not needed: with `full` at 1,156 the current check returns None.

- **[severity: fragile, durable record; introduced by 75a7876]** research/canelevation_overlap.md:43-46
  and scripts/canelevation_overlap_probe.py:10. R3's fix turned "the only difference is format"
  into "a vertical CRS added or dropped in **every pair** (below)" and "So a whole-header
  comparison fails for every pair". The paragraph is about the 13,996 name matches and the
  40-pair probe sample across four projects. The CRS was measured only by the build, over the
  1,964 increment pairs, which come from **two** projects (Lower_Mainland_2016: 1,575;
  Riverine_Floodplain_UTM11_2019: 389). Vancouver_Island_Sunshine_Coast_2018 and
  Riverine_Floodplain_UTM10_2019 (11,739 of the 13,996) never had a CRS read: the probe's `read()`
  (:75-81) keeps only n, mins, maxs and fmt. Those two are 1.4/6 -> 1.4/6 in the sample, so a
  preserved WKT is plausible and "every pair" may simply be false there. The same holds for "re-
  quantised by up to 0.01 m" (the probe tested < 1 m). The probe docstring now says "(The CRS
  differs too, in its vertical part ...)" about its step-2 sample, which it never reads a CRS
  for. Scope both claims to the 1,964 pairs the build compared.

- **[severity: fragile, published in 1,964 bodies]** scripts/laz_item.py:333-335 vs :307-308;
  research/canelevation_overlap.md:40. The docstring says "That cannot see a reclassified
  re-delivery under the same name, so the asset claims what was checked and no more." The asset
  it builds opens with "Natural Resources Canada's copy of the `laz` file" and is titled "NRCan
  CanElevation copy": an unqualified copy claim, then the check. The research heading "A matching
  name has been the same points wherever it was checked" likewise says "same points" where what
  was checked is point count and box (and line 76-77 of the same file says that cannot see a
  reclassification). Same claim R3 removed from CLAUDE.md/NEWS ("copies"), surviving in the
  published asset text and the research's bold line. Low cost to scope ("NRCan's COPC of the
  same-named file, checked at build ..."); the parent may judge "copy" acceptable once checked,
  but the docstring then states a property the code does not have.

## Enumeration table (end of review-round3.md): missing or mis-stated rows

- **Missing: scripts/catalogue_build.py:66-71** (`CANELEVATION_PROJECTS` comment). Two claims
  beyond the "count, 90% floor" row: (a) "Its other BC projects hold no file-level copy" is the
  probe's step-4 observation (2022-24 files on candidate sheets, by count+box; the research,
  :96-103, says it cannot see a re-tiled copy) restated as fact; (b) "a moved or shrunk project
  stops the build" — a project that shrinks by under 10% passes the listing floor; only a loss
  among the increment's pairs stops it, and that is COPC_PAIRS, not this floor. Row should read
  "listing floor 90%; a shrink inside the floor is caught only if it hits a recorded pair".
- **Mis-stated: copc asset description row.** The row lists only the check; the published title
  and lead clause claim "copy" (finding 3). laz_item.py:333-335.
- **Mis-stated: research row ("matches (re-measured)")**. research/canelevation_overlap.md:40
  ("same points") and :43-46 ("every pair", CRS) do not match what was measured (findings 2, 3).
  Add scripts/canelevation_overlap_probe.py:10 as its own row.
- **Missing: research producer, research/canelevation_overlap.md:3-6 vs :72-76.** The header names
  "the per-pair check by `scripts/catalogue_build.py` (`logs/20261009_catalogue_build_v0.2.0.log`)"
  as the producer, but the build logs only per-group pair counts. 371 / 1,593 / max 0.01 m /
  1,575 add vertical / 389 drop CGVD2013 / EPSG 3157 and 2955 are computed from
  data/build/headers.jsonl + copc_headers.jsonl by a script that is not committed (all five
  re-derived above and correct). "Never a number without its producer": name the derivation, or
  have the build log it.
- **Missing: NEWS draft "the largest offset 0.01 m (scale rounding)"** — same producer gap.
- **Missing: NEWS draft "nothing else in any item changed (published items compared to the build
  as sets before upload)"**. A set comparison establishes ids added/removed; "nothing else
  changed" needs bodies compared with the `copc` asset removed (digests of the 7,685 untouched
  items equal; the 1,964 equal once `copc` is dropped). Name the producer and run it against
  this rebuild before the claim ships. (Plausibly true: item_create and HEADER_VERSION are
  unchanged on the branch and uv.lock is untouched.)
- **Missing (verified, no change needed): NEWS draft format bullet** — "1,575 copies
  (`Lower_Mainland_2016`) are LAS 1.4 format 6 where the source is 1.2 format 1": re-derived,
  1,575 1.2/1 -> 1.4/6 and 389 1.4/6 -> 1.4/6.
- **Missing, minor: scripts/catalogue_build.py:6-8** (module docstring, "Where NRCan's
  CanElevation republishes a file as COPC ... the item carries it as a second asset") and
  **scripts/laz_item.py:34-36** ("Where it does, the item carries that copy") — both omit the
  check that gates the asset. Internal comments; listed for completeness of the candidate set.

## Checked and found sound

- `copc_pairs_check` exact floor passes on the real rebuild (332/57/1155/420); pairing is over
  `kept`, so the EXCLUDE file is not counted and 092h's 420 is of 1,019.
- Unrecorded-group refusal fires (test asserts it); runs after the floor loop; only INCREMENT
  groups can appear in `pairs`.
- `--limit` skip: correct direction; s3_sync.sh reads only data/build. Removing the skip keeps
  the suite green (97 passed, mutation in scratch) because the only limited-build test pairs
  nothing — a lost skip would fail every real `--limit` run loudly, not pass. Note only.
- f-string `{COPC_BOX_TOLERANCE_M:g}` renders "0.05" in both the asset and the collection
  description (rebuilt JSON checked); README "5 cm" literal accepted per conventions.
- CLAUDE.md draft bullet: dated, says "share a file name", check matches the code.

---

## Disposition (parent session, 2026-10-09)

1. COPC_PAIRS is now two-sided (`!=`), with a test for one extra pair; comment says why both ways.
2. Research and probe scoped: the 40-pair sample says count and box only (no CRS read); the
   CRS, 0.01 m and format statements are scoped to the build's 1,964 pairs from two projects;
   the other two projects' 11,739 files are named as not compared beyond the sample.
3. Published text no longer says "copy": asset title "Point cloud (COPC), NRCan CanElevation",
   description "the COPC that ... publishes under this file's name, checked at build to ...";
   collection description likewise. Research bold line says count and box, not "same points".
4. Enumeration rows added (below). Producer gap closed by `scripts/copc_pairs_measure.py`
   (header-cache measurement + `--published` body comparison), named in research and NEWS.
5. catalogue_build.py comments: other projects "share no file name (and no header, as far as
   the research could test)"; a sub-10% loss is named as caught by COPC_PAIRS, not the floor.

## Enumeration, final (ends the loop)

Mechanical: `grep -niE "cop(y|ies)|same (point|points|extent|crs|file|box|name)|checked|republish|no file|hold no|identical|only difference|every pair"`
over every changed file and draft, plus the CLAUDE.md bullet: 60 hits, each classified.

- **Published strings** (asset title/description, collection DESCRIPTION): describe the
  check only; tolerance derived from COPC_BOX_TOLERANCE_M. No "copy". Enforced by code.
- **Internal vocabulary** ("copy" = a COPC under test or passed): laz_item.py:40, 301-327;
  catalogue_build.py:80, 162-168, 397-402, 434; probe log strings. Not published.
- **Unrelated "copy"**: ` (2)` copy markers (laz_item.py:67, 121), RGB dsm copies (README:20,
  NEWS:49), "a copy of the bucket" (copc_pairs_measure.py:9).
- **Scoped claims**, each with producer: research 41-48 (probe sample, count+box, < 1 m);
  research 52 and 70-82, NEWS 11-28 (build + copc_pairs_measure.py, 1,964 pairs, 2 projects);
  research 89, 99, 101 (probe steps 3-4, with their stated blind spot); CLAUDE.md bullet
  (name not proof; check stated).
- **Observed counts used as guards**: INCREMENT and CANELEVATION_PROJECTS (90% floors,
  rationale in comments), COPC_PAIRS (exact, two-sided, unrecorded group refused).
