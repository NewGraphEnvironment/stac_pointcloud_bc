#!/usr/bin/env python3
"""Sample the ASPRS classes in each built item's point cloud, to find the ground-only ones (#10).

The LAS header carries no class counts, so a file holding ground returns only reads like any
other to the build. This reads points: for each item in a build (`data/build/items`), the
`laz` file's first FIRST_POINTS points plus SPREAD_POINTS at each of SPREAD_AT through the
file (LAZ is chunked, so a seek fetches one chunk, not the file), and where the item has a
`copc` asset, that COPC's coarse octree levels (COPC_LEVELS), which cover the whole tile.
Each sample's class counts are kept separately, so how often the first points alone would
have misled is measured rather than assumed.

One JSON line per item goes to `--out` as it lands; a re-run reads only the items missing
from it. A failed read is recorded with its error and read again next run. `--summary` prints
the tables research/laz_classes.md quotes and reads nothing remote.

Usage:
    uv run python scripts/laz_classes_probe.py [--build data/build] [--workers 16] [--limit N]
    uv run python scripts/laz_classes_probe.py --summary
"""

import argparse
import collections
import concurrent.futures
import json
import logging
import os
import sys
import time
import urllib.parse

import laspy
import numpy as np
import requests
from tqdm import tqdm

from catalogue_build import cache_tail_repair
from laz_item import ASSET_COPC, ASSET_LAZ, key_parse
from laz_remote import HttpRangeFile

logger = logging.getLogger("laz_classes_probe")

FIRST_POINTS = 100_000
# Fractions of the point count to seek to. LidarBC's LAZ chunks are 50,000 points, so each
# of these is one chunk read.
SPREAD_AT = (0.25, 0.5, 0.75)
SPREAD_POINTS = 50_000
# A file this small is read whole: the spread reads would overlap the first one.
READ_WHOLE_BELOW = FIRST_POINTS + len(SPREAD_AT) * SPREAD_POINTS
# Levels 0-1 of the octree: about 350,000 points spread over a 17M-point tile for 3.2 MB.
# Levels 0-2 cost 11 MB and 19 s on the same tile (measured 2026-10-09).
COPC_LEVELS = range(0, 2)

# ASPRS classes that say nothing grows or stands on the ground: ground, low and high noise,
# water. A sample holding no class outside these is ground-only. Class 1 (unclassified)
# counts against it, because vegetation and buildings left unclassified are still there.
GROUND_ONLY_CLASSES = frozenset({2, 7, 9, 18})


def classes_count(points) -> dict[int, int]:
    """Points per class, keys ascending."""
    c = collections.Counter(np.asarray(points.classification).tolist())
    return {int(k): int(c[k]) for k in sorted(c)}


def ground_only(counts: dict) -> bool | None:
    """Whether a sample holds no class outside GROUND_ONLY_CLASSES; None for an empty one,
    which says nothing either way."""
    present = {int(k) for k, n in counts.items() if n}
    if not present:
        return None
    return present <= GROUND_ONLY_CLASSES


def counts_merge(*samples: dict) -> dict[int, int]:
    out = collections.Counter()
    for s in samples:
        out.update({int(k): n for k, n in s.items()})
    return {k: out[k] for k in sorted(out)}


def laz_sample(url: str, session: requests.Session | None = None) -> dict:
    """Class counts of a LAZ's first points and of a chunk at each SPREAD_AT, with the bytes
    and seconds the reads cost."""
    f = HttpRangeFile(url, session=session)
    t0 = time.monotonic()
    with laspy.open(f) as r:
        n = r.header.point_count
        if n <= READ_WHOLE_BELOW:
            samples = {"all": classes_count(r.read_points(n))}
        else:
            samples = {"first": classes_count(r.read_points(FIRST_POINTS))}
            for at in SPREAD_AT:
                r.seek(int(n * at))
                samples[f"at_{at:g}"] = classes_count(r.read_points(SPREAD_POINTS))
    return {"point_count": n, "samples": samples, "bytes": f.bytes_fetched,
            "seconds": round(time.monotonic() - t0, 2)}


def copc_sample(url: str, session: requests.Session | None = None) -> dict:
    """Class counts of a COPC's coarse octree levels, which sample the whole tile."""
    f = HttpRangeFile(url, session=session)
    t0 = time.monotonic()
    with laspy.CopcReader(f) as r:
        pts = r.query(level=COPC_LEVELS)
        n = r.header.point_count
    return {"point_count": n, "levels": [COPC_LEVELS.start, COPC_LEVELS.stop - 1],
            "classes": classes_count(pts), "bytes": f.bytes_fetched,
            "seconds": round(time.monotonic() - t0, 2)}


def item_probe(item: dict, session: requests.Session | None = None) -> dict:
    """The record for one item: its laz sample and, if it has one, its copc sample."""
    laz = urllib.parse.unquote(item["assets"][ASSET_LAZ]["href"])
    rec = {"id": item["id"], "laz": laz, "laz_sample": laz_sample(laz, session)}
    if ASSET_COPC in item["assets"]:
        rec["copc"] = item["assets"][ASSET_COPC]["href"]
        rec["copc_sample"] = copc_sample(rec["copc"], session)
    return rec


def items_load(d: str) -> list[dict]:
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith(".json") and f != "collection.json":
            with open(os.path.join(d, f)) as fh:
                out.append(json.load(fh))
    return out


def records_load(path: str) -> dict[str, dict]:
    """id -> latest record. A malformed line raises: cache_tail_repair runs first."""
    recs = {}
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                r = json.loads(line)
                recs[r["id"]] = r
    return recs


def probe_all(items: list[dict], out_path: str, workers: int, probe=item_probe) -> dict:
    """Probe every item with no good record in `out_path`, appending each as it lands."""
    cache_tail_repair(out_path)
    done = {k for k, r in records_load(out_path).items() if "error" not in r}
    todo = [i for i in items if i["id"] not in done]
    logger.info("%d items recorded, %d to read", len(items) - len(todo), len(todo))
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=workers, pool_maxsize=workers)
    session.mount("https://", adapter)
    errors = {}
    with open(out_path, "a") as out, \
            concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(probe, i, session): i for i in todo}
        for fut in tqdm(concurrent.futures.as_completed(futures), total=len(futures),
                        desc="classes"):
            i = futures[fut]
            try:
                rec = fut.result()
            except Exception as e:  # a probe records every item, failures included
                rec = {"id": i["id"], "error": f"{type(e).__name__}: {e}"}
                errors[i["id"]] = rec["error"]
            out.write(json.dumps(rec) + "\n")
            out.flush()
    return errors


def verdicts(rec: dict) -> dict:
    """Per record: the ground-only verdict of the first points alone, of every laz sample
    together, and of the copc sample (None where there is none)."""
    s = rec["laz_sample"]["samples"]
    first = s.get("first", s.get("all"))
    return {"first": ground_only(first),
            "laz": ground_only(counts_merge(*s.values())),
            "copc": ground_only(rec["copc_sample"]["classes"]) if "copc_sample" in rec else None}


def summary(items: list[dict], recs: dict[str, dict]) -> None:
    ids = {i["id"] for i in items}
    good = {k: r for k, r in recs.items() if "error" not in r}
    print(f"items {len(ids)}; recorded {len(recs.keys() & ids)}; failed "
          f"{sorted(k for k in recs.keys() & ids if 'error' in recs[k])}; "
          f"unrecorded {len(ids - good.keys())}; recorded but not in build "
          f"{len(recs.keys() - ids)}")
    good = {k: r for k, r in good.items() if k in ids}

    v = {k: verdicts(r) for k, r in good.items()}
    by_group = collections.defaultdict(collections.Counter)
    for k, r in good.items():
        p = key_parse(r["laz"])
        g = f"{p['block']}/{p['sheet']}/{p['year']}"
        by_group[g]["items"] += 1
        by_group[g]["ground_only"] += bool(v[k]["laz"])
    print("\nground-only (all laz samples) per mapsheet-year:")
    for g in sorted(by_group):
        print(f"  {g}\t{by_group[g]['ground_only']} / {by_group[g]['items']}")
    total = sum(c["ground_only"] for c in by_group.values())
    print(f"  total\t{total} / {len(good)}")

    sets = collections.Counter(
        tuple(counts_merge(*r["laz_sample"]["samples"].values())) for r in good.values())
    print("\nclass sets seen (all laz samples), items:")
    for s, n in sets.most_common():
        print(f"  {n}\t{list(s)}")

    fl = collections.Counter((v[k]["first"], v[k]["laz"]) for k in v)
    print(f"\nfirst points vs all laz samples (first, all): {dict(fl)}")
    lc = collections.Counter((v[k]["laz"], v[k]["copc"]) for k in v if v[k]["copc"] is not None)
    print(f"all laz samples vs copc levels (laz, copc): {dict(lc)}")
    fc = collections.Counter((v[k]["first"], v[k]["copc"]) for k in v if v[k]["copc"] is not None)
    print(f"first points vs copc levels (first, copc): {dict(fc)}")
    disagree = sorted(k for k in v if v[k]["copc"] is not None and v[k]["laz"] != v[k]["copc"])
    print(f"laz/copc disagreements: {disagree[:20]}")

    lb = np.array([r["laz_sample"]["bytes"] for r in good.values()])
    ls = np.array([r["laz_sample"]["seconds"] for r in good.values()])
    print(f"\nlaz sample: bytes median {np.median(lb) / 1e6:.2f} MB, total {lb.sum() / 1e9:.1f} GB; "
          f"seconds median {np.median(ls):.2f}, p95 {np.percentile(ls, 95):.2f}")
    cb = [r["copc_sample"]["bytes"] for r in good.values() if "copc_sample" in r]
    if cb:
        print(f"copc sample: bytes median {np.median(cb) / 1e6:.2f} MB, total {sum(cb) / 1e9:.1f} GB")
    print("\nground-only items:")
    for k in sorted(k for k in v if v[k]["laz"]):
        print(f"  {k}\tcopc {v[k]['copc']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default=None, help="default <build>/classes.jsonl")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="file of item ids to probe, one per line")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = args.out or f"{args.build}/classes.jsonl"
    items = items_load(f"{args.build}/items")
    if args.ids:
        want = {x.strip() for x in open(args.ids) if x.strip()}
        items = [i for i in items if i["id"] in want]
        if len(items) != len(want):
            raise SystemExit(f"{len(want) - len(items)} ids not in the build")
    if args.limit:
        items = items[:args.limit]
    if args.summary:
        cache_tail_repair(out)
        summary(items, records_load(out))
        return 0
    errors = probe_all(items, out, args.workers)
    for k, e in sorted(errors.items()):
        logger.error("%s: %s", k, e)
    logger.info("done: %d items, %d failed", len(items), len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
