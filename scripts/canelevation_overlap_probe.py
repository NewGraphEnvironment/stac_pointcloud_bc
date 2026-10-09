"""Which LidarBC .laz does NRCan's CanElevation point cloud series republish (#6)?

Four steps, each printing its own counts:

1. List every .laz on the LidarBC objectstore and under CanElevation's `BC/` and `NRCAN/`
   prefixes, and match the two by file name with `.copc` and `.laz` stripped.
2. Read the headers of a seeded sample of name-matched pairs (10 per CanElevation
   project) and compare point count and bounding box. Point format and LAS version are
   reported, not compared: COPC requires LAS 1.4 format 6-8, so a converted 1.2 file
   differs there. (The CRS differs too, in its vertical part; see the research file.)
3. For CanElevation files on a LidarBC tile id but under another name, read both
   headers (a seeded sample of 10) to see whether they are the same points.
4. For the CanElevation BC projects with no name match, read every header and look for a
   LidarBC 2022-2024 `pointcloud/` file on the candidate sheets with the same point count
   and a bounding box within 1 m.

Usage:
    uv run python scripts/canelevation_overlap_probe.py OUTDIR

OUTDIR receives the listings and headers as JSON, so a rerun of the comparison need not
re-list.
"""

import collections
import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import requests
from laz_item import CANELEVATION, canelevation_keys_list, header_read, keys_list

CE = CANELEVATION + "/"
LIDARBC = "https://nrs.objectstore.gov.bc.ca/gdwuts"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
SEED = 6
# CanElevation BC projects whose file names match nothing on LidarBC. Skeena_Terrace_2023
# is in the bucket but missing from CanElevation's project index (measured 2026-10-09).
UNMATCHED = ("BC/Hope_TB_2023", "BC/Shuswap_TB_2023", "BC/Skeena_Terrace_2023",
             "NRCAN/FHIMP_PICAI_BC_South_East_UTM11_2023",
             "NRCAN/FHIMP_PICAI_BC_South_West_UTM10_2023")
# NTS sheets whose LidarBC 2022-24 groups intersect those projects' bounding boxes in the
# project index, plus 103i (Terrace) for the project the index lacks.
SHEETS = {"082f", "082g", "082j", "082k", "082l", "082m",
          "092g", "092h", "092i", "092j", "103i"}
TILE = re.compile(r"(bc_\d{3}[a-p]\d{3}(?:_\d)+)_")


def ce_list(prefix: str) -> list[dict]:
    """Every object under `prefix` in the CanElevation bucket, keyed relative to it."""
    return [{"key": o["url"][len(CE):], "size": o["size"]}
            for o in canelevation_keys_list(prefix)]


def dump(obj, path: str) -> None:
    with open(path, "w") as fh:
        json.dump(obj, fh)


def stem(name: str) -> str:
    return re.sub(r"(\.copc)?\.laz$", "", name.rsplit("/", 1)[-1].lower())


def lidarbc_path(url: str) -> list[str]:
    """`<block>/<sheet>/<year>/<kind>/<file>` as a list."""
    return url.split("/gdwuts/", 1)[1].split("/")


def ce_project(key: str) -> str:
    return "/".join(key.split("/")[1:3])


def read(url: str) -> tuple[str, dict]:
    try:
        h = header_read(url)
        return url, {"n": h["point_count"], "mins": h["mins"], "maxs": h["maxs"],
                     "fmt": f"{h['las_version']}/{h['point_format']}"}
    except Exception as e:  # recorded and counted, never dropped
        return url, {"error": f"{type(e).__name__}: {e}"[:200]}


def box_diff(a: dict, b: dict) -> float:
    return max(abs(x - y) for x, y in zip(a["mins"] + a["maxs"], b["mins"] + b["maxs"]))


def same(a: dict, b: dict) -> bool:
    return "n" in a and "n" in b and a["n"] == b["n"] and box_diff(a, b) < 1


def headers(urls: list[str]) -> dict[str, dict]:
    with ThreadPoolExecutor(8) as ex:
        out = dict(ex.map(read, urls))
    err = [u for u, h in out.items() if "error" in h]
    print(f"  headers read {len(out)}, errors {len(err)}", flush=True)
    for u in err[:5]:
        print(f"    {u}: {out[u]['error']}")
    return out


def main(out: str) -> None:
    # 1. Listings and name match
    r = requests.get(LIDARBC, params={"delimiter": "/"}, timeout=60)
    r.raise_for_status()
    blocks = [e.text for e in
              ET.fromstring(r.content).findall(".//s3:CommonPrefixes/s3:Prefix", NS)]
    with ThreadPoolExecutor(8) as ex:
        bc_all = [o for part in ex.map(keys_list, blocks) for o in part]
    bc = [o for o in bc_all if o["url"].lower().endswith(".laz")]
    with ThreadPoolExecutor(2) as ex:
        ce = [o for part in ex.map(ce_list, ["pointclouds_nuagespoints/BC/",
                                             "pointclouds_nuagespoints/NRCAN/"])
              for o in part if o["key"].lower().endswith(".laz")]
    dump(bc, f"{out}/lidarbc_laz.json")
    dump(ce, f"{out}/canelev_laz.json")
    print(f"1. LidarBC keys {len(bc_all)}, .laz {len(bc)}; CanElevation BC/ + NRCAN/ "
          f".laz {len(ce)}")

    by_stem = collections.defaultdict(list)
    for o in bc:
        by_stem[stem(o["url"])].append(o["url"])
    pairs = [{"ce": o["key"], "bc": by_stem[stem(o["key"])]}
             for o in ce if stem(o["key"]) in by_stem]
    dump(pairs, f"{out}/pairs.json")
    print(f"   name matches {len(pairs)}; matching more than one LidarBC file "
          f"{sum(len(p['bc']) > 1 for p in pairs)}")

    n_proj = collections.Counter(ce_project(o["key"]) for o in ce)
    hit_proj = collections.Counter(ce_project(p["ce"]) for p in pairs)
    print("   CanElevation project: .laz, name-matched")
    for pr in sorted(n_proj):
        if pr.startswith("BC/") or hit_proj[pr] or "_BC_" in pr:
            print(f"     {pr}\t{n_proj[pr]}\t{hit_proj[pr]}")
    n_grp = collections.Counter("/".join(lidarbc_path(o["url"])[:4]) for o in bc)
    hit_grp = collections.Counter("/".join(lidarbc_path(u)[:4]) for p in pairs for u in p["bc"])
    print("   LidarBC group: name-matched / all .laz")
    for g in sorted(hit_grp):
        print(f"     {g}\t{hit_grp[g]}/{n_grp[g]}")
    print(f"   LidarBC .laz with a CanElevation copy by name: {sum(hit_grp.values())} "
          f"of {len(bc)}")

    # 2. Header sample of name-matched pairs
    rng = random.Random(SEED)
    by_proj = collections.defaultdict(list)
    for p in pairs:
        by_proj[ce_project(p["ce"])].append(p)
    sample = [q for pr in sorted(by_proj) for q in rng.sample(by_proj[pr], 10)]
    print("2. Header sample of name-matched pairs")
    h = headers([CE + p["ce"] for p in sample] + [p["bc"][0] for p in sample])
    for pr in sorted(by_proj):
        rows = [p for p in sample if ce_project(p["ce"]) == pr]
        n_same = sum(same(h[CE + p["ce"]], h[p["bc"][0]]) for p in rows)
        fmts = collections.Counter(f"{h[p['bc'][0]].get('fmt')} -> {h[CE + p['ce']].get('fmt')}"
                                   for p in rows)
        print(f"   {pr}: {n_same}/{len(rows)} same point count and box; "
              f"LAS/format {dict(fmts)}")

    # 3. Same tile id, different name
    matched = {p["ce"] for p in pairs}
    by_tile = collections.defaultdict(list)
    for o in bc:
        m = TILE.match(lidarbc_path(o["url"])[-1].lower())
        if m and lidarbc_path(o["url"])[3] == "pointcloud":
            by_tile[m.group(1)].append(o["url"])
    other = [o["key"] for o in ce if o["key"] not in matched
             and (m := TILE.match(o["key"].rsplit("/", 1)[-1].lower())) and by_tile.get(m.group(1))]
    print(f"3. CanElevation .laz on a LidarBC pointcloud tile id under another name: "
          f"{len(other)} {dict(collections.Counter(ce_project(k) for k in other))}")
    if other:
        pick = rng.sample(other, min(10, len(other)))
        urls = [CE + k for k in pick]
        for k in pick:
            urls += by_tile[TILE.match(k.rsplit("/", 1)[-1].lower()).group(1)]
        h3 = headers(sorted(set(urls)))
        n_same = 0
        for k in pick:
            cands = by_tile[TILE.match(k.rsplit("/", 1)[-1].lower()).group(1)]
            n_same += any(same(h3[CE + k], h3[u]) for u in cands)
        print(f"   sample of {len(pick)}: {n_same} have a LidarBC file on the tile with the "
              f"same point count and box")

    # 4. Unmatched 2023 projects, by header
    ce4 = [CE + o["key"] for o in ce if ce_project(o["key"]) in UNMATCHED]
    bc4 = [o["url"] for o in bc if lidarbc_path(o["url"])[2] in ("2022", "2023", "2024")
           and lidarbc_path(o["url"])[3] == "pointcloud" and lidarbc_path(o["url"])[1] in SHEETS]
    print(f"4. Unmatched projects: CanElevation {len(ce4)} vs LidarBC 2022-24 on "
          f"candidate sheets {len(bc4)}")
    hc, hb = headers(ce4), headers(bc4)
    dump({"ce": hc, "bc": hb}, f"{out}/headers_unmatched.json")
    by_n = collections.defaultdict(list)
    for u, x in hb.items():
        if "n" in x:
            by_n[x["n"]].append(u)
    per, hit_n, hit = collections.Counter(), collections.Counter(), collections.Counter()
    grp = collections.Counter()
    for u, x in hc.items():
        pr = ce_project(u[len(CE):])
        per[pr] += 1
        cands = by_n.get(x.get("n"), [])
        hit_n[pr] += bool(cands)
        for b in cands:
            if same(x, hb[b]):
                hit[pr] += 1
                grp["/".join(lidarbc_path(b)[:3])] += 1
                break
    print("   project: files, same point count as a LidarBC file, same count and box")
    for pr in UNMATCHED:
        print(f"     {pr}\t{per[pr]}\t{hit_n[pr]}\t{hit[pr]}")
    print(f"   LidarBC groups holding a match: {dict(grp) or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1])
