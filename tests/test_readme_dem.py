"""The gridding behind the landing page's DEM (scripts/readme_dem.py, #9)."""

import numpy as np
import pytest

from readme_dem import fill_small_gaps, grid

BOX = (100.0, 200.0, 106.0, 204.0)  # 6 m by 4 m: 3 columns, 2 rows of 2 m cells


def test_grid_mean_puts_row_zero_at_the_north_edge():
    x = np.array([101.0, 101.0, 105.0])
    y = np.array([203.0, 203.5, 201.0])  # two in the NW cell, one in the SE cell
    z = np.array([10.0, 20.0, 7.0])
    g = grid(x, y, z, BOX, 2.0, "mean")
    assert g.shape == (2, 3)
    assert g[0, 0] == 15.0
    assert g[1, 2] == 7.0
    assert np.isnan(g).sum() == 4


def test_grid_max_and_points_outside_the_box_are_dropped():
    x = np.array([101.0, 101.5, 99.0, 106.0])  # the last two sit on or past the west/east edges
    y = np.array([201.0, 201.0, 201.0, 201.0])
    z = np.array([3.0, 9.0, 100.0, 100.0])
    g = grid(x, y, z, BOX, 2.0, "max")
    assert g[1, 0] == 9.0
    assert np.nanmax(g) == 9.0


def test_grid_refuses_an_unknown_reduction():
    with pytest.raises(ValueError):
        grid(np.array([101.0]), np.array([201.0]), np.array([1.0]), BOX, 2.0, "median")


def test_fill_closes_a_small_hole_and_leaves_a_wide_gap():
    a = np.ones((9, 9))
    a[2, 2] = np.nan  # one missing cell inside ground
    a[:, 6:] = np.nan  # a band 3 cells wide, like a river at the edge
    out = fill_small_gaps(a, passes=1)
    assert out[2, 2] == 1.0
    assert np.isnan(out[:, 7:]).all()  # one pass reaches one cell in, no further
    assert np.isnan(a[2, 2])  # the input is not modified
