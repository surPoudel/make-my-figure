"""Tag verification. READ-ONLY.

    python .agents/makemyfigure-release-manager/scripts/verify_tag.py --tag vX.Y.Z            # after tagging
    python .agents/makemyfigure-release-manager/scripts/verify_tag.py --tag vX.Y.Z --pre-check  # before tagging

--pre-check: the tag must NOT exist locally or on origin, the tag name must be vMAJOR.MINOR.PATCH
(optional -rcN), and it must equal "v" + version.py.
default:     the tag exists, is ANNOTATED (project convention since v0.6.1), points at a commit whose
version.py equals the tag, is present on origin at the same commit, and (if gh is available) the
GitHub release for that tag, when it exists, references the same tag.
Exit 1 on any failed check.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def remote_tag_sha(tag: str) -> str:
    out = C.git("ls-remote", "--tags", "origin", tag, f"{tag}^{{}}")
    peeled = [l.split()[0] for l in out.splitlines() if l.endswith("^{}")]
    plain = [l.split()[0] for l in out.splitlines() if l.strip().endswith(f"refs/tags/{tag}")]
    return (peeled or plain or [""])[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--pre-check", action="store_true")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "tag_verification.json"))
    a = ap.parse_args()
    tag = a.tag
    checks = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail}); print(f"  {'ok ' if ok else '!! '}{name}{': ' + detail if detail else ''}")

    ck("tag name is vMAJOR.MINOR.PATCH[-rcN]", C.TAG_RE.match(tag), tag)
    ver = C.version_py()
    ck("tag equals 'v' + version.py", tag == C.pep440_to_tag(ver), f"version.py={ver}")
    local_sha = C.git("rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}")
    remote_sha = remote_tag_sha(tag)
    if a.pre_check:
        ck("tag does not exist locally", not local_sha, local_sha[:12] if local_sha else "")
        ck("tag does not exist on origin", not remote_sha, remote_sha[:12] if remote_sha else "")
    else:
        ck("tag exists locally", local_sha, local_sha[:12])
        if local_sha:
            ck("tag is annotated", C.git("cat-file", "-t", tag) == "tag", C.git("cat-file", "-t", tag))
            tagged_ver = C.git("show", f"{tag}:make_my_figure_core/version.py")
            import re
            m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", tagged_ver)
            ck("version.py at the tagged commit equals the tag", m and C.pep440_to_tag(m.group(1)) == tag, m.group(1) if m else "not found")
            ck("tag exists on origin", remote_sha, remote_sha[:12] if remote_sha else "missing")
            if remote_sha:
                ck("origin tag points at the same commit", remote_sha == local_sha)
            r = C.run(["gh", "release", "view", tag, "--json", "tagName,isDraft,isPrerelease,assets,publishedAt"])
            if r.returncode == 0:
                import json
                rel = json.loads(r.stdout)
                ck("GitHub release exists for the tag", rel.get("tagName") == tag,
                   f"{len(rel.get('assets', []))} assets, draft={rel.get('isDraft')}, prerelease={rel.get('isPrerelease')}, published {rel.get('publishedAt')}")
            else:
                print("  -- no GitHub release for this tag yet (or gh unavailable)")
    ok = all(c["ok"] for c in checks)
    C.write_json(a.json, {"generated": C.now_iso(), "tag": tag, "pre_check": a.pre_check, "checks": checks, "ok": ok})
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
