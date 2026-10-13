#!/usr/bin/env python3
"""Plan a publish of data/build: the items the bucket does not already hold, by digest.

A built item is uploaded when the bucket has no object of its name, or one whose ETag is not
the item file's MD5. Every item JSON is far under the CLI's 8 MB multipart threshold, so a
current upload's ETag is its MD5 (SSE-S3, measured 2026-10-12, #4); a multipart ETag is not
an MD5 and is treated as different. `aws s3 sync` cannot do this on a fresh runner: every file
there is newer than its object, so it re-uploaded all 174k items (95 min).

The collection is published when any item is, or when it differs from the published one.
The release stamp (`version`, collection_version.py) is compared only when the build carries
one: an unstamped build equal to the published collection but for its stamp is the same
catalogue, so a month with nothing new leaves the stamp in place. Published, an unstamped
collection drops it, as stac_dem_bc's --clear-version does: the catalogue is no longer the
release.

Objects in the bucket that the build no longer makes are reported, never deleted (the CI role
cannot delete, rtj#362), and `build-cache/` (scripts/cache_sync.sh) is not an item.

Writes the items to upload as hard links in a stage directory, the plan to
`<build>/publish_plan.json`, and one line to stdout, `<upload> <unbuilt> <collection 0|1>`,
for scripts/s3_sync.sh. Reads the bucket and nothing else.

Usage: python3 scripts/s3_publish.py [--build data/build] [--bucket stac-pointcloud-bc]
"""

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys

from collection_version import VERSION_EXT

CACHE_PREFIX = "build-cache/"
COLLECTION = "collection.json"


def etag_md5(etag: str | None) -> str | None:
    """The MD5 a single-part ETag is; None for a multipart ETag (`<md5>-<parts>`) or none."""
    if not etag:
        return None
    e = etag.strip('"')
    return None if "-" in e else e


def items_to_upload(local: dict[str, str], bucket: dict[str, str]) -> list[str]:
    """Built item file names whose MD5 the bucket's object of that name does not carry."""
    return sorted(n for n, md5 in local.items() if etag_md5(bucket.get(n)) != md5)


def items_unbuilt(local: dict[str, str], bucket: dict[str, str]) -> list[str]:
    """Bucket keys that are neither a built item, the collection, nor the build cache."""
    return sorted(k for k in bucket
                  if k not in local and k != COLLECTION and not k.startswith(CACHE_PREFIX))


def _unstamped(c: dict) -> dict:
    c = copy.deepcopy(c)
    c.pop("version", None)
    c["stac_extensions"] = [e for e in c.get("stac_extensions", []) if e != VERSION_EXT]
    return c


def collection_differs(built: dict, published: dict | None) -> bool:
    """Whether the built collection says anything the published one does not. Its stamp
    counts only when the build carries one."""
    if published is None:
        return True
    if "version" in built:
        return built != published
    return _unstamped(built) != _unstamped(published)


def publish_plan(local: dict[str, str], bucket: dict[str, str], built: dict,
                 published: dict | None) -> dict:
    upload = items_to_upload(local, bucket)
    return {"upload": upload, "unbuilt": items_unbuilt(local, bucket),
            "collection": bool(upload) or collection_differs(built, published)}


def local_digests(items_dir: str) -> dict[str, str]:
    """Item file name -> MD5, for every `*.json` not hidden (s3_sync.sh's exclusions)."""
    out = {}
    for n in os.listdir(items_dir):
        if n.endswith(".json") and not n.startswith("."):
            with open(os.path.join(items_dir, n), "rb") as fh:
                out[n] = hashlib.file_digest(fh, "md5").hexdigest()
    return out


def bucket_listing(bucket: str) -> dict[str, str]:
    """Every key in the bucket -> its ETag, in one CLI call (it pages itself)."""
    r = subprocess.run(["aws", "s3api", "list-objects-v2", "--bucket", bucket,
                        "--query", "Contents[].[Key, ETag]", "--output", "json"],
                       check=True, capture_output=True, text=True)
    return {k: e for k, e in (json.loads(r.stdout) or [])}


def published_collection(bucket: str, listed: dict[str, str]) -> dict | None:
    """The published collection, or None when the listing has none. Fetched only when listed,
    so a failed fetch is a failure, not an absent collection."""
    if COLLECTION not in listed:
        return None
    r = subprocess.run(["aws", "s3", "cp", f"s3://{bucket}/{COLLECTION}", "-"],
                       check=True, capture_output=True)
    return json.loads(r.stdout)


def stage_write(items_dir: str, names: list[str], stage: str) -> None:
    """Make `stage` hold exactly `names`, hard-linked from `items_dir`."""
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    for n in names:
        os.link(os.path.join(items_dir, n), os.path.join(stage, n))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--bucket", default="stac-pointcloud-bc")
    args = ap.parse_args()
    items_dir = os.path.join(args.build, "items")
    local = local_digests(items_dir)
    listed = bucket_listing(args.bucket)
    with open(os.path.join(args.build, COLLECTION)) as fh:
        built = json.load(fh)
    plan = publish_plan(local, listed, built, published_collection(args.bucket, listed))
    stage_write(items_dir, plan["upload"], os.path.join(args.build, "upload"))
    with open(os.path.join(args.build, "publish_plan.json"), "w") as fh:
        json.dump({"built": len(local), "upload": len(plan["upload"]),
                   "unbuilt": len(plan["unbuilt"]), "collection": plan["collection"],
                   "unbuilt_keys": plan["unbuilt"]}, fh, indent=1)
    print(f"{len(local)} items built, {len(listed)} objects in s3://{args.bucket}: "
          f"{len(plan['upload'])} to upload, collection {'changed' if plan['collection'] else 'unchanged'}",
          file=sys.stderr)
    if plan["unbuilt"]:
        print(f"WARNING: {len(plan['unbuilt'])} objects in the bucket are no built item and are "
              f"left in place (not deleted): {', '.join(plan['unbuilt'][:5])}", file=sys.stderr)
    print(len(plan["upload"]), len(plan["unbuilt"]), int(plan["collection"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
