# Release ledger

One JSON file per published tag, written by `scripts/record_release.py --tag vX.Y.Z` from live git and
GitHub data (tag commit and date, annotated flag, version.py at the tag, GitHub release URL, publish
date, asset names and sizes) plus free-text `notes`. Back-filled on 2026-09-23 for v0.6.1, v1.0.0-rc1,
v1.0.0 and v1.1.0; the lightweight v0.x tags are summarised in `references/release-history.md`.
`TEMPLATE.json` shows the fields. Records are committed; they are the durable memory of what was
published and from which commit.
