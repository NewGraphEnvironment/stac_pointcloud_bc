import pytest

from collection_version import VERSION_EXT, version_stamp


def test_stamp_adds_the_extension_once_and_the_version():
    c = version_stamp({"stac_extensions": [VERSION_EXT]}, "0.1.0")
    assert c["version"] == "0.1.0" and c["stac_extensions"] == [VERSION_EXT]


@pytest.mark.parametrize("bad", ["", None, "v0.1.0", "0.1", "0.0.0.9000"])
def test_a_version_that_is_not_x_y_z_is_refused(bad):
    with pytest.raises(ValueError, match="not X.Y.Z"):
        version_stamp({}, bad)
