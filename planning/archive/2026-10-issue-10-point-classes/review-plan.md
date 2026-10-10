# Plan review (Plan agent, 2026-10-10 UTC) and disposition

Frame the reviewer set: a sample can only miss classes, never add them, so a "mixed" verdict
is certain and only a "ground-only" verdict can be wrong. Every check aims at false
ground-only.

| finding | disposition |
|---|---|
| B1 COPC agreement cannot validate the 7 no-COPC deliveries | Taken, stronger: every item any sample calls ground-only is **fully decompressed** (`--confirm`). Mixed is certain, so the prevalence becomes exact, not estimated, in every delivery. |
| B2 a COPC disagreement may be a reclassified re-delivery, not a sampling error | Covered by the full read: the laz is the source of record. |
| B3 {9} or {7} alone reads ground-only; empty sample | Taken: ground-only requires class 2. Empty was already `None` and tested. 1.2 class 8/12: the class-set table shows them; handled if seen. Non-ground fraction reported in the summary. |
| G1 cost is per chunk | Already so (first 2 chunks + 3 single chunks). |
| G2 single-threaded backend seeks pathologically | Taken: `LazrsParallel` pinned. Bytes per file are in each record, so a fallback shows. |
| G3 class-sorted files; last chunk; clamp | Covered by the full read of every ground-only verdict. Seeks are < point_count by construction (`at < 1`, n > 250k). |
| G4 no COPC test path | Not taken: laspy cannot write COPC. `copc_sample` is a thin reader over the tested `classes_count`; verified live (smoke). |
| G5 header identity per file; "delivery" has no key | Taken in the full read (system id, software, creation date, format). Delivery stays mapsheet-year (#5 is open). |
| G6 filtered vs bare tile | Taken: the full read tallies (return_number, number_of_returns). |
| G7 ETag-keyed cache | Phase 4, if items gain a property. The probe is a measurement keyed on the build's ids. |
| G8 move range server to conftest | Not taken: imported from test_laz_item; no duplication. |
| O1 COPC groups first as a gate | Superseded by the full-read confirmation. |
| O2 verdict recomputable from raw counts | Yes: records hold counts; `--summary` recomputes. |
| A1 density screen | Taken: summary reports each ground-only item's density against its mapsheet-year (from `headers.jsonl`). Also a Phase 3 option for #2. |
| A2 COPC levels not class-proportional | Agreed: used for the verdict only, never proportions. |
| A3 the 9,649 are a biased sample for #2 | Agreed; named at the Phase 3 gate. |
| A4 cost; no retry | Failures are recorded and re-read on re-run. Measured cost goes in research. |
| S1 body-diff tool removes only `copc` | Phase 4. |
| S2 laspy floor | Taken: `laspy[lazrs]>=2.7`. |
