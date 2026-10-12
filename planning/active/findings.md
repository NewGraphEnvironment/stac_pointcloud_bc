# Findings — README render: read the 35 MB collection.json to a file, not through R's 60 s URL timeout (#18)

## Issue context

**If we do it:** the README render survives a slow link. **If we never do:** a render on a slow connection (or in the monthly update, #4, if it renders) fails after the 19-minute API fetch, with an error that names `readBin`, not the timeout.

`pc_readme_bucket()` (`scripts/readme_functions.R`) reads the bucket's `collection.json` with `jsonlite::fromJSON(<url>)`. In 0.3.0 that file is 35 MB, and R's URL connections stop at `getOption("timeout")`, 60 s by default. On 2026-10-11, while a `stacs verify` shared the link (about 48 KB/s), the render failed:

```
Error in `readBin()`: ! cannot read from connection
 3. │     └─jsonlite::fromJSON(paste0(BUCKET_URL, "/collection.json"), simplifyVector = FALSE)
```

It rendered with `options(timeout = 1800)` set for that run only.

Fix: download to a tempfile with `curl::curl_fetch_disk()` (no total timeout; check `status_code`), then `fromJSON()` the file. Declare `curl` in `scripts/DESCRIPTION` if it is not there.


## Existing transfer helper (2026-10-12)

`pc_readme_fetch_file(url, path)` (scripts/readme_functions.R, #19): httr2, `low_speed_limit = 10000`, `low_speed_time = 120`, no total timeout. Probed: `req_perform(path=)` on a missing bucket key raises `HTTP 403 Forbidden` (httr2 1.3.0) and writes the error body to `path`, so the caller must clean the file up.

## Errors Encountered

| Error | Resolution |
|-------|------------|
