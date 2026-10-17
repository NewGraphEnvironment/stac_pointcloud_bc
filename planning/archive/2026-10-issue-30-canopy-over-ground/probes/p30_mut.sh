#!/bin/bash
# Restore-the-bug table for #30's helpers: each mutation in a copy, the test file's failures counted.
set -u
REPO=$1; OUT=$2
mut() {
  local name=$1 from=$2 to=$3 d
  d=$(mktemp -d "$OUT/mut_XXXXXX") || exit 1
  cp -R "$REPO/scripts" "$REPO/tests" "$REPO/README.Rmd" "$d/"
  python3 - "$d/scripts/readme_functions.R" "$from" "$to" <<'PY'
import sys
p, a, b = sys.argv[1:]
s = open(p).read()
assert s.count(a) == 1, a
open(p, "w").write(s.replace(a, b))
PY
  n=$(cd "$d" && Rscript -e 'r <- as.data.frame(testthat::test_file("tests/readme_functions_test.R", reporter = "silent")); cat(sum(r$failed > 0 | r$error) - 1L)' 2>/dev/null | tail -1)
  echo "$name: $n new failing tests"
  rm -rf "$d"
}
mut "hillshade not normalised" '/ sin(sun[1] * pi / 180)' ''
mut "ramp ends NA" 'pmin(pmax((v - lo) / (hi - lo), 0), 1)' '(v - lo) / (hi - lo)'
mut "water not painted" '  rgb[wet, ] <- matrix' '  if (FALSE) rgb[wet, ] <- matrix'
mut "canopy opaque at once" 'a <- opacity[1] + diff(opacity)' 'a <- 1 + 0 * diff(opacity)'
mut "drawn interpolated" 'nc, nr, interpolate = FALSE)' 'nc / 2, nr / 2, interpolate = TRUE)'
