#!/usr/bin/env python3
"""Compare a built catalogue with the published one: these changes, and nothing else.

Every published item must still be built, and differ from its build only by what this release
changes on purpose (#2). Each expected change is asserted, then removed, and what is left must
be equal:

- the five `nge:` fields renamed (#12), on the item and on a `copc` asset;
- `lidarbc:delivery` added, equal to the delivery in the item's key (#5);
- the crate schemas of `lidarbc:` and `las:` added to `stac_extensions` (crate#23);
- `classification:classes` added to the `laz` asset, with the classification extension (#10).

A `copc` asset must be unchanged but for its renamed fields: the published groups' pair counts
are pinned in data/copc_pairs.json, so a pair gained or lost there is a regression. Items `links`
are dropped from both sides, as stacs digests bodies without them. The collection is compared
too: the item links a superset, and the other differences printed for NEWS.

Exits 1 on anything unexpected, so acceptance is not done by eye.

Usage:
    aws s3 sync s3://stac-pointcloud-bc /tmp/published
    uv run python scripts/catalogue_compare.py --published /tmp/published [--build data/build]
"""

import argparse
import copy
import json
import os
import sys

from pystac.extensions.classification import ClassificationExtension

from laz_item import ASSET_COPC, ASSET_LAZ, SCHEMA_LAS, SCHEMA_LIDARBC, key_parse

# #12's renames, old -> new. The last two are also on a `copc` asset.
RENAMES = {"nge:product": "lidarbc:product", "nge:datetime_source": "lidarbc:datetime_source",
           "nge:filename_date": "lidarbc:filename_date", "nge:las_version": "las:version",
           "nge:point_format": "las:point_format"}
SCHEMA_CLASSIFICATION = ClassificationExtension.get_schema_uri()


def items_load(d: str) -> dict[str, dict]:
    out = {}
    for f in os.listdir(d):
        if f.endswith(".json") and f != "collection.json":
            with open(os.path.join(d, f)) as fh:
                body = json.load(fh)
            body.pop("links", None)
            out[f[:-5]] = body
    return out


def renamed(d: dict) -> dict:
    return {RENAMES.get(k, k): v for k, v in d.items()}


def item_expected_diff(pub: dict, built: dict) -> list[str]:
    """What differs between a published item and its build beyond this release's changes.
    Empty means "these changes and nothing else"."""
    p, b = copy.deepcopy(pub), copy.deepcopy(built)
    out = []
    p["properties"] = renamed(p["properties"])
    for a in p.get("assets", {}).values():
        a.update(renamed({k: a.pop(k) for k in list(a)}))
    delivery = b["properties"].pop("lidarbc:delivery", None)
    k = key_parse(b["assets"][ASSET_LAZ]["href"].replace("%20", " "))
    if delivery != f"{k['block']}/{k['sheet']}/{k['year']}":
        out.append(f"lidarbc:delivery {delivery!r} is not the key's")
    classes = b["assets"][ASSET_LAZ].pop("classification:classes", None)
    added = set(b.get("stac_extensions", [])) - set(p.get("stac_extensions", []))
    allowed = {SCHEMA_LIDARBC, SCHEMA_LAS} | ({SCHEMA_CLASSIFICATION} if classes else set())
    if added - allowed:
        out.append(f"stac_extensions added beyond this release's: {sorted(added - allowed)}")
    if {SCHEMA_LIDARBC, SCHEMA_LAS} - set(b.get("stac_extensions", [])):
        out.append("stac_extensions lacks a crate schema")
    if set(p.get("stac_extensions", [])) - set(b.get("stac_extensions", [])):
        out.append("stac_extensions lost "
                   f"{sorted(set(p['stac_extensions']) - set(b['stac_extensions']))}")
    p.pop("stac_extensions", None)
    b.pop("stac_extensions", None)
    if p != b:
        keys = sorted({x for x in p.keys() | b.keys() if p.get(x) != b.get(x)})
        for x in ("properties", "assets"):
            if x in keys:
                sub = sorted({y for y in p[x].keys() | b[x].keys() if p[x].get(y) != b[x].get(y)})
                keys[keys.index(x)] = f"{x}: {sub}"
        out.append(f"differs in {keys}")
    return out


def collection_diff(pub: dict, built: dict) -> tuple[list[str], list[str]]:
    """(problems, changes) between the published and built collection.json."""
    problems, changes = [], []
    pi = {l["href"] for l in pub["links"] if l["rel"] == "item"}
    bi = {l["href"] for l in built["links"] if l["rel"] == "item"}
    if pi - bi:
        problems.append(f"{len(pi - bi)} published item links not in the build")
    changes.append(f"item links {len(pi)} -> {len(bi)}")
    for k in sorted(pub.keys() | built.keys()):
        if k in ("links", "version", "extent") or pub.get(k) == built.get(k):
            continue
        changes.append(f"{k}: changed")
    rel = [l for l in built["links"] if l["rel"] == "related"]
    changes.append(f"related links: {[l['href'] for l in rel]}")
    return problems, changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--published", required=True)
    args = ap.parse_args()
    built = items_load(f"{args.build}/items")
    pub = items_load(args.published)
    only_pub = sorted(pub.keys() - built.keys())
    bad = {k: e for k in sorted(pub.keys() & built.keys())
           if (e := item_expected_diff(pub[k], built[k]))}
    classes = sum("classification:classes" in v["assets"][ASSET_LAZ] for v in built.values())
    copc_new = sum(ASSET_COPC in v["assets"] for k, v in built.items() if k not in pub)
    print(f"published {len(pub)}, built {len(built)}; only published {len(only_pub)}, "
          f"new {len(built.keys() - pub.keys())} ({copc_new} with {ASSET_COPC}); "
          f"items with class lists {classes}")
    print(f"published items differing beyond this release's changes: {len(bad)}")
    for k, e in list(bad.items())[:20]:
        print(f"  {k}: {'; '.join(e)}")
    for k in only_pub[:20]:
        print(f"  only published: {k}")
    with open(f"{args.published}/collection.json") as fh:
        pc = json.load(fh)
    with open(f"{args.build}/collection.json") as fh:
        bc = json.load(fh)
    problems, changes = collection_diff(pc, bc)
    print("collection: " + "; ".join(changes))
    for p in problems:
        print(f"  collection problem: {p}")
    return 1 if (bad or only_pub or problems) else 0


if __name__ == "__main__":
    sys.exit(main())
