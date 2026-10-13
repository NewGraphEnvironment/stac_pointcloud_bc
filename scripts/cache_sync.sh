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
#          ETag), so a local push cannot drop the reads a monthly run made. A cache whose
#          uncompressed bytes are unchanged since then is not uploaded (compressed bytes differ
#          between Apple and GNU gzip).
#
# Usage: scripts/cache_sync.sh pull|push [--dryrun]   (from the repo root; ambient AWS credentials)
set -euo pipefail

BUILD="data/build"
BUCKET="stac-pointcloud-bc"
PREFIX="build-cache"
# laz_classes_probe.CLASSES_SAMPLE and CLASSES_FULL, and catalogue_build's two header caches.
FILES=(headers.jsonl copc_headers.jsonl classes.jsonl classes_full.jsonl)
PULLED="$BUILD/cache_pulled"   # per file, as last pulled or pushed: .lines, .cksum, .etag
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
ends_whole() { [ "$(tail -c 1 "$1" | od -An -c | tr -d ' ')" = '\n' ]; }

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
    # What the bucket holds, before any merge: a merged file differs from it and must push.
    cksum < "$PULLED/$f" > "$PULLED/$f.cksum"
    if [ -s "$BUILD/$f" ]; then
      ends_whole "$BUILD/$f" || {
        echo "ERROR: $BUILD/$f ends mid-line; run the build once to repair it, then pull" >&2
        exit 1; }
      awk '!seen[$0]++' "$BUILD/$f" "$PULLED/$f" > "$BUILD/$f.new"
      echo "$f: merged $(lines "$BUILD/$f") local and $n pulled lines into $(lines "$BUILD/$f.new")"
    else
      mv "$PULLED/$f" "$BUILD/$f.new"
      echo "$f: $n lines pulled"
    fi
    rm -f "$PULLED/$f" "$PULLED/$f.gz"
    mv "$BUILD/$f.new" "$BUILD/$f"
    lines "$BUILD/$f" > "$PULLED/$f.lines"
    echo "$etag" > "$PULLED/$f.etag"
  done
  exit 0
fi

# The ETag each check saw, which the upload then requires (If-Match), so a push landing
# between this check and the upload is refused rather than overwritten.
ETAGS=()
for f in "${FILES[@]}"; do
  [ -s "$BUILD/$f" ] || { echo "ERROR: $BUILD/$f missing or empty; not pushing" >&2; exit 1; }
  etag=$(remote_etag "$f")
  ETAGS+=("$etag")
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
i=0
for f in "${FILES[@]}"; do
  expect="${ETAGS[$i]}"
  i=$((i + 1))
  # A build killed mid-append (a timeout) leaves part of a record after the last newline.
  # Cut it, as laz_classes_probe.cache_tail_repair does: merged into another copy it would
  # become a malformed line mid-file, which the readers refuse.
  if ! ends_whole "$BUILD/$f"; then
    sed '$d' "$BUILD/$f" > "$BUILD/$f.whole" && mv "$BUILD/$f.whole" "$BUILD/$f"
    echo "$f: dropped an interrupted record at its end"
  fi
  if [ "$(cksum < "$BUILD/$f")" = "$(cat "$PULLED/$f.cksum" 2>/dev/null || true)" ]; then
    echo "$f: unchanged since pull, not uploaded"
  else
    gzip -n -c "$BUILD/$f" > "$BUILD/$f.gz"
    if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
      echo "$f: $(lines "$BUILD/$f") lines to push (dry run, nothing sent)"
    else
      # The write is the compare-and-swap, and its own ETag is recorded: a listing after it
      # could return another writer's. Single PUT: a cache is far under PutObject's 5 GB.
      if [ -n "$expect" ]; then COND=(--if-match "$expect"); else COND=(--if-none-match '*'); fi
      if ! new=$(aws s3api put-object --bucket "$BUCKET" --key "$PREFIX/$f.gz" \
          --body "$BUILD/$f.gz" --content-type application/gzip "${COND[@]}" \
          --query ETag --output text); then
        echo "ERROR: $PREFIX/$f.gz was not written: it changed after the check (412), or the" \
             "upload failed; pull first" >&2
        exit 1
      fi
      lines "$BUILD/$f" > "$PULLED/$f.lines"
      cksum < "$BUILD/$f" > "$PULLED/$f.cksum"
      echo "$new" > "$PULLED/$f.etag"
      echo "$f: $(lines "$BUILD/$f") lines pushed"
    fi
    rm -f "$BUILD/$f.gz"
  fi
done
