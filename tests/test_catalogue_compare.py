"""The published-vs-build check (#2): this release's changes pass, anything else is named."""

import copy

import pytest

import catalogue_compare as cc
import laz_item
from test_laz_item import COLL, PC, _add, _copc_header, _full, _header


def _published(built: dict) -> dict:
    """A built item as 0.2.0 published it: `nge:` names, no delivery, no crate schemas, no
    class list."""
    p = copy.deepcopy(built)
    p.pop("links", None)
    old = {v: k for k, v in cc.RENAMES.items()}
    p["properties"] = {old.get(k, k): v for k, v in p["properties"].items()
                       if k != "lidarbc:delivery"}
    for a in p["assets"].values():
        for k in [k for k in a if k in old]:
            a[old[k]] = a.pop(k)
        a.pop("classification:classes", None)
    p["stac_extensions"] = [e for e in p["stac_extensions"] if e not in
                            (laz_item.SCHEMA_LIDARBC, laz_item.SCHEMA_LAS, cc.SCHEMA_CLASSIFICATION)]
    return p


def _built(classes=False):
    it = _add(_copc_header())
    if classes:
        laz_item.classes_add(it, _full({2: 1000}))
    d = it.to_dict(include_self_link=False)
    d.pop("links")
    return d


@pytest.mark.parametrize("classes", [False, True])
def test_this_releases_changes_and_nothing_else_pass(classes):
    b = _built(classes)
    assert cc.item_expected_diff(_published(b), b) == []


@pytest.mark.parametrize("mutate, why", [
    (lambda b: b["properties"].__setitem__("lidarbc:delivery", "092/092h/2016"), "not the key's"),
    (lambda b: b["properties"].__setitem__("pc:count", 7), "pc:count"),
    (lambda b: b["assets"]["copc"].__setitem__("las:version", "1.2"), "copc"),
    (lambda b: b["assets"].pop("copc"), "copc"),
    (lambda b: b["stac_extensions"].append("https://x/schema.json"), "beyond this release"),
    (lambda b: b["stac_extensions"].remove(laz_item.SCHEMA_LAS), "lacks a crate schema"),
    (lambda b: b["properties"].__setitem__("end_datetime", "2030-01-01T00:00:00Z"), "end_datetime"),
])
def test_any_other_difference_is_named(mutate, why):
    b = _built()
    p = _published(b)
    mutate(b)
    assert why in "; ".join(cc.item_expected_diff(p, b))


def test_a_class_list_without_its_extension_url_or_the_reverse_is_named():
    b = _built(classes=False)
    p = _published(b)
    b["stac_extensions"].append(cc.SCHEMA_CLASSIFICATION)
    assert "beyond this release" in "; ".join(cc.item_expected_diff(p, b))


def test_the_collection_must_keep_every_published_item_link():
    pub = {"links": [{"rel": "item", "href": "a"}, {"rel": "item", "href": "b"}]}
    built = {"links": [{"rel": "item", "href": "a"}, {"rel": "related", "href": "r"}]}
    problems, changes = cc.collection_diff(pub, built)
    assert problems == ["1 published item links not in the build"]
    assert "related links: ['r']" in changes
