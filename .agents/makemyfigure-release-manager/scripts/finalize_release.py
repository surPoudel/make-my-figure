"""FINALIZE a published release after the CI workflow has attached its installers. GATED (publishes).

    python .agents/makemyfigure-release-manager/scripts/finalize_release.py --tag vX.Y.Z [--prefer-local linux] [--dry-run]
           [--authorize "I authorize finalize for vX.Y.Z"]

Why: the tag push starts .github/workflows/build_desktop_releases.yml, whose three runners upload
their installers to the release with `gh release upload --clobber`. Files that share a name with
locally built ones (the Linux tar.gz / AppImage) are therefore replaced by the CI build, and
SHA256SUMS.txt published at release time no longer describes the attached files.

Steps
  1. Find the workflow run for the tag; require conclusion == success (or --skip-ci-check).
  2. Download every asset of the release into release_staging/<v>/ci_download/ and list them.
  3. With --prefer-local <platform,...>: re-upload the locally built, self-tested artefacts staged under
     release_staging/<v>/<platform>/ (--clobber), e.g. the WSL Linux build (glibc 2.35) over the CI build
     (glibc 2.39).
  4. Regenerate SHA256SUMS.txt over the final asset set and upload it (--clobber).
  5. Download again and verify every hash; write release_history/<tag>.json via record_release.py.
Without --dry-run and the authorization sentence + MMF_RELEASE_AUTHORIZED=yes nothing is uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WORKFLOW = "build_desktop_releases.yml"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ci_run_for_tag(tag: str):
    r = C.run(["gh", "run", "list", "--workflow", WORKFLOW, "--limit", "30", "--json", "databaseId,status,conclusion,headBranch,headSha,createdAt,url"])
    if r.returncode != 0:
        return None
    runs = [x for x in json.loads(r.stdout) if x.get("headBranch") == tag]
    return runs[0] if runs else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--prefer-local", default="", help="comma list of platforms whose staged artefacts replace CI's (e.g. linux)")
    ap.add_argument("--skip-ci-check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--authorize", default="")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    tag = a.tag; v = C.tag_to_pep440(tag)
    base = os.path.join(C.STAGING_ROOT, v)
    rel = C.run(["gh", "release", "view", tag, "--json", "assets,url,isDraft"])
    if rel.returncode != 0:
        print(f"no GitHub release for {tag}"); return 1
    release = json.loads(rel.stdout)
    print(f"release {tag}: {len(release['assets'])} asset(s) attached  {release['url']}")
    run = ci_run_for_tag(tag)
    if run:
        print(f"CI run {run['databaseId']}: {run['status']} / {run.get('conclusion')}  {run['url']}")
        if run["status"] != "completed" or run.get("conclusion") != "success":
            if not a.skip_ci_check:
                print("CI has not finished successfully yet - wait (gh run watch <id>) or pass --skip-ci-check"); return 1
    elif not a.skip_ci_check:
        print("no CI run found for the tag yet (it starts on the tag push); pass --skip-ci-check to finalize without it"); return 1
    # local replacements
    prefer = [p for p in a.prefer_local.split(",") if p]
    replacements = []
    for p in prefer:
        d = os.path.join(base, p)
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if fn.endswith((".whl", ".tar.gz", ".exe", ".zip", ".dmg", ".AppImage", ".pdf")):
                replacements.append(os.path.join(d, fn))
    print("planned actions:")
    for rp in replacements:
        print(f"  gh release upload {tag} {os.path.relpath(rp, C.ROOT)} --clobber")
    print(f"  regenerate SHA256SUMS.txt over the final assets and gh release upload {tag} SHA256SUMS.txt --clobber")
    print(f"  verify all hashes after download; record_release.py --tag {tag}")
    if a.dry_run:
        print("dry run - stopped."); return 0
    expected = f"I authorize finalize for {tag}"
    if a.authorize != expected or os.environ.get("MMF_RELEASE_AUTHORIZED") != "yes":
        print(f'GATE: pass --authorize "{expected}" and set MMF_RELEASE_AUTHORIZED=yes'); return 1
    if not a.yes and input("type yes to upload: ").strip().lower() != "yes":
        print("not confirmed"); return 1
    for rp in replacements:
        C.run(["gh", "release", "upload", tag, rp, "--clobber"], check=True, capture=False)
    dl = os.path.join(base, "ci_download"); shutil.rmtree(dl, ignore_errors=True); os.makedirs(dl)
    C.run(["gh", "release", "download", tag, "-D", dl], check=True, capture=False)
    names = sorted(n for n in os.listdir(dl) if n != "SHA256SUMS.txt")
    sums = os.path.join(dl, "SHA256SUMS.txt")
    with open(sums, "w", encoding="utf-8", newline="\n") as fh:
        for n in names:
            fh.write(f"{sha(os.path.join(dl, n))}  {n}\n")
    ck = C.staging_dir(v, "checksums"); shutil.copy2(sums, os.path.join(ck, "SHA256SUMS.txt"))
    C.run(["gh", "release", "upload", tag, sums, "--clobber"], check=True, capture=False)
    # verify
    vd = os.path.join(base, "ci_verify"); shutil.rmtree(vd, ignore_errors=True); os.makedirs(vd)
    C.run(["gh", "release", "download", tag, "-D", vd], check=True, capture=False)
    recorded = dict(reversed(l.split("  ", 1)) for l in open(os.path.join(vd, "SHA256SUMS.txt"), encoding="utf-8").read().splitlines() if "  " in l)
    bad = [n for n in recorded if sha(os.path.join(vd, n)) != recorded[n]]
    print(f"final release: {len(recorded)} asset(s) in SHA256SUMS.txt, {len(bad)} mismatch(es)")
    for n in names:
        print(f"  {n}  {os.path.getsize(os.path.join(dl, n)) / 1e6:.1f} MB")
    C.run([sys.executable, os.path.join(HERE, "record_release.py"), "--tag", tag, "--notes",
           f"finalized via finalize_release.py; local replacements: {', '.join(os.path.basename(r) for r in replacements) or 'none'}; CI run {run['databaseId'] if run else 'n/a'}"], capture=False)
    shutil.rmtree(vd, ignore_errors=True)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
