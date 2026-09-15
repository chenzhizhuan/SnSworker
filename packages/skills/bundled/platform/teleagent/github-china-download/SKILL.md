---
name: github-china-download
description: Download GitHub Release binaries in China via proxy.
name_cn: GitHub国内下载
description_cn: GitHub仓库国内加速下载
migrated_from: user-created
version: 1.0.0
author: TeleAgent
created: 2026-08-01
category: utility
tags:
- gitcode
- github
- hermes
- utility
updated: 2026-08-01
status: available
---

# GitHub China Download

Download GitHub Release binary assets (zip, tar.gz, exe) from China
where direct GitHub access times out. Covers proxy selection, path
pitfalls on Windows MSYS, and manual install patterns.

## When to Use

- Any tool/driver install fails with GitHub download timeout
- `teleagent computer-use install` or similar hangs on GitHub Releases
- User asks to download from GitHub and direct access fails
- GitCode mirror returns 404 for Release assets

## Quick Reference

| Method | Works? | Notes |
|--------|--------|-------|
| GitHub direct | ✗ | Times out in China |
| GitCode mirror (code) | ✓ | Only syncs repo code |
| GitCode mirror (Releases) | ✗ | 404 — Releases NOT synced |
| ghfast.top proxy | ✓ | Prefix to full GitHub URL |
| gh-proxy.com | ✓ | Backup proxy |
| mirror.ghproxy.com | ✗ | Dead as of 2026-07 |

## Procedure

1. Construct the full GitHub Release URL:
   `https://github.com/<owner>/<repo>/releases/download/<tag>/<file>`

2. Download via proxy (try in order):
   ```bash
   curl -sL -o "$USERPROFILE/download.zip" \
     "https://ghfast.top/<full-github-url>" \
     --connect-timeout 10 -m 120
   ```

3. Verify download size > 1KB (proxy error pages are small).

4. Extract and install to the expected location.

5. Clean up the downloaded archive.

## Pitfalls

- **MSYS /tmp path mapping**: On Windows git-bash, `curl -o /tmp/file`
  writes to a path that may not persist across terminal calls. Always
  use `$USERPROFILE/<file>` or an absolute Windows path.

- **Zip subdirectory**: Many GitHub Release zips contain a subdirectory
  (e.g. `app-v1.0.0-windows-x86_64/`). After unzip, move binaries from
  the subdirectory to the target bin root.

- **Version drift**: Don't hardcode version numbers. Check the install
  script output or the repo's Releases page for the current version
  before constructing the download URL.

- **Proxy availability changes**: These proxies are community-run and
  may die. If both ghfast.top and gh-proxy.com fail, search for current
  working GitHub proxy services.

## Verification

Run the installed binary's `--version` or `--help` to confirm it works.