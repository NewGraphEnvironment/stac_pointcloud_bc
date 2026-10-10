#!/usr/bin/env python3
"""Sample the ASPRS classes in each built item's point cloud, to find the ground-only ones (#10).

The LAS header carries no class counts, so a file holding ground returns only reads like any
other to the build. This reads points: for each item in a build (`data/build/items`), the
`laz` file's first FIRST_POINTS points plus SPREAD_POINTS at each of SPREAD_AT through the
file (LAZ is chunked, so a seek fetches one chunk, not the file), and where the item has a
`copc` asset, that COPC's coarse octree levels (COPC_LEVELS), which cover the whole tile.
Each sample's class counts are kept separately, so how often the first points alone would
have misled is measured rather than assumed.

A sample can only miss a class, never add one, so a class seen is certain and only an absence
can be wrong: "ground-only" (no class but ground, noise and water) and "no ground" (no class
2). `--confirm` therefore downloads and fully decompresses every item a sample gives either
verdict, to `--full`, tallying every point's class and return pair; that makes both counts
exact rather than estimated.

One JSON line per item goes to `--out` as it lands; a re-run reads only the items missing
from it. A failed read is recorded with its error and read again next run. `--summary` prints
the tables research/laz_classes.md quotes and reads nothing remote.

Usage:
    uv run python scripts/laz_classes_probe.py [--build data/build] [--workers 16] [--limit N]
    uv run python scripts/laz_classes_probe.py --confirm [--workers 4]
    uv run python scripts/laz_classes_probe.py --summary
"""

import argparse
import collections
import concurrent.futures
import json
import logging
import os
import sys
import tempfile
import time
import urllib.parse

import laspy
import numpy as np
from laspy import DecompressionSelection, LazBackend
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
# water. A sample holding ground (2) and no class outside these is ground-only. Class 1
# (unclassified) counts against it, because vegetation and buildings left unclassified are
# still there; a sample of water or noise alone has no ground and is not ground-only.
GROUND = 2
GROUND_ONLY_CLASSES = frozenset({GROUND, 7, 9, 18})
# The parallel backend reads by chunk and seeks through the chunk table. The single-threaded
# one seeks inside a chunk by reading point by point, so a silent fall back to it would cost
# far more than the bytes recorded suggest (plan review, G2).
BACKEND = LazBackend.LazrsParallel


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
    return GROUND in present and present <= GROUND_ONLY_CLASSES


def no_ground(counts: dict) -> bool | None:
    """Whether a sample holds points but none of class 2, so a bare-earth surface built from it
    is empty; None for an empty sample."""
    present = {int(k) for k, n in counts.items() if n}
    if not present:
        return None
    return GROUND not in present


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
    with laspy.open(f, laz_backend=BACKEND) as r:
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


def laz_full(url: str, session: requests.Session | None = None) -> dict:
    """Every point's class and (return_number, number_of_returns), from the whole file.

    Downloaded to a temp file first: HttpRangeFile keeps every block it fetches in memory.
    The header's identity is kept too, so a ground-only file can be told apart from its
    neighbours by producer and date, not only by tile.
    """
    s = session or requests.Session()
    t0 = time.monotonic()
    with tempfile.NamedTemporaryFile(suffix=".laz") as tmp:
        with s.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            for b in r.iter_content(1 << 20):
                tmp.write(b)
        tmp.flush()
        size = tmp.tell()
        sel = DecompressionSelection.XY_RETURNS_CHANNEL | DecompressionSelection.CLASSIFICATION
        classes, returns = collections.Counter(), collections.Counter()
        with laspy.open(tmp.name, laz_backend=BACKEND, decompression_selection=sel) as rd:
            h = rd.header
            for pts in rd.chunk_iterator(1_000_000):
                classes.update(np.asarray(pts.classification).tolist())
                rn = np.asarray(pts.return_number).astype(np.int64)
                nr = np.asarray(pts.number_of_returns).astype(np.int64)
                u, c = np.unique(rn * 16 + nr, return_counts=True)
                returns.update({f"{k // 16}/{k % 16}": int(n) for k, n in zip(u, c)})
    if size != int(r.headers.get("Content-Length", size)):
        raise OSError(f"downloaded {size} bytes of {r.headers['Content-Length']}: {url}")
    return {"point_count": h.point_count, "points_read": sum(classes.values()),
            "classes": {int(k): int(classes[k]) for k in sorted(classes)},
            "returns": dict(sorted(returns.items())),
            "system_identifier": h.system_identifier, "generating_software": h.generating_software,
            "creation_date": str(h.creation_date), "las_version": str(h.version),
            "point_format": h.point_format.id, "bytes": size,
            "seconds": round(time.monotonic() - t0, 2)}


def full_probe(item: dict, session: requests.Session | None = None) -> dict:
    laz = urllib.parse.unquote(item["assets"][ASSET_LAZ]["href"])
    return {"id": item["id"], "laz": laz, "full": laz_full(laz, session)}


def ground_only_ids(recs: dict[str, dict]) -> set[str]:
    """The items any sample calls ground-only."""
    return {k for k, r in recs.items() if "error" not in r
            and any(v is True for v in verdicts(r).values())}


def no_ground_ids(recs: dict[str, dict]) -> set[str]:
    """The items whose samples together hold no ground: the laz samples merged, and the copc
    sample where there is one. One chunk without ground is ordinary; a tile without it is not."""
    out = set()
    for k, r in recs.items():
        if "error" in r:
            continue
        merged = counts_merge(*r["laz_sample"]["samples"].values())
        if no_ground(merged) or ("copc_sample" in r and no_ground(r["copc_sample"]["classes"])):
            out.add(k)
    return out


def confirm_ids(recs: dict[str, dict]) -> set[str]:
    """The items a sample calls ground-only or no-ground: the only verdicts it can get wrong."""
    return ground_only_ids(recs) | no_ground_ids(recs)


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


def density(header: dict) -> float:
    """Points per square metre of the header box."""
    area = (header["maxs"][0] - header["mins"][0]) * (header["maxs"][1] - header["mins"][1])
    return header["point_count"] / area if area > 0 else float("nan")


def summary(items: list[dict], recs: dict[str, dict], full: dict[str, dict] | None = None,
            headers: dict[str, dict] | None = None) -> None:
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
    def nonground(c):
        n = sum(c.values())
        return sum(x for k, x in c.items() if int(k) not in GROUND_ONLY_CLASSES) / n if n else 0
    near = sorted(k for k, r in good.items() if v[k]["laz"] is False
                  and nonground(counts_merge(*r["laz_sample"]["samples"].values())) < 0.01)
    print(f"\nmixed, but under 1% of sampled points outside {sorted(GROUND_ONLY_CLASSES)}: "
          f"{len(near)} {near[:10]}")

    # Density against the item's mapsheet-year: is ground-only a low-density outlier there?
    dens, pct = {}, {}
    if headers:
        for k, r in good.items():
            if r["laz"] in headers:
                dens[k] = density(headers[r["laz"]])
        grp = collections.defaultdict(list)
        for k, d in dens.items():
            p = key_parse(good[k]["laz"])
            grp[f"{p['block']}/{p['sheet']}/{p['year']}"].append(d)
        for k, d in dens.items():
            p = key_parse(good[k]["laz"])
            ds = np.array(grp[f"{p['block']}/{p['sheet']}/{p['year']}"])
            pct[k] = 100 * float(np.mean(ds < d))

    want = confirm_ids(good)
    full = {k: f for k, f in (full or {}).items() if k in want}
    print(f"\nto confirm by a full read: {len(want)}; read {len(full)}; "
          f"unread {sorted(want - full.keys())[:10]}")
    errs = sorted(k for k, f in full.items() if "error" in f)
    if errs:
        print(f"full-read failures: {errs}")
    for label, ids, test in (("ground-only", ground_only_ids(good), ground_only),
                             ("no ground", no_ground_ids(good), no_ground)):
        print(f"\nsampled {label}: {len(ids)}")
        print("id\tsampled(first,laz,copc ground-only)\tfull_classes\tpts/m2\t"
              "density_pct_in_group\tnonlast_share\tsingle_share\tcreation\tsoftware")
        for k in sorted(ids):
            f = full.get(k, {}).get("full")
            row = [k, ",".join(str(x)[0] if x is not None else "-" for x in v[k].values())]
            if f:
                n = sum(f["returns"].values()) or 1
                nonlast = sum(c for rn, c in f["returns"].items()
                              if int(rn.split("/")[0]) < int(rn.split("/")[1])) / n
                single = f["returns"].get("1/1", 0) / n
                row += [str(f["classes"]), f"{dens.get(k, float('nan')):.2f}",
                        f"{pct.get(k, float('nan')):.0f}", f"{nonlast:.3f}", f"{single:.3f}",
                        f["creation_date"], f["generating_software"].strip()]
            print("\t".join(row))
        confirmed = sorted(k for k in ids if "full" in full.get(k, {})
                           and test(full[k]["full"]["classes"]))
        print(f"{label}, confirmed by a full read: {len(confirmed)}")
        cg = collections.Counter()
        for k in confirmed:
            p = key_parse(good[k]["laz"])
            cg[f"{p['block']}/{p['sheet']}/{p['year']}"] += 1
        for g in sorted(cg):
            print(f"  {g}\t{cg[g]}")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default=None, help="default <build>/classes.jsonl")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", help="file of item ids to probe, one per line")
    ap.add_argument("--full", default=None, help="default <build>/classes_full.jsonl")
    ap.add_argument("--confirm", action="store_true",
                    help="fully read every item any sample calls ground-only")
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
    full = args.full or f"{args.build}/classes_full.jsonl"
    if args.summary:
        cache_tail_repair(out)
        cache_tail_repair(full)
        headers = {}
        if os.path.exists(f"{args.build}/headers.jsonl"):
            with open(f"{args.build}/headers.jsonl") as fh:
                headers = {r["url"]: r["header"] for r in map(json.loads, fh)}
        summary(items, records_load(out), records_load(full), headers)
        return 0
    if args.confirm:
        cache_tail_repair(out)
        want = confirm_ids(records_load(out))
        items = [i for i in items if i["id"] in want]
        errors = probe_all(items, full, args.workers, probe=full_probe)
    else:
        errors = probe_all(items, out, args.workers)
    for k, e in sorted(errors.items()):
        logger.error("%s: %s", k, e)
    logger.info("done: %d items, %d failed", len(items), len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
