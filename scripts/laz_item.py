"""STAC items for LidarBC `.laz` files.

`item_create()` is pure: an href and a header record in, a `pystac.Item` out, with
nothing about the bucket, the STAC host or CI in it (stactools-shaped, #1). Everything
that touches the network is in `header_read()`, `keys_list()` and
`canelevation_keys_list()`.

The module constants are also declared in stacs.toml; tests/test_stacs_config.py fails
if the two disagree.
"""

import functools
import json
import logging
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import laspy
import pystac
import requests
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError
from pystac.extensions.classification import Classification, ClassificationExtension
from pystac.extensions.file import FileExtension
from pystac.extensions.pointcloud import PointcloudExtension, Schema, SchemaType
from pystac.extensions.projection import ProjectionExtension

from laz_remote import HttpRangeFile

COLLECTION_ID = "stac-pointcloud-bc"
PATH_S3 = "https://nrs.objectstore.gov.bc.ca/gdwuts"
PATH_S3_STAC = "https://stac-pointcloud-bc.s3.us-west-2.amazonaws.com"
ASSET_LAZ = "laz"
MEDIA_TYPE_LAZ = "application/vnd.laszip"
PRODUCTS = ("pointcloud", "dsm")

# The JSON Schemas of the two custom prefixes (crate#23, decided in #12). pystac fetches
# each when it validates, so validation checks every `lidarbc:` and `las:` value, and a build
# depends on these URLs answering. A released version is never edited; a new field is a new
# version, and v1.0.0 refuses a `lidarbc:` or `las:` key it does not declare.
SCHEMA_LIDARBC = "https://newgraphenvironment.github.io/crate/stac/lidarbc/v1.0.0/schema.json"
SCHEMA_LAS = "https://newgraphenvironment.github.io/crate/stac/las/v1.0.0/schema.json"
SCHEMAS_CUSTOM = {"lidarbc": SCHEMA_LIDARBC, "las": SCHEMA_LAS}
# Copies of both, checked in byte for byte (tests/test_schemas.py compares them with the published
# files when online). Validation reads these, never the URLs, so a Pages or DNS hiccup cannot fail
# a build; a published version never changes, so a copy can only drift by a hand edit.
SCHEMA_FILES = {u: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "schemas", p, "v1.0.0", "schema.json")
                for p, u in SCHEMAS_CUSTOM.items()}
# What the build always writes (crate's schemas require nothing, because stac-elevation-bc
# carries only lidarbc:delivery; they type what is present, and presence is the build's job).
FIELDS_ITEM = ("lidarbc:product", "lidarbc:delivery", "lidarbc:datetime_source", "las:version",
               "las:point_format")
FIELDS_COPC = ("las:version", "las:point_format")
# `lidarbc:delivery`, shared with stac-elevation-bc so the two match on one filter (#5,
# stac_dem_bc#55): the three path segments after `gdwuts/`.
DELIVERY = re.compile(r"^[0-9]{3}/[0-9]{3}[a-p]/[0-9]{4}$")

# NRCan's CanElevation series publishes COPC under many LidarBC file names
# (research/canelevation_overlap.md, #6). Where it does and copc_asset_add's header check
# passes, the item carries that file as a second asset; the `laz` stays the source of record.
CANELEVATION = "https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com"
ASSET_COPC = "copc"
MEDIA_TYPE_COPC = "application/vnd.laszip+copc"
# A copy has the same point count, horizontal CRS, and header box (x, y and z) within this
# of the LidarBC file's. Over all 13,970 linked pairs the largest offset was 0.01 m, the
# LidarBC scale rounded into COPC's (2026-10-11, #2); a datum re-realisation or a
# reprojection moves a box far more. COPC conversion rewrites LAS 1.2 as 1.4, so the header
# is compared on what conversion keeps, not as a whole.
COPC_BOX_TOLERANCE_M = 0.05

# The shape of the record header_read() returns. Bumped whenever that shape changes, so
# a cached record of an older shape is read again rather than built from.
HEADER_VERSION = 2

# NTS 1:250k grid for BC's blocks: (south latitude, east longitude). Each block is
# 4 x 4 sheets of 1 deg latitude x 2 deg longitude, lettered from the southeast in a
# snake: A-D westward along the south row, E-H eastward, I-L westward, M-P eastward.
NTS_BLOCKS = {"082": (48, -112), "083": (52, -112), "092": (48, -120), "093": (52, -120),
              "094": (56, -120), "102": (48, -128), "103": (52, -128), "104": (56, -128)}
_NTS_ROWS = ("ABCD", "HGFE", "IJKL", "PONM")  # each written east -> west
# A LidarBC .laz covers at most one sub-tile of a 1:20k sheet: median 1,660 x 1,417 m,
# none over 2.4 km (all 174,282 items, 2026-10-11, #2; the first increment's 9,650 gave
# 1,829 x 1,418 m). Files at the edge of coverage are much smaller -- 1,302 have a side
# under 100 m, the first increment's smallest 1 x 1 m with 14 points -- and are real, so
# there is no lower bound beyond a box of positive size. The upper bound is what catches a
# box anchored at the UTM origin.
TILE_SIDE_MAX_M = 5_000

# <block>/<sheet>/<year>/<product>/<file>.laz
_KEY = re.compile(r"^(\d{3})/(\d{3}[a-z])/(\d{4})/([a-z]+)/([^/]+\.laz)$")
# The last underscore token before `.laz` (an optional ` (2)` copy marker and `_dsm`
# suffix allowed) is the acquisition date: yyyymmdd, yymmdd or yyyy. A yyyymmdd before it
# (`_20250509_20251014`) makes the pair the first and last day flown (date_parse).
_DATE = re.compile(r"_(?:(\d{8})_)?(\d{4}|\d{6}|\d{8})(?:_dsm)?(?: \(\d+\))?\.laz$")


def url_scheme_check(url: str) -> str:
    """Return `url`, refusing the one-slash `https:/` form that ngr < 0.0.3 wrote
    (stac_dem_bc#51). Silently repairing it would hide a stale writer."""
    if url.startswith("https:/") and not url.startswith("https://"):
        raise ValueError(f"one-slash URL (https:/) - regenerate it with ngr >= 0.0.3: {url}")
    return url


def key_parse(url: str) -> dict:
    """Split an objectstore URL into its parts. Raises on anything off the bucket or
    not shaped <block>/<sheet>/<year>/<product>/<file>.laz, rather than guessing."""
    url_scheme_check(url)
    prefix = PATH_S3 + "/"
    if not url.startswith(prefix):
        raise ValueError(f"URL is not on the objectstore ({PATH_S3}): {url}")
    key = url[len(prefix):]
    m = _KEY.match(key)
    if not m:
        raise ValueError(f"key is not <block>/<sheet>/<year>/<product>/<file>.laz: {key}")
    block, sheet, year, product, name = m.groups()
    if not sheet.startswith(block):
        raise ValueError(f"sheet {sheet} is not in block {block}: {key}")
    if product not in PRODUCTS:
        raise ValueError(f"unknown product directory {product!r}: {key}")
    return {"key": key, "block": block, "sheet": sheet, "year": int(year),
            "product": product, "name": name}


def nts_sheet_bounds(block: str, sheet: str) -> tuple[float, float, float, float]:
    """(west, south, east, north) in degrees of the NTS 1:250k sheet a key names, e.g.
    `082`, `082e` -> 082E. item_create refuses a footprint centre outside it: of the listed
    files that reach the check, 4 fail, and are in EXCLUDE with the reason (2026-10-11, #2)."""
    if block not in NTS_BLOCKS:
        raise ValueError(f"no NTS grid recorded for block {block}")
    lat0, lon_east = NTS_BLOCKS[block]
    letter = sheet[-1].upper()
    for row, letters in enumerate(_NTS_ROWS):
        if letter in letters:
            col = letters.index(letter)
            return (lon_east - 2 * (col + 1), lat0 + row, lon_east - 2 * col, lat0 + row + 1)
    raise ValueError(f"{sheet!r} is not an NTS 1:250k sheet letter")


def url_to_item_id(url: str) -> str:
    """Item id from the key path, as stac_dem_bc derives its ids: `/` -> `-`, no
    extension. The product directory stays in the id, so a `pointcloud` and a `dsm`
    file of the same tile never collide."""
    return key_parse(url)["key"].replace("/", "-").removesuffix(".laz")


def href_encode(url: str) -> str:
    """Percent-encode the path at construction (spaces in ` (2)` copies), leaving the
    scheme and host alone. Idempotent on an already-encoded path is NOT assumed:
    callers pass the raw objectstore URL exactly once."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(parts._replace(path=urllib.parse.quote(parts.path, safe="/()")))


def date_parse(name: str, path_year: int, trust_filename: bool = True) -> dict:
    """Acquisition time from the filename, trusted only when it agrees with the year
    directory; otherwise the year directory as a range.

    Returns `{"datetime": dt}` for a day, or `{"start": dt, "end": dt}` for a range of days
    or a year, plus `source` (`filename` / `path`) and `filename_date` (the last token, or
    None).

    Two day tokens (`_20250509_20251014`) are the first and last day flown, and the year
    directory is the year of the first: in 30 such files from 15 deliveries every sampled
    point's GPS time fell between the two, including 14 whose last day is in a later year
    (`093c/2023` `_20230921_20251001` holds points from 2023, 2024 and 2025; 2026-10-11, #2).
    So they are a range, and only the first day need agree with the directory.

    The filename date is not reliably the acquisition date. `082k/2017` files are named
    `_180827` while their GPS times fall in October 2017; `092g/092h/092j 2016` names carry
    2017 dates that match the header's creation date, a processing date. So a filename
    date whose year differs from the directory year is recorded, not published as the
    acquisition time. Whether a token is trustworthy is a property of the delivery, not
    of one file: `082k/2017` also holds `_171015` files whose GPS times are not the 15th.
    So a caller that finds any disagreeing token in a delivery passes
    `trust_filename=False` for all of it, and every file gets the directory year.
    """
    m = _DATE.search(name)
    first, tok = (m.group(1), m.group(2)) if m else (None, None)
    if tok and len(tok) == 8:
        dt = datetime.strptime(tok, "%Y%m%d").replace(tzinfo=timezone.utc)
    elif tok and len(tok) == 6:
        dt = datetime.strptime(tok, "%y%m%d").replace(tzinfo=timezone.utc)
    else:
        dt = None
    d1 = (datetime.strptime(first, "%Y%m%d").replace(tzinfo=timezone.utc)
          if first and first != tok and len(tok) == 8 else None)
    year = dt.year if dt else (int(tok) if tok else None)
    agrees = (d1.year == path_year and d1 <= dt) if d1 else year == path_year
    if dt and agrees and trust_filename:
        if d1:
            return {"start": d1, "end": dt.replace(hour=23, minute=59, second=59),
                    "source": "filename", "filename_date": tok}
        return {"datetime": dt, "source": "filename", "filename_date": tok}
    source = "filename" if (agrees and trust_filename) else "path"
    return {"start": datetime(path_year, 1, 1, tzinfo=timezone.utc),
            "end": datetime(path_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            "source": source, "filename_date": tok}


def compound_reorder(wkt: str) -> str | None:
    """A WKT1 COMPD_CS written vertical-first, with its two parts swapped; None for any
    other WKT.

    OGC 01-009 puts the horizontal part first and PROJ refuses the other order. 2,008
    files in seven 2021 deliveries carry `COMPD_CS[..., VERT_CS[...], PROJCS[...]]`
    (2026-10-11, #2). The swap changes the order only, so both parts keep their own
    definitions and authority codes."""
    s = wkt.strip()
    if not (s.startswith("COMPD_CS[") and s.endswith("]")):
        return None
    body = s[len("COMPD_CS["):-1]
    parts, depth, quoted, start = [], 0, False, 0
    for i, c in enumerate(body):
        if c == '"':
            quoted = not quoted
        elif quoted:
            continue
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(body[start:i])
            start = i + 1
    parts.append(body[start:])
    kinds = [p.split("[", 1)[0].strip() for p in parts]
    if len(parts) < 3 or kinds[1] != "VERT_CS" or kinds[2] not in ("PROJCS", "GEOGCS"):
        return None
    parts[1], parts[2] = parts[2], parts[1]
    return "COMPD_CS[" + ",".join(parts) + "]"


@functools.lru_cache(maxsize=16)
def _crs_reordered(wkt: str) -> CRS:
    """Parse a vertical-first compound by its swapped form, logged once per distinct WKT."""
    crs = CRS.from_wkt(compound_reorder(wkt))
    logging.getLogger(__name__).warning("CRS written vertical-first, read swapped: %s",
                                        crs.name)
    return crs


def header_crs(h: laspy.LasHeader) -> CRS | None:
    """The header's CRS, as laspy parses it, except that a WKT compound written
    vertical-first is read with its parts swapped (`compound_reorder`). Any other
    parse failure raises as before."""
    try:
        return h.parse_crs()
    except CRSError:
        wkts = [r.string for r in [*h.vlrs, *(h.evlrs or [])]
                if isinstance(r, laspy.vlrs.known.WktCoordinateSystemVlr)]
        if len(wkts) != 1 or compound_reorder(wkts[0]) is None:
            raise
        return _crs_reordered(wkts[0])


def header_read(url: str, session: requests.Session | None = None) -> dict:
    """The facts an item needs, from the LAS header and VLRs only (one ~64 KB range
    request; research/laz_header_read.md). No points are decompressed."""
    f = HttpRangeFile(href_encode(url), session=session)
    with laspy.open(f) as reader:
        h = reader.header
        crs = header_crs(h)
        dims = [(d.name, d.num_bits, d.kind.name) for d in h.point_format.dimensions]
        return {
            "header_version": HEADER_VERSION,
            "las_version": str(h.version),
            "point_format": h.point_format.id,
            "point_count": int(h.point_count),
            "mins": [float(v) for v in h.mins],
            "maxs": [float(v) for v in h.maxs],
            "crs_wkt": crs.to_wkt() if crs else None,
            "dimensions": dims,
            "file_size": f.size,
        }


_SCHEMA_TYPES = {
    "FloatingPoint": SchemaType.FLOATING,
    "UnsignedInteger": SchemaType.UNSIGNED,
    "SignedInteger": SchemaType.SIGNED,
    # A bit field (return_number, classification in formats 0-5, the flags) is published
    # as a one-byte unsigned value, as PDAL reports it. Its bit width / 8 is 0.
    "BitField": SchemaType.UNSIGNED,
}


def _schema(name: str, num_bits: int, kind: str) -> Schema:
    """One `pc:schemas` entry. Raises on a laspy kind it does not know, rather than
    publishing a guessed type."""
    if kind not in _SCHEMA_TYPES:
        raise ValueError(f"unknown laspy dimension kind {kind!r} for {name}")
    size = 1 if kind == "BitField" else num_bits // 8
    if size < 1:
        raise ValueError(f"dimension {name} has {num_bits} bits, not a whole byte")
    return Schema.create(name=name, size=size, type=_SCHEMA_TYPES[kind])


def _horizontal(crs: CRS) -> CRS:
    """The horizontal CRS a footprint and `proj:code` describe: the first part of a
    compound, unwrapped from a BoundCRS (a TOWGS84 binding hides the EPSG code)."""
    horiz = crs.sub_crs_list[0] if crs.is_compound else crs
    return horiz.source_crs if horiz.is_bound else horiz


@functools.lru_cache(maxsize=256)
def _crs_to_wgs84(crs_wkt: str) -> tuple[CRS, Transformer]:
    """The horizontal CRS of a header's WKT and its transformer to WGS84. Cached: a build
    meets a handful of distinct WKTs over 175k files, and parsing each per file dominated
    item_create. Called from one thread (a Transformer is not thread-safe)."""
    horiz = _horizontal(CRS.from_wkt(crs_wkt))
    return horiz, Transformer.from_crs(horiz, "EPSG:4326", always_xy=True)


def item_create(url: str, header: dict, collection_href: str,
                trust_filename_date: bool = True) -> pystac.Item:
    """A STAC item for one `.laz`. Pure: no I/O.

    `collection_href` is where the collection JSON is served; STAC requires an item
    that names its collection to link to it, and the caller owns that location.

    Geometry is the header's bounding box, transformed from the file's CRS to WGS84
    by its four corners (a tile is ~2 km, so edge curvature is far below a metre).
    A file with no CRS in its header raises: guessing a UTM zone from the filename
    would publish a footprint that is wrong by hundreds of kilometres if the guess
    is wrong.
    """
    parts = key_parse(url)
    # Checked first, so a key the sheet check would also refuse is named for this.
    delivery = f"{parts['block']}/{parts['sheet']}/{parts['year']}"
    if not DELIVERY.match(delivery):
        raise ValueError(f"delivery {delivery!r} is not <block>/<sheet>/<year>: {url}")
    if not header.get("crs_wkt"):
        raise ValueError(f"no CRS in the LAS header: {url}")
    if header.get("header_version") != HEADER_VERSION:
        raise ValueError(f"header record is version {header.get('header_version')}, "
                         f"not {HEADER_VERSION} - read it again: {url}")
    horiz, to_wgs84 = _crs_to_wgs84(header["crs_wkt"])
    (x0, y0, _), (x1, y1, _) = header["mins"], header["maxs"]
    hi = TILE_SIDE_MAX_M
    if not (0 < x1 - x0 <= hi and 0 < y1 - y0 <= hi):
        raise ValueError(f"implausible header box {header['mins']} - {header['maxs']} "
                         f"(sides {x1 - x0:.0f} x {y1 - y0:.0f} m): {url}")
    corners = [to_wgs84.transform(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    lons, lats = [c[0] for c in corners], [c[1] for c in corners]
    geometry = {"type": "Polygon",
                "coordinates": [[list(c) for c in corners] + [list(corners[0])]]}
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    # The footprint must be where the file says it is: its centre in the NTS sheet named
    # in the key. A box in BC but in the wrong UTM zone lands three sheets west; a box
    # anchored at the UTM origin lands near the equator. Both are header faults.
    cx, cy = to_wgs84.transform((x0 + x1) / 2, (y0 + y1) / 2)
    w, s, e, n = nts_sheet_bounds(parts["block"], parts["sheet"])
    if not (w <= cx <= e and s <= cy <= n):
        raise ValueError(f"footprint centre ({cx:.3f}, {cy:.3f}) is not in NTS sheet "
                         f"{parts['sheet'].upper()} {(w, s, e, n)}: {url}")

    when = date_parse(parts["name"], parts["year"], trust_filename_date)
    item = pystac.Item(
        id=url_to_item_id(url),
        geometry=geometry,
        bbox=bbox,
        datetime=when.get("datetime"),
        start_datetime=when.get("start"),
        end_datetime=when.get("end"),
        properties={
            "lidarbc:product": parts["product"],
            "lidarbc:delivery": delivery,
            "lidarbc:datetime_source": when["source"],
            "las:version": header["las_version"],
            "las:point_format": header["point_format"],
        },
        collection=COLLECTION_ID,
        stac_extensions=[SCHEMA_LIDARBC, SCHEMA_LAS],
    )
    if when["filename_date"]:
        item.properties["lidarbc:filename_date"] = when["filename_date"]

    pc = PointcloudExtension.ext(item, add_if_missing=True)
    pc.apply(
        count=header["point_count"],
        type="lidar",
        encoding="LASzip",
        schemas=[_schema(n, b, k) for n, b, k in header["dimensions"]],
    )

    proj = ProjectionExtension.ext(item, add_if_missing=True)
    epsg = horiz.to_epsg()
    proj.apply(
        code=f"EPSG:{epsg}" if epsg else None,
        wkt2=None if epsg else horiz.to_wkt(),
        bbox=[x0, y0, x1, y1],
    )

    asset = pystac.Asset(
        href=href_encode(url),
        media_type=MEDIA_TYPE_LAZ,
        roles=["data"],
        title="Point cloud (LAZ)" if parts["product"] == "pointcloud"
        else "RGB-colourised point cloud (LAZ)",
    )
    item.add_asset(ASSET_LAZ, asset)
    FileExtension.ext(asset, add_if_missing=True).size = header["file_size"]
    item.add_link(pystac.Link(rel=pystac.RelType.COLLECTION, target=collection_href,
                              media_type=pystac.MediaType.JSON))
    return item


# ASPRS classes by value, as LAS 1.4 R15 names them; LAS 1.0-1.3 gave 8 and 12 other
# meanings (ASPRS_CLASSES_LAS12). Names follow the classification extension's pattern
# (^[0-9A-Za-z-_]+$). A value not listed is published as `class_<value>`.
ASPRS_CLASSES = {
    0: "never_classified", 1: "unclassified", 2: "ground", 3: "low_vegetation",
    4: "medium_vegetation", 5: "high_vegetation", 6: "building", 7: "low_noise",
    9: "water", 10: "rail", 11: "road_surface", 13: "wire_guard", 14: "wire_conductor",
    15: "transmission_tower", 16: "wire_connector", 17: "bridge_deck", 18: "high_noise",
}
ASPRS_CLASSES_LAS12 = {8: "model_key_point", 12: "overlap"}


def asprs_class_name(value: int, las_version: str) -> str:
    if las_version < "1.4" and value in ASPRS_CLASSES_LAS12:
        return ASPRS_CLASSES_LAS12[value]
    return ASPRS_CLASSES.get(value, f"class_{value}")


def classes_add(item: pystac.Item, full: dict) -> pystac.Item:
    """List every class in the item's file, with its point count, as the `laz` asset's
    `classification:classes`. Pure: no I/O.

    `full` is a whole-file read of the `laz` file (laz_classes_probe.laz_full): every point
    tallied, not a sample, which is the only basis on which the list may claim to be
    complete. A read whose point count is not the header's, or not the points it tallied,
    raises rather than publishing classes of some other file.
    """
    asset = item.assets[ASSET_LAZ]
    n = item.properties["pc:count"]
    if full["point_count"] != n or full["points_read"] != n:
        raise ValueError(f"{item.id}: the class read covers {full['points_read']} of "
                         f"{full['point_count']} points, the header {n}")
    if full["las_version"] != item.properties["las:version"]:
        raise ValueError(f"{item.id}: the class read is LAS {full['las_version']}, the "
                         f"header {item.properties['las:version']}")
    counts = {int(k): int(v) for k, v in full["classes"].items()}
    ClassificationExtension.ext(asset, add_if_missing=True).classes = [
        Classification.create(value=v, name=asprs_class_name(v, full["las_version"]),
                              count=counts[v])
        for v in sorted(counts)]
    return item


def copc_asset_add(item: pystac.Item, href: str, copc_header: dict,
                   laz_header: dict) -> pystac.Item:
    """Add CanElevation's COPC copy of the item's file as the `copc` asset. Pure: no I/O.

    `copc_header` and `laz_header` are header_read() of the copy and of the LidarBC file
    the item was made from. A matching file name is how a copy is found, not proof that it
    is one, so the copy must have the same point count, the same horizontal CRS, and a box
    within COPC_BOX_TOLERANCE_M; anything else raises rather than linking other points.
    That cannot see a reclassified re-delivery under the same name, so the asset claims
    what was checked and no more. The copy's own LAS version and point format go on the
    asset: the item's `pc:schemas` describe the `laz` file.
    """
    if ASSET_COPC in item.assets:
        raise ValueError(f"{item.id} already has a {ASSET_COPC!r} asset")
    if copc_header["point_count"] != laz_header["point_count"]:
        raise ValueError(f"COPC has {copc_header['point_count']} points, the LAZ "
                         f"{laz_header['point_count']}: {href} is not a copy of {item.id}")
    crs = [_horizontal(CRS.from_wkt(h["crs_wkt"])) if h.get("crs_wkt") else None
           for h in (copc_header, laz_header)]
    epsg = [c.to_epsg() if c else None for c in crs]
    same_crs = crs[0] is not None and (epsg[0] == epsg[1] if None not in epsg
                                       else crs[0].equals(crs[1]))
    if not same_crs:
        raise ValueError(f"COPC horizontal CRS {crs[0] and crs[0].name!r} is not the LAZ's "
                         f"{crs[1] and crs[1].name!r}: {href} is not a copy of {item.id}")
    off = max(abs(a - b) for a, b in zip(copc_header["mins"] + copc_header["maxs"],
                                         laz_header["mins"] + laz_header["maxs"]))
    if not off < COPC_BOX_TOLERANCE_M:
        raise ValueError(f"COPC box is {off:.2f} m from the LAZ's: {href} is not a copy "
                         f"of {item.id}")
    asset = pystac.Asset(
        href=href_encode(href),
        media_type=MEDIA_TYPE_COPC,
        roles=["data"],
        title="Point cloud (COPC), NRCan CanElevation",
        description="The Cloud Optimized Point Cloud that Natural Resources Canada's "
                    "CanElevation series publishes under this file's name, checked at build "
                    "to have the same point count and horizontal CRS as the `laz` file and a "
                    f"header box within {COPC_BOX_TOLERANCE_M:g} m of it. Distributed by NRCan "
                    "under the Open Government Licence - Canada.",
        extra_fields={"las:version": copc_header["las_version"],
                      "las:point_format": copc_header["point_format"]},
    )
    item.add_asset(ASSET_COPC, asset)
    FileExtension.ext(asset, add_if_missing=True).size = copc_header["file_size"]
    return item


# A listing is hundreds of pages; one dropped connection or 5xx in a 10-minute walk would
# otherwise throw the walk away (measured 2026-10-11: RemoteDisconnected on a CanElevation page,
# #2). A page is re-requested with the same marker, so a retry cannot skip or repeat keys.
PAGE_ATTEMPTS = 4
PAGE_BACKOFF_S = 2.0


def page_get(s: requests.Session, url: str, params: dict, timeout: float,
             sleep=time.sleep) -> requests.Response:
    """One listing page, retried on a connection error, a timeout or a 5xx. Any other status
    is returned for the caller to refuse; the last failure is raised."""
    for attempt in range(PAGE_ATTEMPTS):
        try:
            r = s.get(url, params=params, timeout=timeout)
            if r.status_code < 500 or attempt == PAGE_ATTEMPTS - 1:
                return r
        except (requests.ConnectionError, requests.Timeout):
            if attempt == PAGE_ATTEMPTS - 1:
                raise
        sleep(PAGE_BACKOFF_S * 2 ** attempt)
    raise AssertionError("unreachable")


def keys_list(prefix: str, session: requests.Session | None = None,
              timeout: float = 60) -> list[dict]:
    """Every object under `prefix` on the objectstore, paged by marker, as
    `{"url", "etag", "size"}`. The ETag is what tells a re-delivered file from the one
    a cached header was read from.

    Raises on a non-200 rather than returning what it had, so a failed listing is
    never mistaken for an empty directory. URLs are joined with `/`, never a path
    normaliser (ngr#38).
    """
    s = session or requests.Session()
    out, marker = [], None
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while True:
        params = {"prefix": prefix}
        if marker:
            params["marker"] = marker
        r = page_get(s, PATH_S3, params, timeout)
        if r.status_code != 200:
            raise OSError(f"listing {prefix!r} returned {r.status_code}")
        root = ET.fromstring(r.content)
        contents = root.findall(".//s3:Contents", ns)
        keys = [c.findtext("s3:Key", namespaces=ns) for c in contents]
        out.extend({"url": f"{PATH_S3}/{c.findtext('s3:Key', namespaces=ns)}",
                    "etag": (c.findtext("s3:ETag", default="", namespaces=ns) or "").strip('"'),
                    "size": int(c.findtext("s3:Size", default="0", namespaces=ns) or 0)}
                   for c in contents)
        truncated = (root.findtext("s3:IsTruncated", default="false", namespaces=ns) == "true")
        if not truncated:
            break
        if not keys:
            # A truncated page with no keys has no marker to continue from. Stopping
            # would return a partial listing as if complete; looping would never end.
            raise OSError(f"listing {prefix!r} reported truncated with no keys")
        marker = keys[-1]
    return out


def canelevation_keys_list(prefix: str, session: requests.Session | None = None,
                           timeout: float = 60) -> list[dict]:
    """Every object under `prefix` in the CanElevation bucket (ListObjectsV2), as
    `{"url", "etag", "size"}` like keys_list(), and refusing what it refuses: a non-200,
    and a truncated page with no token to continue from."""
    s = session or requests.Session()
    out, token = [], None
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while True:
        params = {"list-type": "2", "prefix": prefix}
        if token:
            params["continuation-token"] = token
        r = page_get(s, CANELEVATION + "/", params, timeout)
        if r.status_code != 200:
            raise OSError(f"listing {prefix!r} returned {r.status_code}")
        root = ET.fromstring(r.content)
        out.extend({"url": f"{CANELEVATION}/{c.findtext('s3:Key', namespaces=ns)}",
                    "etag": (c.findtext("s3:ETag", default="", namespaces=ns) or "").strip('"'),
                    "size": int(c.findtext("s3:Size", default="0", namespaces=ns) or 0)}
                   for c in root.findall(".//s3:Contents", ns))
        if root.findtext("s3:IsTruncated", default="false", namespaces=ns) != "true":
            return out
        token = root.findtext("s3:NextContinuationToken", namespaces=ns)
        if not token:
            raise OSError(f"listing {prefix!r} reported truncated with no continuation token")


def schemas_check(body: dict) -> None:
    """Refuse a STAC body (item or collection, as JSON) that writes a key of a custom prefix
    without listing that prefix's schema in `stac_extensions`. Without it validation skips
    the field's schema entirely and would pass any value."""
    def keys(x):
        if isinstance(x, dict):
            for k, v in x.items():
                yield k
                yield from keys(v)
        elif isinstance(x, list):
            for v in x:
                yield from keys(v)
    used = {k.split(":", 1)[0] for k in keys(body) if ":" in k}
    missing = sorted(p for p in used & SCHEMAS_CUSTOM.keys()
                     if SCHEMAS_CUSTOM[p] not in body.get("stac_extensions", []))
    if missing:
        raise ValueError(f"{body.get('id')}: writes {', '.join(p + ':' for p in missing)} keys "
                         f"without the schema in stac_extensions")


def schemas_preload() -> None:
    """Put the checked-in copies of the crate schemas into pystac's validator cache, under their
    published URLs, so no validate() in this process fetches them. Idempotent."""
    import pystac.validation
    cache = pystac.validation.RegisteredValidator.get_validator().schema_cache
    for url, path in SCHEMA_FILES.items():
        if url not in cache:
            with open(path) as fh:
                cache[url] = json.load(fh)


def fields_check(body: dict) -> None:
    """Refuse an item body (as JSON) missing a field the build always writes, or carrying one
    empty: every FIELDS_ITEM in properties, `lidarbc:filename_date` where the date came from the
    file name, and both `las:` fields on a `copc` asset."""
    p = body["properties"]
    want = list(FIELDS_ITEM)
    if p.get("lidarbc:datetime_source") == "filename":
        want.append("lidarbc:filename_date")
    missing = [k for k in want if p.get(k) in (None, "")]
    if ASSET_COPC in body.get("assets", {}):
        missing += [f"{ASSET_COPC}.{k}" for k in FIELDS_COPC
                    if body["assets"][ASSET_COPC].get(k) in (None, "")]
    if missing:
        raise ValueError(f"{body.get('id')}: missing {', '.join(missing)}")
