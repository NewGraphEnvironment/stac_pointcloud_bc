# Code-check round 4: the round 3 fix to `scripts/cache_sync.sh` (conditional PUT, #4)

Reviewer: subagent, 2026-10-12. Scope: `round3_fix.patch` and the whole current script, plus
`.github/workflows/update.yml` and README.Rmd "Monthly update". Probes ran in a scratch copy
under `$TMPDIR` (scratchpad `r4/`) under macOS `/bin/bash` 3.2.57, with a fake `aws` backed by
a local directory: `list-objects-v2 --query ... --output text` prints `key<TAB>"etag"` (or
`None`), and `s3api put-object` honours `--if-match` / `--if-none-match '*'`, returning
PreconditionFailed with exit 254, and on success prints the quoted ETag. Nothing in the repo
(apart from this file) or in S3 was written.

## Clean

No issues found.

## What was checked

| check | result |
|---|---|
| `ETAGS` stays aligned with `FILES` when a file is skipped as unchanged | Aligned. Loop 1 appends once per file unconditionally, or exits. Loop 2 reads and increments `i` before any branch. Traced with `bash -x`: files 1 and 3 changed and 2 and 4 unchanged, so each `--if-match` carried its own file's ETag and only 1 and 3 were PUT |
| bash 3.2, `ETAGS+=("")` and `${ETAGS[$i]}` under `set -u` | The element is set, so it reads as `""` with no unbound error, and the length counts it (`[] 2`). The real run with headers absent remotely took the `--if-none-match '*'` path |
| `if ! new=$(aws ...)` | It captures the CLI's status. The 412 path took the branch (rc 1, "pull first"), and the success path captured the quoted ETag into `.etag` |
| quoting of the ETag passed to `--if-match` | `expect` holds the listing's quoted string. It reaches argv intact (`--if-match '"da97…"'`), and matches the form the real-bucket probe accepted. `'*'` in `COND` stays literal (the log shows a bare `*` argument, not a glob) |
| race between check and PUT (round 3's window 1) | Simulated as a writer landing inside put-object: PreconditionFailed, the other writer's object was left intact, markers untouched. The next push is refused by the ETag guard. `pull` then merges (`6 local and 1 pulled into 7`), `push` uploads, and a second push is a no-op. Same for a remote created between a "none" check and an `--if-none-match '*'` PUT |
| round 3's window 2 (listing after upload) | Gone: `.etag` is the PUT's own response |
| dry run | Guard and shrink check run. No put-object call, no marker write, the `.gz` removed. The output says "to push (dry run, nothing sent)" |
| markers against the round 2 table | `.etag` is the listing before fetch (pull) or the PUT's returned ETag (push), so it is "remote object as last seen". `.cksum` and `.lines` are unchanged from round 2. All three are written only after a successful PUT, never on a dry run or a refusal |
| permissions | `rtj/modules/gha_s3_role` grants `s3:PutObject` on `bucket/*` with no condition. A conditional PUT needs nothing more |
| update.yml / README.Rmd | Still accurate. The workflow calls the script unchanged and treats a failed push as `continue-on-error`, with the comment "a local push during the run, a transient error", which is what a 412 now is. README's "`push` refuses to replace a cache the monthly run has written since this tree last pulled" and the script's header (lines 12-16) both still describe the behaviour, now atomic |

## Noted, not defects

- A refused or failed PUT exits before `rm -f "$BUILD/$f.gz"`, so the `.gz` is left in
  `data/build/`. That is the same as before the fix (a failed `aws s3 cp` under `set -e`).
  Nothing reads it: `s3_sync.sh` uploads only `$BUILD/upload` and `collection.json`, and the
  next push overwrites it.
- Suppose a transient 5xx arrives after the PUT landed and the CLI retries. The retry then
  fails its own `If-Match` (412), so the script reports failure though the bytes are up. The
  markers are left stale, so the next push refuses and pull merges back to the same content.
  This fails safe and loses no read.
