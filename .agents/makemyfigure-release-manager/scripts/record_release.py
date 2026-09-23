"""Append a release record to the ledger (release_history/<tag>.json) from live git + GitHub data.

    python .agents/makemyfigure-release-manager/scripts/record_release.py --tag vX.Y.Z [--notes "free text"]

Read-only with respect to the repository; only writes the ledger file. Used after publication and
to back-fill historical releases. Fields: tag, commit, tag date, annotated?, version.py at the tag,
GitHub release (published date, assets with sizes), plot-type/statistics counts at that commit when
importable, and free-text notes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--notes", default="")
    a = ap.parse_args()
    tag = a.tag
    commit = C.git("rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}")
    if not commit:
        print(f"tag {tag} not found locally (git fetch --tags?)"); return 1
    kind = C.git("cat-file", "-t", tag)
    ver = re.search(r"__version__\s*=\s*['\"]([^'\"]+)", C.git("show", f"{tag}:make_my_figure_core/version.py") or "")
    rec = {"tag": tag, "commit": commit, "commit_short": commit[:10], "commit_date": C.git("show", "-s", "--format=%cI", commit),
           "annotated": kind == "tag", "tag_date": C.git("for-each-ref", "--format=%(taggerdate:iso8601)", f"refs/tags/{tag}") or None,
           "tag_message": C.git("for-each-ref", "--format=%(contents:subject)", f"refs/tags/{tag}") or None,
           "version_py_at_tag": ver.group(1) if ver else None, "recorded": C.now_iso(), "notes": a.notes}
    r = C.run(["gh", "release", "view", tag, "--json", "publishedAt,createdAt,isPrerelease,isDraft,assets,author,url"])
    if r.returncode == 0:
        g = json.loads(r.stdout)
        rec["github_release"] = {"url": g.get("url"), "published_at": g.get("publishedAt"), "prerelease": g.get("isPrerelease"), "draft": g.get("isDraft"),
                                 "assets": [{"name": x["name"], "size": x["size"]} for x in g.get("assets", [])]}
    else:
        rec["github_release"] = None
    os.makedirs(C.LEDGER_DIR, exist_ok=True)
    out = os.path.join(C.LEDGER_DIR, f"{tag}.json")
    C.write_json(out, rec)
    print(f"ledger record written -> {os.path.relpath(out, C.ROOT)}  ({'annotated' if rec['annotated'] else 'lightweight'} tag at {commit[:10]}, "
          f"{len((rec.get('github_release') or {}).get('assets', []))} GitHub assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
