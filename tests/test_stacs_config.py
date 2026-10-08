"""stacs.toml is this catalogue's declaration to stacs, and a second copy of values
scripts/laz_item.py defines. Each is pinned to its module here, so a collection id or
bucket changed in one place fails rather than registering against the wrong target.

The audit tests run the installed `stacs` CLI in process against items built by
`item_create`, so they prove the config is wired, not just present.
"""

import json
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from pyproj import CRS

# A hard import, not importorskip: an environment built without stacs must fail here.
import stacs
from stacs.cli import ConfigError, main as stacs_main, read_config

import laz_item

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "stacs.toml"
STACS_VERSION = "0.1.1"


@pytest.fixture(scope="module")
def cfg():
    return read_config(str(CONFIG))


def _locked_stacs_tag():
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    (pkg,) = [p for p in lock["package"] if p["name"] == "stacs"]
    (tag,) = parse_qs(urlsplit(pkg["source"]["git"]).query)["tag"]
    return tag


def test_every_install_path_pins_the_same_stacs_tag():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["tool"]["uv"]["sources"]["stacs"]["tag"] == f"v{STACS_VERSION}"
    assert _locked_stacs_tag() == f"v{STACS_VERSION}"
    assert stacs.__version__ == STACS_VERSION


def test_collection_id_is_the_modules(cfg):
    assert cfg["catalogue"]["collection_id"] == laz_item.COLLECTION_ID


def test_bucket_url_is_the_modules(cfg):
    assert cfg["catalogue"]["bucket_url"] == laz_item.PATH_S3_STAC


def test_required_asset_is_the_modules(cfg):
    assert cfg["assets"]["require"] == laz_item.ASSET_LAZ


def test_the_password_is_named_never_given(cfg, tmp_path):
    assert cfg["transport"]["password_env"] == "POSTGRES_PASSWORD"
    leaky = tmp_path / "stacs.toml"
    leaky.write_text(CONFIG.read_text().replace("[transport]\n", "[transport]\npassword = \"x\"\n", 1))
    with pytest.raises(ConfigError, match=r"unknown key\(s\) in \[transport\]: password$"):
        read_config(str(leaky))


def _item(drop_asset=False):
    url = f"{laz_item.PATH_S3}/092/092g/2016/pointcloud/bc_092g019_1_4_1_xyes_8_utm10_20170713.laz"
    header = {
        "header_version": laz_item.HEADER_VERSION,
        "las_version": "1.2", "point_format": 1, "point_count": 10,
        "mins": [547410.45, 5441555.91, 2.2], "maxs": [549246.4, 5442961.42, 100.49],
        "crs_wkt": CRS.from_epsg(3157).to_wkt(), "file_size": 1,
        "dimensions": [("X", 32, "SignedInteger")],
    }
    d = laz_item.item_create(url, header, f"{laz_item.PATH_S3_STAC}/collection.json") \
        .to_dict(include_self_link=False)
    if drop_asset:
        d["assets"] = {}
    return d


def _audit(tmp_path, capsys, item):
    d = tmp_path / "items"
    d.mkdir()
    (d / f"{item['id']}.json").write_text(json.dumps(item))
    capsys.readouterr()
    rc = stacs_main(["audit", "--config", str(CONFIG), "--dir", str(d)])
    return rc, capsys.readouterr().err


def test_an_item_as_built_passes_the_audit(tmp_path, capsys):
    rc, err = _audit(tmp_path, capsys, _item())
    assert rc == 0, err


def test_an_item_without_the_laz_asset_fails_the_audit(tmp_path, capsys):
    rc, err = _audit(tmp_path, capsys, _item(drop_asset=True))
    assert rc != 0
    assert laz_item.ASSET_LAZ in err
