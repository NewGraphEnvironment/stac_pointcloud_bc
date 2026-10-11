#!/usr/bin/env python3
"""Measure the `copc` pairs of a built catalogue, and what changed against the published one.

Reads the build's items and its two header caches (`headers.jsonl`, `copc_headers.jsonl`)
and prints, for every item with a `copc` asset: the count per group, how far the two header
boxes differ, the CRS names and horizontal EPSG of both files, and the LAS version and point
format of both. These are the numbers research/canelevation_overlap.md and NEWS.md quote (#6).

The published-vs-build comparison it once did for 0.2.0 is `catalogue_compare.py` (#2).

Usage:
    uv run python scripts/copc_pairs_measure.py [--build data/build]
"""

import argparse
import collections
import json
import os
import sys

from pyproj import CRS

from laz_item import ASSET_COPC, ASSET_LAZ, _horizontal, key_parse


def cache_load(path: str) -> dict[str, dict]:
    with open(path) as fh:
        return {r["url"]: r["header"] for r in map(json.loads, fh)}


def items_load(d: str) -> dict[str, dict]:
    out = {}
    for f in os.listdir(d):
        if f.endswith(".json") and f != "collection.json":
            with open(os.path.join(d, f)) as fh:
                body = json.load(fh)
            body.pop("links", None)
            out[f[:-5]] = body
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    args = ap.parse_args()

    items = items_load(f"{args.build}/items")
    laz = cache_load(f"{args.build}/headers.jsonl")
    copc = cache_load(f"{args.build}/copc_headers.jsonl")
    paired = {k: v for k, v in items.items() if ASSET_COPC in v["assets"]}

    groups, crs, epsg, fmt = (collections.Counter() for _ in range(4))
    boxes, xy, z = collections.Counter(), 0.0, 0.0
    for v in paired.values():
        # The laz href is percent-encoded at construction; the cache is keyed by the raw URL.
        u = v["assets"][ASSET_LAZ]["href"].replace("%20", " ")
        a, b = laz[u], copc[v["assets"][ASSET_COPC]["href"]]
        p = key_parse(u)
        groups[f"{p['block']}/{p['sheet']}/{p['year']}"] += 1
        dxy = max(abs(x - y) for x, y in zip(a["mins"][:2] + a["maxs"][:2],
                                             b["mins"][:2] + b["maxs"][:2]))
        dz = max(abs(a["mins"][2] - b["mins"][2]), abs(a["maxs"][2] - b["maxs"][2]))
        xy, z = max(xy, dxy), max(z, dz)
        boxes["identical" if max(dxy, dz) == 0 else "differ"] += 1
        ca, cb = CRS.from_wkt(a["crs_wkt"]), CRS.from_wkt(b["crs_wkt"])
        crs[(ca.name, cb.name)] += 1
        epsg[(_horizontal(ca).to_epsg(), _horizontal(cb).to_epsg())] += 1
        fmt[(f"{a['las_version']}/{a['point_format']}",
             f"{b['las_version']}/{b['point_format']}")] += 1

    print(f"items {len(items)}, with {ASSET_COPC} {len(paired)}")
    for g, n in sorted(groups.items()):
        print(f"  {g}\t{n}")
    print(f"box: {dict(boxes)}; largest offset x/y {xy:.4f} m, z {z:.4f} m")
    print("CRS (laz -> copc):")
    for (x, y), n in crs.most_common():
        print(f"  {n}\t{x} -> {y}")
    print(f"horizontal EPSG (laz, copc): {dict(epsg)}")
    print(f"LAS version/format (laz -> copc): {dict(fmt)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
