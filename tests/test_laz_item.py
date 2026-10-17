"""Contract tests for scripts/laz_item.py, scripts/laz_remote.py and the build's guards.

The remote-read tests run against a local HTTP server that, like the objectstore, answers
ranges with 206 and does NOT advertise Accept-Ranges (research/laz_header_read.md), over
a LAZ written here by laspy -- so the header path is exercised end to end with no network.
"""

import http.server
import json
import os
import threading
import urllib.parse
from datetime import datetime, timezone

import laspy
import numpy as np
import pystac
import pytest
from pyproj import CRS
from pyproj.exceptions import CRSError

import catalogue_build
import laz_item
from laz_item import (
    ASSET_LAZ,
    LONLAT_DECIMALS,
    PATH_S3,
    PATH_S3_STAC,
    date_parse,
    header_read,
    href_encode,
    item_create,
    key_parse,
    keys_list,
    url_to_item_id,
)
from laz_remote import HttpRangeFile

@pytest.fixture(autouse=True)
def no_live_listing(monkeypatch):
    """The build's listers reach real buckets. A test that does not replace them fails here
    rather than passing on whatever the network returns (one did, 2026-10-09)."""
    def refuse(*a, **k):
        raise AssertionError("a test reached a live bucket listing")
    monkeypatch.setattr(catalogue_build, "keys_list", refuse)
    monkeypatch.setattr(catalogue_build, "canelevation_keys_list", refuse)
    monkeypatch.setattr(catalogue_build, "blocks_list", refuse)
    monkeypatch.setattr(laz_item, "PAGE_BACKOFF_S", 0)  # a 5xx test retries without waiting


@pytest.fixture(autouse=True)
def no_recorded_pairs(monkeypatch):
    """main() checks COPC pairs against data/copc_pairs.json before reading a header. These
    builds pair nothing unless they say so."""
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})


@pytest.fixture(autouse=True)
def no_recorded_groups(monkeypatch):
    """main() checks the listing against the committed GROUPS file. These builds list a
    handful of files, so record none; the tests of that check pass their own."""
    monkeypatch.setattr(catalogue_build, "groups_load", lambda path=None: {})


@pytest.fixture(autouse=True)
def no_unreadable_files(monkeypatch):
    """main() refuses a CLASSES_UNREADABLE entry whose file is not in a full build. These
    builds list a handful of files, so name none; the tests of that check name their own."""
    monkeypatch.setattr(catalogue_build, "CLASSES_UNREADABLE", {})


def _targets_etag(item_id):
    """The ETag the build listed for an item, from the targets file it writes before its class
    step: what a real sample would read back from the file."""
    for d in ("data/build", "data/build-limit"):
        p = f"{d}/{catalogue_build.CLASS_TARGETS}"
        if os.path.exists(p):
            for t in map(json.loads, open(p)):
                if t["id"] == item_id:
                    return t["etag"]
    raise AssertionError(f"{item_id} is not a class target")


def _sample(classes):
    """A point-sample probe returning `classes` (ints) for every item, at its listed ETag,
    shaped as item_probe's record (with the `copc` href it was taken with, if any)."""
    def probe(item, session=None):
        rec = {"id": item["id"], "laz": urllib.parse.unquote(item["assets"]["laz"]["href"]),
               "laz_sample": {"etag": _targets_etag(item["id"]), "point_count": 1000,
                              "samples": {"all": {str(k): v for k, v in classes.items()}},
                              "bytes": 1, "seconds": 0}}
        if "copc" in item["assets"]:
            rec["copc"] = item["assets"]["copc"]["href"]
        return rec
    return probe


@pytest.fixture(autouse=True)
def point_reads(monkeypatch):
    """main() samples the points of every file and reads whole what a sample flags.
    These builds sample a mixed tile, which flags nothing; a whole read is a test failure. The
    tests of that wiring set their own."""
    monkeypatch.setattr(catalogue_build, "item_probe", _sample({1: 400, 2: 600}))

    def refuse(*a, **k):
        raise AssertionError("a test reached a whole-file read")
    monkeypatch.setattr(catalogue_build, "full_probe", refuse)


PC = f"{PATH_S3}/092/092g/2016/pointcloud/bc_092g019_1_4_1_xyes_8_utm10_20170713.laz"
FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures"
# A real UTM 11 key in 082E (bc_082e053_4_4_2, 2019), for boxes in UTM 11 coordinates.
PC11 = f"{PATH_S3}/082/082e/2019/pointcloud/bc_082e053_4_4_2_cyes_12_utm11_2019.laz"
COLL = f"{PATH_S3_STAC}/collection.json"


# =============================================================================
# Keys, ids, dates
# =============================================================================

def test_a_one_slash_url_is_refused_not_repaired():
    with pytest.raises(ValueError, match="one-slash"):
        key_parse(PC.replace("https://", "https:/", 1))


@pytest.mark.parametrize("url, why", [
    ("https://example.invalid/gdwuts/092/092g/2016/pointcloud/x.laz", "not on the objectstore"),
    (f"{PATH_S3}/092/092g/2016/chm/x.laz", "unknown product"),
    (f"{PATH_S3}/092/092g/pointcloud/x.laz", "is not <block>"),
    (f"{PATH_S3}/092/092g/2016/pointcloud/x.tif", "is not <block>"),
])
def test_key_parse_refuses_what_it_cannot_place(url, why):
    with pytest.raises(ValueError, match=why):
        key_parse(url)


def test_ids_keep_the_product_so_a_tile_in_both_directories_cannot_collide():
    dsm = PC.replace("/pointcloud/", "/dsm/")
    assert url_to_item_id(PC) == "092-092g-2016-pointcloud-bc_092g019_1_4_1_xyes_8_utm10_20170713"
    assert url_to_item_id(PC) != url_to_item_id(dsm)


def test_a_copy_marker_stays_in_the_id_and_is_encoded_in_the_href():
    url = f"{PATH_S3}/082/082l/2018/pointcloud/bc_082l024_2_4_3_xyes_12_utm11_2018 (2).laz"
    assert url_to_item_id(url).endswith("_2018 (2)")
    assert href_encode(url).endswith("_2018%20(2).laz")
    assert href_encode(url).startswith("https://")


def _d(*a):
    return datetime(*a, tzinfo=timezone.utc)


@pytest.mark.parametrize("name, year, day", [
    ("bc_092g019_1_4_1_xyes_8_utm10_20170713.laz", 2017, _d(2017, 7, 13)),
    ("bc_082e003_1_4_4_xyes_8_utm11_170603.laz", 2017, _d(2017, 6, 3)),
    ("bc_092g026_4_3_1_xyes_8_utm10_20170601_dsm.laz", 2017, _d(2017, 6, 1)),
    ("bc_092h053_3_4_1_xyes_7_utm10_20160724 (2).laz", 2016, _d(2016, 7, 24)),
])
def test_a_day_in_the_filename_is_the_datetime_when_its_year_agrees(name, year, day):
    got = date_parse(name, year)
    assert got["datetime"] == day and got["source"] == "filename"


@pytest.mark.parametrize("name, path_year", [
    # Named 2018-08-27; GPS time puts these files in October 2017 (review, 2026-10-07).
    ("bc_082k001_1_1_1_xyes_8_utm11_180827.laz", 2017),
    # Named for a 2017 processing date in a 2016 delivery.
    ("bc_092g019_1_4_1_xyes_8_utm10_20170713.laz", 2016),
])
def test_a_filename_date_in_another_year_is_recorded_not_published(name, path_year):
    got = date_parse(name, path_year)
    assert "datetime" not in got
    assert got["start"] == _d(path_year, 1, 1) and got["end"] == _d(path_year, 12, 31, 23, 59, 59)
    assert got["source"] == "path"
    assert got["filename_date"] in name


def test_two_days_in_the_filename_are_the_first_and_last_day_flown():
    """Measured: every sampled point's GPS time falls between the two (#2)."""
    got = date_parse("bc_094p025_1_2_3_xyes_8_utm10_20250509_20251014.laz", 2025)
    assert got == {"start": _d(2025, 5, 9), "end": _d(2025, 10, 14, 23, 59, 59),
                   "source": "filename", "filename_date": "20251014"}
    # the year directory is the first day's: flying can run into a later year
    got = date_parse("bc_094j045_3_3_4_xyes_8_utm10_20240531_20250510.laz", 2024)
    assert got["start"] == _d(2024, 5, 31) and got["end"] == _d(2025, 5, 10, 23, 59, 59)
    assert got["source"] == "filename"
    # the same day twice is that day
    got = date_parse("bc_093c080_4_4_4_xyes_8_utm10_20230916_20230916.laz", 2023)
    assert got["datetime"] == _d(2023, 9, 16)
    # and untrusted, the directory year as for any other name
    got = date_parse("bc_094p025_1_2_3_xyes_8_utm10_20250509_20251014.laz", 2025,
                     trust_filename=False)
    assert got["start"] == _d(2025, 1, 1) and got["source"] == "path"


@pytest.mark.parametrize("name", [
    "bc_094p025_1_2_3_xyes_8_utm10_20241228_20250103.laz",  # first day in another year
    "bc_094p025_1_2_3_xyes_8_utm10_20251014_20250509.laz",  # first after last
])
def test_two_days_that_cannot_be_a_range_in_the_year_are_recorded_not_published(name):
    got = date_parse(name, 2025)
    assert got["start"] == _d(2025, 1, 1) and got["end"] == _d(2025, 12, 31, 23, 59, 59)
    assert got["source"] == "path"


def test_a_year_only_date_is_a_range_not_january_first():
    got = date_parse("bc_082e004_3_1_3_xyes_12_utm11_2018.laz", 2018)
    assert got == {"start": _d(2018, 1, 1), "end": _d(2018, 12, 31, 23, 59, 59),
                   "source": "filename", "filename_date": "2018"}


def test_a_name_with_no_date_falls_back_to_the_year_directory_and_says_so():
    # A 7-digit token is not a date of any known shape.
    got = date_parse("bc_082e004_3_1_3_xyes_12_utm11_2016072.laz", 2016)
    assert got["source"] == "path" and got["filename_date"] is None
    assert got["start"] == _d(2016, 1, 1)


# =============================================================================
# The item
# =============================================================================

def _header(crs_wkt=CRS.from_epsg(3157).to_wkt(), point_format=1,
            mins=(547410.45, 5441555.91, 2.2), maxs=(549246.4, 5442961.42, 100.49)):
    """Shaped exactly as header_read() returns, dimensions included -- taken from laspy's
    own point format, not written by hand, so bit fields arrive as they really do."""
    return {
        "header_version": laz_item.HEADER_VERSION,
        "las_version": "1.2", "point_format": point_format, "point_count": 1000,
        "mins": list(mins), "maxs": list(maxs),
        "crs_wkt": crs_wkt, "file_size": 82_300_000,
        "dimensions": [(d.name, d.num_bits, d.kind.name)
                       for d in laspy.PointFormat(point_format).dimensions],
    }


def test_item_is_valid_stac_and_carries_the_laz_asset():
    it = item_create(PC, _header(), COLL)
    it.validate()
    d = it.to_dict(include_self_link=False)
    assert d["assets"][ASSET_LAZ]["href"] == PC
    assert d["assets"][ASSET_LAZ]["file:size"] == 82_300_000
    assert d["properties"]["pc:count"] == 1000
    assert d["properties"]["proj:code"] == "EPSG:3157"
    assert d["properties"]["lidarbc:product"] == "pointcloud"
    assert [l["href"] for l in d["links"] if l["rel"] == "collection"] == [COLL]


def test_the_footprint_is_the_header_box_in_wgs84():
    """Checked against an independent transform of the same corners."""
    from pyproj import Transformer
    it = item_create(PC, _header(), COLL)
    t = Transformer.from_crs("EPSG:3157", "EPSG:4326", always_xy=True)
    lon, lat = t.transform(547410.45, 5441555.91)
    assert it.geometry["coordinates"][0][0] == pytest.approx([lon, lat])
    assert it.bbox[0] == pytest.approx(min(c[0] for c in it.geometry["coordinates"][0]))
    # Fraser Valley, not somewhere a wrong zone would put it
    assert -123 < lon < -122 and 49 < lat < 49.5


def test_the_footprint_is_rounded_so_a_linux_build_matches_a_mac_one():
    """Unrounded, 75% of footprints differed in the last bits between macOS arm64 and
    linux/amd64 (5.7e-14 degrees at most), so a monthly CI build would have rewritten them
    (#4). 8 decimals is about 1 mm; a header box is stored to 1 cm."""
    it = item_create(PC, _header(), COLL)
    vals = [v for c in it.geometry["coordinates"][0] for v in c] + list(it.bbox)
    assert LONLAT_DECIMALS == 8
    assert all(round(v, LONLAT_DECIMALS) == v for v in vals)
    assert any(round(v, LONLAT_DECIMALS - 1) != v for v in vals)  # rounded, not truncated


UTM11_BOX = dict(mins=(324688.19, 5494147.55, 1497.05), maxs=(326539.47, 5495593.23, 1795.62))


def test_a_compound_crs_publishes_its_horizontal_code():
    h = _header(CRS.from_string("EPSG:2955+6647").to_wkt(), **UTM11_BOX)
    d = item_create(PC11, h, COLL).to_dict(include_self_link=False)
    assert d["properties"]["proj:code"] == "EPSG:2955"


def test_a_compound_crs_whose_horizontal_is_bound_still_publishes_its_code():
    """The real CRS of 082f/2018 (fixture read from bc_082f001_2_2_1): a COMPOUNDCRS whose
    horizontal part is a BOUNDCRS. Its to_epsg() is None until unwrapped."""
    wkt = (FIXTURES / "crs_compound_bound_2955.wkt").read_text()
    assert CRS.from_wkt(wkt).sub_crs_list[0].is_bound
    d = item_create(PC11, _header(wkt, **UTM11_BOX), COLL).to_dict(include_self_link=False)
    assert d["properties"]["proj:code"] == "EPSG:2955"
    assert "proj:wkt2" not in d["properties"] or d["properties"]["proj:wkt2"] is None


@pytest.mark.parametrize("point_format", [1, 3, 6, 7])
def test_every_schema_entry_has_a_real_size_and_type(point_format):
    """Bit fields (return_number, flags, classification in format 1) are 1-byte unsigned,
    never size 0 or signed."""
    d = item_create(PC, _header(point_format=point_format), COLL).to_dict(include_self_link=False)
    schemas = {s["name"]: s for s in d["properties"]["pc:schemas"]}
    assert all(s["size"] >= 1 for s in schemas.values())
    assert schemas["return_number"] == {"name": "return_number", "size": 1, "type": "unsigned"}
    assert schemas["classification"]["type"] == "unsigned"
    assert schemas["gps_time"] == {"name": "gps_time", "size": 8, "type": "floating"}


def test_an_unknown_dimension_kind_is_refused():
    h = _header()
    h["dimensions"] = [("weird", 8, "Complex")]
    with pytest.raises(ValueError, match="unknown laspy dimension kind"):
        item_create(PC, h, COLL)


@pytest.mark.parametrize("mins, maxs, why", [
    # The real fault in 092h003_2_3_1 (2016): mins at the UTM origin.
    ((0, 0, 0), (611484.67, 5432744.76, 1847.61), "implausible header box"),
    # A box of no area: a header whose mins and maxs were never set from the points.
    ((547410.45, 5441555.91, 0), (547410.45, 5441555.91, 0), "implausible header box"),
    # Tile-sized, but nowhere near BC in UTM 10 terms.
    ((100000.0, 1000000.0, 0), (101800.0, 1001400.0, 1), "not in NTS sheet"),
])
def test_an_implausible_header_box_is_refused(mins, maxs, why):
    with pytest.raises(ValueError, match=why):
        item_create(PC, _header(mins=mins, maxs=maxs), COLL)


def test_a_sliver_at_the_edge_of_coverage_is_a_real_file_not_a_fault():
    """bc_092g068_4_2_1 (2016) is 1 x 1 m with 14 points; 104 files are under 100 m."""
    it = item_create(PC, _header(mins=(547410.0, 5441555.0, 2.0), maxs=(547411.0, 5441556.0, 3.0)), COLL)
    it.validate()


def test_a_header_record_of_an_older_shape_is_refused():
    h = _header()
    h["header_version"] = 1
    with pytest.raises(ValueError, match="read it again"):
        item_create(PC, h, COLL)


def test_the_filename_date_is_recorded_beside_a_path_datetime():
    d = item_create(PC.replace("/2016/", "/2016/"), _header(), COLL).to_dict(include_self_link=False)
    assert d["properties"]["lidarbc:filename_date"] == "20170713"
    assert d["properties"]["lidarbc:datetime_source"] == "path"
    assert d["properties"]["start_datetime"].startswith("2016-01-01")


def test_a_header_with_no_crs_is_refused_rather_than_guessed():
    with pytest.raises(ValueError, match="no CRS"):
        item_create(PC, _header(crs_wkt=None), COLL)


# =============================================================================
# Remote read: HttpRangeFile and header_read over a local range server
# =============================================================================

class _RangeHandler(http.server.BaseHTTPRequestHandler):
    """206 for a Range GET, no Accept-Ranges on HEAD -- the objectstore's behaviour."""
    payload = b""
    honour_ranges = True

    def log_message(self, *a):
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()

    def do_GET(self):
        rng = self.headers.get("Range")
        if rng and self.honour_ranges:
            start, end = (int(x) for x in rng.split("=")[1].split("-"))
            body = self.payload[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(self.payload)}")
        else:
            body = self.payload
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def served_laz(tmp_path):
    hdr = laspy.LasHeader(point_format=1, version="1.2")
    hdr.offsets = [547000.0, 5441000.0, 0.0]
    hdr.scales = [0.01, 0.01, 0.01]
    hdr.add_crs(CRS.from_epsg(3157))
    las = laspy.LasData(hdr)
    # Larger than one 64 KB block, so "one block, not the file" can fail.
    n = 200_000
    # Random, not evenly spaced: LAZ compresses a regular sequence to almost nothing.
    rng = np.random.default_rng(1)
    las.x = rng.uniform(547410.45, 549246.4, n)
    las.y = rng.uniform(5441555.91, 5442961.42, n)
    las.z = rng.uniform(2.2, 100.49, n)
    path = tmp_path / "t.laz"
    las.write(str(path))
    handler = type("H", (_RangeHandler,), {"payload": path.read_bytes()})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/t.laz", handler, path
    srv.shutdown()


def test_header_read_over_ranges_matches_a_local_read(served_laz, monkeypatch):
    url, _, path = served_laz
    monkeypatch.setattr(laz_item, "href_encode", lambda u: u)
    h = header_read(url)
    local = laspy.read(str(path))
    assert h["point_count"] == len(local.points) == 200_000
    assert h["mins"] == pytest.approx(list(local.header.mins))
    assert h["maxs"] == pytest.approx(list(local.header.maxs))
    assert CRS.from_wkt(h["crs_wkt"]).to_epsg() == 3157
    assert h["file_size"] == path.stat().st_size


def test_a_header_read_transfers_one_block_not_the_file(served_laz):
    url, _, path = served_laz
    assert path.stat().st_size > 2 * laz_item.HttpRangeFile.__init__.__globals__["BLOCK"]
    f = HttpRangeFile(url)
    with laspy.open(f) as r:
        _ = r.header.point_count
    assert f.requests == 1
    assert f.bytes_fetched <= laz_item.HttpRangeFile.__init__.__globals__["BLOCK"]


def test_a_server_ignoring_the_range_is_refused(served_laz):
    """A 200 to a Range GET would hand back the whole file as if it were one block."""
    url, handler, _ = served_laz
    handler.honour_ranges = False
    f = HttpRangeFile(url)
    with pytest.raises(OSError, match="not 206"):
        f.read(10)


# =============================================================================
# Listing
# =============================================================================

def _page(keys, truncated):
    ns = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'
    body = "".join(f'<Contents><Key>{k}</Key><ETag>"e-{k}"</ETag><Size>7</Size></Contents>'
                   for k in keys)
    return f'<ListBucketResult {ns}><IsTruncated>{str(truncated).lower()}</IsTruncated>{body}</ListBucketResult>'


class _Session:
    def __init__(self, pages, status=200):
        self.pages, self.status, self.markers = list(pages), status, []

    def get(self, url, params=None, timeout=None):
        self.markers.append(params.get("marker"))
        resp = type("R", (), {})()
        resp.status_code = self.status
        resp.content = self.pages.pop(0).encode() if self.pages else b""
        return resp


def test_keys_list_pages_by_marker_and_keeps_the_double_slash():
    s = _Session([_page(["a/1.laz", "a/2.laz"], True), _page(["a/3.laz"], False)])
    urls = [o["url"] for o in keys_list("a/", session=s)]
    assert urls == [f"{PATH_S3}/a/{i}.laz" for i in (1, 2, 3)]
    assert s.markers == [None, "a/2.laz"]
    assert all(u.startswith("https://") for u in urls)


def test_a_truncated_page_with_no_keys_raises_rather_than_returning_a_partial_list():
    s = _Session([_page(["a/1.laz"], True), _page([], True)])
    with pytest.raises(OSError, match="truncated with no keys"):
        keys_list("a/", session=s)


def test_a_failed_listing_raises_rather_than_reading_as_empty():
    with pytest.raises(OSError, match="returned 503"):
        keys_list("a/", session=_Session([""], status=503))


def _listed(keys):
    return [{"url": f"{PATH_S3}/{k}", "etag": "e", "size": 1} for k in keys]


def test_the_build_refuses_a_group_listed_short():
    found = {"092/092g/2016": 1000, "092/092j/2016": 10}
    with pytest.raises(RuntimeError, match="092/092j/2016: 10 of 182"):
        catalogue_build.groups_check(found, {"092/092g/2016": 1000, "092/092j/2016": 182})


def test_a_recorded_group_not_listed_at_all_is_refused():
    with pytest.raises(RuntimeError, match="092/092j/2016: 0 of 182"):
        catalogue_build.groups_check({"092/092g/2016": 5}, {"092/092j/2016": 182})


def test_a_group_at_the_floor_passes_and_a_new_group_is_built_and_logged(caplog):
    catalogue_build.groups_check({"092/092j/2016": 90, "093/093a/2020": 7},
                                 {"092/092j/2016": 100})
    assert "093/093a/2020: 7 .laz, a group not in" in caplog.text


def test_the_listing_keeps_only_pointcloud_laz():
    objs = _listed(["092/092g/2016/pointcloud/a_2016.laz", "092/092g/2016/dsm/a_2016.laz",
                  "092/092g/2016/dem/a_2016.tif", "092/092g/2016/pointcloud/readme.txt"])
    assert [o["url"].rsplit("/", 2)[-2] for o in catalogue_build.pointcloud_select(objs)] == \
        ["pointcloud"]


@pytest.mark.parametrize("key", ["092/092g/2016/pointcloud/sub/a_2016.laz",
                                 "092/092g/2016/pointcloud/a_2016.LAZ"])
def test_a_pointcloud_laz_off_the_key_pattern_fails_the_listing(key):
    with pytest.raises(ValueError, match="key is not"):
        catalogue_build.pointcloud_select(_listed([key]))


def test_the_listing_walks_every_block_the_root_names(monkeypatch):
    walked = []

    def keys(prefix, session=None):
        walked.append(prefix)
        return _listed([f"{prefix}{prefix[:3]}a/2020/pointcloud/x_2020.laz"])
    monkeypatch.setattr(catalogue_build, "blocks_list", lambda s=None: ["092", "093"])
    monkeypatch.setattr(catalogue_build, "keys_list", keys)
    assert walked == [] and len(catalogue_build.listing()) == 2
    assert walked == ["092/", "093/"]


# The real lister, taken before the autouse fixture replaces it; given a session it reaches
# nothing but that session.
blocks_list = catalogue_build.blocks_list


class _Root:
    def __init__(self, prefixes, truncated=False, status=200):
        body = "".join(f"<CommonPrefixes><Prefix>{p}</Prefix></CommonPrefixes>" for p in prefixes)
        self.content = (f"<ListBucketResult><Prefix></Prefix><IsTruncated>"
                        f"{str(truncated).lower()}</IsTruncated>{body}</ListBucketResult>").encode()
        self.status_code = status

    def get(self, url, params=None, timeout=None):
        assert params == {"delimiter": "/"}
        return self


def test_blocks_are_the_three_digit_root_directories():
    s = _Root(["082/", "092/", "albers10k2m/", "index/", "test/"])
    assert blocks_list(s) == ["082", "092"]


@pytest.mark.parametrize("root, err, match", [
    (_Root(["082/", "105/"]), RuntimeError, "no NTS grid in laz_item.NTS_BLOCKS: 105"),
    (_Root(["082/"], truncated=True), OSError, "truncated"),
    (_Root(["082/"], status=503), OSError, "returned 503"),
    (_Root(["albers10k2m/"]), OSError, "names no block"),
])
def test_a_root_listing_that_cannot_be_trusted_raises(root, err, match):
    with pytest.raises(err, match=match):
        blocks_list(root)


def test_groups_record_writes_the_counts_and_builds_nothing(tmp_path, monkeypatch):
    objs = _listed(["092/092g/2016/pointcloud/a_2016.laz", "092/092g/2016/pointcloud/b_2016.laz",
                  "093/093a/2020/pointcloud/c_2020.laz"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "GROUPS", str(tmp_path / "groups.json"))
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS_PATH", str(tmp_path / "pairs.json"))
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [_ce("c_2020.copc.laz")])
    monkeypatch.setattr(catalogue_build, "headers_fetch",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("built")))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--groups-record"])
    assert catalogue_build.main() == 0
    assert json.loads((tmp_path / "groups.json").read_text()) == \
        {"092/092g/2016": 2, "093/093a/2020": 1}
    assert json.loads((tmp_path / "pairs.json").read_text()) == {"093/093a/2020": 1}


@pytest.mark.parametrize("found, force, refused", [
    ({"092/092g/2016": 80}, False, True),      # under the floor
    ({"092/092g/2016": 95}, False, False),     # a fall within the floor is logged
    ({}, False, True),                         # a group gone
    ({"092/092g/2016": 80}, True, False),
])
def test_recording_refuses_to_lower_a_floor_without_force(tmp_path, monkeypatch, found, force,
                                                          refused):
    g = tmp_path / "groups.json"
    g.write_text(json.dumps({"092/092g/2016": 100}))
    monkeypatch.setattr(catalogue_build, "GROUPS", str(g))
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS_PATH", str(tmp_path / "pairs.json"))
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build, "groups_load", lambda path=None: json.loads(g.read_text()))
    if refused:
        with pytest.raises(RuntimeError, match="would lower 1 counts"):
            catalogue_build.records_write(found, {}, force)
        assert json.loads(g.read_text()) == {"092/092g/2016": 100}
    else:
        catalogue_build.records_write(found, {}, force)
        assert json.loads(g.read_text()) == found


def test_recording_refuses_any_fall_in_copc_pairs_without_force(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue_build, "GROUPS", str(tmp_path / "groups.json"))
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS_PATH", str(tmp_path / "pairs.json"))
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {"092/092g/2016": 100})
    with pytest.raises(RuntimeError, match="pairs.json"):
        catalogue_build.records_write({}, {"092/092g/2016": 99}, False)


def test_the_build_checks_groups_before_reading_anything(tmp_path, monkeypatch):
    objs = _listed(["092/092g/2016/pointcloud/a_2016.laz"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "groups_load", lambda path=None: {"092/092g/2016": 5})
    monkeypatch.setattr(catalogue_build, "copc_listing",
                        lambda: (_ for _ in ()).throw(AssertionError("read on")))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    with pytest.raises(RuntimeError, match="092/092g/2016: 1 of 5"):
        catalogue_build.main()


def test_item_link_hrefs_encode_only_the_space_stacs_decodes():
    assert catalogue_build.item_link_href("x-bc_1_2018 (2)") == f"{PATH_S3_STAC}/x-bc_1_2018%20(2).json"


def test_the_collection_links_every_item_and_spans_their_extent():
    a = item_create(PC, _header(), COLL)
    b = item_create(PC.replace("/2016/", "/2017/"), _header(), COLL)
    c = catalogue_build.collection_build([a, b])
    c.validate()
    d = c.to_dict(include_self_link=True)
    assert sorted(l["href"] for l in d["links"] if l["rel"] == "item") == \
        sorted(catalogue_build.item_link_href(i.id) for i in (a, b))
    interval = d["extent"]["temporal"]["interval"][0]
    # a: 2016 directory, 2017 filename -> the 2016 range; b: 2017 directory, agreeing day
    assert interval[0].startswith("2016-01-01") and interval[1].startswith("2017-07-13")
    json.dumps(d)


def test_keys_list_carries_the_etag_and_size():
    (o,) = keys_list("a/", session=_Session([_page(["a/1.laz"], False)]))
    assert o == {"url": f"{PATH_S3}/a/1.laz", "etag": "e-a/1.laz", "size": 7}


# =============================================================================
# The header cache and the build's refusal
# =============================================================================

def _objs(*etags):
    return [{"url": f"{PATH_S3}/092/092g/2016/pointcloud/f{i}.laz", "etag": e, "size": 1}
            for i, e in enumerate(etags)]


def _counting_reader(calls, fail=()):
    def read(url, session=None):
        calls.append(url)
        if url in fail:
            raise OSError("boom")
        return {"for": url, "header_version": laz_item.HEADER_VERSION}
    return read


def test_a_rerun_reads_only_what_is_missing(tmp_path):
    cache, calls = str(tmp_path / "h.jsonl"), []
    objs = _objs("a", "b")
    catalogue_build.headers_fetch(objs, cache, 2, reader=_counting_reader(calls))
    assert len(calls) == 2
    h, errors = catalogue_build.headers_fetch(objs, cache, 2, reader=_counting_reader(calls))
    assert len(calls) == 2 and not errors
    assert h == {o["url"]: {"for": o["url"], "header_version": laz_item.HEADER_VERSION}
                 for o in objs}


def test_a_redelivered_file_is_read_again(tmp_path):
    """Same key, new ETag: the cached header describes a file that no longer exists."""
    cache, calls = str(tmp_path / "h.jsonl"), []
    catalogue_build.headers_fetch(_objs("a"), cache, 1, reader=_counting_reader(calls))
    catalogue_build.headers_fetch(_objs("CHANGED"), cache, 1, reader=_counting_reader(calls))
    assert len(calls) == 2


def test_a_failed_read_is_reported_not_cached_and_retried(tmp_path):
    cache, calls = str(tmp_path / "h.jsonl"), []
    objs = _objs("a", "b")
    bad = objs[1]["url"]
    h, errors = catalogue_build.headers_fetch(objs, cache, 2, reader=_counting_reader(calls, {bad}))
    assert list(errors) == [bad] and bad not in h
    h, errors = catalogue_build.headers_fetch(objs, cache, 2, reader=_counting_reader(calls))
    assert not errors and calls.count(bad) == 2 and len(h) == 2


def test_a_truncated_last_cache_line_is_dropped_and_read_again(tmp_path):
    cache, calls = str(tmp_path / "h.jsonl"), []
    objs = _objs("a", "b")
    catalogue_build.headers_fetch(objs, cache, 1, reader=_counting_reader(calls))
    text = open(cache).read()
    open(cache, "w").write(text[: len(text) - 10])  # cut mid-record, as a kill would
    h, errors = catalogue_build.headers_fetch(objs, cache, 1, reader=_counting_reader(calls))
    assert not errors and len(h) == 2 and len(calls) == 3
    # and the file is whole again: every line parses
    assert all(json.loads(l) for l in open(cache).read().splitlines() if l)


def test_a_malformed_line_mid_cache_raises(tmp_path):
    cache = tmp_path / "h.jsonl"
    cache.write_text('{"url": "u", "etag": "a", "header": {}}\nnot json\n{"url": "v", "etag": "a", "header": {}}\n')
    with pytest.raises(json.JSONDecodeError):
        catalogue_build.headers_load(str(cache))


def test_the_build_refuses_when_any_header_failed(tmp_path, monkeypatch):
    """Publishing without one file would read as complete. Nothing is written."""
    objs = _objs("a", "b")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "header_read",
                        _counting_reader([], {objs[0]["url"]}))
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (catalogue_build.header_read,))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    assert catalogue_build.main() == 1
    assert not (tmp_path / "data/build/collection.json").exists()
    assert not (tmp_path / "data/build/items").exists()


def test_a_cached_header_of_an_older_shape_is_read_again(tmp_path):
    cache, calls = str(tmp_path / "h.jsonl"), []
    objs = _objs("a")
    with open(cache, "w") as fh:
        fh.write(json.dumps({"url": objs[0]["url"], "etag": "a",
                             "header": {"header_version": 1}}) + "\n")
    h, _ = catalogue_build.headers_fetch(objs, cache, 1, reader=_counting_reader(calls))
    assert calls == [objs[0]["url"]]
    assert h[objs[0]["url"]]["header_version"] == laz_item.HEADER_VERSION


# =============================================================================
# Round 3: the sheet check, delivery-level dates, EXCLUDE, --limit
# =============================================================================

@pytest.mark.parametrize("block, sheet, bounds", [
    ("082", "082e", (-120, 49, -118, 50)),   # Penticton
    ("092", "092h", (-122, 49, -120, 50)),   # Hope
    ("092", "092g", (-124, 49, -122, 50)),   # Vancouver
    ("082", "082l", (-120, 50, -118, 51)),   # Vernon
    ("082", "082k", (-118, 50, -116, 51)),
    ("092", "092j", (-124, 50, -122, 51)),
    ("082", "082a", (-114, 48, -112, 49)),   # the SE corner sheet of the block
    ("082", "082p", (-114, 51, -112, 52)),
])
def test_nts_sheet_bounds(block, sheet, bounds):
    assert laz_item.nts_sheet_bounds(block, sheet) == bounds


def test_a_box_in_the_wrong_utm_zone_is_refused():
    """UTM 11 coordinates labelled UTM 10: inside BC, but three sheets west of 082E."""
    with pytest.raises(ValueError, match="not in NTS sheet"):
        item_create(PC11, _header(CRS.from_epsg(3157).to_wkt(), **UTM11_BOX), COLL)


def test_an_untrusted_delivery_publishes_the_year_even_for_an_agreeing_token():
    """082k/2017: `_171015` agrees with its year, but its delivery also names files
    `_180827`, and GPS time does not support the 15th (review, 2026-10-07)."""
    got = date_parse("bc_082k016_3_3_3_xyes_8_utm11_171015.laz", 2017, trust_filename=False)
    assert "datetime" not in got and got["source"] == "path" and got["filename_date"] == "171015"


def test_a_delivery_with_any_disagreeing_date_is_untrusted_as_a_whole():
    k = f"{PATH_S3}/082/082k/2017/pointcloud/bc_082k016_3_3_3_xyes_8_utm11_"
    e = f"{PATH_S3}/082/082e/2018/pointcloud/bc_082e004_3_1_3_xyes_12_utm11_"
    urls = [k + "171015.laz", k + "180827.laz", e + "2018.laz"]
    assert catalogue_build.groups_with_untrusted_dates(urls) == {"082/082k/2017"}


def test_an_exclude_entry_whose_fault_is_gone_stops_the_build():
    u = next(iter(catalogue_build.EXCLUDE))
    assert catalogue_build.exclusions_check([u], {u: _header(mins=(0.0, 0.0, 0.0))}) == [u]
    with pytest.raises(RuntimeError, match="may have been fixed"):
        catalogue_build.exclusions_check([u], {u: _header(mins=(547410.0, 5441555.0, 2.0))})


def test_an_exclude_entry_fixed_outside_its_mins_stops_the_build():
    """092h011's fault is its maxs: a corrected re-delivery keeps the recorded mins."""
    (u,) = [k for k in catalogue_build.EXCLUDE if "092h011_1_2_2" in k]
    mins = tuple(catalogue_build.EXCLUDE[u]["mins"])
    broken = _header(mins=mins, maxs=(3263847.73, 5440545.01, 564.36))
    assert catalogue_build.exclusions_check([u], {u: broken}) == [u]
    fixed = _header(mins=mins, maxs=(579850.0, 5440545.01, 564.36))
    with pytest.raises(RuntimeError, match="now makes an item"):
        catalogue_build.exclusions_check([u], {u: fixed})


NO_CRS = f"{PATH_S3}/103/103h/2017/pointcloud/bc_103h039_1_1_1_xyes_17_utm09_20170806.laz"


def test_an_excluded_delivery_drops_every_file_and_nothing_else():
    hs = {NO_CRS: {**_header(None), "mins": [1.0, 1.0, 1.0]}, PC: _header()}
    assert catalogue_build.exclusions_check([NO_CRS, PC], hs) == [NO_CRS]


def test_an_excluded_delivery_whose_files_gain_a_crs_stops_the_build():
    with pytest.raises(RuntimeError, match="103/103h/2017 records no CRS, but 1 of its files"):
        catalogue_build.exclusions_check([NO_CRS], {NO_CRS: _header()})


def test_a_limited_build_never_writes_where_a_publish_reads(tmp_path, monkeypatch):
    objs = [{"url": PC, "etag": "a", "size": 1}, {"url": PC11, "etag": "b", "size": 1}]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    headers = {PC: _header(), PC11: _header(CRS.from_string("EPSG:2955+6647").to_wkt(), **UTM11_BOX)}
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (lambda u, session=None: headers[u],))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1", "--limit", "1"])
    assert catalogue_build.main() == 0
    assert (tmp_path / "data/build-limit/collection.json").exists()
    assert not (tmp_path / "data/build").exists()


def test_the_build_applies_delivery_distrust_to_every_file_in_it(tmp_path, monkeypatch):
    """Wiring, not just the helper: an agreeing `_171015` in a delivery that also names
    `_180827` must be published with the year range, end to end through main()."""
    k = f"{PATH_S3}/082/082k/2017/pointcloud/bc_082k016_3_3_3_xyes_8_utm11_"
    objs = [{"url": k + "171015.laz", "etag": "a", "size": 1},
            {"url": k.replace("016_3_3_3", "016_3_3_4") + "180827.laz", "etag": "b", "size": 1}]
    # a box in 082K (-118..-116, 50..51) in UTM 11
    box = dict(mins=(430000.0, 5560000.0, 1.0), maxs=(431800.0, 5561400.0, 2.0))
    h = _header(CRS.from_epsg(2955).to_wkt(), **box)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__", (lambda u, session=None: h,))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    assert catalogue_build.main() == 0
    agreeing = json.loads((tmp_path / "data/build/items" /
                           f"{url_to_item_id(objs[0]['url'])}.json").read_text())["properties"]
    assert "start_datetime" in agreeing and agreeing.get("datetime") is None
    assert agreeing["lidarbc:filename_date"] == "171015"


# =============================================================================
# CanElevation's COPC copy (#6)
# =============================================================================

CE_HREF = f"{laz_item.CANELEVATION}/pointclouds_nuagespoints/BC/Lower_Mainland_2016/" \
          "bc_092g019_1_4_1_xyes_8_utm10_20170713.copc.laz"


def _copc_header(crs_wkt=CRS.from_string("EPSG:3157+5703").to_wkt(), **kw):
    """The copy as header_read() returns it: LAS 1.4 format 6, the same points and box, its
    CRS a compound of the same horizontal (as the real copies carry, 2026-10-09)."""
    h = _header(crs_wkt, point_format=6, **kw)
    h.update(las_version="1.4", file_size=93_000_000)
    return h


def _add(copc_header, laz_header=None):
    laz_header = laz_header or _header()
    return laz_item.copc_asset_add(item_create(PC, laz_header, COLL), CE_HREF, copc_header,
                                   laz_header)


def test_a_copc_copy_is_a_second_asset_and_the_laz_stays_the_source():
    it = _add(_copc_header())
    it.validate()
    d = it.to_dict(include_self_link=False)
    copc = d["assets"][laz_item.ASSET_COPC]
    assert copc["href"] == CE_HREF and copc["href"].startswith("https://")
    assert copc["type"] == "application/vnd.laszip+copc"
    assert copc["file:size"] == 93_000_000 and copc["roles"] == ["data"]
    # the copy's own format, since the item's pc:schemas describe the LAZ
    assert copc["las:version"] == "1.4" and copc["las:point_format"] == 6
    assert d["properties"]["las:version"] == "1.2"
    assert d["assets"][ASSET_LAZ] == item_create(PC, _header(), COLL).to_dict(
        include_self_link=False)["assets"][ASSET_LAZ]


@pytest.mark.parametrize("kw, why", [
    ({"point_count": 999}, "999 points"),
    # x, y and z: a sub-metre horizontal shift is what a re-realised datum looks like
    ({"mins": (547410.6, 5441555.91, 2.2)}, "0.15 m from"),
    ({"maxs": (549246.4, 5442961.2, 100.49)}, "0.22 m from"),
    ({"maxs": (549246.4, 5442961.42, 100.79)}, "0.30 m from"),
    ({"crs_wkt": CRS.from_epsg(2955).to_wkt()}, "horizontal CRS"),
    ({"crs_wkt": None}, "horizontal CRS"),
])
def test_a_copc_that_is_not_the_same_points_is_refused(kw, why):
    h = _copc_header(**{k: v for k, v in kw.items() if k != "point_count"})
    h["point_count"] = kw.get("point_count", h["point_count"])
    with pytest.raises(ValueError, match=why):
        _add(h)


def test_a_copc_box_off_by_the_scale_rounding_is_a_copy():
    """0.01 m: the largest offset over all 1,964 real pairs (2026-10-09)."""
    h = _copc_header(mins=(547410.46, 5441555.90, 2.21))
    assert "copc" in _add(h).assets


def test_a_second_copc_on_one_item_is_refused():
    it = _add(_copc_header())
    with pytest.raises(ValueError, match="already has"):
        laz_item.copc_asset_add(it, CE_HREF, _copc_header(), _header())


def _page2(keys, token):
    ns = 'xmlns="http://s3.amazonaws.com/doc/2006-03-01/"'
    body = "".join(f'<Contents><Key>{k}</Key><ETag>&quot;e-{k}-7&quot;</ETag><Size>9</Size></Contents>'
                   for k in keys)
    tok = f"<NextContinuationToken>{token}</NextContinuationToken>" if token else ""
    trunc = "true" if token is not None else "false"
    return f'<ListBucketResult {ns}><IsTruncated>{trunc}</IsTruncated>{tok}{body}</ListBucketResult>'


class _Session2(_Session):
    """Records the continuation token of each request, where _Session records the marker."""
    def get(self, url, params=None, timeout=None):
        return super().get(url, {"marker": params.get("continuation-token")}, timeout)


def test_canelevation_keys_list_pages_by_token_and_carries_etag_and_size():
    s = _Session2([_page2(["p/1.copc.laz", "p/2.copc.laz"], "T1"), _page2(["p/3.copc.laz"], None)])
    objs = laz_item.canelevation_keys_list("p/", session=s)
    assert [o["url"] for o in objs] == [f"{laz_item.CANELEVATION}/p/{i}.copc.laz" for i in (1, 2, 3)]
    assert objs[0]["etag"] == "e-p/1.copc.laz-7" and objs[0]["size"] == 9
    assert s.markers == [None, "T1"]


def test_a_canelevation_page_truncated_with_no_token_raises():
    s = _Session2([_page2(["p/1.copc.laz"], "")])
    with pytest.raises(OSError, match="no continuation token"):
        laz_item.canelevation_keys_list("p/", session=s)


def test_a_failed_canelevation_listing_raises_rather_than_reading_as_empty():
    with pytest.raises(OSError, match="returned 403"):
        laz_item.canelevation_keys_list("p/", session=_Session2([""], status=403))


def _ce(name, etag="c"):
    return {"url": f"{laz_item.CANELEVATION}/pointclouds_nuagespoints/BC/P/{name}",
            "etag": etag, "size": 1}


def test_the_build_refuses_a_canelevation_project_listed_short(monkeypatch):
    def short(prefix, session=None):
        n = 10 if "Lower_Mainland_2016" in prefix else 9000
        return [_ce(f"f{i}.copc.laz") for i in range(n)]
    monkeypatch.setattr(catalogue_build, "canelevation_keys_list", short)
    with pytest.raises(RuntimeError, match="Lower_Mainland_2016: 10 .laz"):
        catalogue_build.copc_listing()


def test_copc_pairs_match_by_name_without_copc_or_laz():
    other = PC.replace("019_1_4_1", "019_1_4_2")
    pairs = catalogue_build.copc_pairs([PC, other], [_ce(PC.rsplit("/", 1)[1].replace(".laz", ".copc.laz"))])
    assert list(pairs) == [PC]


def test_a_duplicate_name_nothing_in_the_build_matches_is_not_its_business():
    dup = [_ce("bc_999x001_1_1_1.copc.laz"), _ce("bc_999x001_1_1_1.laz")]
    assert catalogue_build.copc_pairs([PC], dup) == {}


@pytest.mark.parametrize("urls, copc, why", [
    ([PC], [_ce("bc_092g019_1_4_1_xyes_8_utm10_20170713.copc.laz"),
            _ce("bc_092g019_1_4_1_xyes_8_utm10_20170713.laz")], "two CanElevation files"),
    ([PC, PC.replace("/2016/", "/2017/")], [_ce("bc_092g019_1_4_1_xyes_8_utm10_20170713.copc.laz")],
     "two LidarBC files"),
])
def test_a_name_held_by_two_files_fails_the_build(urls, copc, why):
    with pytest.raises(RuntimeError, match=why):
        catalogue_build.copc_pairs(urls, copc)


def _main_with_copc(tmp_path, monkeypatch, copc_header):
    """main() over one LidarBC file whose CanElevation copy has `copc_header`
    (an exception to raise it as a failed read)."""
    objs = [{"url": PC, "etag": "a", "size": 1}]
    ce = _ce("bc_092g019_1_4_1_xyes_8_utm10_20170713.copc.laz")

    def read(u, session=None):
        if u == PC:
            return _header()
        if isinstance(copc_header, Exception):
            raise copc_header
        return copc_header
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [ce])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {"092/092g/2016": 1})
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__", (read,))
    monkeypatch.setattr(catalogue_build, "item_probe", _sample({1: 400, 2: 600}))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    return catalogue_build.main(), ce


def test_the_build_carries_the_copc_copy_on_its_item(tmp_path, monkeypatch):
    rc, ce = _main_with_copc(tmp_path, monkeypatch, _copc_header())
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert d["assets"]["copc"]["href"] == ce["url"] and d["assets"][ASSET_LAZ]["href"] == PC
    c = json.loads((tmp_path / "data/build/collection.json").read_text())
    assert "Natural Resources Canada" in [p["name"] for p in c["providers"]]
    assert "Lower_Mainland_2016" in c["description"]


def test_the_build_samples_again_an_item_sampled_before_its_copc_was_paired(tmp_path,
                                                                             monkeypatch):
    """A ground-only sample of the laz alone, at the current ETag: taken before the pair, it
    is another item's sample, so the build samples again (with the COPC) and goes by that."""
    os.makedirs(tmp_path / "data/build")
    (tmp_path / "data/build" / catalogue_build.CLASSES_SAMPLE).write_text(
        json.dumps({**_rec(url_to_item_id(PC), {"2": 1000}), "laz": PC}) + "\n")
    rc, ce = _main_with_copc(tmp_path, monkeypatch, _copc_header())
    assert rc == 0  # the new sample is mixed: nothing to read whole
    last = (tmp_path / "data/build" / catalogue_build.CLASSES_SAMPLE).read_text().splitlines()
    assert json.loads(last[-1])["copc"] == ce["url"]


def test_the_build_refuses_when_a_copc_header_failed(tmp_path, monkeypatch):
    rc, _ = _main_with_copc(tmp_path, monkeypatch, OSError("boom"))
    assert rc == 1
    assert not (tmp_path / "data/build/items").exists()


def test_the_build_reports_every_copc_that_is_not_a_copy_then_refuses(tmp_path, monkeypatch,
                                                                         caplog):
    h = _copc_header()
    h["point_count"] = 7
    rc, _ = _main_with_copc(tmp_path, monkeypatch, h)
    assert rc == 1
    assert "1 of 1 CanElevation name matches are not copies" in caplog.text
    assert "7 points" in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def _record_not_copy(monkeypatch, copc_points, laz_points=1000):
    ce = _ce("bc_092g019_1_4_1_xyes_8_utm10_20170713.copc.laz")
    monkeypatch.setattr(catalogue_build, "COPC_NOT_COPIES", {ce["url"]: {
        "item": url_to_item_id(PC), "copc_points": copc_points, "laz_points": laz_points}})


def test_a_recorded_non_copy_is_left_unlinked_and_the_build_passes(tmp_path, monkeypatch, caplog):
    _record_not_copy(monkeypatch, 7)
    h = _copc_header()
    h["point_count"] = 7
    rc, ce = _main_with_copc(tmp_path, monkeypatch, h)
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert "copc" not in d["assets"]
    assert f"not linked, recorded in copc_not_copies.json: {ce['url']}" in caplog.text
    # nor sampled for classes: the class step reads an item's COPC where it has one
    (t,) = [json.loads(x) for x in (tmp_path / "data/build" / catalogue_build.CLASS_TARGETS)
            .read_text().splitlines()]
    assert t["copc"] is None


def test_a_recorded_non_copy_whose_counts_moved_stops_the_build(tmp_path, monkeypatch):
    _record_not_copy(monkeypatch, 7)
    h = _copc_header()
    h["point_count"] = 8
    with pytest.raises(RuntimeError, match="records .* with 7 points against the LAZ's 1000"):
        _main_with_copc(tmp_path, monkeypatch, h)


def test_the_recorded_non_copies_are_named_and_counted_as_found():
    assert len(catalogue_build.COPC_NOT_COPIES) == 26
    for url, rec in catalogue_build.COPC_NOT_COPIES.items():
        assert "/Vancouver_Island_Sunshine_Coast_2018/" in url
        assert rec["copc_points"] < rec["laz_points"]
        assert rec["item"].endswith("-pointcloud-" + url.rsplit("/", 1)[1][:-len(".copc.laz")])


def test_a_group_that_pairs_short_fails_the_build(monkeypatch):
    """A rename on either side passes every listing floor and pairs nothing."""
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {"082/082e/2019": 332, "082/082l/2019": 57,
                                                        "092/092g/2016": 1155, "092/092h/2016": 420})
    base = f"{PATH_S3}/092/092g/2016/pointcloud/"
    full = {f"{base}f{i}.laz": {} for i in range(1155)}
    other = {f"{PATH_S3}/{g}/pointcloud/f{i}.laz": {}
             for g, n in catalogue_build.COPC_PAIRS.items() if g != "092/092g/2016"
             for i in range(n)}
    catalogue_build.copc_pairs_check(full | other)
    short = dict(list(full.items())[:1154]) | other
    with pytest.raises(RuntimeError, match="092/092g/2016: 1154 items paired"):
        catalogue_build.copc_pairs_check(short)
    extra = full | other | {f"{base}extra.laz": {}}
    with pytest.raises(RuntimeError, match="092/092g/2016: 1156 items paired"):
        catalogue_build.copc_pairs_check(extra)
    unrecorded = full | other | {f"{PATH_S3}/082/082f/2018/pointcloud/f.laz": {}}
    with pytest.raises(RuntimeError, match=r"not in copc_pairs.json: 082/082f/2018 \(1\)"):
        catalogue_build.copc_pairs_check(unrecorded)


def test_the_build_checks_the_pair_count_before_writing(tmp_path, monkeypatch):
    """Wiring: a full build whose copies vanished (renamed) stops in main()."""
    objs = [{"url": PC, "etag": "a", "size": 1}]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [_ce("renamed.copc.laz")])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {"092/092g/2016": 1})
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (lambda u, session=None: _header(),))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    with pytest.raises(RuntimeError, match="0 items paired"):
        catalogue_build.main()
    assert not (tmp_path / "data/build/items").exists()


# =============================================================================
# Whole-file class reads (#10)
# =============================================================================

def _full(classes, n=None, las_version="1.2", etag="a"):
    """A record as laz_classes_probe.laz_full() returns it."""
    n = sum(classes.values()) if n is None else n
    return {"etag": etag, "point_count": n, "points_read": sum(classes.values()),
            "classes": {str(k): v for k, v in classes.items()}, "las_version": las_version}


def test_a_whole_file_read_lists_every_class_with_its_count_on_the_laz_asset():
    it = laz_item.classes_add(item_create(PC, _header(), COLL), _full({1: 400, 2: 600}))
    it.validate()
    d = it.to_dict(include_self_link=False)
    assert d["assets"][ASSET_LAZ]["classification:classes"] == [
        {"value": 1, "name": "unclassified", "count": 400},
        {"value": 2, "name": "ground", "count": 600}]
    assert any("classification" in e for e in d["stac_extensions"])


@pytest.mark.parametrize("full, why", [
    (_full({2: 999}), "covers 999 of 999 points, the header 1000"),
    (_full({2: 999}, n=1000), "covers 999 of 1000"),  # a read that stopped short
    (_full({2: 1000}, las_version="1.4"), "LAS 1.4, the header 1.2"),
])
def test_a_class_read_of_other_points_is_refused(full, why):
    with pytest.raises(ValueError, match=why):
        laz_item.classes_add(item_create(PC, _header(), COLL), full)


@pytest.mark.parametrize("value, version, name", [
    (8, "1.2", "model_key_point"), (12, "1.3", "overlap"),
    (8, "1.4", "class_8"), (30, "1.4", "class_30"), (0, "1.2", "never_classified"),
])
def test_class_names_follow_the_las_version(value, version, name):
    assert laz_item.asprs_class_name(value, version) == name


def test_a_class_read_applies_only_to_the_file_it_was_read_from():
    other = PC.replace("019_1_4_1", "019_1_4_2")
    items = {PC: item_create(PC, _header(), COLL)}
    records = {
        PC: {"laz": PC, "full": _full({2: 1000}, etag="old")},
        other: {"laz": other, "full": _full({2: 1000})},
    }
    problems = catalogue_build.classes_attach(items, {PC: "new"}, records)
    # A read of a file not in the build is not applied, and not a problem here:
    # classes_check decides what must have been read.
    assert "re-delivered" in problems[PC] and other not in problems
    assert "classification:classes" not in items[PC].assets[ASSET_LAZ].extra_fields
    failed = {PC: {"id": url_to_item_id(PC), "laz": PC, "error": "OSError: 503"}}
    assert "failed" in catalogue_build.classes_attach(items, {PC: "a"}, failed)[PC]


def _main_with_classes(tmp_path, monkeypatch, records, sampled=None, full_probe=None):
    """main() over PC with `records` already in the whole-read cache; its sample holds
    `sampled` (ground only, which flags it, by default) and a whole read returns `full_probe`'s
    record (refused by default)."""
    objs = [{"url": PC, "etag": "a", "size": 1}]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build, "item_probe", _sample(sampled or {2: 1000}))
    if full_probe:
        monkeypatch.setattr(catalogue_build, "full_probe", full_probe)
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (lambda u, session=None: _header(),))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    os.makedirs("data/build", exist_ok=True)
    with open(f"data/build/{catalogue_build.CLASSES_FULL}", "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return catalogue_build.main()


def _whole(classes, etag="a"):
    def probe(item, session=None):
        return {"id": item["id"], "laz": PC, "full": _full(classes, etag=etag)}
    return probe


def _fails(item, session=None):
    raise OSError("503")


def test_the_build_lists_the_classes_of_a_file_read_whole(tmp_path, monkeypatch):
    rc = _main_with_classes(tmp_path, monkeypatch,
                            [{"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000})}])
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert d["assets"][ASSET_LAZ]["classification:classes"] == [
        {"value": 2, "name": "ground", "count": 1000}]
    c = json.loads((tmp_path / "data/build/collection.json").read_text())
    assert "classification:classes" in c["description"]
    # Every file is sampled (#17): the description names no screen and no one-off audit.
    assert "percentile" not in c["description"] and "lowest" not in c["description"]
    assert "random 5%" not in c["description"]
    assert "every file" in c["description"]
    # Stated in the direction the flags make true (code-check #17 round 1): a first chunk of
    # ground alone flags a file whose other chunks hold class 1, so it is the item WITHOUT a
    # list that is known to hold ground and another class.
    assert "an item without a list holds ground" in c["description"]


def test_the_build_samples_then_reads_whole_what_the_sample_flags(tmp_path, monkeypatch):
    """A fresh checkout: no cache at all. The build samples, the sample flags, it reads whole."""
    rc = _main_with_classes(tmp_path, monkeypatch, [], full_probe=_whole({2: 1000}))
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert d["assets"][ASSET_LAZ]["classification:classes"][0]["count"] == 1000
    assert (tmp_path / "data/build" / catalogue_build.CLASSES_SAMPLE).exists()


def test_a_mixed_sample_reads_nothing_whole_and_lists_nothing(tmp_path, monkeypatch):
    assert _main_with_classes(tmp_path, monkeypatch, [], sampled={1: 5, 2: 5}) == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert "classification:classes" not in d["assets"][ASSET_LAZ]


def test_a_flagged_file_whose_whole_read_fails_is_refused(tmp_path, monkeypatch, caplog):
    rc = _main_with_classes(tmp_path, monkeypatch, [], full_probe=_fails)
    assert rc == 1
    assert "flagged by its sample, with no whole-file read at the current ETag" in caplog.text
    assert "OSError: 503" in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def test_a_file_whose_sample_fails_is_refused(tmp_path, monkeypatch, caplog):
    assert _main_with_classes(tmp_path, monkeypatch, [], sampled={1: 5, 2: 5}) == 0
    monkeypatch.setattr(catalogue_build, "item_probe", _fails)
    (tmp_path / "data/build" / catalogue_build.CLASSES_SAMPLE).unlink()
    assert catalogue_build.main() == 1
    assert "no point sample at the current ETag and COPC (OSError: 503)" in caplog.text


def test_a_stale_whole_read_is_read_again(tmp_path, monkeypatch):
    stale = {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 7}, etag="old")}
    rc = _main_with_classes(tmp_path, monkeypatch, [stale], full_probe=_whole({2: 1000}))
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert d["assets"][ASSET_LAZ]["classification:classes"][0]["count"] == 1000


def test_a_stale_whole_read_that_cannot_be_redone_is_refused(tmp_path, monkeypatch, caplog):
    stale = {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000}, etag="old")}
    assert _main_with_classes(tmp_path, monkeypatch, [stale], full_probe=_fails) == 1
    assert not (tmp_path / "data/build/items").exists()


def test_a_read_its_current_sample_does_not_flag_is_refused_until_recorded(
        tmp_path, monkeypatch, caplog):
    """A good whole read of a file whose sample no longer flags it (from a research --confirm,
    say): an empty data/build would not publish its list, so it must be recorded."""
    read = {"id": url_to_item_id(PC), "laz": PC, "full": _full({1: 600, 2: 400})}
    assert _main_with_classes(tmp_path, monkeypatch, [read], sampled={1: 5, 2: 5}) == 1
    assert "its sample does not flag it, and it is not recorded" in caplog.text


def test_a_stale_read_of_a_file_its_new_sample_does_not_flag_is_neither_read_nor_applied(
        tmp_path, monkeypatch):
    """Re-delivered (#4), and the new sample does not flag it: as from an empty data/build,
    no whole read and no list."""
    stale = {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000}, etag="old")}
    rc = _main_with_classes(tmp_path, monkeypatch, [stale], sampled={1: 5, 2: 5},
                            full_probe=_fails)
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert "classification:classes" not in d["assets"][ASSET_LAZ]
    assert len((tmp_path / "data/build" / catalogue_build.CLASSES_FULL).read_text()
               .splitlines()) == 1  # nothing read


def test_a_sample_taken_with_another_copc_is_not_good_and_is_taken_again(tmp_path):
    """A sample's flags count its COPC's classes, so a pair added or dropped since makes it
    another item's sample."""
    import laz_classes_probe as lcp
    rec = _rec("A", {"1": 5, "2": 5})
    assert lcp.sample_good(rec, {"A": "a"}, {"A": None})
    assert not lcp.sample_good(rec, {"A": "a"}, {"A": "https://c/A.copc.laz"})
    assert not lcp.sample_good({**rec, "copc": "https://c/A.copc.laz"}, {"A": "a"}, {"A": None})
    assert lcp.sample_good(rec, {"A": "a"}, None)  # whole reads take no COPC
    out = tmp_path / "classes.jsonl"
    out.write_text(json.dumps(rec) + "\n")
    item = {"id": "A", "assets": {"laz": {"href": PC}, "copc": {"href": "https://c/A.copc.laz"}}}
    probed = []

    def probe(i, session=None):
        probed.append(i["id"])
        return {**_rec(i["id"], {"2": 5}), "copc": i["assets"]["copc"]["href"]}
    lcp.probe_all([item], str(out), 1, probe=probe, current={"A": "a"})
    assert probed == []  # laz ETag alone: the whole-read rule
    lcp.probe_all([item], str(out), 1, probe=probe, current={"A": "a"}, match_copc=True)
    assert probed == ["A"]
    p = catalogue_build.classes_check({PC}, {PC: "A"}, {"A": "a"}, {"A": rec}, {}, [],
                                      copc={"A": "https://c/A.copc.laz"})
    assert "no point sample at the current ETag and COPC" in p[PC]


def test_a_failed_whole_read_is_retried_on_the_next_run(tmp_path, monkeypatch, caplog):
    err = {"id": url_to_item_id(PC), "error": "OSError: 503", "laz": PC}
    assert _main_with_classes(tmp_path, monkeypatch, [err], full_probe=_fails) == 1
    assert _main_with_classes(tmp_path, monkeypatch, [err], full_probe=_whole({2: 1000})) == 0


def test_a_class_read_of_a_file_that_left_the_build_is_not_applied(tmp_path, monkeypatch,
                                                                   caplog):
    gone = PC.replace("019_1_4_1", "019_1_4_2")
    recs = [{"id": url_to_item_id(gone), "laz": gone, "full": _full({2: 1000})}]
    assert _main_with_classes(tmp_path, monkeypatch, recs, sampled={1: 5, 2: 5}) == 0
    assert "not in this build, not applied" in caplog.text


def test_a_class_cache_cut_off_mid_write_is_repaired_not_fatal(tmp_path, monkeypatch):
    good = {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000})}
    assert _main_with_classes(tmp_path, monkeypatch, [good]) == 0
    for f in (catalogue_build.CLASSES_FULL, catalogue_build.CLASSES_SAMPLE):
        with open(tmp_path / "data/build" / f, "a") as fh:
            fh.write('{"id": "x", "laz": "https://x')  # a read killed mid-line
    assert catalogue_build.main() == 0


def _rec(k, classes, etag="a"):
    return {"id": k, "laz_sample": {"etag": etag, "samples": {"all": classes}}}


def test_classes_check_requires_a_whole_read_for_every_flagged_sample_screened_or_not():
    """An audit or #10 sample outside the screen that flags still needs its whole read."""
    a, b = PC, PC.replace("019_1_4_1", "019_1_4_2")
    ids = {a: "A", b: "B"}
    cur = {"A": "a", "B": "a"}
    samples = {"A": _rec("A", {"1": 5, "2": 5}), "B": _rec("B", {"1": 5})}
    p = catalogue_build.classes_check({a}, ids, cur, samples, {}, ["B"])
    assert list(p) == [b] and "flagged by its sample" in p[b]
    full = {"B": {"id": "B", "full": _full({1: 5})}}
    assert catalogue_build.classes_check({a}, ids, cur, samples, full, ["B"]) == {}
    # and outside the screen it must be in the committed list, or the class list it earns
    # would exist only where this sample is cached
    p = catalogue_build.classes_check({a}, ids, cur, samples, full, [])
    assert list(p) == [b] and "record it with --classes-record" in p[b]


def test_classes_check_requires_a_whole_read_of_every_required_file():
    a, b = PC, PC.replace("019_1_4_1", "019_1_4_2")
    ids, cur = {a: "A", b: "B"}, {"A": "a", "B": "a"}
    samples = {"A": _rec("A", {"1": 5, "2": 5})}  # B never sampled: a fresh cache
    p = catalogue_build.classes_check({a}, ids, cur, samples, {}, ["B", "not-in-this-build"])
    assert list(p) == [b] and "classes_required.json, with no whole-file read" in p[b]
    full = {"B": {"id": "B", "full": _full({1: 5})}}
    assert catalogue_build.classes_check({a}, ids, cur, samples, full, ["B"]) == {}


def test_classes_check_requires_every_whole_read_its_sample_does_not_flag_to_be_recorded():
    """A whole read the build publishes with no current sample flagging it
    (the #10 survey's samples carry no ETag): unrecorded, its list would live only in the cache.
    Not checked under --limit, a slice of the build."""
    a, b = PC, PC.replace("019_1_4_1", "019_1_4_2")
    ids, cur = {a: "A", b: "B"}, {"A": "a", "B": "a"}
    samples = {"A": _rec("A", {"1": 5, "2": 5})}
    full = {"B": {"id": "B", "full": _full({1: 5, 2: 5})}}
    p = catalogue_build.classes_check({a}, ids, cur, samples, full, [])
    assert list(p) == [b] and "its sample does not flag it, and it is not recorded" in p[b]
    assert catalogue_build.classes_check({a}, ids, cur, samples, full, ["B"]) == {}
    assert catalogue_build.classes_check({a}, ids, cur, samples, full, [], unrecorded=False) == {}


@pytest.mark.parametrize("sample, why", [
    (None, "no point sample"), (_rec("A", {"1": 5, "2": 5}, etag="old"), "no point sample"),
    ({"id": "A", "error": "OSError: x"}, "(OSError: x)")])
def test_classes_check_requires_a_current_sample_of_every_screened_file(sample, why):
    samples = {"A": sample} if sample else {}
    p = catalogue_build.classes_check({PC}, {PC: "A"}, {"A": "a"}, samples, {}, [])
    assert why in p[PC]


# Eleven files of one delivery, PC the densest: the two least dense are in the research screen
# (density_screen), and the build samples all eleven (#17).
GROUP11 = [PC] + [PC.replace("019_1_4_1", f"019_{a}_{b}_1") for a, b in
                  ((1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3), (4, 4))]


def _main_with_required(tmp_path, monkeypatch, required, cached_samples=(), argv=(),
                        cached_full=(), build="data/build", full_probe=None, item_probe=None):
    """main() over GROUP11 with `required` as data/classes_required.json and only
    `cached_samples` in the sample cache; every sample is mixed (unless `item_probe`), every
    whole read of PC is ground and vegetation. PC is the group's densest file."""
    objs = [{"url": u, "etag": "a", "size": 1} for u in GROUP11]
    monkeypatch.chdir(tmp_path)
    req = tmp_path / "classes_required.json"
    req.write_text(json.dumps(required))
    monkeypatch.setattr(catalogue_build, "CLASSES_REQUIRED_PATH", str(req))
    monkeypatch.setattr(catalogue_build, "CLASSES_REQUIRED", required)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build, "item_probe", item_probe or _sample({1: 5, 2: 5}))
    monkeypatch.setattr(catalogue_build, "full_probe", full_probe or _whole({1: 600, 2: 400}))

    def header(u, session=None):
        h = _header()
        h["point_count"] = 1000 if u == PC else 10 + GROUP11.index(u)
        return h
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__", (header,))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1", *argv])
    os.makedirs(build, exist_ok=True)
    with open(f"{build}/{catalogue_build.CLASSES_SAMPLE}", "w") as fh:
        for r in cached_samples:
            fh.write(json.dumps(r) + "\n")
    with open(f"{build}/{catalogue_build.CLASSES_FULL}", "w") as fh:
        for r in cached_full:
            fh.write(json.dumps(r) + "\n")
    return catalogue_build.main(), req


def test_a_required_file_outside_the_screen_is_read_whole_from_a_fresh_cache(tmp_path,
                                                                            monkeypatch):
    rc, _ = _main_with_required(tmp_path, monkeypatch, [url_to_item_id(PC)])
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert [c["value"] for c in d["assets"][ASSET_LAZ]["classification:classes"]] == [1, 2]


def _sample_except(special, default=None):
    """A point-sample probe: `special` (laz url -> classes, or an exception to raise) for the
    files it names, `default` (mixed) for the rest."""
    def probe(item, session=None):
        u = urllib.parse.unquote(item["assets"]["laz"]["href"])
        got = special.get(u, default or {1: 5, 2: 5})
        if isinstance(got, Exception):
            raise got
        return _sample(got)(item, session)
    return probe


def test_the_build_samples_every_file_whatever_its_density(tmp_path, monkeypatch):
    """PC is the densest of its group, far outside the research screen; its sample has no
    ground, so it is read whole and listed, with nothing to record (#17)."""
    rc, req = _main_with_required(tmp_path, monkeypatch, [],
                                  item_probe=_sample_except({PC: {1: 1000}}),
                                  full_probe=_whole({1: 1000}))
    assert rc == 0 and json.loads(req.read_text()) == []
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert [c["value"] for c in d["assets"][ASSET_LAZ]["classification:classes"]] == [1]
    import laz_classes_probe as lcp
    sampled = lcp.records_load(str(tmp_path / "data/build" / catalogue_build.CLASSES_SAMPLE))
    assert set(sampled) == {url_to_item_id(u) for u in GROUP11}


def test_a_dense_file_with_no_sample_is_refused(tmp_path, monkeypatch, caplog):
    rc, _ = _main_with_required(tmp_path, monkeypatch, [],
                                item_probe=_sample_except({PC: OSError("503")}))
    assert rc == 1 and "no point sample at the current ETag and COPC (OSError: 503)" in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def test_a_flag_once_outside_the_screen_is_derived_and_classes_record_drops_it_forced(
        tmp_path, monkeypatch):
    """The 5% audit's flags were recorded because the screen could not derive them. Every file
    sampled, they are derived, and --force drops them from the committed list."""
    pc = url_to_item_id(PC)
    probe = _sample_except({PC: {2: 1000}})  # ground only: flags
    rc, req = _main_with_required(tmp_path, monkeypatch, [pc], item_probe=probe,
                                  argv=["--classes-record", "--force"])
    assert rc == 0 and json.loads(req.read_text()) == []
    rc, req = _main_with_required(tmp_path, monkeypatch, [], item_probe=probe)
    assert rc == 0


UNREADABLE = {PC: {"reason": "lazrs cannot read its chunk table. Found 2026-10-11 (#2).",
                   "error": "no chunks available in chunk table", "etag": "a"}}
CHUNKS = OSError("LazrsError: IoError: no chunks available in chunk table")


def test_a_file_the_sampler_cannot_read_is_named_and_left_without_a_list(tmp_path, monkeypatch,
                                                                         caplog):
    monkeypatch.setattr(catalogue_build, "CLASSES_UNREADABLE", UNREADABLE)
    rc, _ = _main_with_required(tmp_path, monkeypatch, [],
                                item_probe=_sample_except({PC: CHUNKS}))
    assert rc == 0 and "not sampled, by CLASSES_UNREADABLE" in caplog.text
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert "classification:classes" not in d["assets"][ASSET_LAZ]


@pytest.mark.parametrize("probe, etag, why", [
    ({}, "a", "now samples"),  # mixed: the entry no longer applies
    ({PC: OSError("503")}, "a", "fails otherwise (OSError: 503)"),
    ({PC: CHUNKS}, "old", "re-delivered"),  # the fault was seen in another copy of the file
    ({PC: {2: 1000}}, "a", "now samples"),  # reads and flags: the carve-out's advice must show
])
def test_a_classes_unreadable_entry_that_no_longer_shows_its_fault_is_refused(
        tmp_path, monkeypatch, caplog, probe, etag, why):
    monkeypatch.setattr(catalogue_build, "CLASSES_UNREADABLE", {PC: {**UNREADABLE[PC],
                                                                     "etag": etag}})
    rc, _ = _main_with_required(tmp_path, monkeypatch, [], item_probe=_sample_except(probe))
    assert rc == 1 and why in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def test_an_empty_point_sample_is_refused_not_passed(tmp_path, monkeypatch, caplog):
    """No points says nothing about classes: an item without a list would claim ground and
    another class it was never seen to hold."""
    rc, _ = _main_with_required(tmp_path, monkeypatch, [], item_probe=_sample_except({PC: {}}))
    assert rc == 1 and "its point sample holds no points" in caplog.text


def test_a_classes_unreadable_entry_for_a_file_not_in_the_build_is_refused(tmp_path,
                                                                          monkeypatch, caplog):
    gone = PC.replace("019_1_4_1", "019_4_4_4")
    monkeypatch.setattr(catalogue_build, "CLASSES_UNREADABLE", {gone: UNREADABLE[PC]})
    rc, _ = _main_with_required(tmp_path, monkeypatch, [])
    assert rc == 1 and "names a file not in this build" in caplog.text
    rc, _ = _main_with_required(tmp_path, monkeypatch, [], argv=["--limit", "11"],
                                build="data/build-limit")
    assert rc == 0  # a slice leaves most files out


def test_a_whole_read_its_sample_does_not_flag_must_be_recorded_and_classes_record_records_it(
        tmp_path, monkeypatch, caplog):
    read = {"id": url_to_item_id(PC), "laz": PC, "full": _full({1: 600, 2: 400})}
    rc, req = _main_with_required(tmp_path, monkeypatch, [], cached_full=[read])
    assert rc == 1 and "its sample does not flag it, and it is not recorded" in caplog.text
    rc, req = _main_with_required(tmp_path, monkeypatch, [], argv=["--classes-record"],
                                  cached_full=[read])
    assert rc == 0 and json.loads(req.read_text()) == [url_to_item_id(PC)]


def test_classes_record_records_a_low_density_read_its_sample_does_not_flag(tmp_path,
                                                                             monkeypatch, caplog):
    low = GROUP11[1]  # among the two least dense, and its sample is mixed
    read = {"id": url_to_item_id(low), "laz": low, "full": _full({1: 6, 2: 5})}  # 11 points
    rc, req = _main_with_required(tmp_path, monkeypatch, [], cached_full=[read])
    assert rc == 1 and "its sample does not flag it, and it is not recorded" in caplog.text
    rc, req = _main_with_required(tmp_path, monkeypatch, [], argv=["--classes-record"],
                                  cached_full=[read])
    assert rc == 0 and json.loads(req.read_text()) == [url_to_item_id(low)]


def test_classes_record_keeps_a_recorded_id_this_cache_cannot_support_unless_forced(
        tmp_path, monkeypatch):
    """A fresh cache has no sample and no read of PC: recording reads PC whole first (it is
    required), so it keeps PC even forced; only an id no longer listed can be dropped."""
    pc = url_to_item_id(PC)
    rc, req = _main_with_required(tmp_path, monkeypatch, [pc, "gone"], argv=["--classes-record"])
    assert rc == 0 and json.loads(req.read_text()) == sorted([pc, "gone"])
    rc, req = _main_with_required(tmp_path, monkeypatch, [pc, "gone"],
                                  argv=["--classes-record", "--force"])
    assert rc == 0 and json.loads(req.read_text()) == [pc]


def test_a_limit_build_does_not_require_recording_against_its_partial_screen(tmp_path,
                                                                            monkeypatch):
    read = {"id": url_to_item_id(PC), "laz": PC, "full": _full({1: 600, 2: 400})}
    rc, _ = _main_with_required(tmp_path, monkeypatch, [], argv=["--limit", "11"],
                                cached_full=[read], build="data/build-limit")
    assert rc == 0


def test_classes_record_force_keeps_a_listed_id_whose_read_failed_and_refuses(tmp_path,
                                                                              monkeypatch):
    """--force drops only ids no longer listed or now derived: a 503 on a required file's
    read must not drop it and pass with no list."""
    pc = url_to_item_id(PC)
    rc, req = _main_with_required(tmp_path, monkeypatch, [pc],
                                  argv=["--classes-record", "--force"], full_probe=_fails)
    assert rc == 1 and json.loads(req.read_text()) == [pc]


def test_the_probe_carries_a_copc_href_encoded_as_the_build_item_does(tmp_path):
    """sample_good compares the href a sample was taken with to the build's, as strings."""
    import laz_classes_probe as lcp
    raw = "https://c.example/BC/A B/x+y.copc.laz"
    p = tmp_path / "class_targets.jsonl"
    p.write_text(json.dumps({"id": "A", "laz": PC, "copc": raw, "etag": "a"}) + "\n")
    items, _ = lcp.targets_load(str(p))
    assert lcp.item_copc(items[0]) == laz_item.href_encode(raw) != raw


def test_classes_record_refuses_a_limit(tmp_path, monkeypatch):
    pc = url_to_item_id(PC)
    with pytest.raises(SystemExit) as e:
        _main_with_required(tmp_path, monkeypatch, [pc], argv=["--limit", "3", "--classes-record"])
    assert e.value.code == 2
    assert json.loads((tmp_path / "classes_required.json").read_text()) == [pc]


def test_the_screen_is_the_research_percentile_within_each_group():
    """The research screen (the 5% audit draws outside it; the build no longer uses it, #17).
    Share of the group strictly less dense <= 10%: in a group of 10 the two least dense, ties
    included; a group of one is always screened."""
    g1 = [f"{PATH_S3}/092/092g/2016/pointcloud/f{i}_2016.laz" for i in range(10)]
    g2 = [f"{PATH_S3}/093/093a/2020/pointcloud/solo_2020.laz"]
    pts = {u: 100 * (i + 1) for i, u in enumerate(g1)}
    pts[g1[2]] = 200  # ties the second least dense
    pts[g2[0]] = 10 ** 9
    headers = {u: {"point_count": n, "mins": [0, 0, 0], "maxs": [10, 10, 1]}
               for u, n in pts.items()}
    import laz_classes_probe as lcp
    assert lcp.density_screen(g1 + g2, headers) == {g1[0], g1[1], g1[2], g2[0]}


def test_a_class_record_naming_no_file_is_refused_with_its_line(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text(json.dumps({"id": "x", "error": "OSError: 503"}) + "\n")
    with pytest.raises(ValueError, match="line 1 names no laz file"):
        catalogue_build.classes_records_load(str(p))


def test_a_build_refused_for_want_of_class_reads_has_already_listed_what_to_read(
        tmp_path, monkeypatch):
    """The probe's research runs read the targets file, so a refusal must not stop it."""
    assert _main_with_classes(tmp_path, monkeypatch, [], full_probe=_fails) == 1
    assert not (tmp_path / "data/build/items").exists()
    t = [json.loads(x) for x in
         (tmp_path / "data/build" / catalogue_build.CLASS_TARGETS).read_text().splitlines()]
    assert t == [{"id": url_to_item_id(PC), "laz": PC, "etag": "a", "copc": None}]

def test_an_empty_listing_etag_matches_no_class_read():
    items = {PC: item_create(PC, _header(), COLL)}
    records = {PC: {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000}, etag="")}}
    assert "no ETag" in catalogue_build.classes_attach(items, {PC: ""}, records)[PC]


# =============================================================================
# Field names (#12)
# =============================================================================

# Every prefixed key the build may write. A standard extension's prefix covers its own
# fields; the two custom prefixes name what a field describes: `lidarbc:` LidarBC's paths
# and file names, `las:` the LAS format, true of the CanElevation copy as of the LAZ.
PREFIXES_STANDARD = {"pc", "proj", "file", "classification"}
FIELDS_CUSTOM = {"lidarbc:product", "lidarbc:delivery", "lidarbc:datetime_source",
                 "lidarbc:filename_date", "las:version", "las:point_format"}


def _keys(x):
    """Every dict key anywhere in a JSON-shaped value."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _keys(v)
    elif isinstance(x, list):
        for v in x:
            yield from _keys(v)


# Every key the build writes, by path (`[]` for a list element), from three builds that
# between them take every branch item_create and main() write through: a COPC copy, a class
# read, a CRS with no EPSG code (`proj:wkt2`) and a trusted filename date (`datetime`). Pinned whole, so a key added anywhere - an item's top level,
# a link, a provider - fails here rather than in whichever place a hand-picked check missed.
ITEM_PATHS = {
    "assets", "assets.copc", "assets.copc.description", "assets.copc.file:size",
    "assets.copc.href", "assets.copc.las:point_format", "assets.copc.las:version",
    "assets.copc.roles", "assets.copc.title", "assets.copc.type", "assets.laz",
    "assets.laz.classification:classes", "assets.laz.classification:classes[].count",
    "assets.laz.classification:classes[].name", "assets.laz.classification:classes[].value",
    "assets.laz.file:size", "assets.laz.href", "assets.laz.roles", "assets.laz.title",
    "assets.laz.type", "bbox", "collection", "geometry", "geometry.coordinates",
    "geometry.type", "id", "links", "links[].href", "links[].rel", "links[].type",
    "properties", "properties.datetime", "properties.end_datetime",
    "properties.las:point_format", "properties.las:version",
    "properties.lidarbc:datetime_source", "properties.lidarbc:delivery",
    "properties.lidarbc:filename_date",
    "properties.lidarbc:product", "properties.pc:count", "properties.pc:encoding",
    "properties.pc:schemas", "properties.pc:schemas[].name", "properties.pc:schemas[].size",
    "properties.pc:schemas[].type", "properties.pc:type", "properties.proj:bbox",
    "properties.proj:code", "properties.proj:wkt2", "properties.start_datetime",
    "stac_extensions", "stac_version", "type",
}
COLLECTION_PATHS = {
    "description", "extent", "extent.spatial", "extent.spatial.bbox", "extent.temporal",
    "extent.temporal.interval", "id", "keywords", "license", "links", "links[].href",
    "links[].rel", "links[].title", "links[].type", "providers", "providers[].name",
    "providers[].roles", "providers[].url", "stac_extensions", "stac_version", "summaries",
    "summaries.lidarbc:product", "title", "type",
}


def _paths(x, at=""):
    """Every dict key anywhere in a JSON-shaped value, as a path from the root."""
    if isinstance(x, dict):
        for k, v in x.items():
            p = f"{at}.{k}" if at else k
            yield p
            yield from _paths(v, p)
    elif isinstance(x, list):
        for v in x:
            yield from _paths(v, at + "[]")


def test_the_declared_fields_are_the_ones_the_pinned_paths_carry():
    """FIELDS_CUSTOM and the pinned paths are two statements of one fact; hold them equal."""
    keys = {p.split(".")[-1].removesuffix("[]") for p in ITEM_PATHS | COLLECTION_PATHS}
    assert {k for k in keys if ":" in k and k.split(":")[0] not in PREFIXES_STANDARD} == \
        FIELDS_CUSTOM
    assert not {k for k in keys if k.startswith("nge:")}


def test_every_field_an_item_carries_is_a_standard_one_or_declared():
    it = laz_item.classes_add(_add(_copc_header()), _full({1: 400, 2: 600}))
    c = catalogue_build.collection_build([it])
    keys = set(_keys(it.to_dict(include_self_link=False))) | set(_keys(c.to_dict()))
    prefixed = {k for k in keys if ":" in k}
    assert not {k for k in prefixed if k.startswith("nge:")}
    assert {k for k in prefixed if k.split(":")[0] not in PREFIXES_STANDARD} == FIELDS_CUSTOM


def test_every_key_the_build_writes_is_pinned(tmp_path, monkeypatch):
    """What main() writes, not just what item_create returns: a key added at build level,
    or anywhere in the item or collection, fails. The three builds take every branch that
    writes a key; a branch none of them takes is a branch this cannot see."""
    for run in ("copc", "classes", "branches"):
        (tmp_path / run).mkdir()
    assert _main_with_copc(tmp_path / "copc", monkeypatch, _copc_header())[0] == 0
    assert _main_with_classes(tmp_path / "classes", monkeypatch,
                              [{"id": url_to_item_id(PC), "laz": PC,
                                "full": _full({1: 400, 2: 600})}]) == 0
    assert _main_with_branches(tmp_path / "branches", monkeypatch) == 0
    items, coll = set(), set()
    for run in ("copc", "classes", "branches"):
        out = tmp_path / run / "data/build"
        files = list((out / "items").glob("*.json"))
        assert files
        for f in files:
            items |= set(_paths(json.loads(f.read_text())))
        coll |= set(_paths(json.loads((out / "collection.json").read_text())))
    assert items == ITEM_PATHS
    assert coll == COLLECTION_PATHS


# A real 082K/2017 file whose Esri WKT has no EPSG code (197 such files, research/laz_header_read.md),
# and PC moved to a 2017 directory, where its `_20170713` agrees and is trusted.
PC_NO_EPSG = f"{PATH_S3}/082/082k/2017/pointcloud/bc_082k005_1_1_3_xyes_8_utm11_180827.laz"
PC_DATED = PC.replace("/2016/", "/2017/")


def _main_with_branches(tmp_path, monkeypatch):
    objs = [{"url": PC_NO_EPSG, "etag": "a", "size": 1}, {"url": PC_DATED, "etag": "b", "size": 1}]
    headers = {PC_NO_EPSG: _header((FIXTURES / "crs_esri_utm11_082k.wkt").read_text(),
                                   mins=(486850.99, 5540035.2, 1895.87),
                                   maxs=(487464.79, 5541426.46, 2272.88)),
               PC_DATED: _header()}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (lambda u, session=None: headers[u],))
    monkeypatch.setattr(catalogue_build, "item_probe", _sample({1: 400, 2: 600}))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    return catalogue_build.main()


def test_the_branch_build_takes_the_branches_it_is_for(tmp_path, monkeypatch):
    """Otherwise the pinned paths would silently stop covering them."""
    assert _main_with_branches(tmp_path, monkeypatch) == 0
    p = {u: json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(u)}.json")
                       .read_text())["properties"] for u in (PC_NO_EPSG, PC_DATED)}
    assert p[PC_NO_EPSG].get("proj:code") is None and p[PC_NO_EPSG]["proj:wkt2"]
    assert p[PC_DATED]["lidarbc:datetime_source"] == "filename" and p[PC_DATED]["datetime"]


# =============================================================================
# Delivery key, field schemas, related collection (#2, #5, crate#23)
# =============================================================================

def test_every_item_carries_its_delivery_from_the_key():
    it = item_create(PC, _header(), COLL)
    assert it.properties["lidarbc:delivery"] == "092/092g/2016"
    assert it.id.startswith(it.properties["lidarbc:delivery"].replace("/", "-") + "-")


def test_a_delivery_off_the_shared_pattern_is_refused(monkeypatch):
    real = laz_item.key_parse
    monkeypatch.setattr(laz_item, "key_parse", lambda u: {**real(u), "sheet": "092z"})
    with pytest.raises(ValueError, match="delivery '092/092z/2016'"):
        item_create(PC, _header(), COLL)


def test_items_and_the_collection_name_the_schemas_of_their_custom_fields():
    it = item_create(PC, _header(), COLL)
    assert {laz_item.SCHEMA_LIDARBC, laz_item.SCHEMA_LAS} <= set(it.stac_extensions)
    c = catalogue_build.collection_build([it])
    assert c.stac_extensions == [laz_item.SCHEMA_LIDARBC]
    laz_item.schemas_check(it.to_dict())
    laz_item.schemas_check(c.to_dict())


@pytest.mark.parametrize("drop, prefix", [(laz_item.SCHEMA_LIDARBC, "lidarbc:"),
                                          (laz_item.SCHEMA_LAS, "las:")])
def test_a_custom_field_without_its_schema_is_refused(drop, prefix):
    d = item_create(PC, _header(), COLL).to_dict()
    d["stac_extensions"].remove(drop)
    with pytest.raises(ValueError, match=f"writes {prefix} keys without the schema"):
        laz_item.schemas_check(d)


def test_a_las_field_only_on_an_asset_still_needs_its_schema():
    d = _add(_copc_header()).to_dict()
    d["properties"] = {k: v for k, v in d["properties"].items() if not k.startswith("las:")}
    d["stac_extensions"].remove(laz_item.SCHEMA_LAS)
    with pytest.raises(ValueError, match="writes las: keys"):
        laz_item.schemas_check(d)


def test_the_schemas_reject_a_value_off_their_pattern():
    """The schema URLs are not decoration: validation fetches them and checks the values."""
    it = item_create(PC, _header(), COLL)
    it.properties["lidarbc:delivery"] = "092/092G/2016"
    with pytest.raises(pystac.errors.STACValidationError):
        it.validate()


def test_the_collection_links_stac_elevation_bc_once():
    c = catalogue_build.collection_build([item_create(PC, _header(), COLL)]).to_dict()
    rel = [l for l in c["links"] if l["rel"] == "related"]
    assert rel == [catalogue_build.RELATED_ELEVATION]


@pytest.mark.parametrize("drop", [laz_item.SCHEMA_LIDARBC, laz_item.SCHEMA_LAS])
def test_the_build_refuses_an_item_missing_a_schema_it_needs(tmp_path, monkeypatch, drop):
    """main() checks what it writes, not only what item_create returns: a copc asset added at
    build level carries `las:` keys too."""
    real = catalogue_build.item_create

    def dropping(*a, **k):
        it = real(*a, **k)
        it.stac_extensions.remove(drop)
        return it
    monkeypatch.setattr(catalogue_build, "item_create", dropping)
    with pytest.raises(ValueError, match="without the schema"):
        _main_with_copc(tmp_path, monkeypatch, _copc_header())
    assert not (tmp_path / "data/build/items").exists()


# =============================================================================
# Listing-time checks and aggregated refusals (#2 plan review: G5, G6, G10, A4, O1)
# =============================================================================

@pytest.mark.parametrize("name", ["bc_092g019_1_4_1_xyes#8_2016.laz", "bc_092g019_é_2016.laz",
                                  "bc_092g019_1+4_2016.laz"])
def test_a_file_name_item_links_cannot_carry_is_refused_at_listing(name):
    with pytest.raises(ValueError, match="file name outside"):
        catalogue_build.pointcloud_select(_listed([f"092/092g/2016/pointcloud/{name}"]))


def test_a_copy_marker_name_passes_the_listing():
    assert catalogue_build.pointcloud_select(
        _listed(["082/082l/2018/pointcloud/bc_082l024_2_4_3_xyes_12_utm11_2018 (2).laz"]))


def test_every_listing_fault_is_named_in_one_refusal():
    keys = ["092/082e/2016/pointcloud/a_2016.laz", "092/092z/2016/pointcloud/b_2016.laz",
            "092/092g/2016/PointCloud/c_2016.laz", "092/092g/2016/pointcloud/d#_2016.laz"]
    with pytest.raises(ValueError, match="4 .laz keys cannot be placed") as e:
        catalogue_build.pointcloud_select(_listed(keys))
    for why in ("sheet 082e is not in block 092", "'092z' is not an NTS 1:250k sheet letter",
                "key is not", "file name outside"):
        assert why in str(e.value)


def test_a_sheet_outside_its_block_is_refused_by_key_parse():
    with pytest.raises(ValueError, match="sheet 082e is not in block 092"):
        key_parse(f"{PATH_S3}/092/082e/2016/pointcloud/a_2016.laz")


def test_a_date_token_that_is_no_date_names_every_file():
    urls = [f"{PATH_S3}/092/092g/2016/pointcloud/a_20161301.laz",
            f"{PATH_S3}/092/092g/2016/pointcloud/b_20163201.laz",
            f"{PATH_S3}/092/092g/2016/pointcloud/c_2016.laz"]
    with pytest.raises(ValueError, match="2 file names carry a date token that is no date") as e:
        catalogue_build.groups_with_untrusted_dates(urls)
    assert "a_20161301.laz" in str(e.value) and "b_20163201.laz" in str(e.value)


def test_every_item_fault_is_collected_not_only_the_first():
    a, b, c = PC, PC.replace("019_1_4_1", "019_1_4_2"), PC.replace("019_1_4_1", "019_1_4_3")
    headers = {a: _header(mins=(0, 0, 0)), b: _header(mins=(1, 1, 1)), c: _header()}
    items, faults = catalogue_build.items_create([a, b, c], headers, COLL, set())
    assert [i.id for i in items] == [url_to_item_id(c)] and set(faults) == {a, b}
    assert len({catalogue_build.fault_class(e) for e in faults.values()}) == 1


def test_the_build_reports_item_faults_by_class_and_writes_nothing(tmp_path, monkeypatch, caplog):
    objs = [{"url": u, "etag": "a", "size": 1}
            for u in (PC, PC.replace("019_1_4_1", "019_1_4_2"))]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (lambda u, session=None: _header(mins=(0, 0, 0)),))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    assert catalogue_build.main() == 1
    assert "2 files: implausible header box" in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def test_duplicate_ids_are_refused_before_any_header_is_read(tmp_path, monkeypatch):
    objs = [{"url": u, "etag": "a", "size": 1}
            for u in (PC, PC.replace("019_1_4_1", "019_1_4_2"))]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "url_to_item_id", lambda u: "same")
    monkeypatch.setattr(catalogue_build, "headers_fetch",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("read")))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    with pytest.raises(RuntimeError, match="duplicate item ids"):
        catalogue_build.main()


def test_validation_in_a_process_pool_reports_each_invalid_item():
    good = item_create(PC, _header(), COLL).to_dict(include_self_link=False)
    bad = json.loads(json.dumps(good))
    bad["id"], bad["properties"]["lidarbc:delivery"] = "bad", "092/092G/2016"
    errs = catalogue_build.validate_all([good] * 600 + [bad], workers=2)
    assert len(errs) == 1 and errs[0].startswith("bad: ")
    assert catalogue_build.validate_all([good, bad], workers=1)[0].startswith("bad: ")


class _Flaky:
    """A session failing `fails` times (an exception or a status) before answering 200."""
    def __init__(self, fails):
        self.fails, self.calls = list(fails), 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        f = self.fails.pop(0) if self.fails else 200
        if isinstance(f, Exception):
            raise f
        r = type("R", (), {})()
        r.status_code = f
        return r


def test_a_listing_page_is_retried_on_a_dropped_connection_or_5xx():
    import requests
    s = _Flaky([requests.ConnectionError("dropped"), 503, requests.Timeout("slow")])
    assert laz_item.page_get(s, "u", {}, 1, sleep=lambda t: None).status_code == 200
    assert s.calls == 4


def test_a_listing_page_failing_every_attempt_raises_and_a_4xx_is_not_retried():
    import requests
    s = _Flaky([requests.ConnectionError("dropped")] * laz_item.PAGE_ATTEMPTS)
    with pytest.raises(requests.ConnectionError):
        laz_item.page_get(s, "u", {}, 1, sleep=lambda t: None)
    s = _Flaky([403])
    assert laz_item.page_get(s, "u", {}, 1, sleep=lambda t: None).status_code == 403
    assert s.calls == 1
    s = _Flaky([503] * laz_item.PAGE_ATTEMPTS)
    assert laz_item.page_get(s, "u", {}, 1, sleep=lambda t: None).status_code == 503


def test_the_build_refuses_an_item_missing_one_of_its_fields(tmp_path, monkeypatch):
    real = catalogue_build.item_create

    def dropping(*a, **k):
        it = real(*a, **k)
        it.properties.pop("lidarbc:delivery")
        return it
    monkeypatch.setattr(catalogue_build, "item_create", dropping)
    with pytest.raises(ValueError, match="missing lidarbc:delivery"):
        _main_with_copc(tmp_path, monkeypatch, _copc_header())


# =============================================================================
# A compound CRS written vertical-first (2,008 files in seven 2021 deliveries, #2)
# =============================================================================

VERTICAL_FIRST = (FIXTURES / "crs_compound_vertical_first_093p.wkt").read_text()


def _header_with_wkt(wkt: str) -> laspy.LasHeader:
    h = laspy.LasHeader(point_format=6, version="1.4")
    h.vlrs.append(laspy.vlrs.known.WktCoordinateSystemVlr(wkt))
    return h


def test_a_vertical_first_compound_is_refused_by_proj_and_read_swapped():
    with pytest.raises(CRSError):
        CRS.from_wkt(VERTICAL_FIRST)
    crs = laz_item.header_crs(_header_with_wkt(VERTICAL_FIRST))
    assert crs.is_compound
    assert [c.is_vertical for c in crs.sub_crs_list] == [False, True]
    assert crs.sub_crs_list[1].name == "CGVD2013 height"
    assert laz_item._horizontal(crs).to_epsg() == 3157


def test_a_swapped_crs_round_trips_through_the_header_cache_into_proj_code():
    wkt = laz_item.header_crs(_header_with_wkt(VERTICAL_FIRST)).to_wkt()
    url = f"{PATH_S3}/093/093p/2021/pointcloud/bc_093p075_1_2_3_xyes_8_utm10_2021.laz"
    it = item_create(url, _header(wkt, mins=(650000.0, 6170000.0, 700.0),
                                  maxs=(651000.0, 6171000.0, 900.0)), COLL)
    assert it.properties["proj:code"] == "EPSG:3157"


def test_only_a_vertical_first_compound_is_reordered():
    assert laz_item.compound_reorder((FIXTURES / "crs_compound_bound_2955.wkt").read_text()) is None
    assert laz_item.compound_reorder((FIXTURES / "crs_esri_utm11_082k.wkt").read_text()) is None
    swapped = laz_item.compound_reorder(VERTICAL_FIRST)
    assert swapped.index("PROJCS[") < swapped.index("VERT_CS[")
    assert laz_item.compound_reorder(swapped) is None  # a WKT1 compound already in order
    assert sorted(swapped) == sorted(VERTICAL_FIRST)  # the same characters, reordered


def test_any_other_crs_parse_failure_still_raises():
    broken = VERTICAL_FIRST.replace("VERT_CS[", "VERT_XX[", 1)
    with pytest.raises(CRSError):
        laz_item.header_crs(_header_with_wkt(broken))
