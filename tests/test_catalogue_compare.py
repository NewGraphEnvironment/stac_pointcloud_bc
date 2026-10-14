"""The published-vs-build check (#22): the footprint rounding passes, anything else is named."""

import copy
import json
import sys

import pytest

import catalogue_compare as cc
import laz_item
from collection_version import version_stamp
from test_laz_item import _add, _copc_header

# What a 0.3.0 coordinate looks like: the rounded value plus last-place noise under half a unit.
NOISE = 3.7e-9


def _built():
    d = _add(_copc_header()).to_dict(include_self_link=False)
    d.pop("links")
    return d


def _unround(x):
    if isinstance(x, list):
        return [_unround(v) for v in x]
    if isinstance(x, dict):
        return {k: _unround(v) for k, v in x.items()}
    return x + NOISE if isinstance(x, float) else x


def _published(built: dict) -> dict:
    """A built item as 0.3.0 published it: the same, with unrounded lon/lat."""
    p = copy.deepcopy(built)
    p["geometry"] = _unround(p["geometry"])
    p["bbox"] = _unround(p["bbox"])
    return p


def test_the_build_is_rounded_so_the_fixture_has_something_to_round():
    b = _built()
    assert all(round(v, laz_item.LONLAT_DECIMALS) == v for v in b["bbox"])
    assert _published(b)["bbox"] != b["bbox"]


def test_the_rounding_and_nothing_else_passes():
    b = _built()
    assert cc.item_expected_diff(_published(b), b) == []


def _set_lon(b, d):
    b["geometry"]["coordinates"][0][1][0] += d


@pytest.mark.parametrize("mutate, why", [
    (lambda b: _set_lon(b, 1e-7), "beyond the rounding"),
    (lambda b: b["bbox"].__setitem__(0, b["bbox"][0] - 1e-7), "beyond the rounding"),
    (lambda b: _set_lon(b, 1e-10), "more than 8 decimals"),
    (lambda b: b["geometry"]["coordinates"][0].insert(1, [-123.0, 49.0]), "length"),
    (lambda b: b["geometry"].__setitem__("type", "MultiPolygon"), "geometry.type"),
    (lambda b: b["geometry"].__setitem__("crs", "x"), "geometry: keys"),
    (lambda b: b["properties"].__setitem__("pc:count", 7), "pc:count"),
    (lambda b: b["properties"].__setitem__("end_datetime", "2030-01-01T00:00:00Z"), "end_datetime"),
    (lambda b: b["properties"].__setitem__("lidarbc:delivery", "092/092h/2016"), "lidarbc:delivery"),
    (lambda b: b["assets"]["copc"].__setitem__("las:version", "1.2"), "copc"),
    (lambda b: b["assets"].pop("copc"), "copc"),
    (lambda b: b["stac_extensions"].append("https://x/schema.json"), "stac_extensions"),
])
def test_any_other_difference_is_named(mutate, why):
    b = _built()
    p = _published(b)
    mutate(b)
    assert why in "; ".join(cc.item_expected_diff(p, b))


def _collection(hrefs, bbox=(-125.0, 49.0, -120.0, 52.0)):
    return {"type": "Collection", "id": "c", "description": "d", "stac_extensions": ["s"],
            "extent": {"spatial": {"bbox": [list(bbox)]},
                       "temporal": {"interval": [["2012-01-01T00:00:00Z", None]]}},
            "links": [{"rel": "related", "href": "r"}]
                     + [{"rel": "item", "href": h} for h in hrefs]}


def test_the_collection_as_released_passes_its_unstamped_build():
    pub = version_stamp(_collection(["a", "b"], bbox=(-125.0 + NOISE, 49.0, -120.0, 52.0)), "0.3.0")
    problems, changes = cc.collection_diff(pub, _collection(["a", "b"]), new=0)
    assert problems == []
    assert "version 0.3.0 -> None" in changes


@pytest.mark.parametrize("mutate, new, why", [
    (lambda c: c["links"].pop(), 0, "published item links not in the build"),
    (lambda c: c["links"].__setitem__(0, {"rel": "related", "href": "x"}), 0, "non-item links"),
    (lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(0, -126.0), 0, "beyond the rounding"),
    (lambda c: c["extent"]["temporal"]["interval"][0].__setitem__(1, "2026-01-01T00:00:00Z"), 0,
     "extent.temporal"),
    (lambda c: c.__setitem__("description", "e"), 0, "description: changed"),
    (lambda c: c["stac_extensions"].append("t"), 0, "stac_extensions"),
])
def test_any_other_collection_difference_is_a_problem(mutate, new, why):
    built = _collection(["a", "b"])
    mutate(built)
    problems, _ = cc.collection_diff(_collection(["a", "b"]), built, new=new)
    assert why in "; ".join(problems)


def test_new_items_may_widen_the_extent():
    built = _collection(["a", "b", "c"], bbox=(-126.0, 49.0, -120.0, 52.0))
    problems, changes = cc.collection_diff(_collection(["a", "b"]), built, new=1)
    assert problems == []
    assert any(c.startswith("extent widened, with 1 new item(s)") for c in changes)


def test_a_published_value_exactly_half_way_still_passes():
    """Half a unit in the last place, the most a true rounding can move a value."""
    b = _built()
    p = copy.deepcopy(b)
    p["bbox"][0] = b["bbox"][0] + 0.5 * 10 ** -laz_item.LONLAT_DECIMALS
    assert cc.item_expected_diff(p, b) == []


@pytest.mark.parametrize("mutate, why", [
    (lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(0, -124.0), "does not contain"),
    (lambda c: c["extent"]["temporal"]["interval"][0].__setitem__(0, "2013-01-01T00:00:00Z"),
     "does not contain"),
    (lambda c: c["extent"]["temporal"]["interval"].append(["2020-01-01T00:00:00Z", None]),
     "structure"),
    (lambda c: c["extent"]["spatial"]["bbox"].append([-126.0, 48.0, -119.0, 53.0]), "structure"),
])
def test_new_items_may_only_widen_the_extent(mutate, why):
    built = _collection(["a", "b", "c"])
    mutate(built)
    problems, _ = cc.collection_diff(_collection(["a", "b"]), built, new=1)
    assert why in "; ".join(problems)


def _tree(tmp_path, pub_items, built_items, pub_links=None):
    """A published dir and a build dir as main() reads them."""
    pub, build = tmp_path / "published", tmp_path / "build"
    (build / "items").mkdir(parents=True)
    pub.mkdir()
    for d, items in ((pub, pub_items), (build / "items", built_items)):
        for k, body in items.items():
            (d / f"{k}.json").write_text(json.dumps({**body, "links": [{"rel": "self"}]}))
    coll = _collection([f"{k}.json" for k in built_items])
    coll["extent"] = cc.items_envelope(built_items)
    (build / "collection.json").write_text(json.dumps(coll))
    pc = _collection([f"{k}.json" for k in (pub_items if pub_links is None else pub_links)])
    pc["extent"] = cc.items_envelope(pub_items)
    (pub / "collection.json").write_text(json.dumps(pc))
    return ["--published", str(pub), "--build", str(build)]


def _edit(path, f):
    d = json.loads(path.read_text())
    f(d)
    path.write_text(json.dumps(d))


def _main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["catalogue_compare.py", *argv])
    return cc.main()


def test_main_passes_the_rounding_alone(tmp_path, monkeypatch, capsys):
    b = _built()
    assert _main(monkeypatch, _tree(tmp_path, {"x": _published(b)}, {"x": b})) == 0
    out = capsys.readouterr().out
    assert "differing beyond the rounding: 0" in out
    n = len(cc.coords(b["geometry"])) + len(cc.coords(b["bbox"]))
    assert f"coordinates compared {n}, equal to the published rounded to 8 decimals {n}" in out


def test_main_fails_an_item_only_in_the_bucket(tmp_path, monkeypatch, capsys):
    """Published, linked and copied, but no longer built. The collection's item-link check
    catches it too; the item report is pinned on its own."""
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b), "y": _published(b)}, {"x": b})
    assert _main(monkeypatch, argv) == 1
    assert "only published: y" in capsys.readouterr().out


def test_main_fails_an_item_that_differs_beyond_the_rounding(tmp_path, monkeypatch):
    b = _built()
    p = _published(b)
    b["properties"]["pc:count"] = 7
    assert _main(monkeypatch, _tree(tmp_path, {"x": p}, {"x": b})) == 1


def test_main_fails_a_linked_item_missing_from_the_local_copy(tmp_path, monkeypatch, capsys):
    """An interrupted copy of the bucket: the collection links y, the copy lacks it."""
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b, "y": b}, pub_links=["x", "y"])
    assert _main(monkeypatch, argv) == 1
    assert "not copied: y" in capsys.readouterr().out


def test_main_fails_a_local_file_the_collection_does_not_link(tmp_path, monkeypatch, capsys):
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b), "z": _published(b)}, {"x": b, "z": b},
                 pub_links=["x"])
    assert _main(monkeypatch, argv) == 1
    assert "unlinked: z" in capsys.readouterr().out


def test_main_fails_on_a_collection_problem_alone(tmp_path, monkeypatch):
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b})
    coll = tmp_path / "build" / "collection.json"
    c = json.loads(coll.read_text())
    c["description"] = "changed"
    coll.write_text(json.dumps(c))
    assert _main(monkeypatch, argv) == 1


def test_linked_ids_reads_ids_back_as_s3_sync_does():
    c = {"links": [{"rel": "item", "href": "https://b.s3/x%20y.json"},
                   {"rel": "self", "href": "https://b.s3/collection.json"}]}
    assert cc.linked_ids(c) == {"x y"}


@pytest.mark.parametrize("mutate", [
    lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(1, 50.0),
    lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(2, -121.0),
    lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(3, 51.0),
    lambda c: c["extent"]["temporal"]["interval"][0].__setitem__(1, "2026-01-01T00:00:00Z"),
    lambda c: c["extent"]["spatial"]["bbox"].__setitem__(0, [-126.0, 48.0, -119.0]),
    lambda c: c["extent"]["temporal"]["interval"].__setitem__(0, ["2012-01-01T00:00:00Z"]),
    lambda c: c["extent"].__setitem__("extra", 1),
    lambda c: c["extent"]["spatial"].__setitem__("extra", 1),
])
def test_new_items_cannot_shrink_or_reshape_the_extent(mutate):
    """Each edge and each structural check, one at a time."""
    built = _collection(["a", "b", "c"])
    mutate(built)
    problems, _ = cc.collection_diff(_collection(["a", "b"]), built, new=1)
    assert problems


def test_main_reports_a_new_item_and_passes(tmp_path, monkeypatch, capsys):
    b = _built()
    n = copy.deepcopy(b)
    n["bbox"][0] -= 1.0
    n["geometry"]["coordinates"][0][0][0] -= 1.0
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b, "n": n}, pub_links=["x"])
    assert _main(monkeypatch, argv) == 0
    assert "new: n" in capsys.readouterr().out


def test_main_fails_a_new_item_whose_footprint_is_not_rounded(tmp_path, monkeypatch):
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b, "n": _published(b)}, pub_links=["x"])
    assert _main(monkeypatch, argv) == 1


def test_main_fails_an_extent_that_moved_with_nothing_new(tmp_path, monkeypatch):
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b})
    _edit(tmp_path / "build" / "collection.json",
          lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(0, -180.0))
    assert _main(monkeypatch, argv) == 1


def test_main_fails_an_extent_that_is_not_the_items_envelope(tmp_path, monkeypatch):
    """With a new item the published extent need only be contained, but the built one must
    still be exactly its items' envelope."""
    b = _built()
    n = copy.deepcopy(b)
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b, "n": n}, pub_links=["x"])
    _edit(tmp_path / "build" / "collection.json",
          lambda c: c["extent"]["spatial"].__setitem__("bbox", [[-180.0, -90.0, 180.0, 90.0]]))
    assert _main(monkeypatch, argv) == 1


@pytest.mark.parametrize("links, why", [
    (["x"], "item file, not linked: y"),
    (["x", "y", "w"], "linked, no item file: w"),
])
def test_main_fails_a_build_whose_collection_and_items_disagree(tmp_path, monkeypatch, capsys,
                                                                links, why):
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b, "y": b}, pub_links=["x"])
    _edit(tmp_path / "build" / "collection.json",
          lambda c: c.__setitem__("links", [l for l in c["links"] if l["rel"] != "item"]
                                  + [{"rel": "item", "href": f"{k}.json"} for k in links]))
    assert _main(monkeypatch, argv) == 1
    assert why in capsys.readouterr().out


def test_main_fails_an_extent_change_with_nothing_new_even_one_that_widens(tmp_path, monkeypatch):
    """The build's extent is its items' envelope, and wider than the published: with nothing
    new that is a change, though with something new it would be allowed."""
    b = _built()
    argv = _tree(tmp_path, {"x": _published(b)}, {"x": b})
    _edit(tmp_path / "published" / "collection.json",
          lambda c: c["extent"]["spatial"]["bbox"][0].__setitem__(0, b["bbox"][0] + 0.5))
    assert _main(monkeypatch, argv) == 1
