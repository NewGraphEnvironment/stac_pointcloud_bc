#!/usr/bin/env python3
"""Build the stac-pointcloud-bc catalogue, locally.

Lists every `pointcloud/*.laz` on the province's objectstore (#2; the first increment, #1,
was 11 mapsheet-years), refusing a group listed short of its count in GROUPS, reads each
file's LAS header over one range request, and writes item JSON and a
collection.json to `data/build/`. Where NRCan's CanElevation publishes a COPC under a
file's name (#6), its header is read too (cached in `copc_headers.jsonl`), and if it passes
laz_item.copc_asset_add's check the item carries it as a second asset. Publishing (s3) and registering (stacs) are separate
steps, so a build can be inspected before anything leaves this machine.

Headers are cached in `data/build/headers.jsonl`, so a re-run reads only what is missing.
Any file whose header cannot be read fails the build: a collection published without it
would read as complete.

Usage:
    uv run python scripts/catalogue_build.py [--workers 16] [--limit N]
    uv run python scripts/catalogue_build.py --groups-record
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
import time
import urllib.parse
from datetime import datetime, timezone

import pystac
import pystac.validation
import requests
from tqdm import tqdm

from laz_classes_probe import (
    CLASS_TARGETS,
    CLASSES_FULL,
    CLASSES_SAMPLE,
    SCREEN_PERCENTILE,
    cache_tail_repair,
    confirm_ids,
    density_screen,
    full_probe,
    item_probe,
    probe_all,
    record_good,
    records_load,
    sample_good,
)
from laz_item import (
    ASSET_COPC,
    ASSET_LAZ,
    COLLECTION_ID,
    COPC_BOX_TOLERANCE_M,
    HEADER_VERSION,
    date_parse,
    key_parse,
    PATH_S3_STAC,
    NTS_BLOCKS,
    PATH_S3,
    nts_sheet_bounds,
    url_to_item_id,
    SCHEMA_LIDARBC,
    canelevation_keys_list,
    classes_add,
    copc_asset_add,
    header_read,
    item_create,
    fields_check,
    keys_list,
    schemas_check,
    schemas_preload,
    url_scheme_check,
)

logger = logging.getLogger("catalogue_build")

OUT = "data/build"

# The pointcloud/*.laz count per mapsheet-year (`<block>/<sheet>/<year>`), committed, written
# by `--groups-record` from a whole-bucket walk. A recorded group listed under 90% of its count
# is refused as truncated: the dataset has only ever grown, so a shrink that large is a listing
# that went wrong, not a delivery withdrawn. A group not recorded is logged and built, so new
# deliveries do not stop the monthly update (#4); record them with the next release.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUPS = os.path.join(ROOT, "data", "pointcloud_groups.json")
GROUP_FLOOR = 0.9
# A file name the build will publish: item_link_href encodes only the space (stacs decodes
# only %20), so anything else that needs encoding would break an item link at register time.
NAME_OK = re.compile(r"^[A-Za-z0-9_.() -]+$")

# The CanElevation projects that publish COPC under LidarBC file names, with the .laz count
# measured 2026-10-09 (research/canelevation_overlap.md, #6). Its other BC projects share
# no file name with LidarBC (and no header, as far as the research could test), and are not
# listed. A listing under 90% of its count is refused, as for GROUPS, though not because
# the bucket only grows: it has moved once already (FTP to S3). A smaller loss passes here
# and is caught by COPC_PAIRS, for the groups it records.
CANELEVATION_ROOT = "pointclouds_nuagespoints"
CANELEVATION_PROJECTS = {
    "BC/Vancouver_Island_Sunshine_Coast_2018": 7873,
    "BC/Riverine_Floodplain_UTM10_2019": 3866,
    "BC/Riverine_Floodplain_UTM11_2019": 682,
    "BC/Lower_Mainland_2016": 1714,
}

# Items with a CanElevation copy per group, committed beside GROUPS and written by the same
# `--groups-record` (first measured 2026-10-09, #6). The listing floors above cannot see a
# rename on either side, which pairs nothing while every count passes. Pairing is a
# deterministic join, so there is no slack either way: a group pairing other than this is
# refused (fewer would drop published `copc` assets without a word; more would publish assets
# a later shrink back to this count could drop unseen), and so is a group that pairs and is
# not recorded. Record the new counts when the change is real.
COPC_PAIRS_PATH = os.path.join(ROOT, "data", "copc_pairs.json")
with open(COPC_PAIRS_PATH) as _fh:
    COPC_PAIRS = json.load(_fh)
# CanElevation COPC that share a LidarBC file's name and fail copc_asset_add's header check,
# recorded with both point counts: those items carry no `copc` asset. 26, all in
# Vancouver_Island_Sunshine_Coast_2018, each with fewer points than the LidarBC file (found
# 2026-10-11, #2). A recorded count that no longer matches stops the build for review.
COPC_NOT_COPIES_PATH = os.path.join(ROOT, "data", "copc_not_copies.json")
with open(COPC_NOT_COPIES_PATH) as _fh:
    COPC_NOT_COPIES = json.load(_fh)
# Item ids read whole that the screen and a current sample do not derive: flags outside the
# screen (the 5% audit's), and whole reads made for another reason (the first increment's
# survey of every file, a research --confirm). The build publishes class lists for exactly
# these and the screened files a current sample flags (classes_published), and reads each
# whole, so no list depends on a local cache (data/build is not committed). A flag or a good
# whole read the list should hold and lacks stops the build. `--classes-record` adds them, and
# drops none unless given --force.
CLASSES_REQUIRED_PATH = os.path.join(ROOT, "data", "classes_required.json")
with open(CLASSES_REQUIRED_PATH) as _fh:
    CLASSES_REQUIRED = json.load(_fh)

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
    "https://nrs.objectstore.gov.bc.ca/gdwuts/082/082j/2022/pointcloud/"
    "bc_082j025_2_2_1_xyes_8_utm11_2022.laz": {
        "reason": "header box runs from easting 0 to northing 7,000,000 (640,950 x "
                  "1,437,312 m) for one tile: the box is not the data's. Found 2026-10-11"
                  " (#2).",
        "mins": [0.0, 5562687.78, 0.0],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/082/082m/2019/pointcloud/"
    "bc_082m081_3_3_3_xyes_16_utm11_2019.laz": {
        "reason": "a 6 x 130 m sliver of 24,510 points straddling 120 W, the sheet's west"
                  " edge; its centre is under a metre outside 082M. Found 2026-10-11 "
                  "(#2).",
        "mins": [293554.99, 5752780.3, 775.63],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092b/2023/pointcloud/"
    "bc_093c080_4_4_4_xyes_8_utm10_20230916_20230916.laz": {
        "reason": "a 093C tile filed under 092B (its name and its footprint, 124.01 W "
                  "52.79 N, are in 093C); the same file is also under 092N/2023. Found "
                  "2026-10-11 (#2).",
        "mins": [430875.64, 5849101.15, 1318.8],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092g/2021/pointcloud/"
    "bc_092g010_2_1_1_xyes_4_utm10_2021.laz": {
        "reason": "header has 0 points and an inverted box (mins easting 859,015, maxs "
                  "0). Found 2026-10-11 (#2).",
        "mins": [859015.36, 0.0, 0.0],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092g/2021/pointcloud/"
    "bc_092g020_4_4_4_xyes_4_utm10_2021.laz": {
        "reason": "header has 0 points and an inverted box (mins easting 859,015, maxs "
                  "0.3). Found 2026-10-11 (#2).",
        "mins": [859015.36, 0.0, 0.0],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092h/2021/pointcloud/"
    "bc_092h011_1_2_2_xyes_4_utm10_2021.laz": {
        "reason": "header maxs easting is 3,263,847, so the box is 2,685 km wide for one "
                  "tile. Found 2026-10-11 (#2).",
        "mins": [578450.42, 5439128.86, 15.14],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092k/2018/pointcloud/"
    "bc_092k005_3_4_3_xyes_8_utm10_2018.laz": {
        "reason": "header has 1 point, so the box is a point (0 x 0 m). Found 2026-10-11 (#2).",
        "mins": [346219.68, 5550929.38, 135.57],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092k/2020/pointcloud/"
    "bc_092k043_3_1_3_xyes_8_utm10_2020.laz": {
        "reason": "header has 0 points and the empty-box sentinels (mins 99999999.99, "
                  "maxs -99999999.99). Found 2026-10-11 (#2).",
        "mins": [99999999.99, 99999999.99, 99999999.99],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/092/092n/2023/pointcloud/"
    "bc_093c080_4_4_4_xyes_8_utm10_20230916_20230916.laz": {
        "reason": "a 093C tile filed under 092N (its name and its footprint, 124.01 W "
                  "52.79 N, are in 093C); the same file is also under 092B/2023. Found "
                  "2026-10-11 (#2).",
        "mins": [430875.64, 5849101.15, 1318.8],
    },
    "https://nrs.objectstore.gov.bc.ca/gdwuts/093/093n/2021/pointcloud/"
    "bc_093n052_1_2_3_xyes_8_utm10_2021.laz": {
        "reason": "header declares UTM 9N (EPSG:3156) but the name says utm10, and only "
                  "as UTM 10N does the box fall in 093N (125.74 W, not 131.74 W). Found "
                  "2026-10-11 (#2).",
        "mins": [326359.85114856396, 6155198.308212042, 1036.09],
    },
}

# Whole deliveries left out because no file in them states a CRS: no WKT and no GeoKeys,
# only the LASzip VLR (measured 2026-10-11, #2): 985 files, every file of each. One DEM tile
# of each delivery declares NAD83(CSRS) / UTM 8N or 9N (EPSG:3155, 3156), but an item's
# `proj:code` describes the file: indexing them from the DEM's CRS is #15. If any file in one
# gains a CRS, the build refuses: review it.
_NO_CRS = ("no file in the delivery states a CRS (no WKT, no GeoKeys); a DEM tile of the "
           "delivery declares NAD83(CSRS) / UTM 8N or 9N. Found 2026-10-11 (#2); #15.")
EXCLUDE_DELIVERIES = {
    "093/093e/2017": {"reason": _NO_CRS},
    "103/103b/2017": {"reason": _NO_CRS},
    "103/103c/2017": {"reason": _NO_CRS},
    "103/103f/2017": {"reason": _NO_CRS},
    "103/103g/2017": {"reason": _NO_CRS},
    "103/103h/2017": {"reason": _NO_CRS},
    "103/103j/2017": {"reason": _NO_CRS},
    "103/103k/2017": {"reason": _NO_CRS},
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
    "A LAS header does not say which classes a file holds. Files that a sample of their "
    "points found to hold only ground, noise and water, or no ground at all, were read "
    "whole: their `laz` asset lists every class present, with its point count, in "
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
# The raster products of the same deliveries. The same shape stac-elevation-bc carries back
# (stac_dem_bc#55): the published collection.json, matched on lidarbc:delivery (#5).
RELATED_ELEVATION = {
    "rel": "related",
    "href": "https://stac-dem-bc.s3.amazonaws.com/collection.json",
    "type": "application/json",
    "title": "DEM and DSM rasters from the same LidarBC deliveries (stac-elevation-bc); "
             "match items on lidarbc:delivery",
}


def blocks_list(session: requests.Session | None = None) -> list[str]:
    """The NTS block directories at the objectstore's root (`082`, `092`, ...). One that
    NTS_BLOCKS does not know raises: its keys would fail the sheet check one by one, hours
    into a build, and skipping it would drop a delivery without a word."""
    s = session or requests.Session()
    r = s.get(PATH_S3, params={"delimiter": "/"}, timeout=60)
    if r.status_code != 200:
        raise OSError(f"listing the root returned {r.status_code}")
    if re.search(rb"<IsTruncated>true</IsTruncated>", r.content):
        raise OSError("the root listing is truncated; page it before trusting it")
    prefixes = [p.decode() for p in re.findall(rb"<Prefix>([^<]+)</Prefix>", r.content)]
    blocks = sorted(p.rstrip("/") for p in prefixes if re.fullmatch(r"\d{3}/", p))
    unknown = [b for b in blocks if b not in NTS_BLOCKS]
    if unknown:
        raise RuntimeError(f"block directories with no NTS grid in laz_item.NTS_BLOCKS: "
                           f"{', '.join(unknown)} - add them before building")
    if not blocks:
        raise OSError("the root listing names no block directory")
    return blocks


def group_of(url: str) -> str:
    p = key_parse(url)
    return f"{p['block']}/{p['sheet']}/{p['year']}"


def pointcloud_select(objs: list[dict]) -> list[dict]:
    """The `pointcloud/*.laz` objects. Every `.laz` (any case) is parsed, whatever directory
    it is in, and each fault is collected, so one listing names them all: a key off the
    <block>/<sheet>/<year>/<product>/<file>.laz pattern, an unknown product directory, an
    NTS sheet letter the grid does not have, or a file name item links cannot carry."""
    out, faults, products = [], [], collections.Counter()
    for o in objs:
        u = url_scheme_check(o["url"])
        if not u.lower().endswith(".laz"):
            continue
        try:
            p = key_parse(u)
            nts_sheet_bounds(p["block"], p["sheet"])
            if not NAME_OK.match(p["name"]):
                raise ValueError(f"file name outside {NAME_OK.pattern}: {p['key']}")
        except ValueError as e:
            faults.append(str(e))
            continue
        products[p["product"]] += 1
        if p["product"] == "pointcloud":
            out.append(o)
    if faults:
        raise ValueError(f"{len(faults)} .laz keys cannot be placed:\n  " + "\n  ".join(faults))
    logger.info(".laz by product directory: %s", dict(sorted(products.items())))
    return out


def groups_load(path: str = GROUPS) -> dict[str, int]:
    with open(path) as fh:
        return json.load(fh)


def groups_count(objs: list[dict]) -> dict[str, int]:
    return dict(sorted(collections.Counter(group_of(o["url"]) for o in objs).items()))


def groups_check(found: dict[str, int], recorded: dict[str, int]) -> None:
    """Refuse a recorded group listed under GROUP_FLOOR of its count (or not at all); log a
    group not recorded."""
    short = {g: (found.get(g, 0), n) for g, n in recorded.items()
             if found.get(g, 0) < GROUP_FLOOR * n}
    if short:
        raise RuntimeError("groups listed under 90% of their recorded pointcloud .laz count - "
                           "refusing a truncated listing: " + ", ".join(
                               f"{g}: {f} of {n}" for g, (f, n) in sorted(short.items())))
    for g in sorted(set(found) - set(recorded)):
        logger.warning("%s: %d .laz, a group not in %s - built; record it with --groups-record",
                       g, found[g], GROUPS)


def records_write(found: dict[str, int], pairs: dict[str, int], force: bool) -> None:
    """Write GROUPS and COPC_PAIRS_PATH from this listing. A group whose count would drop below
    GROUP_FLOOR of its record, or vanish, is refused without `force`: re-recording after a
    truncated listing would otherwise lower the floor that exists to catch one."""
    recorded = groups_load() if os.path.exists(GROUPS) else {}
    for path, new, old in ((GROUPS, found, recorded), (COPC_PAIRS_PATH, pairs, COPC_PAIRS)):
        lowered = {g: (new.get(g, 0), n) for g, n in old.items() if new.get(g, 0) < n}
        for g, (f, n) in sorted(lowered.items()):
            logger.warning("%s: %s from %d to %d", os.path.basename(path), g, n, f)
        for g in sorted(set(new) - set(old)):
            logger.info("%s: %s new, %d", os.path.basename(path), g, new[g])
        steep = {g: v for g, v in lowered.items()
                 if path == COPC_PAIRS_PATH or v[0] < GROUP_FLOOR * v[1]}
        if steep and not force:
            raise RuntimeError(f"recording would lower {len(steep)} counts in {path} "
                               f"({', '.join(sorted(steep)[:5])}); pass --force if that is real")
    for path, new in ((GROUPS, found), (COPC_PAIRS_PATH, pairs)):
        with open(f"{path}.new", "w") as fh:
            json.dump(dict(sorted(new.items())), fh, indent=1)
            fh.write("\n")
        os.replace(f"{path}.new", path)
        logger.info("recorded %d groups, %d in all, in %s", len(new), sum(new.values()), path)


def listing() -> list[dict]:
    """Every pointcloud/*.laz object on the objectstore (`{"url", "etag", "size"}`), walked
    one block at a time, sorted by url."""
    s = requests.Session()
    objs = []
    for b in blocks_list(s):
        found = pointcloud_select(keys_list(f"{b}/", session=s))
        logger.info("block %s: %d pointcloud .laz", b, len(found))
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
    n = collections.Counter(group_of(u) for u in pairs)
    for g, expected in COPC_PAIRS.items():
        if n[g] != expected:
            raise RuntimeError(f"{g}: {n[g]} items paired with a CanElevation COPC, not the "
                               f"{expected} recorded in copc_pairs.json - a renamed, moved or new "
                               f"file on either side; record the count if the change is real")
    new = sorted(set(n) - set(COPC_PAIRS))
    if new:
        raise RuntimeError(f"groups pairing with CanElevation but not in copc_pairs.json: "
                           f"{', '.join(f'{g} ({n[g]})' for g in new)} - record their counts")


def copc_not_copy_check(u: str, copc_url: str, copc_headers: dict, headers: dict) -> None:
    """A recorded non-copy is left unlinked, provided both files still have the point counts
    recorded for it; otherwise either side changed and the entry is reviewed, not trusted."""
    rec = COPC_NOT_COPIES[copc_url]
    now = (copc_headers[copc_url]["point_count"], headers[u]["point_count"])
    if now != (rec["copc_points"], rec["laz_points"]):
        raise RuntimeError(f"copc_not_copies.json records {copc_url} with "
                           f"{rec['copc_points']} points against the LAZ's {rec['laz_points']}, "
                           f"but they now read {now[0]} and {now[1]} - review the entry")
    logger.warning("not linked, recorded in copc_not_copies.json: %s (COPC %d points, LAZ %d)",
                   copc_url, *now)


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
        try:  # the mins can survive a fix of another field (a box's maxs, a CRS)
            item_create(u, headers[u], f"{PATH_S3_STAC}/collection.json")
        except ValueError:
            pass
        else:
            raise RuntimeError(f"EXCLUDE entry for {u}: the file now makes an item - it may "
                               f"have been fixed; review the entry")
        logger.warning("excluded by EXCLUDE: %s: %s", u, EXCLUDE[u]["reason"])
        out.append(u)
    by_delivery = collections.defaultdict(list)
    for u in urls:
        if group_of(u) in EXCLUDE_DELIVERIES:
            by_delivery[group_of(u)].append(u)
    for g, us in sorted(by_delivery.items()):
        stated = [u for u in us if headers[u].get("crs_wkt")]
        if stated:
            raise RuntimeError(f"EXCLUDE_DELIVERIES entry for {g} records no CRS, but "
                               f"{len(stated)} of its files now state one (e.g. {stated[0]}) - "
                               f"review the entry")
        logger.warning("excluded by EXCLUDE_DELIVERIES: %s (%d files): %s", g, len(us),
                       EXCLUDE_DELIVERIES[g]["reason"])
        out += us
    return out


def groups_with_untrusted_dates(urls: list[str]) -> set[str]:
    """Deliveries (mapsheet-years) in which any filename date's year disagrees with the
    directory. Their filename dates are not used for any file (laz_item.date_parse). A token
    that is no date at all raises, naming every such file."""
    bad, faults = set(), []
    for u in urls:
        p = key_parse(u)
        try:
            when = date_parse(p["name"], p["year"])
        except ValueError as e:
            faults.append(f"{p['key']}: {e}")
            continue
        if when["filename_date"] and when["source"] == "path":
            bad.add(group_of(u))
    if faults:
        raise ValueError(f"{len(faults)} file names carry a date token that is no date:\n  "
                         + "\n  ".join(faults))
    return bad


def items_create(kept: list[str], headers: dict, collection_href: str,
                 untrusted: set[str]) -> tuple[list[pystac.Item], dict[str, str]]:
    """item_create for every file, collecting refusals rather than stopping at the first, so
    one run names every header fault (each is triaged into EXCLUDE or a fix)."""
    items, faults = [], {}
    for u in kept:
        try:
            items.append(item_create(u, headers[u], collection_href,
                                     trust_filename_date=group_of(u) not in untrusted))
        except ValueError as e:
            faults[u] = str(e)
    return items, faults


def fault_class(message: str) -> str:
    """A refusal message with its numbers and url removed: what to count faults by."""
    return re.sub(r"-?\d+(\.\d+)?(e[-+]?\d+)?", "#", message.split(": https://")[0])


def class_targets_write(path: str, kept: list[str], items: list[pystac.Item],
                        etags: dict[str, str], pairs: dict[str, dict]) -> None:
    """One line per file this build keeps: its item id, laz url, listing ETag and paired
    COPC url (or null). Replaced whole, so a reader never sees a half-written list."""
    with open(f"{path}.new", "w") as fh:
        for u, i in zip(kept, items):
            fh.write(json.dumps({"id": i.id, "laz": u, "etag": etags[u],
                                 "copc": pairs[u]["url"] if u in pairs else None}) + "\n")
    os.replace(f"{path}.new", path)


def classes_records_load(path: str) -> dict[str, dict]:
    """The whole-file class reads: laz url -> the latest record. Later lines win."""
    out = {}
    if os.path.exists(path):
        with open(path) as fh:
            for n, line in enumerate(fh, 1):
                r = json.loads(line)
                if "laz" not in r:
                    raise ValueError(f"{path} line {n} names no laz file ({r.get('id')}): "
                                     "written before failed reads carried one; remove it "
                                     "and re-run the build")
                out[r["laz"]] = r
    return out


def classes_attach(items: dict[str, pystac.Item], etags: dict[str, str],
                   records: dict[str, dict]) -> dict[str, str]:
    """Add each whole-file class read of a file in the build to its item (`items` and `etags`
    keyed by laz url). Returns the problems, keyed by url: a failed read, a read of an older
    delivery (ETag changed), or a read classes_add refuses. A read of a file not in the build
    is not applied and not a problem here: classes_check decides what must have been read.
    """
    problems = {}
    for u, r in records.items():
        if u not in items:
            continue
        if "error" in r:
            problems[u] = f"the class read failed: {r['error']}; re-run the build"
        elif not etags[u]:
            problems[u] = ("the listing gives this file no ETag, so no class read can be "
                           "matched to it; look at the listing before building")
        elif r["full"]["etag"] != etags[u]:
            problems[u] = (f"read at ETag {r['full']['etag']}, listed at {etags[u]}: the file "
                           "was re-delivered; re-run the build, which reads it again")
        else:
            try:
                classes_add(items[u], r["full"])
            except ValueError as e:
                problems[u] = f"{e}; remove its line from {CLASSES_FULL} and re-run the build"
    return problems


def class_target(item: pystac.Item) -> dict:
    """An item in the shape the class probe reads: its id and asset hrefs."""
    return {"id": item.id, "assets": {k: {"href": a.href} for k, a in item.assets.items()}}


def classes_check(screened: set[str], ids: dict[str, str], current: dict[str, str],
                  samples: dict[str, dict], full: dict[str, dict],
                  required: list[str], unrecorded: bool = True,
                  copc: dict[str, str | None] | None = None) -> dict[str, str]:
    """What stops a build publishing class lists it cannot stand behind, by laz url:
    - a screened file with no good point sample (current ETag, current COPC: sample_good);
    - a file any good sample flags (screened or not: audit samples count too), or one in
      `required` (CLASSES_REQUIRED), with no good whole-file read at its current ETag;
    - with `unrecorded`, a file a good sample flags outside the screen, or a good whole read
      outside classes_published(), that `required` lacks: an empty data/build would not
      reproduce its class list. Off under --limit, whose screen is that of partial groups.
    Derived from the screen and the samples, so a cache that is missing, short or stale is
    refused without a count to keep (#2). `samples` and `full` are keyed by item id."""
    problems = {}
    for u in sorted(screened):
        r = samples.get(ids[u])
        if r is None or not sample_good(r, current, copc):
            problems[u] = ("no point sample at the current ETag and COPC"
                           + (f" ({r['error']})" if r and "error" in r else ""))
    by_id = {i: u for u, i in ids.items()}
    inside = {ids[u] for u in screened}
    good = {k: r for k, r in samples.items() if k in by_id and sample_good(r, current, copc)}
    flagged = confirm_ids(good)
    for k in sorted(flagged | {k for k in required if k in by_id}):
        r = full.get(k)
        if r is None or not record_good(r, current):
            why = "flagged by its sample" if k in flagged else f"in {CLASSES_REQUIRED_PATH}"
            problems[by_id[k]] = (f"{why}, with no whole-file read at the current ETag"
                                  + (f" ({r['error']})" if r and "error" in r else ""))
    published = classes_published(inside, flagged, required, by_id)
    read = {k for k, r in full.items() if k in by_id and record_good(r, current)}
    for k in sorted(((flagged - inside) | read) - published) if unrecorded else ():
        how = ("flagged by a sample outside the screen" if k in flagged and k not in inside
               else "read whole, but neither screened and flagged nor recorded")
        problems[by_id[k]] = "; ".join(filter(None, [
            problems.get(by_id[k]), f"{how}, and not in {CLASSES_REQUIRED_PATH}; record it "
            f"with --classes-record"]))
    return problems


def classes_published(inside: set[str], flagged: set[str], required: list[str],
                      listed) -> set[str]:
    """The item ids whose class lists a build publishes: the screened files a current sample
    flags, and the recorded ones still listed. What an empty data/build would publish, so the
    whole-read step, classes_check and classes_attach all take it from here and a local cache
    can speed a build up but never add a list (#2)."""
    return (inside & flagged) | {k for k in required if k in listed}


def validate_one(body: dict) -> str | None:
    """None if `body` validates (core and every schema in stac_extensions), else the error."""
    schemas_preload()  # in each pool worker too
    try:
        pystac.validation.validate_dict(body)
    except pystac.errors.STACValidationError as e:
        return f"{body.get('id')}: {str(e)[:1000]}"
    return None


def validate_all(bodies: list[dict], workers: int) -> list[str]:
    """Validate every body, in a process pool when there are many: at about 40 ms each, 175k
    items are two hours in one process. Each worker caches the schemas it fetches."""
    if len(bodies) < 500 or workers < 2:
        return [e for e in map(validate_one, bodies) if e]
    t0 = time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers, os.cpu_count() or 1)) as ex:
        errs = [e for e in ex.map(validate_one, bodies, chunksize=250) if e]
    logger.info("validated %d items in %.0f s", len(bodies), time.monotonic() - t0)
    return errs


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
        summaries=pystac.Summaries({"lidarbc:product": sorted(
            {i.properties["lidarbc:product"] for i in items})}),
        stac_extensions=[SCHEMA_LIDARBC],
    )
    c.set_self_href(f"{PATH_S3_STAC}/collection.json")
    c.add_link(pystac.Link.from_dict(RELATED_ELEVATION))
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
    ap.add_argument("--groups-record", action="store_true",
                    help="write the listing's per-group .laz and COPC pair counts to "
                         "data/pointcloud_groups.json and data/copc_pairs.json, and stop")
    ap.add_argument("--classes-record", action="store_true",
                    help="add to data/classes_required.json every file outside the density "
                         "screen that a cached sample flags or that has a cached whole read")
    ap.add_argument("--force", action="store_true",
                    help="with --groups-record, allow a recorded count to fall; with "
                         "--classes-record, drop recorded ids no longer listed or now screened and "
                         "flagged")
    args = ap.parse_args()
    if args.classes_record and args.limit:  # a slice's screen is that of partial groups
        ap.error("--classes-record records the committed list, so it cannot run with --limit")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # A local, not a reassigned module global: a second main() in one process (a test)
    # must not inherit the first one's --limit directory.
    out = "data/build-limit" if args.limit else OUT

    os.makedirs(out, exist_ok=True)
    objs = listing()
    found = groups_count(objs)
    if not args.groups_record:
        groups_check(found, groups_load())
    # Listed before any header is read, so a short CanElevation listing fails fast.
    copc_objs = copc_listing()
    # Everything that needs only the listing is checked here, before hours of header reads:
    # group floors, COPC pairs, date tokens and item ids.
    named = [o["url"] for o in objs if o["url"] not in EXCLUDE]
    pairs = copc_pairs(named, copc_objs)
    if args.groups_record:
        records_write(found, dict(collections.Counter(group_of(u) for u in pairs)), args.force)
        return 0
    copc_pairs_check(pairs)
    untrusted = groups_with_untrusted_dates(named)
    ids = collections.Counter(url_to_item_id(u) for u in named)
    if any(n > 1 for n in ids.values()):
        raise RuntimeError(f"duplicate item ids: {sorted(k for k, n in ids.items() if n > 1)[:5]}")
    for g in sorted(untrusted):
        logger.info("filename dates not used in %s: some disagree with its year", g)
    if args.limit:
        objs = objs[: args.limit]
    urls = [o["url"] for o in objs]
    logger.info("%d pointcloud .laz in %d groups", len(urls), len(found))

    headers, errors = headers_fetch(objs, f"{out}/headers.jsonl", args.workers)
    if errors:
        for u, e in sorted(errors.items()):
            logger.error("header read failed: %s: %s", u, e)
        logger.error("%d of %d headers failed - not building; re-run to retry them",
                     len(errors), len(urls))
        return 1

    collection_href = f"{PATH_S3_STAC}/collection.json"
    excluded = exclusions_check(urls, headers)
    kept = [u for u in urls if u not in excluded]
    items, faults = items_create(kept, headers, collection_href, untrusted)
    if faults:
        by_class = collections.defaultdict(list)
        for u, e in sorted(faults.items()):
            by_class[fault_class(e)].append(e)
        for cls, es in sorted(by_class.items(), key=lambda x: -len(x[1])):
            logger.error("%d files: %s; e.g. %s", len(es), cls, " | ".join(es[:3]))
        for u, e in sorted(faults.items()):
            logger.error("refused: %s", e)
        logger.error("%d of %d files refused by item_create - not building; triage each into "
                     "EXCLUDE or a fix", len(faults), len(kept))
        return 1
    pairs = {u: o for u, o in pairs.items() if u in set(kept)}
    # One item per group through the full validator now, an hour before the class step ends:
    # the first meeting of real items with the crate schemas should not be the last step.
    first = {}
    for u, i in zip(kept, items):
        first.setdefault(group_of(u), i)
    invalid = validate_all([i.to_dict(include_self_link=False) for i in first.values()],
                           args.workers)
    if invalid:
        for e in invalid[:20]:
            logger.error("invalid: %s", e)
        logger.error("%d of %d sample items fail STAC validation - not building", len(invalid),
                     len(first))
        return 1
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
        if u in pairs and pairs[u]["url"] in COPC_NOT_COPIES:
            copc_not_copy_check(u, pairs.pop(u)["url"], copc_headers, headers)
        elif u in pairs:
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
    for g, n in sorted(collections.Counter(group_of(u) for u in pairs).items()):
        logger.info("%s: %d items with a CanElevation COPC copy", g, n)

    etags = {o["url"]: o["etag"] for o in objs}
    class_targets_write(f"{out}/{CLASS_TARGETS}", kept, items, etags, pairs)
    # Point classes (#10): sample the low-density tail, read whole what a sample flags, and list
    # the classes of every file read whole. Each step reads only what its cache lacks at the
    # file's current ETag, so a re-run retries failures and nothing else.
    ids = {u: i.id for u, i in zip(kept, items)}
    current = {i.id: etags[u] for u, i in zip(kept, items)}
    screened = density_screen(kept, headers)
    logger.info("%d of %d files screened (density at or below the %g percentile of their "
                "mapsheet-year)", len(screened), len(kept), SCREEN_PERCENTILE)
    targets = {i.id: class_target(i) for i in items}
    sample_path, full_path = f"{out}/{CLASSES_SAMPLE}", f"{out}/{CLASSES_FULL}"
    probe_all([targets[ids[u]] for u in sorted(screened)], sample_path, args.workers,
              probe=item_probe, current=current, match_copc=True)
    samples = {k: r for k, r in records_load(sample_path).items() if k in current}
    cache_tail_repair(full_path)
    copcs = {i.id: (i.assets[ASSET_COPC].href if ASSET_COPC in i.assets else None)
             for i in items}
    inside = {ids[u] for u in screened}
    flagged = confirm_ids({k: r for k, r in samples.items() if sample_good(r, current, copcs)})
    prior = {k: r for k, r in records_load(full_path).items() if k in current}
    required = CLASSES_REQUIRED
    # Read whole what the build publishes, and every flag outside the screen (refused below
    # until recorded). A stale read of anything else is left stale and is not applied.
    want = {k for k in classes_published(inside, flagged, required, current) | flagged
            if not (k in prior and record_good(prior[k], current))}
    probe_all([targets[k] for k in sorted(want)], full_path, args.workers, probe=full_probe,
              current=current)
    full = {k: r for k, r in records_load(full_path).items() if k in current}
    if args.classes_record:  # after the reads, so a read made good in this run is recorded
        found = ((flagged - inside)
                 | {k for k, r in full.items() if record_good(r, current)} - (inside & flagged))
        # --force drops only an id no longer listed or now derived (screened and flagged): a
        # listed one whose read failed in this run stays required, and is refused below.
        keep = {k for k in CLASSES_REQUIRED if k in current and k not in inside & flagged}
        required = sorted(found | (keep if args.force else set(CLASSES_REQUIRED)))
        dropped = set(CLASSES_REQUIRED) - set(required)
        with open(f"{CLASSES_REQUIRED_PATH}.new", "w") as fh:
            json.dump(required, fh, indent=1)
            fh.write("\n")
        os.replace(f"{CLASSES_REQUIRED_PATH}.new", CLASSES_REQUIRED_PATH)
        logger.info("recorded %d ids in %s (%d no longer needed, %s)", len(required),
                    CLASSES_REQUIRED_PATH, len(dropped), "dropped" if args.force else "kept")
    problems = classes_check(screened, ids, current, samples, full, required,
                             unrecorded=not args.limit, copc=copcs)
    if problems:
        for u, e in sorted(problems.items()):
            logger.error("class read: %s: %s", u, e)
        logger.error("%d files lack the class reads the screen requires - not building; "
                     "re-run to retry them", len(problems))
        return 1
    records = classes_records_load(full_path)
    gone = sorted(set(records) - set(kept))
    if gone and not args.limit:  # a slice leaves most files out; that is not news
        logger.warning("%d class reads are of files not in this build, not applied: %s",
                       len(gone), gone[:5])
    published = classes_published(inside, flagged, required, current)
    records = {u: r for u, r in records.items() if u in ids and ids[u] in published}
    problems = classes_attach(dict(zip(kept, items)), etags, records)
    if problems:
        for u, e in sorted(problems.items()):
            logger.error("class read: %s: %s", u, e)
        logger.error("%d class reads cannot be applied - not building", len(problems))
        return 1
    read = collections.Counter(group_of(u) for u in records)
    for g, n in sorted(read.items()):
        logger.info("%s: %d items read whole for their classes", g, n)
    logger.info("classes: %d screened, %d sampled, %d flagged by a sample, %d read whole",
                len(screened), len(samples), len(flagged), len(records))
    bodies = []
    for i in items:
        if ASSET_LAZ not in i.assets:
            raise RuntimeError(f"{i.id} has no {ASSET_LAZ!r} asset")
        d = i.to_dict(include_self_link=False)
        schemas_check(d)
        fields_check(d)
        bodies.append(d)
    invalid = validate_all(bodies, args.workers)
    if invalid:
        for e in invalid[:20]:
            logger.error("invalid: %s", e)
        logger.error("%d of %d items fail STAC validation - not building", len(invalid), len(bodies))
        return 1

    c = collection_build(items)
    schemas_check(c.to_dict())
    schemas_preload()
    c.validate()

    # Everything is built and validated before anything on disk changes. The new set is
    # written beside the old and swapped in last, so a failure at any point leaves the
    # previous build whole: never new items beside an old collection.json.
    stage = f"{out}/items.new"
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    for d in bodies:
        with open(f"{stage}/{d['id']}.json", "w") as fh:
            json.dump(d, fh)
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
