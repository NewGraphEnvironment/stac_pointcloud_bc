#!/usr/bin/env bash
# Publish a built catalogue: item JSON first, then collection.json.
#
# Items first, so a failure part-way leaves unreferenced items rather than a
# collection.json linking items that are not there (as stac_dem_bc's s3_sync-ci.sh).
#
# Usage: scripts/s3_sync.sh [--dryrun]    (from the repo root; uses the ambient AWS credentials)
set -euo pipefail

BUILD="data/build"
BUCKET="s3://stac-pointcloud-bc"
EXTRA_ARGS=()
# A preview flag must preview: anything but no argument or exactly --dryrun is refused,
# so a mistyped `--dry-run` cannot publish.
case "$#:${1:-}" in
  0:) ;;
  1:--dryrun) EXTRA_ARGS+=(--dryrun) ;;
  *) echo "usage: $0 [--dryrun]" >&2; exit 2 ;;
esac

[ -s "$BUILD/collection.json" ] || { echo "ERROR: $BUILD/collection.json missing or empty" >&2; exit 1; }
[ -d "$BUILD/items" ] || { echo "ERROR: $BUILD/items missing" >&2; exit 1; }

# The collection must link exactly the item files being uploaded -- as SETS, not counts.
# An id is read back from a link the way stacs reads it: the file name, %20 decoded.
ITEMS=$(python3 - "$BUILD" <<'PY'
import json, os, sys
build = sys.argv[1]
c = json.load(open(os.path.join(build, "collection.json")))
linked = {l["href"].rsplit("/", 1)[1].replace("%20", " ")
          for l in c["links"] if l["rel"] == "item"}
files = {f for f in os.listdir(os.path.join(build, "items")) if f.endswith(".json")}
if linked != files:
    print(f"ERROR: collection.json and {build}/items disagree: "
          f"{len(linked - files)} linked but absent, {len(files - linked)} present but unlinked",
          file=sys.stderr)
    sys.exit(1)
print(len(files))
PY
)

echo "Uploading $ITEMS item JSON(s), then collection.json -> $BUCKET"
aws s3 sync "$BUILD/items" "$BUCKET" --exclude ".*" --exclude "*.tmp" \
  --content-type application/json ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
aws s3 cp "$BUILD/collection.json" "$BUCKET/collection.json" \
  --content-type application/json ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
echo "Sync complete: $ITEMS item(s) + collection.json"
