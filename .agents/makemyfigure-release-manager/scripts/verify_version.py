"""Version audit. READ-ONLY. Exit 1 when authoritative locations disagree (or differ from --expect).

    python .agents/makemyfigure-release-manager/scripts/verify_version.py [--expect 1.2.0] [--json out.json]

Locations (from the v1.1.0 / v1.1.1 release commits): make_my_figure_core/version.py (single
source; pyproject.toml reads it dynamically; the About dialog imports it), the first released
section of CHANGELOG.md, the README version badge and installer file names, the version banner
of both generated manuals, and docs/RELEASE_NOTES_v<version>.md. The PyInstaller bundle version
and the Inno Setup version are injected at build time from version.py, so they are not files to check.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expect", help="version the locations must all show (default: version.py)")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "version_audit.json"))
    ap.add_argument("--allow-missing-notes", action="store_true", help="do not fail when the release notes file is absent (LOCAL BUILD)")
    a = ap.parse_args()
    v = (a.expect or C.version_py()).lstrip("v")
    fmt_ok = bool(C.SEMVER_RE.match(v))
    rows = C.version_locations(v)
    for r in rows:
        r["matches"] = (r["value"] == v) if r["value"] is not None else False
    failures = [r for r in rows if not r["matches"]]
    if a.allow_missing_notes:
        failures = [r for r in failures if not r["location"].startswith("docs/RELEASE_NOTES")]
    out = {"generated": C.now_iso(), "expected": v, "tag": C.pep440_to_tag(v), "format_ok": fmt_ok, "rows": rows,
           "ok": fmt_ok and not failures}
    C.write_json(a.json, out)
    print(f"version audit for {v} (tag {out['tag']}) - format {'ok' if fmt_ok else 'INVALID (expected X.Y.Z or X.Y.ZrcN)'}")
    for r in rows:
        print(f"  {'ok ' if r['matches'] else '!! '}{r['location']}: {r['value']}")
    print("RESULT:", "PASS" if out["ok"] else f"FAIL ({len(failures)} location(s) disagree)")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
