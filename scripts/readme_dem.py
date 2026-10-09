"""From a STAC search to a bare-earth DEM, for the landing page (#9).

Finds the items covering a window over the lower Kanaka Creek, reads only that window from
each item's `copc` asset over HTTPS, and grids its ground returns into a hillshaded DEM.
Writes fig/kanaka_dem.png and data/readme_dem.json, which
README.Rmd reads. Run by README.Rmd when it renders with `update_query = TRUE`:

    uv run --group readme python scripts/readme_dem.py
"""

import json
import sys
from pathlib import Path

import numpy as np
from laspy import Bounds, CopcReader
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).parent))
from laz_remote import HttpRangeFile  # noqa: E402  counts the bytes each read transfers

API = "https://images.a11s.one"
COLLECTION = "stac-pointcloud-bc"
# Kanaka Creek's mouth on the Fraser (Freshwater Atlas: the downstream end of its main stem,
# which the atlas routes to the Fraser's centreline).
MOUTH_LON, MOUTH_LAT = -122.58946, 49.19945
# The window, in metres from that point: north and east, over the creek's lower channel.
WEST, EAST, SOUTH, NORTH = 300, 1300, 200, 1000
CELL = 2.0  # m. Ground returns here are ~0.4 per m², so 1 m cells would be mostly empty.
GROUND = 2  # ASPRS class


def window_items(client, crs: str, x: float, y: float) -> tuple[list, tuple]:
    """The items whose footprint meets the window, and the window in `crs`."""
    box = (x - WEST, y - SOUTH, x + EAST, y + NORTH)
    to_ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    ring = [to_ll.transform(px, py) for px, py in
            [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]), (box[0], box[1])]]
    search = client.search(collections=[COLLECTION],
                           intersects={"type": "Polygon", "coordinates": [ring]})
    return sorted(search.items(), key=lambda i: i.id), box


def grid(x, y, v, box, cell, how):
    """Per-cell mean or max of `v` on a grid over `box`; NaN where no point fell."""
    nx = int(round((box[2] - box[0]) / cell))
    ny = int(round((box[3] - box[1]) / cell))
    col = np.floor((x - box[0]) / cell).astype(int)
    row = np.floor((box[3] - y) / cell).astype(int)  # row 0 is the north edge
    keep = (col >= 0) & (col < nx) & (row >= 0) & (row < ny)
    idx = row[keep] * nx + col[keep]
    v = v[keep]
    if how == "mean":
        s = np.bincount(idx, weights=v, minlength=nx * ny)
        n = np.bincount(idx, minlength=nx * ny)
        out = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    elif how == "max":
        out = np.full(nx * ny, -np.inf)
        np.maximum.at(out, idx, v)
        out[np.isinf(out)] = np.nan
    else:
        raise ValueError(how)
    return out.reshape(ny, nx)


def fill_small_gaps(a, passes):
    """Fill NaN cells from their 3x3 neighbours' mean, `passes` times.

    Each pass closes about one cell from every side, so gaps under buildings close while a
    wide one, such as the Fraser, where water gives almost no returns, stays NaN rather than
    being smeared across.
    """
    a = a.copy()
    for _ in range(passes):
        p = np.pad(a, 1, constant_values=np.nan)
        nb = np.stack([p[1 + dr:p.shape[0] - 1 + dr, 1 + dc:p.shape[1] - 1 + dc]
                       for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)])
        n = np.sum(~np.isnan(nb), axis=0)
        m = np.nansum(nb, axis=0) / np.maximum(n, 1)
        hole = np.isnan(a) & (n >= 3)
        if not hole.any():
            break
        a[hole] = m[hole]
    return a


def main() -> None:
    from pystac_client import Client

    # --- shown on the landing page: begin
    client = Client.open(API)
    # Several deliveries can cover one place. Take the earliest item at the mouth that has a
    # copc (ids sort by sheet, then year), and read only its delivery: two flights averaged
    # into one grid would be neither.
    at_mouth = sorted((i for i in client.search(
        collections=[COLLECTION],
        intersects={"type": "Point", "coordinates": [MOUTH_LON, MOUTH_LAT]}).items()
        if "copc" in i.assets), key=lambda i: i.id)
    if not at_mouth:
        sys.exit("no item with a copc asset covers the mouth")
    year = at_mouth[0].properties["start_datetime"][:4]
    crs = at_mouth[0].properties["proj:code"]
    x0, y0 = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(MOUTH_LON, MOUTH_LAT)
    items, box = window_items(client, crs, x0, y0)
    items = [i for i in items if i.properties["start_datetime"][:4] == year]
    if any("copc" not in i.assets for i in items):
        # A laz-only tile would have to be downloaded whole; this demo is the windowed read.
        sys.exit("an item in the window has no copc asset: " +
                 ", ".join(i.id for i in items if "copc" not in i.assets))
    if any(i.properties["proj:code"] != crs for i in items):
        sys.exit("items in the window do not share one CRS")

    xs, ys, zs, cls = [], [], [], []
    fetched = size = 0
    ground_only = []
    for it in items:
        f = HttpRangeFile(it.assets["copc"].href)
        with CopcReader(f) as rd:
            # Only the COPC octree nodes that meet the window are fetched.
            pts = rd.query(bounds=Bounds(mins=np.array(box[:2]), maxs=np.array(box[2:])))
        xs.append(np.asarray(pts.x))
        ys.append(np.asarray(pts.y))
        zs.append(np.asarray(pts.z))
        cls.append(np.asarray(pts.classification))
        fetched += f.bytes_fetched
        size += f.size
        if len(pts) and np.all(cls[-1] == GROUND):
            ground_only.append(it.id)
    x, y, z, c = (np.concatenate(a) for a in (xs, ys, zs, cls))
    # --- shown on the landing page: end
    g = c == GROUND
    if g.sum() == 0:
        sys.exit("no ground returns in the window")

    dem = fill_small_gaps(grid(x[g], y[g], z[g], box, CELL, "mean"), passes=10)
    plot(dem, box)
    out = {
        "items": [i.id for i in items],
        "copc": [i.assets["copc"].href for i in items],
        "crs": crs,
        "window_m": [WEST + EAST, SOUTH + NORTH],
        "cell_m": CELL,
        "points": int(len(x)),
        "ground_points": int(g.sum()),
        "bytes_read": int(fetched),
        "bytes_files": int(size),
        # Items whose points in the window are all ground: a delivery can carry no vegetation
        # or buildings at all, so nothing above the ground can be measured from it.
        "ground_only_items": ground_only,
        "elevation_m": [round(float(np.nanmin(dem)), 1), round(float(np.nanmax(dem)), 1)],
    }
    Path("data/readme_dem.json").write_text(json.dumps(out, indent=2) + "\n")


def plot(dem, box, path="fig/kanaka_dem.png"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource, ListedColormap

    ext = [0, box[2] - box[0], 0, box[3] - box[1]]
    water = np.isnan(dem)
    # Shade a surface filled right across the water, then paint the water over it. Filling
    # with one constant instead puts a cliff at every bank, which shades black.
    filled = fill_small_gaps(dem, passes=max(dem.shape))
    filled = np.where(np.isnan(filled), np.nanmin(dem), filled)
    lo, hi = np.nanpercentile(dem, [1, 99])
    # gist_earth starts at black, which is where banks just below `lo` land; start past it.
    cmap = ListedColormap(plt.get_cmap("gist_earth")(np.linspace(0.15, 1.0, 256)))
    cmap.set_under(cmap(0))
    rgb = LightSource(azdeg=315, altdeg=45).shade(
        filled, cmap=cmap, vert_exag=3, dx=CELL, dy=CELL,
        blend_mode="soft", vmin=lo, vmax=hi)
    rgb[water] = (0.78, 0.86, 0.94, 1.0)
    fig, ax = plt.subplots(figsize=(9, 9 * ext[3] / ext[1]), constrained_layout=True)
    ax.imshow(rgb, extent=ext)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(lo, hi))
    fig.colorbar(sm, ax=ax, shrink=0.6, label="ground elevation (m)")
    ax.plot([50, 550], [60, 60], color="black", lw=2)
    ax.text(300, 90, "500 m", ha="center", fontsize=8)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
