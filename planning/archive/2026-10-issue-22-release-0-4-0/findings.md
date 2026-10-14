# Findings — Release 0.4.0: publish the rounded footprints (#22)

## Issue context

**If we do it:** the published items carry footprints rounded to 8 decimals (`laz_item.LONLAT_DECIMALS`, #4), so a monthly CI build on linux/amd64 writes the same bytes as the published catalogue, and the monthly update publishes only real growth. **If we never do:** every monthly run plans about 174k uploads and is refused by its 40,000-item ceiling (`MAX_UPLOAD`), so the update never publishes.

Why: unrounded, 6,559 of 8,713 sampled footprints differed between macOS arm64 and linux/amd64 in their last bits (at most 5.7e-14 degrees). Rounded, 0 of 8,713 differ (#4, `planning/archive/…issue-4…/findings.md`). Every item's `geometry` and `bbox` change once, by under 1 mm, and the collection extent with them. Nothing else should change.

Do it before the first scheduled run (the 6th of the month after #4 merges), or that run goes red on the ceiling. That is harmless, but it is noise.

Steps, from a tailnet machine:

1. `bash scripts/cache_sync.sh pull`, then `PYTHONPATH=scripts uv run python scripts/catalogue_build.py` (warm, about 53 min).
2. Adapt `scripts/catalogue_compare.py` to this release's change: published `geometry` and `bbox` rounded to 8 dp equal the build, and nothing else differs. Run it against a sync of the bucket.
3. `bash scripts/cache_sync.sh push`, then `uv run python scripts/collection_version.py --version 0.4.0`.
4. `bash scripts/s3_sync.sh --dryrun` should plan about 174,282 items. Then run `bash scripts/s3_sync.sh` (95 min).
5. `stacs verify`, `stacs register --mode drift`, `stacs verify` (`PYTHONUNBUFFERED=1`; about 3 h).
   The register also loads the `lidarbc:delivery` queryable declared in `stacs.toml` (#5), so the first verify reports it missing as well, and the last should say `1 declared queryable(s) served as declared`. Then tick #5's queryable box and close it. Before step 5, confirm the host's pypgstac is 0.9.6 or later, which stacs needs to load queryables (`ssh root@geopro 'cd /opt/geoserv/scripts && /root/.local/bin/uv pip show pypgstac'`; cloud-init installs it unpinned, so probably 0.9.9). This is the first queryables load on this database. pgstac's `queryables_trigger` runs `maintain_partitions()` inside the load, which should change nothing, but if an index differs from what pgstac expects it is rebuilt there.
6. NEWS 0.4.0, then dispatch the update workflow with `dryrun`, which should plan 0 items and leave the collection unchanged.

## Errors Encountered

| Error | Resolution |
|-------|------------|

## Plan review, checked (2026-10-14)

- `review-plan.md` G5 said `register --mode drift --dryrun` exercises the host's `_db` path. It does not:
  stacs v0.2.0 README, "--dryrun": a drift dryrun stops "after comparing every body with the API but
  before the asset audit", and "none of them runs the script on the host, so the env file, pypgstac and
  the database check are first exercised by a real load". It is still the right before-check (the full
  comparison, no write); the first real exercise of v0.2.0's database check is the register itself.
- Host pypgstac: 0.9.9 (`uv pip show pypgstac` on geopro, 2026-10-14), inside 0.9.6–0.10.0.

## The compare's cross-checks (enumerated, 2026-10-14)

Seven artifacts: the local copy's files, the published collection's links and extent; the build's
items/, its collection's links and extent; and new items. Every pair the release depends on is
checked: copy files = published links (`not_copied`, `unlinked`); build items/ = build links
(`build_mismatch`); build extent = its items' envelope; published links vs build links (`only_pub`,
`new`, and `pi - bi`); each shared item (rounding only); published extent vs built (rounding, or
containment when something is new); each new item's rounding. Not checked: the published extent
against the published items, which describes the state being replaced, not the one published.
