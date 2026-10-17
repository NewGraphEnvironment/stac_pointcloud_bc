# Findings — Sample the point classes of every file (#17)

## Issue context

Body pending: GitHub unreachable (api.github.com and github.com time out, other hosts answer;
not the sandbox) from 2026-10-17 18:04 UTC. What the repo records about #17:

- `research/laz_classes.md`: "#17 (sampling the rest)"; "About 38 unsampled files lack a list they
  should have (the audit, above); which ones is known only by sampling them all (#17)."
- NEWS 0.3.0: "about 38 of the 148,894 items neither screened nor audited ... sampling them is #17."
- `planning/archive/2026-10-issue-2-index-all-pointcloud/progress.md`: "Screen audit decided: ship
  as is; sampling the other 148,894 files is #17."

## Why sampling every file closes the gap, not just narrows it

A sample can only miss a class. A file with no class 2 gives a sample with no class 2; a ground-only
file gives a sample of classes in {2, 7, 9, 18} only. So with every file sampled, every no-ground or
ground-only file is flagged and then read whole. What stays open: files the sampler cannot read (2
known: `082e075_1_4_3`, `094j045_3_3_4`, lazrs "no chunks available in chunk table") and empty samples.

## Cost (from 0.3.0's measures)

Audit pace: 7,836 files in 63 min at 16 workers, laz sample median 2.65 MB, COPC levels 0-1 median
3.17 MB. 148,894 files: about 20 h and 400 GB of range reads, once. Afterwards only new or
re-delivered files are sampled each month.

## Errors Encountered

| Error | Resolution |
|-------|------------|
| `gh`: `net/http: TLS handshake timeout`; curl to github.com times out | GitHub unreachable from this host; planned from local record, body diffed before PR |
