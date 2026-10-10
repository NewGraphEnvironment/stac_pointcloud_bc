"""Contract tests for scripts/laz_item.py, scripts/laz_remote.py and the build's guards.

The remote-read tests run against a local HTTP server that, like the objectstore, answers
ranges with 206 and does NOT advertise Accept-Ranges (research/laz_header_read.md), over
a LAZ written here by laspy -- so the header path is exercised end to end with no network.
"""

import http.server
import json
import os
import threading
from datetime import datetime, timezone

import laspy
import numpy as np
import pytest
from pyproj import CRS

import catalogue_build
import laz_item
from laz_item import (
    ASSET_LAZ,
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


@pytest.fixture(autouse=True)
def no_class_reads(monkeypatch):
    """main() refuses a build whose class reads are not CLASSES_READ. These builds have none,
    so expect none; the tests of that wiring set their own."""
    monkeypatch.setattr(catalogue_build, "CLASSES_READ", {})


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
    assert d["properties"]["nge:product"] == "pointcloud"
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
    assert d["properties"]["nge:filename_date"] == "20170713"
    assert d["properties"]["nge:datetime_source"] == "path"
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


def test_the_build_refuses_a_group_listed_short(monkeypatch):
    def short(prefix, session=None):
        n = 10 if prefix.startswith("092/092j/2016") else 5000
        return [{"url": f"{PATH_S3}/{prefix}f{i}.laz", "etag": "e", "size": 1} for i in range(n)]
    monkeypatch.setattr(catalogue_build, "keys_list", short)
    with pytest.raises(RuntimeError, match="092/092j/2016: 10 pointcloud .laz"):
        catalogue_build.listing()


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
    (u,) = catalogue_build.EXCLUDE
    assert catalogue_build.exclusions_check([u], {u: {"mins": [0.0, 0.0, 0.0]}}) == [u]
    with pytest.raises(RuntimeError, match="may have been fixed"):
        catalogue_build.exclusions_check([u], {u: {"mins": [547410.0, 5441555.0, 2.0]}})


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
    assert agreeing["nge:filename_date"] == "171015"


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
    assert copc["nge:las_version"] == "1.4" and copc["nge:point_format"] == 6
    assert d["properties"]["nge:las_version"] == "1.2"
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


def test_a_group_that_pairs_short_fails_the_build():
    """A rename on either side passes every listing floor and pairs nothing."""
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
    with pytest.raises(RuntimeError, match=r"not in COPC_PAIRS: 082/082f/2018 \(1\)"):
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
    # A read of a file not in the build is not applied, and not a problem here: it leaves
    # CLASSES_READ short, which main() refuses.
    assert "re-delivered" in problems[PC] and other not in problems
    assert "classification:classes" not in items[PC].assets[ASSET_LAZ].extra_fields
    failed = {PC: {"id": url_to_item_id(PC), "laz": PC, "error": "OSError: 503"}}
    assert "failed" in catalogue_build.classes_attach(items, {PC: "a"}, failed)[PC]


def _main_with_classes(tmp_path, monkeypatch, records, expected):
    objs = [{"url": PC, "etag": "a", "size": 1}]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogue_build, "OUT", "data/build")
    monkeypatch.setattr(catalogue_build, "listing", lambda: objs)
    monkeypatch.setattr(catalogue_build, "copc_listing", lambda: [])
    monkeypatch.setattr(catalogue_build, "COPC_PAIRS", {})
    monkeypatch.setattr(catalogue_build, "CLASSES_READ", expected)
    monkeypatch.setattr(catalogue_build.headers_fetch, "__defaults__",
                        (lambda u, session=None: _header(),))
    monkeypatch.setattr("sys.argv", ["catalogue_build.py", "--workers", "1"])
    os.makedirs("data/build", exist_ok=True)
    with open(f"data/build/{catalogue_build.CLASSES_FULL}", "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return catalogue_build.main()


def test_the_build_lists_the_classes_of_a_file_read_whole(tmp_path, monkeypatch):
    rc = _main_with_classes(tmp_path, monkeypatch,
                            [{"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000})}],
                            {"092/092g/2016": 1})
    assert rc == 0
    d = json.loads((tmp_path / "data/build/items" / f"{url_to_item_id(PC)}.json").read_text())
    assert d["assets"][ASSET_LAZ]["classification:classes"] == [
        {"value": 2, "name": "ground", "count": 1000}]
    c = json.loads((tmp_path / "data/build/collection.json").read_text())
    assert "classification:classes" in c["description"]


def test_a_build_missing_its_class_reads_is_refused(tmp_path, monkeypatch, caplog):
    """The cache is gitignored; a fresh checkout would otherwise drop every list unseen."""
    rc = _main_with_classes(tmp_path, monkeypatch, [], {"092/092g/2016": 1})
    assert rc == 1
    assert "expected {'092/092g/2016': 1} (CLASSES_READ)" in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def test_a_build_with_a_stale_class_read_is_refused(tmp_path, monkeypatch, caplog):
    rc = _main_with_classes(
        tmp_path, monkeypatch,
        [{"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000}, etag="old")}],
        {"092/092g/2016": 1})
    assert rc == 1
    assert "re-delivered" in caplog.text
    assert not (tmp_path / "data/build/items").exists()


def test_a_failed_class_read_is_refused_by_name_and_a_retry_replaces_it(tmp_path, monkeypatch,
                                                                         caplog):
    """The cache as laz_classes_probe.probe_all writes it: a failed read, then (on a re-run)
    a good one. The failure alone refuses the build by name; the retry lets it through."""
    err = {"id": url_to_item_id(PC), "error": "OSError: 503", "laz": PC}
    good = {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000})}
    assert _main_with_classes(tmp_path, monkeypatch, [err], {"092/092g/2016": 1}) == 1
    assert "the class read failed: OSError: 503" in caplog.text
    assert _main_with_classes(tmp_path, monkeypatch, [err, good], {"092/092g/2016": 1}) == 0


def test_a_class_record_naming_no_file_is_refused_with_its_line(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text(json.dumps({"id": "x", "error": "OSError: 503"}) + "\n")
    with pytest.raises(ValueError, match="line 1 names no laz file"):
        catalogue_build.classes_records_load(str(p))


def test_a_class_read_of_a_file_that_left_the_build_shows_as_a_short_count(tmp_path,
                                                                             monkeypatch, caplog):
    gone = PC.replace("019_1_4_1", "019_1_4_2")
    recs = [{"id": url_to_item_id(gone), "laz": gone, "full": _full({2: 1000})}]
    assert _main_with_classes(tmp_path, monkeypatch, recs, {"092/092g/2016": 1}) == 1
    assert "expected {'092/092g/2016': 1} (CLASSES_READ)" in caplog.text
    assert "not in this build, not applied" in caplog.text


def test_a_build_refused_for_want_of_class_reads_has_already_listed_what_to_read(
        tmp_path, monkeypatch):
    """A fresh checkout has no class cache, so the build refuses before writing items. The
    probe reads the targets file, not items, so the refusal must not stop it being written."""
    assert _main_with_classes(tmp_path, monkeypatch, [], {"092/092g/2016": 1}) == 1
    assert not (tmp_path / "data/build/items").exists()
    t = [json.loads(x) for x in
         (tmp_path / "data/build" / catalogue_build.CLASS_TARGETS).read_text().splitlines()]
    assert t == [{"id": url_to_item_id(PC), "laz": PC, "etag": "a", "copc": None}]


def test_an_empty_listing_etag_matches_no_class_read():
    items = {PC: item_create(PC, _header(), COLL)}
    records = {PC: {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000}, etag="")}}
    assert "no ETag" in catalogue_build.classes_attach(items, {PC: ""}, records)[PC]


def test_a_class_cache_cut_off_mid_write_is_repaired_not_fatal(tmp_path, monkeypatch):
    good = {"id": url_to_item_id(PC), "laz": PC, "full": _full({2: 1000})}
    rc = _main_with_classes(tmp_path, monkeypatch, [good], {"092/092g/2016": 1})
    assert rc == 0
    with open(tmp_path / "data/build" / catalogue_build.CLASSES_FULL, "a") as fh:
        fh.write('{"id": "x", "laz": "https://x')  # a --confirm killed mid-line
    assert catalogue_build.main() == 0
