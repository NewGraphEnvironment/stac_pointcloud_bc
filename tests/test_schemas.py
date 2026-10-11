"""The checked-in crate schemas (crate#23) are the published ones, and the build reads them."""

import json

import pystac
import pystac.validation
import pytest
import requests

import laz_item
from test_laz_item import COLL, PC, _add, _copc_header, _header


@pytest.mark.parametrize("url", sorted(laz_item.SCHEMA_FILES))
def test_each_copy_is_the_published_file_byte_for_byte(url):
    """A published version never changes, so this fails only if a copy was edited by hand."""
    try:
        r = requests.get(url, timeout=15)
    except (requests.ConnectionError, requests.Timeout) as e:
        pytest.skip(f"offline: {e}")
    if r.status_code >= 500:
        pytest.skip(f"{url} returned {r.status_code}")
    assert r.status_code == 200
    with open(laz_item.SCHEMA_FILES[url], "rb") as fh:
        assert fh.read() == r.content


def test_each_copy_names_its_published_url_as_its_id():
    for url, path in laz_item.SCHEMA_FILES.items():
        with open(path) as fh:
            assert json.load(fh)["$id"] == url


def test_validation_reads_the_copies_not_the_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a validate() fetched a schema")
    cache = pystac.validation.RegisteredValidator.get_validator().schema_cache
    for url in laz_item.SCHEMA_FILES:
        cache.pop(url, None)
    laz_item.schemas_preload()
    monkeypatch.setattr(pystac.StacIO.default(), "read_text", refuse)
    for url in laz_item.SCHEMA_FILES:
        assert url in cache
    # A custom field off its type fails on the copy alone.
    d = laz_item.item_create(PC, _header(), COLL).to_dict()
    d["properties"]["las:point_format"] = 11
    with pytest.raises(pystac.errors.STACValidationError):
        pystac.validation.validate_dict(d)


@pytest.mark.parametrize("key, value", [("lidarbc:datetime_source", "header"),
                                        ("lidarbc:unknown", "x"), ("las:version", 1.2),
                                        ("lidarbc:delivery", "092/092G/2016")])
def test_the_schemas_refuse_what_crate_says_they_refuse(key, value):
    d = laz_item.item_create(PC, _header(), COLL).to_dict()
    d["properties"][key] = value
    with pytest.raises(pystac.errors.STACValidationError):
        pystac.validation.validate_dict(d)


def test_a_copc_asset_las_field_is_typed_too():
    d = _add(_copc_header()).to_dict()
    d["assets"]["copc"]["las:point_format"] = "6"
    with pytest.raises(pystac.errors.STACValidationError):
        pystac.validation.validate_dict(d)


@pytest.mark.parametrize("drop", list(laz_item.FIELDS_ITEM))
def test_the_build_checks_its_own_fields_are_present(drop):
    d = laz_item.item_create(PC, _header(), COLL).to_dict()
    laz_item.fields_check(d)
    d["properties"].pop(drop)
    with pytest.raises(ValueError, match=f"missing {drop}"):
        laz_item.fields_check(d)


def test_an_empty_field_is_missing_and_copc_fields_are_required():
    d = _add(_copc_header()).to_dict()
    laz_item.fields_check(d)
    d["assets"]["copc"].pop("las:version")
    with pytest.raises(ValueError, match="missing copc.las:version"):
        laz_item.fields_check(d)
    d = laz_item.item_create(PC, _header(), COLL).to_dict()
    d["properties"]["lidarbc:product"] = ""
    with pytest.raises(ValueError, match="missing lidarbc:product"):
        laz_item.fields_check(d)


def test_a_filename_date_is_required_where_the_date_came_from_it():
    d = laz_item.item_create(PC.replace("/2016/", "/2017/"), _header(), COLL).to_dict()
    assert d["properties"]["lidarbc:datetime_source"] == "filename"
    d["properties"].pop("lidarbc:filename_date")
    with pytest.raises(ValueError, match="missing lidarbc:filename_date"):
        laz_item.fields_check(d)
