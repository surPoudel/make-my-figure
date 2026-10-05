# v1.2.0 — baseline

## Release source

`main`, the commit tagged `v1.2.0` (see RELEASE_SOURCE.md); audited from `932427e`. Previous tag `v1.1.1` → commit `8105769`.

## Baseline test run (Phase 4) — before any release edit

Run on the release commit with the working tree clean of code changes:

```
3956 passed, 4 skipped, 0 failed, 0 errors   (35m27s)
exit=0
```

The four skips, each with a stated reason rather than a silent skip:

| Test | Reason |
|---|---|
| `test_package_data.py:152` | opt-in: needs `RUN_PACKAGING_BUILD_TESTS=1` to build and install (slow) — **run separately in Phase 10** |
| `test_publication_recreation_pipeline.py:52` | gapminder already cached; the offline path is not exercised |
| 2 further skips | reported by `-rs` in the run log |

Independently confirmed by GitHub Actions on the same commit: workflow `Tests`, run
`37140999143`, job `pytest (headless)` on `ubuntu-22.04` — the image the released Linux app is
built on — conclusion **success** in 30m10s.

**The baseline is green. Nothing was released from a failing baseline.**

## Live facts at baseline (queried, not counted by hand)

| Fact | Value | Source |
|---|---|---|
| Registered plot types | **45** | `registry.available_plot_types()` |
| Plot types with bundled examples | 45 of 45 | `examples.plot_types_with_examples()` |
| Plot types at v1.1.1 | 39 | the same call in a `v1.1.1` worktree |
| Statistical procedures | 18 | release-manager audit |
| Plot types added | 6, all spatial | set difference of the two registry queries |
| Plot types removed | 0 | — |

Nothing was removed, so v1.2.0 is additive at the registry level.

## Pre-existing conditions found and resolved before release

1. **Private-file check STOPped on `reports/journal_presets/manuscript_future_claims.md`.** The
   trigger was the filename alone — a rule meant to catch manuscript drafts matches anything
   beginning with `manuscript`, and `reports/` is already exempt from content scanning. The file
   is a claims-discipline record, not a draft. Resolved by the author's decision: untracked from
   the repository and kept locally; `.gitignore` records why. `MANUAL_PRESET_ACCEPTANCE.md` W3 was
   updated so the acceptance record stays truthful about where the document now lives.
2. **Six tracked audit logs contained absolute personal paths** (`/Users/spoudel1/…`,
   `/home/spoudel1/…`, the OneDrive path). Scrubbed to repository-relative paths — the same
   treatment commit `5a2b686` applied to the research records. Interpreter paths became
   `<site-packages>/…`, which carries the same information without the machine.
3. The private-file check now reports **0 STOP**. The 8 remaining WARNs are all untracked local
   files (two publisher PDFs, example-figure PDFs) that are not in the release source; Phase 10/14
   re-checks them against the built artifacts rather than trusting the tree.

## Version locations (Phase 8)

All seven agree on 1.2.0 — `verify_version.py --expect 1.2.0` → PASS:
`version.py`, `CHANGELOG.md` first released section, README badge, README installer names,
Quick Start banner, User Manual banner, `docs/RELEASE_NOTES_v1.2.0.md`.

Historical references to 1.1.1 were left exactly as written. Every one of them in `tests/` and
`make_my_figure_core/package/reader.py` is a comment or docstring describing past behaviour, and
no test asserts the current version, so the bump broke nothing. Verified before bumping.
