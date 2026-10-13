#!/usr/bin/env bash
# Publish a built catalogue: the item JSON the bucket lacks, then collection.json.
#
# What to upload is decided by digest (scripts/s3_publish.py): an item whose MD5 the
# bucket's object already carries is not sent, and collection.json goes only when an item
# does or it changed. The same path serves a local release and the monthly run (#4).
# Items first, so a failure part-way leaves unreferenced items rather than a
# collection.json linking items that are not there (as stac_dem_bc's s3_sync-ci.sh).
# Nothing is deleted: an object the build no longer makes is reported and left.
#
# Usage: scripts/s3_sync.sh [--dryrun]    (from the repo root; uses the ambient AWS credentials)
#   --dryrun still reads the bucket to plan, and uploads nothing.
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

# Python >= 3.12 (pyproject.toml), so through uv, not the system python3.
PLAN=$(uv run --frozen python scripts/s3_publish.py --build "$BUILD" --bucket "${BUCKET#s3://}")
read -r N_UPLOAD N_UNBUILT PUB_COLLECTION <<<"$PLAN"
case "$N_UPLOAD:$N_UNBUILT:$PUB_COLLECTION" in
  *[!0-9:]*|:*|*::*|*:) echo "ERROR: unreadable publish plan: '$PLAN'" >&2; exit 1 ;;
esac

# MAX_UPLOAD, when set (the monthly run sets it), caps the items one publish may send: more is
# a rewrite of the catalogue, which is a release, not a month's growth.
if [ -n "${MAX_UPLOAD:-}" ]; then
  case "$MAX_UPLOAD" in
    *[!0-9]*|??????????*) echo "ERROR: MAX_UPLOAD must be at most 9 digits, not '$MAX_UPLOAD'" >&2; exit 2 ;;
  esac
  if [ "$N_UPLOAD" -gt "$((10#$MAX_UPLOAD))" ]; then
    echo "ERROR: $N_UPLOAD items to upload, over MAX_UPLOAD=$MAX_UPLOAD - a rewrite of the" \
         "catalogue is a release; publish it deliberately" >&2
    exit 1
  fi
fi

echo "Built $ITEMS item(s): uploading $N_UPLOAD, collection.json $([ "$PUB_COLLECTION" = 1 ] && echo yes || echo no) -> $BUCKET"
if [ "$N_UPLOAD" -gt 0 ]; then
  aws s3 cp "$BUILD/upload" "$BUCKET" --recursive --only-show-errors \
    --content-type application/json ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
fi
if [ "$PUB_COLLECTION" = 1 ]; then
  aws s3 cp "$BUILD/collection.json" "$BUCKET/collection.json" \
    --content-type application/json ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
fi
echo "Sync complete${EXTRA_ARGS[@]+ (dry run, nothing sent)}: $N_UPLOAD item(s) uploaded, collection.json $([ "$PUB_COLLECTION" = 1 ] && echo uploaded || echo unchanged), $N_UNBUILT unbuilt object(s) left in place"
