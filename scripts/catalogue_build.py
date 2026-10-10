#!/usr/bin/env python3
"""Build the stac-pointcloud-bc catalogue for the first increment, locally.

Lists `pointcloud/*.laz` in the 11 mapsheet-years whose `dsm/` holds no raster (#1),
reads each file's LAS header over one range request, and writes item JSON and a
collection.json to `data/build/`. Where NRCan's CanElevation publishes a COPC under a
file's name (#6), its header is read too (cached in `copc_headers.jsonl`), and if it passes
laz_item.copc_asset_add's check the item carries it as a second asset. Publishing (s3) and registering (stacs) are separate
steps, so a build can be inspected before anything leaves this machine.

Headers are cached in `data/build/headers.jsonl`, so a re-run reads only what is missing.
Any file whose header cannot be read fails the build: a collection published without it
would read as complete.

Usage:
    uv run python scripts/catalogue_build.py [--workers 16] [--limit N]
"""

import argparse
import collections
import concurrent.futures
import json
import logging
import os
import re
import shutil
import sys
import urllib.parse
from datetime import datetime, timezone

import pystac
import requests
from tqdm import tqdm

from laz_item import (
    ASSET_LAZ,
    COLLECTION_ID,
    COPC_BOX_TOLERANCE_M,
    HEADER_VERSION,
    date_parse,
    key_parse,
    PATH_S3_STAC,
    canelevation_keys_list,
    classes_add,
    copc_asset_add,
    header_read,
    item_create,
    keys_list,
    url_scheme_check,
)

logger = logging.getLogger("catalogue_build")

OUT = "data/build"

# The 11 mapsheet-years whose dsm/ directory holds no raster (stac_dem_bc's
# no_raster_dsm groups), with the pointcloud/*.laz count measured on a full bucket walk
# 2026-10-06. A listing under 90% of its count is refused as truncated: the dataset has
# only ever grown.
INCREMENT = {
    "082/082e/2018": 1995, "082/082e/2019": 871, "082/082f/2018": 1061,
    "082/082g/2018": 215, "082/082j/2018": 207, "082/082k/2017": 267,
    "082/082l/2018": 774, "082/082l/2019": 1352, "092/092g/2016": 1706,
    "092/092h/2016": 1020, "092/092j/2016": 182,
}

# The CanElevation projects that publish COPC under LidarBC file names, with the .laz count
# measured 2026-10-09 (research/canelevation_overlap.md, #6). Its other BC projects share
# no file name with LidarBC (and no header, as far as the research could test), and are not
# listed. A listing under 90% of its count is refused, as for INCREMENT, though not because
# the bucket only grows: it has moved once already (FTP to S3). A smaller loss passes here
# and is caught by COPC_PAIRS, for the groups it records.
CANELEVATION_ROOT = "pointclouds_nuagespoints"
CANELEVATION_PROJECTS = {
    "BC/Vancouver_Island_Sunshine_Coast_2018": 7873,
    "BC/Riverine_Floodplain_UTM10_2019": 3866,
    "BC/Riverine_Floodplain_UTM11_2019": 682,
    "BC/Lower_Mainland_2016": 1714,
}

# Items with a CanElevation copy per INCREMENT group, measured 2026-10-09 (#6). The listing
# floors above cannot see a rename on either side, which pairs nothing while every count
# passes. Pairing is a deterministic join, so there is no slack either way: a group pairing
# other than this is refused (fewer would drop published `copc` assets without a word; more
# would publish assets a later shrink back to this count could drop unseen), and so is a
# group that pairs and is not named here. Record the new count when the change is real.
COPC_PAIRS = {"082/082e/2019": 332, "082/082l/2019": 57, "092/092g/2016": 1155,
              "092/092h/2016": 420}

# Whole-file class reads (#10), written by `laz_classes_probe.py --confirm` beside the build,
# for every item a point sample called ground-only or groundless; each such item lists its
# classes (classification:classes on the `laz` asset). CLASSES_READ is how many per group,
# measured 2026-10-10 (research/laz_classes.md). The cache is regenerable and gitignored, so
# a build that found it missing or short would drop the lists without a word: anything but
# these counts is refused, as for COPC_PAIRS. Record the new count when the change is real.
CLASSES_FULL = "classes_full.jsonl"
CLASSES_READ = {"082/082e/2018": 32, "082/082k/2017": 1, "082/082l/2018": 17,
                "082/082l/2019": 19, "092/092g/2016": 2, "092/092h/2016": 2}

# Files whose header is known to be faulty, excluded by name with the reason. Anything
# else item_create() refuses fails the build, so a new fault is seen rather than dropped.
# Each entry records the fault as observed; if the header no longer shows it (the file
# was re-delivered fixed), the build stops and asks for the entry to be removed rather
# than excluding a good file forever.
EXCLUDE = {
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092h/2016/pointcloud/"
    "bc_092h003_2_3_1_xyes_7_utm10_20160913.laz": {
        "reason": "header mins are [0, 0, 0] (maxs 611484.67, 5432744.76): the box runs "
                  "from the UTM origin, so the footprint would reach the equator. Found "
                  "2026-10-07 (#1).",
        "mins": [0.0, 0.0, 0.0],
    },
}

TITLE = "Point clouds from British Columbia - stac-pointcloud-bc"
DESCRIPTION = (
    "LidarBC point clouds (LAZ) from British Columbia, one item per file as published on "
    "the province's objectstore. Each item's footprint, point count and CRS come from the "
    "file's LAS header. The `laz` asset is the file itself; nothing is copied. The raster "
    "elevation products of the same deliveries are the stac-elevation-bc collection. "
    "Natural Resources Canada's CanElevation series publishes COPC under many LidarBC file "
    "names, in four of its projects (Vancouver_Island_Sunshine_Coast_2018, "
    "Riverine_Floodplain_UTM10_2019, Riverine_Floodplain_UTM11_2019, Lower_Mainland_2016). "
    "Where an item's file name is one of them, the item also carries that COPC as its `copc` "
    "asset, checked to have the same point count and horizontal CRS and a header box within "
    f"{COPC_BOX_TOLERANCE_M:g} m; the `laz` asset stays the source of record. "
    "A LAS header does not say which classes a file holds. Every file here was sampled "
    "(its first 100,000 points and a chunk at a quarter, half and three quarters through), "
    "and each one a sample found to hold only ground, noise and water, or no ground at all, "
    "was read whole: its `laz` asset lists every class present, with its point count, in "
    "`classification:classes`. An item without that list was not read whole. Most of the "
    "listed items hold no ground (class 2) at all, and so give no bare-earth surface; "
    "vegetation in this collection is mostly unclassified (class 1), not classes 3 to 5."
)
PROVIDERS = [
    {"name": "Province of British Columbia", "roles": ["producer", "licensor", "host"],
     "url": "https://lidar.gov.bc.ca/"},
    {"name": "Natural Resources Canada", "roles": ["host"],
     "url": "https://open.canada.ca/data/en/dataset/7069387e-9986-4297-9f55-0288e9676947"},
    {"name": "New Graph Environment", "roles": ["processor"],
     "url": "https://www.newgraphenvironment.com"},
]
KEYWORDS = ["lidar", "point cloud", "laz", "british columbia", "lidarbc"]


def listing() -> list[dict]:
    """Every pointcloud/*.laz object in the increment (`{"url", "etag", "size"}`),
    refusing a short group."""
    s = requests.Session()
    objs = []
    for group, expected in INCREMENT.items():
        found = [o for o in keys_list(f"{group}/pointcloud/", session=s)
                 if url_scheme_check(o["url"]).lower().endswith(".laz")]
        if len(found) < 0.9 * expected:
            raise RuntimeError(f"{group}: {len(found)} pointcloud .laz, under 90% of the "
                               f"{expected} measured 2026-10-06 - refusing a truncated listing")
        logger.info("%s: %d .laz (measured %d)", group, len(found), expected)
        objs.extend(found)
    return sorted(objs, key=lambda o: o["url"])


def copc_listing() -> list[dict]:
    """Every .laz in the CanElevation projects that republish LidarBC files
    (`{"url", "etag", "size"}`), refusing a short project."""
    s = requests.Session()
    objs = []
    for project, expected in CANELEVATION_PROJECTS.items():
        found = [o for o in canelevation_keys_list(f"{CANELEVATION_ROOT}/{project}/", session=s)
                 if o["url"].lower().endswith(".laz")]
        if len(found) < 0.9 * expected:
            raise RuntimeError(f"CanElevation {project}: {len(found)} .laz, under 90% of the "
                               f"{expected} measured 2026-10-09 - refusing a truncated listing")
        logger.info("CanElevation %s: %d .laz (measured %d)", project, len(found), expected)
        objs.extend(found)
    return objs


def file_stem(url: str) -> str:
    """A file's name with `.copc` and `.laz` stripped: what a LidarBC file and its
    CanElevation copy share."""
    return re.sub(r"(\.copc)?\.laz$", "", url.rsplit("/", 1)[-1].lower())


def copc_pairs(urls: list[str], copc_objs: list[dict]) -> dict[str, dict]:
    """LidarBC url -> the CanElevation object of the same name. A matched name held by two
    files on either side raises: which one is the copy would be a guess. Names nothing in
    `urls` matches are not this build's business."""
    by_stem = collections.defaultdict(list)
    for o in copc_objs:
        by_stem[file_stem(o["url"])].append(o)
    pairs, seen = {}, {}
    for u in urls:
        k = file_stem(u)
        if k not in by_stem:
            continue
        if len(by_stem[k]) > 1:
            raise RuntimeError(f"two CanElevation files named {k}: "
                               f"{', '.join(o['url'] for o in by_stem[k])}")
        if k in seen:
            raise RuntimeError(f"two LidarBC files named {k}: {seen[k]}, {u}")
        seen[k] = u
        pairs[u] = by_stem[k][0]
    return pairs


def copc_pairs_check(pairs: dict[str, dict]) -> None:
    """Refuse a group that paired other than COPC_PAIRS records, or paired at all without
    a recorded count."""
    n = collections.Counter("/".join(key_parse(u)["key"].split("/")[:3]) for u in pairs)
    for g, expected in COPC_PAIRS.items():
        if n[g] != expected:
            raise RuntimeError(f"{g}: {n[g]} items paired with a CanElevation COPC, not the "
                               f"{expected} recorded in COPC_PAIRS - a renamed, moved or new "
                               f"file on either side; record the count if the change is real")
    new = sorted(set(n) - set(COPC_PAIRS))
    if new:
        raise RuntimeError(f"groups pairing with CanElevation but not in COPC_PAIRS: "
                           f"{', '.join(f'{g} ({n[g]})' for g in new)} - record their counts")


def cache_tail_repair(path: str) -> None:
    """Cut an interrupted append off the cache.

    Every record is written as one line ending in a newline, so bytes after the last
    newline are a record a kill cut short. Removing them -- rather than skipping them on
    read -- matters: the next append would otherwise land after them and leave a
    malformed line mid-file, which headers_load refuses.
    """
    if not os.path.exists(path):
        return
    with open(path, "rb+") as fh:
        data = fh.read()
        if not data or data.endswith(b"\n"):
            return
        keep = data.rfind(b"\n") + 1
        logger.warning("dropping %d bytes of an interrupted record at the end of %s",
                       len(data) - keep, path)
        fh.truncate(keep)


def headers_load(path: str) -> dict[str, dict]:
    """The header cache: url -> {"etag", "header"}. Later lines win. Any line that does
    not parse raises: after cache_tail_repair, none should exist."""
    cache = {}
    if not os.path.exists(path):
        return cache
    with open(path) as fh:
        for line in fh:
            rec = json.loads(line)
            cache[rec["url"]] = {"etag": rec.get("etag"), "header": rec["header"]}
    return cache


def headers_fetch(objs: list[dict], cache_path: str, workers: int,
                  reader=header_read) -> tuple[dict, dict]:
    """Read every header not cached for the object's current ETag, appending each to the
    cache as it lands, so an interrupted run keeps what it had read. A file re-delivered
    under the same key has a new ETag, so its stale header is read again."""
    cache_tail_repair(cache_path)
    cache = headers_load(cache_path)
    headers = {o["url"]: cache[o["url"]]["header"] for o in objs
               if o["url"] in cache and cache[o["url"]]["etag"] == o["etag"]
               and cache[o["url"]]["header"].get("header_version") == HEADER_VERSION}
    todo = [o for o in objs if o["url"] not in headers]
    logger.info("%d headers cached, %d to read", len(objs) - len(todo), len(todo))
    errors = {}
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=workers, pool_maxsize=workers)
    session.mount("https://", adapter)
    with open(cache_path, "a") as out, \
            concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(reader, o["url"], session): o for o in todo}
        for fut in tqdm(concurrent.futures.as_completed(futures), total=len(futures),
                        desc="headers"):
            o = futures[fut]
            try:
                h = fut.result()
            except Exception as e:  # recorded per file; the build refuses below
                errors[o["url"]] = f"{type(e).__name__}: {e}"
                continue
            headers[o["url"]] = h
            out.write(json.dumps({"url": o["url"], "etag": o["etag"], "header": h}) + "\n")
            out.flush()
    return headers, errors


def exclusions_check(urls: list[str], headers: dict) -> list[str]:
    """The EXCLUDE entries that apply, each confirmed to still show its recorded fault."""
    out = []
    for u in urls:
        if u not in EXCLUDE:
            continue
        if headers[u]["mins"] != EXCLUDE[u]["mins"]:
            raise RuntimeError(f"EXCLUDE entry for {u} records mins {EXCLUDE[u]['mins']} but "
                               f"the header now reads {headers[u]['mins']} - the file may have "
                               f"been fixed; review the entry")
        logger.warning("excluded by EXCLUDE: %s: %s", u, EXCLUDE[u]["reason"])
        out.append(u)
    return out


def groups_with_untrusted_dates(urls: list[str]) -> set[str]:
    """Deliveries (mapsheet-years) in which any filename date's year disagrees with the
    directory. Their filename dates are not used for any file (laz_item.date_parse)."""
    bad = set()
    for u in urls:
        p = key_parse(u)
        when = date_parse(p["name"], p["year"])
        if when["filename_date"] and when["source"] == "path":
            bad.add(f"{p['block']}/{p['sheet']}/{p['year']}")
    return bad


def classes_records_load(path: str) -> dict[str, dict]:
    """The whole-file class reads: laz url -> the latest record. Later lines win."""
    out = {}
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                r = json.loads(line)
                out[r["laz"]] = r
    return out


def classes_attach(items: dict[str, pystac.Item], etags: dict[str, str],
                   records: dict[str, dict]) -> dict[str, str]:
    """Add each whole-file class read to its item (`items` and `etags` keyed by laz url).
    Returns the problems, keyed by url: a failed read, a read of a file not in the build, or
    of an older delivery of it (ETag changed), or a read classes_add refuses."""
    problems = {}
    for u, r in records.items():
        if "error" in r:
            problems[u] = f"the class read failed: {r['error']}"
        elif u not in items:
            problems[u] = "a class read of a file that is not in the build"
        elif r["full"]["etag"] != etags[u]:
            problems[u] = (f"read at ETag {r['full']['etag']}, listed at {etags[u]}: the file "
                           "was re-delivered; re-run laz_classes_probe.py --confirm")
        else:
            try:
                classes_add(items[u], r["full"])
            except ValueError as e:
                problems[u] = str(e)
    return problems


def item_link_href(item_id: str) -> str:
    """Where an item is published. Only the space is encoded: stacs reads an id back from
    this href by decoding %20, and nothing else (stacs catalogue._href_to_id)."""
    return f"{PATH_S3_STAC}/{item_id.replace(' ', '%20')}.json"


def collection_build(items: list[pystac.Item]) -> pystac.Collection:
    bboxes = [i.bbox for i in items]
    spatial = [[min(b[0] for b in bboxes), min(b[1] for b in bboxes),
                max(b[2] for b in bboxes), max(b[3] for b in bboxes)]]
    starts, ends = [], []
    for i in items:
        p = i.properties
        if i.datetime:
            starts.append(i.datetime)
            ends.append(i.datetime)
        else:
            starts.append(pystac.utils.str_to_datetime(p["start_datetime"]))
            ends.append(pystac.utils.str_to_datetime(p["end_datetime"]))
    c = pystac.Collection(
        id=COLLECTION_ID,
        title=TITLE,
        description=DESCRIPTION,
        license="CC-BY-4.0",
        providers=[pystac.Provider.from_dict(p) for p in PROVIDERS],
        keywords=KEYWORDS,
        extent=pystac.Extent(pystac.SpatialExtent(spatial),
                             pystac.TemporalExtent([[min(starts), max(ends)]])),
        summaries=pystac.Summaries({"nge:product": sorted({i.properties["nge:product"]
                                                             for i in items})}),
    )
    c.set_self_href(f"{PATH_S3_STAC}/collection.json")
    for i in items:
        c.add_link(pystac.Link(rel=pystac.RelType.ITEM, target=item_link_href(i.id),
                               media_type=pystac.MediaType.GEOJSON))
    return c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int,
                    help="first N files only (development); written to data/build-limit, "
                         "never data/build, so a partial build cannot be published")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # A local, not a reassigned module global: a second main() in one process (a test)
    # must not inherit the first one's --limit directory.
    out = "data/build-limit" if args.limit else OUT

    os.makedirs(out, exist_ok=True)
    objs = listing()
    # Listed before any header is read, so a short CanElevation listing fails fast.
    copc_objs = copc_listing()
    if args.limit:
        objs = objs[: args.limit]
    urls = [o["url"] for o in objs]
    logger.info("%d files in the increment", len(urls))

    headers, errors = headers_fetch(objs, f"{out}/headers.jsonl", args.workers)
    if errors:
        for u, e in sorted(errors.items()):
            logger.error("header read failed: %s: %s", u, e)
        logger.error("%d of %d headers failed - not building; re-run to retry them",
                     len(errors), len(urls))
        return 1

    collection_href = f"{PATH_S3_STAC}/collection.json"
    excluded = exclusions_check(urls, headers)
    untrusted = groups_with_untrusted_dates(urls)
    for g in sorted(untrusted):
        logger.info("filename dates not used in %s: some disagree with its year", g)

    def group(u):
        p = key_parse(u)
        return f"{p['block']}/{p['sheet']}/{p['year']}"
    kept = [u for u in urls if u not in excluded]
    items = [item_create(u, headers[u], collection_href,
                         trust_filename_date=group(u) not in untrusted)
             for u in kept]

    pairs = copc_pairs(kept, copc_objs)
    if not args.limit:  # a limited build is a slice, and is never published
        copc_pairs_check(pairs)
    copc_headers, errors = headers_fetch(list(pairs.values()), f"{out}/copc_headers.jsonl",
                                         args.workers)
    if errors:
        for u, e in sorted(errors.items()):
            logger.error("COPC header read failed: %s: %s", u, e)
        logger.error("%d of %d COPC headers failed - not building; re-run to retry them",
                     len(errors), len(pairs))
        return 1
    mismatched = {}
    for u, i in zip(kept, items):
        if u in pairs:
            try:
                copc_asset_add(i, pairs[u]["url"], copc_headers[pairs[u]["url"]], headers[u])
            except ValueError as e:  # all reported together, then the build refuses
                mismatched[u] = str(e)
    if mismatched:
        for u, e in sorted(mismatched.items()):
            logger.error("COPC is not a copy: %s", e)
        logger.error("%d of %d CanElevation name matches are not copies - not building",
                     len(mismatched), len(pairs))
        return 1
    for g, n in sorted(collections.Counter(group(u) for u in pairs).items()):
        logger.info("%s: %d items with a CanElevation COPC copy", g, n)

    records = classes_records_load(f"{out}/{CLASSES_FULL}")
    if args.limit:  # a slice: only the reads of files in it
        records = {u: r for u, r in records.items() if u in set(kept)}
    etags = {o["url"]: o["etag"] for o in objs}
    problems = classes_attach(dict(zip(kept, items)), etags, records)
    if problems:
        for u, e in sorted(problems.items()):
            logger.error("class read: %s: %s", u, e)
        logger.error("%d class reads cannot be applied - not building", len(problems))
        return 1
    read = collections.Counter(group(u) for u in records)
    if not args.limit and dict(read) != CLASSES_READ:
        logger.error("whole-file class reads per group %s, expected %s (CLASSES_READ) - "
                     "not building", dict(sorted(read.items())), CLASSES_READ)
        return 1
    for g, n in sorted(read.items()):
        logger.info("%s: %d items read whole for their classes", g, n)
    ids = [i.id for i in items]
    if len(set(ids)) != len(ids):
        raise RuntimeError("duplicate item ids in the increment")
    for i in items:
        if ASSET_LAZ not in i.assets:
            raise RuntimeError(f"{i.id} has no {ASSET_LAZ!r} asset")
        i.validate()

    c = collection_build(items)
    c.validate()

    # Everything is built and validated before anything on disk changes. The new set is
    # written beside the old and swapped in last, so a failure at any point leaves the
    # previous build whole: never new items beside an old collection.json.
    stage = f"{out}/items.new"
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    for i in items:
        with open(f"{stage}/{i.id}.json", "w") as fh:
            json.dump(i.to_dict(include_self_link=False), fh)
    with open(f"{out}/collection.json.new", "w") as fh:
        json.dump(c.to_dict(include_self_link=True), fh, indent=1)
    old = f"{out}/items.old"
    shutil.rmtree(old, ignore_errors=True)
    if os.path.exists(f"{out}/items"):
        os.replace(f"{out}/items", old)
    os.replace(stage, f"{out}/items")
    os.replace(f"{out}/collection.json.new", f"{out}/collection.json")
    shutil.rmtree(old, ignore_errors=True)

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    logger.info("built %d items (%d excluded, %d with a COPC copy) and collection.json in "
                "%s at %s", len(items), len(excluded), len(pairs), out, built_at)
    return 0


if __name__ == "__main__":
    sys.exit(main())
