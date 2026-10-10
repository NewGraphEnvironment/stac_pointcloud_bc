"""Contract tests for scripts/laz_classes_probe.py (#10).

The sample reads run against the same local 206-only range server as test_laz_item.py, over
LAZ files written here with known classes at known positions, so "the first points alone would
mislead" is a case the tests can build rather than one they hope for.
"""

import http.server
import json
import threading

import laspy
import numpy as np
import pytest
from pyproj import CRS

import laz_classes_probe as lcp
from laz_classes_probe import (
    confirm_ids,
    counts_merge,
    ground_only,
    laz_full,
    laz_sample,
    no_ground,
    probe_all,
    verdicts,
)
from test_laz_item import _RangeHandler


def _laz(path, classes):
    hdr = laspy.LasHeader(point_format=1, version="1.2")
    hdr.offsets = [547000.0, 5441000.0, 0.0]
    hdr.scales = [0.01, 0.01, 0.01]
    hdr.add_crs(CRS.from_epsg(3157))
    las = laspy.LasData(hdr)
    n = len(classes)
    rng = np.random.default_rng(1)
    las.x = rng.uniform(547410.45, 549246.4, n)
    las.y = rng.uniform(5441555.91, 5442961.42, n)
    las.z = rng.uniform(2.2, 100.49, n)
    las.classification = classes
    las.write(str(path))
    return path


@pytest.fixture
def serve(tmp_path):
    servers = []

    def _serve(classes):
        path = _laz(tmp_path / f"t{len(servers)}.laz", np.asarray(classes, dtype=np.uint8))
        handler = type("H", (_RangeHandler,), {"payload": path.read_bytes()})
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}/{path.name}", path

    yield _serve
    for s in servers:
        s.shutdown()


@pytest.mark.parametrize("counts, want", [
    ({2: 5}, True),
    ({2: 5, 7: 1, 9: 3, 18: 1}, True),
    ({1: 1, 2: 5}, False),  # unclassified may be vegetation left unclassified
    ({5: 3}, False),
    ({9: 4}, False),  # water alone: no ground in it
    ({7: 1, 18: 2}, False),  # noise alone
    ({1: 6}, False),  # never classified

    ({}, None),
    ({2: 0}, None),  # a class with no points is not a class seen
])
def test_ground_only_is_no_class_outside_ground_noise_and_water(counts, want):
    assert ground_only(counts) is want


def test_a_tile_ground_only_in_its_first_points_is_caught_by_a_spread_chunk(serve):
    # 20 chunks of 50,000, so the seeks skip whole chunks and the bytes check can fail.
    n = 1_000_000
    classes = np.full(n, 2)
    classes[490_000:560_000] = 5  # under the seek to 50%, nowhere near the first points
    url, path = serve(classes)
    s = laz_sample(url)
    assert s["point_count"] == n
    assert s["samples"]["first"] == {2: lcp.FIRST_POINTS}
    assert s["samples"]["at_0.25"] == {2: lcp.SPREAD_POINTS}
    assert 5 in s["samples"]["at_0.5"]
    assert set(s["samples"]) == {"first", "at_0.25", "at_0.5", "at_0.75"}
    rec = {"laz_sample": s}
    assert verdicts(rec) == {"first": True, "laz": False, "copc": None}
    # Seeks, not a read through: five of twenty chunks, so well under the file.
    assert s["bytes"] < 0.5 * path.stat().st_size


def test_a_small_tile_is_read_whole_as_one_sample(serve):
    url, _ = serve([2] * 1000 + [1] * 10)
    s = laz_sample(url)
    assert s["samples"] == {"all": {1: 10, 2: 1000}}
    assert verdicts({"laz_sample": s})["first"] is False


def test_the_copc_verdict_is_reported_beside_the_laz_one():
    rec = {"laz_sample": {"samples": {"first": {2: 9}}},
           "copc_sample": {"classes": {1: 3, 2: 9}}}
    assert verdicts(rec) == {"first": True, "laz": True, "copc": False}


def test_counts_merge_sums_by_class_whatever_the_key_type():
    # Keys come back from JSON as strings.
    assert counts_merge({"2": 3, "1": 1}, {2: 4}) == {1: 1, 2: 7}


def test_a_rerun_probes_only_failed_and_missing_items(tmp_path):
    out = tmp_path / "classes.jsonl"
    items = [{"id": f"i{k}"} for k in range(4)]
    calls, failed = [], set()

    def probe(item, session=None):
        calls.append(item["id"])
        if item["id"] == "i2" and not failed:
            failed.add("i2")
            raise OSError("range request returned 503")
        return {"id": item["id"], "laz_sample": {}}

    errors = probe_all(items, str(out), workers=2, probe=probe)
    assert errors == {"i2": "OSError: range request returned 503"}
    recs = lcp.records_load(str(out))
    assert recs["i2"] == {"id": "i2", "error": "OSError: range request returned 503"}
    calls.clear()
    assert probe_all(items, str(out), workers=2, probe=probe) == {}
    assert calls == ["i2"]
    assert "error" not in lcp.records_load(str(out))["i2"]


def test_an_interrupted_last_record_is_dropped_and_read_again(tmp_path):
    out = tmp_path / "classes.jsonl"
    out.write_text(json.dumps({"id": "i0", "laz_sample": {}}) + "\n" + '{"id": "i1", "la')
    calls = []

    def probe(item, session=None):
        calls.append(item["id"])
        return {"id": item["id"], "laz_sample": {}}

    probe_all([{"id": "i0"}, {"id": "i1"}], str(out), workers=1, probe=probe)
    assert calls == ["i1"]
    assert set(lcp.records_load(str(out))) == {"i0", "i1"}


@pytest.mark.parametrize("counts, want", [
    ({1: 5, 7: 2}, True),
    ({0: 9}, True),  # never classified
    ({1: 5, 2: 1}, False),
    ({}, None),
])
def test_no_ground_is_points_but_none_of_class_2(counts, want):
    assert no_ground(counts) is want


def test_every_item_a_sample_calls_ground_only_or_groundless_is_confirmed_and_no_other():
    g, m, w = {2: 9}, {1: 1, 2: 9}, {1: 9, 9: 3}
    recs = {
        # A chunk without ground is ordinary; the tile's samples together have it.
        "one_chunk_groundless": {"laz_sample": {"samples": {"first": w, "at_0.5": m}}},
        "groundless": {"laz_sample": {"samples": {"first": w, "at_0.5": {1: 4}}}},
        "all_ground": {"laz_sample": {"samples": {"first": g}}},
        "first_only": {"laz_sample": {"samples": {"first": g, "at_0.5": m}}},
        "copc_only": {"laz_sample": {"samples": {"first": m}}, "copc_sample": {"classes": g}},
        "mixed": {"laz_sample": {"samples": {"first": m}}, "copc_sample": {"classes": m}},
        "failed": {"error": "OSError: x"},
    }
    assert confirm_ids(recs) == {"all_ground", "first_only", "copc_only", "groundless"}


def test_a_full_read_tallies_every_point_as_a_local_read_does(serve):
    classes = np.full(120_000, 2)
    classes[70_000:70_010] = 1
    url, path = serve(classes)
    f = laz_full(url)
    local = laspy.read(str(path))
    assert f["points_read"] == f["point_count"] == len(local.points)
    assert f["classes"] == {1: 10, 2: 119_990}
    want = {}
    for rn, nr in zip(np.asarray(local.return_number), np.asarray(local.number_of_returns)):
        want[f"{rn}/{nr}"] = want.get(f"{rn}/{nr}", 0) + 1
    assert f["returns"] == dict(sorted(want.items()))
    assert f["bytes"] == path.stat().st_size
    assert ground_only(f["classes"]) is False
