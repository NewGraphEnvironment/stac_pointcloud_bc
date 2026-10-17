#!/usr/bin/env python3
"""Compare a built catalogue with the published one: this release's change, and nothing else.

#17 samples every file's classes, so a build may give an item that had no class list one: the
`laz` asset's `classification:classes` and the classification extension, both added together.
A list the published item already carries must be unchanged, and none may be dropped. The
collection's `description` may change (it says how the lists were made).

Footprints were rounded to `laz_item.LONLAT_DECIMALS` in 0.4.0 (#22, #4), and are still held
to that: `geometry` and `bbox` may differ only by the rounding, each built coordinate carrying
at most LONLAT_DECIMALS decimals and lying within half a unit of its last place of the
published one (plus float slack, `TOLERANCE`), with the same structure. Every other key must
be equal, `copc` asset included. (The 0.3.0 version of this script, which checked #2's changes,
is at tag v0.3.0.)

Items `links` are dropped from both sides, as stacs digests bodies without them. The published
items are the ones the published collection.json links; each must be in the local copy, and the
copy must hold no other. The build is held to the same: its collection.json links exactly its
items/, and its extent is exactly its items' envelope. A new item's footprint is rounded too. An item only in the build is new LidarBC data and is reported, not
failed; one only in the bucket fails.
The collection is compared too: its item links must be a superset of the published ones, its
extent must be the published one to TOLERANCE when nothing is new and contain it when something
is, and `version` and the version extension's URL are free (the release stamps them, after this
check). Anything else that differs is printed and fails.

Exits 1 on anything unexpected, so acceptance is not done by eye.

Usage:
    aws s3 sync s3://stac-pointcloud-bc /tmp/published --exclude 'build-cache/*'
    uv run python scripts/catalogue_compare.py --published /tmp/published [--build data/build]
"""

import argparse
import copy
import json
import os
import sys

from pystac.extensions.classification import ClassificationExtension

from collection_version import VERSION_EXT
from laz_item import ASSET_LAZ, LONLAT_DECIMALS

# Half a unit in the last kept place, plus slack for the binary form of either value.
TOLERANCE = 0.5 * 10 ** -LONLAT_DECIMALS + 1e-12
ROUNDED = ("geometry", "bbox")
CLASSES = "classification:classes"
CLASSIFICATION_EXT = ClassificationExtension.get_schema_uri()


def classes_added(pub: dict, built: dict) -> bool:
    """Whether the build gives the item a class list it had none of (#17): the list on the laz
    asset and the classification extension, where the published item carries neither."""
    pa, ba = pub.get("assets", {}).get(ASSET_LAZ, {}), built.get("assets", {}).get(ASSET_LAZ, {})
    return (CLASSES in ba and CLASSES not in pa
            and CLASSIFICATION_EXT in built.get("stac_extensions", [])
            and CLASSIFICATION_EXT not in pub.get("stac_extensions", []))


def items_load(d: str) -> dict[str, dict]:
    out = {}
    for f in os.listdir(d):
        if f.endswith(".json") and f != "collection.json":
            with open(os.path.join(d, f)) as fh:
                body = json.load(fh)
            body.pop("links", None)
            out[f[:-5]] = body
    return out


def linked_ids(collection: dict) -> set[str]:
    """The item ids a collection links, read back from each href the way s3_sync.sh and stacs
    read them: the file name, %20 decoded, without `.json`."""
    out = set()
    for l in collection["links"]:
        if l["rel"] == "item":
            name = l["href"].rsplit("/", 1)[-1].replace("%20", " ")
            out.add(name[:-5] if name.endswith(".json") else name)
    return out


def rounding_diff(pub, built, where: str) -> list[str]:
    """Where `built` is not `pub` rounded: the same structure, every number within TOLERANCE
    and carrying at most LONLAT_DECIMALS decimals."""
    if isinstance(pub, dict) and isinstance(built, dict):
        if pub.keys() != built.keys():
            return [f"{where}: keys {sorted(pub)} -> {sorted(built)}"]
        return [e for k in pub for e in rounding_diff(pub[k], built[k], f"{where}.{k}")]
    if isinstance(pub, list) and isinstance(built, list):
        if len(pub) != len(built):
            return [f"{where}: length {len(pub)} -> {len(built)}"]
        return [e for i, (p, b) in enumerate(zip(pub, built))
                for e in rounding_diff(p, b, f"{where}[{i}]")]
    if (isinstance(pub, (int, float)) and isinstance(built, (int, float))
            and not isinstance(pub, bool) and not isinstance(built, bool)):
        if abs(pub - built) > TOLERANCE:
            return [f"{where}: {pub!r} -> {built!r}, beyond the rounding"]
        if round(built, LONLAT_DECIMALS) != built:
            return [f"{where}: {built!r} carries more than {LONLAT_DECIMALS} decimals"]
        return []
    return [] if pub == built else [f"{where}: {pub!r} -> {built!r}"]


def coords(x):
    """Every number in a geometry or bbox, in order."""
    if isinstance(x, dict):
        return [v for k in sorted(x) for v in coords(x[k])]
    if isinstance(x, list):
        return [v for e in x for v in coords(e)]
    return [x] if isinstance(x, (int, float)) and not isinstance(x, bool) else []


def items_envelope(items: dict[str, dict]) -> dict:
    """The extent a collection of these items must carry: the envelope of their bboxes, and
    their earliest and latest datetime, as catalogue_build.collection_build derives it."""
    boxes = [i["bbox"] for i in items.values()]
    starts = [i["properties"].get("datetime") or i["properties"]["start_datetime"]
              for i in items.values()]
    ends = [i["properties"].get("datetime") or i["properties"]["end_datetime"]
            for i in items.values()]
    return {"spatial": {"bbox": [[min(b[0] for b in boxes), min(b[1] for b in boxes),
                                  max(b[2] for b in boxes), max(b[3] for b in boxes)]]},
            # pystac writes whole-second UTC `...Z` strings, which order as their instants.
            "temporal": {"interval": [[min(starts), max(ends)]]}}


def extent_widened(pub: dict, built: dict) -> list[str]:
    """Where the built extent does not contain the published one: what new items may do to it.
    Each spatial box may only grow (to TOLERANCE), each interval may only start earlier or end
    later, and the structure is the published one."""
    out = []
    for where, p, b in (("extent", pub, built), ("extent.spatial", pub["spatial"], built["spatial"]),
                        ("extent.temporal", pub["temporal"], built["temporal"])):
        if p.keys() != b.keys():
            out.append(f"{where}: keys {sorted(p)} -> {sorted(b)}")
    pb, bb = pub["spatial"]["bbox"], built["spatial"]["bbox"]
    if len(pb) != len(bb) or any(len(p) != 4 or len(b) != 4 for p, b in zip(pb, bb)):
        return [f"extent.spatial: structure {pb} -> {bb}"]
    for i, (p, b) in enumerate(zip(pb, bb)):
        if not (b[0] <= p[0] + TOLERANCE and b[1] <= p[1] + TOLERANCE
                and b[2] >= p[2] - TOLERANCE and b[3] >= p[3] - TOLERANCE):
            out.append(f"extent.spatial.bbox[{i}]: {p} -> {b}, does not contain the published")
    pt, bt = pub["temporal"]["interval"], built["temporal"]["interval"]
    if len(pt) != len(bt) or any(len(p) != 2 or len(b) != 2 for p, b in zip(pt, bt)):
        return out + [f"extent.temporal: structure {pt} -> {bt}"]
    for i, (p, b) in enumerate(zip(pt, bt)):
        # ISO 8601 UTC strings order as their instants; None is an open end.
        start_ok = b[0] is None or (p[0] is not None and b[0] <= p[0])
        end_ok = b[1] is None or (p[1] is not None and b[1] >= p[1])
        if not (start_ok and end_ok):
            out.append(f"extent.temporal.interval[{i}]: {p} -> {b}, does not contain the published")
    return out


def item_expected_diff(pub: dict, built: dict) -> list[str]:
    """What differs between a published item and its build beyond the rounding. Empty means
    "this release's change and nothing else"."""
    out = [e for k in ROUNDED for e in rounding_diff(pub.get(k), built.get(k), k)]
    p, b = copy.deepcopy(pub), copy.deepcopy(built)
    for k in ROUNDED:
        p.pop(k, None)
        b.pop(k, None)
    if classes_added(p, b):
        b["assets"][ASSET_LAZ].pop(CLASSES)
        b["stac_extensions"].remove(CLASSIFICATION_EXT)
    if p != b:
        keys = sorted({x for x in p.keys() | b.keys() if p.get(x) != b.get(x)})
        for x in ("properties", "assets"):
            if x in keys and isinstance(p.get(x), dict) and isinstance(b.get(x), dict):
                sub = sorted({y for y in p[x].keys() | b[x].keys() if p[x].get(y) != b[x].get(y)})
                keys[keys.index(x)] = f"{x}: {sub}"
        out.append(f"differs in {keys}")
    return out


def collection_diff(pub: dict, built: dict, new: int) -> tuple[list[str], list[str]]:
    """(problems, changes) between the published and built collection.json, given how many
    items are new in the build (new items may move the extent)."""
    problems, changes = [], []
    pi = {l["href"] for l in pub["links"] if l["rel"] == "item"}
    bi = {l["href"] for l in built["links"] if l["rel"] == "item"}
    if pi - bi:
        problems.append(f"{len(pi - bi)} published item links not in the build")
    changes.append(f"item links {len(pi)} -> {len(bi)}")
    other = lambda c: [l for l in c["links"] if l["rel"] != "item"]
    if other(pub) != other(built):
        problems.append("non-item links changed")
    if pub.get("version") != built.get("version"):
        changes.append(f"version {pub.get('version')} -> {built.get('version')}")
    ext = rounding_diff(pub.get("extent"), built.get("extent"), "extent")
    if ext and new:
        try:
            wider = extent_widened(pub["extent"], built["extent"])
        except (KeyError, TypeError) as e:
            wider = [f"extent: unreadable ({e!r})"]
        problems.extend(wider)
        if not wider:
            changes.append(f"extent widened, with {new} new item(s): {'; '.join(ext[:4])}")
    else:
        problems.extend(ext)
    exts = lambda c: [e for e in c.get("stac_extensions", []) if e != VERSION_EXT]
    if exts(pub) != exts(built):
        problems.append(f"stac_extensions: {exts(pub)} -> {exts(built)}")
    for k in sorted(pub.keys() | built.keys()):
        if k == "description" and pub.get(k) != built.get(k):
            changes.append("description changed")
        elif (k not in ("links", "version", "extent", "stac_extensions", "description")
                and pub.get(k) != built.get(k)):
            problems.append(f"{k}: changed")
    return problems, changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--published", required=True)
    args = ap.parse_args()
    built = items_load(f"{args.build}/items")
    pub = items_load(args.published)
    with open(f"{args.published}/collection.json") as fh:
        pc = json.load(fh)
    with open(f"{args.build}/collection.json") as fh:
        bc = json.load(fh)
    # The published set is what the published collection links, not what a local copy of the
    # bucket happens to hold: an interrupted copy must fail here, not read as new items.
    linked = linked_ids(pc)
    not_copied = sorted(linked - pub.keys())
    unlinked = sorted(pub.keys() - linked)
    # The build is checked against itself too: its items/ and its collection.json are two
    # writes, and the collection is what is published.
    build_linked = linked_ids(bc)
    build_mismatch = sorted(build_linked ^ built.keys())
    only_pub = sorted(linked - build_linked)
    new = sorted(build_linked - linked)
    bad = {k: e for k in sorted(pub.keys() & built.keys())
           if (e := item_expected_diff(pub[k], built[k]))}
    # A new item has no published twin, but its footprint is rounded like every other.
    bad.update({k: e for k in new if k in built
                and (e := [x for f in ROUNDED for x in rounding_diff(built[k].get(f),
                                                                     built[k].get(f), f)])})
    shared = sorted(pub.keys() & built.keys())
    moved = sum(pub[k]["bbox"] != built[k]["bbox"] for k in shared)
    pairs = [(p, b) for k in shared for x in ROUNDED
             for p, b in zip(coords(pub[k].get(x)), coords(built[k].get(x)))]
    exact = sum(round(p, LONLAT_DECIMALS) == b for p, b in pairs)
    shift = max((abs(p - b) for p, b in pairs), default=0.0)
    print(f"published {len(pub)}, built {len(built)}; only published {len(only_pub)}, "
          f"new {len(new)}; published items whose bbox the rounding moved {moved}")
    print(f"coordinates compared {len(pairs)}, equal to the published rounded to "
          f"{LONLAT_DECIMALS} decimals {exact}; largest shift {shift:.3g} degrees")
    gained = sum(classes_added(pub[k], built[k]) for k in shared)
    print(f"published items given a class list they had none of: {gained}")
    print(f"published items differing beyond the rounding: {len(bad)}")
    for k, e in list(bad.items())[:20]:
        print(f"  {k}: {'; '.join(e[:3])}")
    for k in only_pub[:20]:
        print(f"  only published: {k}")
    for k in new[:20]:
        print(f"  new: {k}")
    print(f"linked by the published collection {len(linked)}: not in the local copy "
          f"{len(not_copied)}, local files it does not link {len(unlinked)}")
    for k in (not_copied + unlinked)[:20]:
        print(f"  {'not copied' if k in linked else 'unlinked'}: {k}")
    print(f"linked by the built collection {len(build_linked)}: differing from its items/ "
          f"{len(build_mismatch)}")
    for k in build_mismatch[:20]:
        print(f"  {'linked, no item file' if k in build_linked else 'item file, not linked'}: {k}")
    problems, changes = collection_diff(pc, bc, len(new))
    if built:
        envelope = items_envelope(built)
        if bc.get("extent") != envelope:
            problems.append(f"extent {bc.get('extent')} is not its items' envelope {envelope}")
    print("collection: " + "; ".join(changes))
    for p in problems:
        print(f"  collection problem: {p}")
    return 1 if (bad or only_pub or not_copied or unlinked or build_mismatch or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
