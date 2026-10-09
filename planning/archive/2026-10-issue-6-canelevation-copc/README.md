## Outcome

NRCan's CanElevation series publishes COPC under 13,996 LidarBC file names, in four of its
projects (`research/canelevation_overlap.md`). The maintainer chose to link (decision A), and
v0.2.0 does: 1,964 of the 9,649 items carry the CanElevation COPC as a second asset, `copc`,
and the collection description names the four projects. The build pairs by name but trusts
the header. It reads every CanElevation file it pairs, links it only when point count and
horizontal CRS are the same and the box (x, y, z) is within 0.05 m, and refuses a group whose
pair count differs from the one recorded (`COPC_PAIRS`). What the four code-check rounds
taught: every round found published or durable text claiming more than the code checked
("same CRS", "same extent", "copies", "only difference is format"). Each fix restated a
fresh observation as a guarantee, and the next round found it again, so the loop ended on a
mechanical enumeration of every such claim rather than on a quiet round (review-round4.md).

## Measurement

Over all 1,964 pairs (1,575 `Lower_Mainland_2016`, 389 `Riverine_Floodplain_UTM11_2019`):
largest box offset 0.01 m in x/y and in z (371 identical, 1,593 within 0.01 m); horizontal
EPSG equal in every pair (3157, 2955), full CRS equal in none; 1,575 converted LAS 1.2/1 ->
1.4/6. That moved the tolerance from 1 m (the probe's) to 0.05 m, and the asset text from
"same CRS and extent" to what is checked. Against the published v0.1.0, exactly those 1,964
bodies changed, by the `copc` asset alone; registration verified `IN SYNC` (9,649 both ways).
Producer: `scripts/copc_pairs_measure.py` (`--published` for the body comparison).

## Evidence

`logs/20261009_*` (gitignored: build, sync and register logs of v0.2.0); the review files
in this directory.

Closed by: PR #8
