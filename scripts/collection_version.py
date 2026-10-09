#!/usr/bin/env python3
"""Stamp a release version on the built collection, via the STAC Version Extension.

A version means "the published catalogue is in this state" (NEWS.md), so it is written
at release time, with the version passed in, never derived. As in stac_dem_bc.

Usage:
    uv run python scripts/collection_version.py --version 0.1.0 [--path data/build/collection.json]
"""

import argparse
import json
import re
import sys

VERSION_EXT = "https://stac-extensions.github.io/version/v1.2.0/schema.json"


def version_stamp(collection: dict, version: str) -> dict:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version or ""):
        raise ValueError(f"refusing to stamp {version!r}: not X.Y.Z")
    exts = collection.get("stac_extensions") or []
    if VERSION_EXT not in exts:
        exts.append(VERSION_EXT)
    collection["stac_extensions"] = exts
    collection["version"] = version
    return collection


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--path", default="data/build/collection.json")
    args = ap.parse_args()
    with open(args.path) as fh:
        c = json.load(fh)
    version_stamp(c, args.version)
    with open(args.path, "w") as fh:
        json.dump(c, fh, indent=1)
    print(f"stamped {args.path} version {args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
