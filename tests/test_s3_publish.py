"""What a publish uploads: the built items whose digest the bucket does not hold, and the
collection when anything changed. Pure functions over a listing, so no bucket is touched."""

import hashlib
import json

from collection_version import VERSION_EXT
from s3_publish import (
    CACHE_PREFIX,
    collection_differs,
    etag_md5,
    items_to_upload,
    items_unbuilt,
    local_digests,
    publish_plan,
    stage_write,
)

A, B = "a" * 32, "b" * 32


def test_a_single_part_etag_is_the_md5_and_a_multipart_one_is_nothing():
    assert etag_md5(f'"{A}"') == A
    assert etag_md5(A) == A
    assert etag_md5(f'"{A}-5"') is None
    assert etag_md5(None) is None


def test_an_item_uploads_when_its_digest_differs_is_multipart_or_is_absent():
    local = {"same.json": A, "changed.json": A, "multipart.json": A, "new.json": A}
    bucket = {"same.json": f'"{A}"', "changed.json": f'"{B}"',
              "multipart.json": f'"{A}-2"'}
    assert items_to_upload(local, bucket) == ["changed.json", "multipart.json", "new.json"]


def test_a_name_with_a_space_and_parentheses_is_its_own_key():
    name = "082-082l-2018-pointcloud-bc_082l024_2_4_3_xyes_12_utm11_2018 (2).json"
    assert items_to_upload({name: A}, {name: f'"{A}"'}) == []
    assert items_to_upload({name: A}, {name.replace(" ", "%20"): f'"{A}"'}) == [name]


def test_unbuilt_keys_are_reported_but_not_the_collection_or_the_cache():
    bucket = {"kept.json": A, "gone.json": A, "collection.json": A,
              f"{CACHE_PREFIX}headers.jsonl.gz": A}
    assert items_unbuilt({"kept.json": A}, bucket) == ["gone.json"]


def _coll(**kw):
    c = {"type": "Collection", "id": "c", "description": "d", "links": [],
         "stac_extensions": ["https://example.org/lidarbc.json"]}
    c.update(kw)
    return c


def _stamped(**kw):
    c = _coll(**kw)
    c["stac_extensions"] = c["stac_extensions"] + [VERSION_EXT]
    c["version"] = "0.3.0"
    return c


def test_an_unstamped_build_equal_to_the_published_but_for_its_stamp_is_unchanged():
    assert not collection_differs(_coll(), _stamped())


def test_an_unstamped_build_that_differs_elsewhere_is_changed():
    assert collection_differs(_coll(description="new"), _stamped())


def test_a_stamped_build_compares_its_stamp():
    newer = _stamped()
    newer["version"] = "0.4.0"
    assert collection_differs(newer, _stamped())
    assert not collection_differs(_stamped(), _stamped())


def test_a_collection_the_bucket_lacks_is_changed():
    assert collection_differs(_coll(), None)


def test_the_collection_publishes_whenever_an_item_does():
    plan = publish_plan({"new.json": A}, {}, _coll(), _stamped())
    assert plan["upload"] == ["new.json"] and plan["collection"]


def test_an_unchanged_catalogue_publishes_nothing():
    plan = publish_plan({"x.json": A}, {"x.json": f'"{A}"', "collection.json": "e-5"},
                        _coll(), _stamped())
    assert plan == {"upload": [], "unbuilt": [], "collection": False}


def test_local_digests_are_the_md5_of_each_item_file(tmp_path):
    (tmp_path / "x (2).json").write_bytes(b'{"id": "x (2)"}')
    (tmp_path / ".hidden.json").write_bytes(b"{}")
    (tmp_path / "y.json.tmp").write_bytes(b"{}")
    assert local_digests(str(tmp_path)) == {
        "x (2).json": hashlib.md5(b'{"id": "x (2)"}').hexdigest()}


def test_the_stage_holds_exactly_the_items_to_upload(tmp_path):
    items = tmp_path / "items"
    items.mkdir()
    for n in ("a.json", "b.json"):
        (items / n).write_text(json.dumps({"id": n}))
    stage = tmp_path / "upload"
    stage.mkdir()
    (stage / "stale.json").write_text("{}")  # left by an earlier plan
    stage_write(str(items), ["b.json"], str(stage))
    assert sorted(p.name for p in stage.iterdir()) == ["b.json"]
    assert (stage / "b.json").read_bytes() == (items / "b.json").read_bytes()

