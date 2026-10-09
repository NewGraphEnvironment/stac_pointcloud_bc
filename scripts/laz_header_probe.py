"""Measure what a header-only read of a remote .laz costs, and what it yields.

For each URL: bytes transferred, range requests, wall time, point count, bounds, CRS,
point format and LAS version. With --points N it also decompresses the first N points
and tabulates their classification and return numbers (that read costs more bytes, and
is reported separately).

Usage:
    uv run python scripts/laz_header_probe.py URLS_FILE [--points 200000]
"""

import argparse
import collections
import sys
import time

import laspy

from laz_remote import HttpRangeFile


def probe(url: str, n_points: int = 0) -> dict:
    f = HttpRangeFile(url)
    t0 = time.monotonic()
    with laspy.open(f) as reader:
        h = reader.header
        crs = h.parse_crs()
        rec = {
            "url": url,
            "size_mb": round(f.size / 1e6, 1),
            "header_bytes": f.bytes_fetched,
            "header_requests": f.requests,
            "header_s": round(time.monotonic() - t0, 2),
            "version": str(h.version),
            "point_format": h.point_format.id,
            "points": h.point_count,
            "mins": [round(v, 2) for v in h.mins],
            "maxs": [round(v, 2) for v in h.maxs],
            "crs": crs.to_string() if crs else None,
            "vlrs": [v.description or type(v).__name__ for v in h.vlrs],
            "evlrs": len(reader.evlrs or []) if hasattr(reader, "evlrs") else None,
        }
        if n_points:
            before = f.bytes_fetched
            t1 = time.monotonic()
            pts = reader.read_points(min(n_points, h.point_count))
            rec["points_read"] = len(pts)
            rec["points_bytes"] = f.bytes_fetched - before
            rec["points_s"] = round(time.monotonic() - t1, 2)
            rec["classification"] = dict(collections.Counter(int(c) for c in pts.classification).most_common())
            rec["return_number"] = dict(collections.Counter(int(c) for c in pts.return_number).most_common())
            rec["number_of_returns"] = dict(collections.Counter(int(c) for c in pts.number_of_returns).most_common())
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("urls_file")
    ap.add_argument("--points", type=int, default=0)
    args = ap.parse_args()
    urls = [u.strip() for u in open(args.urls_file) if u.strip()]
    for url in urls:
        try:
            print(probe(url, args.points), flush=True)
        except Exception as e:  # a probe reports every file, failures included
            print({"url": url, "error": f"{type(e).__name__}: {e}"}, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
