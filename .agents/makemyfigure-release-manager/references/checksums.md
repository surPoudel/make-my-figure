# Checksums

`generate_checksums.py --version X.Y.Z` writes `release_staging/<v>/checksums/SHA256SUMS.txt` in
`sha256sum` format (`<hex>  <filename>`) over every public artefact found under
`python/ windows/ macos/ linux/ manuals/` (manifests and JSON are excluded), plus
`release_artifacts.json` (filename, size, sha256, platform, architecture, artefact type, expected-but-
missing list). `--verify` re-hashes and compares. The v1.1.0 release published the same file format
(10 lines; hashes preserved in the ledger record and in `/tmp/rel_audit` at release time).

Users verify with `sha256sum -c SHA256SUMS.txt` (Linux/macOS) or
`Get-FileHash -Algorithm SHA256 <file>` (PowerShell). The release notes draft repeats each hash in a table.

Rule: checksums are generated once, after every platform folder is final, immediately before
`release`. `release` re-verifies them (`--verify`) and refuses to publish on mismatch.
