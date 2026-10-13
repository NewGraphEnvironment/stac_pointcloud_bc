#!/usr/bin/env bash
# Move the build's read caches to and from s3://stac-pointcloud-bc/build-cache/ (#4).
#
# The build reads every header, COPC header and class sample it has not cached at the
# file's current ETag. Cold, that is about 2.5 h of headers and 3 h of samples, more than a
# GitHub runner's 6 h, so the monthly run starts from these. They hold reads of public
# files, nothing published, so they live beside the catalogue (gzipped, about 20 MB).
#
#   pull   fetch each cache. Where data/build already has one (a local build), the two are
#          merged, local lines first: every reader keeps a key's last line and re-checks its
#          ETag, so a merge loses no read and adds none that is not checked.
#   push   upload each cache, refusing one with fewer lines than were pulled, and refusing
#          to replace a remote cache that is not the one this tree last pulled or pushed (by
#          ETag), so a local push cannot drop the reads a monthly run made. An unchanged cache
#          is not uploaded.
#
# Usage: scripts/cache_sync.sh pull|push [--dryrun]   (from the repo root; ambient AWS credentials)
set -euo pipefail

BUILD="data/build"
BUCKET="stac-pointcloud-bc"
PREFIX="build-cache"
# laz_classes_probe.CLASSES_SAMPLE and CLASSES_FULL, and catalogue_build's two header caches.
FILES=(headers.jsonl copc_headers.jsonl classes.jsonl classes_full.jsonl)
PULLED="$BUILD/cache_pulled"   # the last pulled or pushed <file>.gz, its .lines and .etag
EXTRA_ARGS=()
case "$#:${1:-}:${2:-}" in
  1:pull:|1:push:) ;;
  2:pull:--dryrun|2:push:--dryrun) EXTRA_ARGS+=(--dryrun) ;;
  *) echo "usage: $0 pull|push [--dryrun]" >&2; exit 2 ;;
esac
MODE="$1"
mkdir -p "$BUILD" "$PULLED"

# The remote cache's ETag, or nothing when there is none. A listing, not a head-object: a
# 404 from head-object cannot tell a missing key from a missing bucket.
remote_etag() {
  aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX/$1.gz" \
    --query 'Contents[].[Key, ETag]' --output text |
    awk -F'\t' -v k="$PREFIX/$1.gz" '$1 == k { print $2 }'
}

lines() { wc -l < "$1" | tr -d ' '; }

if [ "$MODE" = pull ]; then
  for f in "${FILES[@]}"; do
    etag=$(remote_etag "$f")
    [ -n "$etag" ] || { echo "ERROR: no $PREFIX/$f.gz in $BUCKET; not building cold" >&2; exit 1; }
    aws s3 cp "s3://$BUCKET/$PREFIX/$f.gz" "$PULLED/$f.gz" --only-show-errors \
      ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
    [ ${#EXTRA_ARGS[@]} -eq 0 ] || continue
    gunzip -c "$PULLED/$f.gz" > "$PULLED/$f"
    n=$(lines "$PULLED/$f")
    [ "$n" -gt 0 ] || { echo "ERROR: $PREFIX/$f.gz holds no lines" >&2; exit 1; }
    if [ -s "$BUILD/$f" ]; then
      [ "$(tail -c 1 "$BUILD/$f" | od -An -c | tr -d ' ')" = '\n' ] || {
        echo "ERROR: $BUILD/$f ends mid-line; run the build once to repair it, then pull" >&2
        exit 1; }
      awk '!seen[$0]++' "$BUILD/$f" "$PULLED/$f" > "$BUILD/$f.new"
      echo "$f: merged $(lines "$BUILD/$f") local and $n pulled lines into $(lines "$BUILD/$f.new")"
    else
      mv "$PULLED/$f" "$BUILD/$f.new"
      echo "$f: $n lines pulled"
    fi
    rm -f "$PULLED/$f"
    mv "$BUILD/$f.new" "$BUILD/$f"
    lines "$BUILD/$f" > "$PULLED/$f.lines"
    echo "$etag" > "$PULLED/$f.etag"
  done
  exit 0
fi

for f in "${FILES[@]}"; do
  [ -s "$BUILD/$f" ] || { echo "ERROR: $BUILD/$f missing or empty; not pushing" >&2; exit 1; }
  etag=$(remote_etag "$f")
  if [ -n "$etag" ] && [ "$etag" != "$(cat "$PULLED/$f.etag" 2>/dev/null || true)" ]; then
    echo "ERROR: $PREFIX/$f.gz is not the copy this tree last pulled or pushed; pull first" >&2
    exit 1
  fi
  if [ -s "$PULLED/$f.lines" ]; then
    had=$(cat "$PULLED/$f.lines")
    now=$(lines "$BUILD/$f")
    [ "$now" -ge "$had" ] || {
      echo "ERROR: $BUILD/$f has $now lines, fewer than the $had pulled; not pushing" >&2
      exit 1; }
  fi
done
for f in "${FILES[@]}"; do
  gzip -n -c "$BUILD/$f" > "$BUILD/$f.gz"
  if [ -s "$PULLED/$f.gz" ] && cmp -s "$BUILD/$f.gz" "$PULLED/$f.gz"; then
    echo "$f: unchanged since pull, not uploaded"
  else
    aws s3 cp "$BUILD/$f.gz" "s3://$BUCKET/$PREFIX/$f.gz" --only-show-errors \
      --content-type application/gzip ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
    echo "$f: $(lines "$BUILD/$f") lines pushed${EXTRA_ARGS[@]+ (dry run, nothing sent)}"
    if [ ${#EXTRA_ARGS[@]} -eq 0 ]; then
      mv "$BUILD/$f.gz" "$PULLED/$f.gz"
      lines "$BUILD/$f" > "$PULLED/$f.lines"
      remote_etag "$f" > "$PULLED/$f.etag"
    fi
  fi
  rm -f "$BUILD/$f.gz"
done
