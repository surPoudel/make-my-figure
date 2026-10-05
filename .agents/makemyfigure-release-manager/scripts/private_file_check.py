"""Security / private-file check of what a build would ship. READ-ONLY.

    python .agents/makemyfigure-release-manager/scripts/private_file_check.py [--tree] [--sdist path.tar.gz] [--wheel path.whl] [--app dist/MakeMyFigure]

Default: scans the files git would include in a release (tracked files) plus the untracked files
present in the working tree, for names and contents that must never ship: manuscript drafts,
private source data, OneDrive / home paths, API keys and tokens, .env files, credentials,
benchmark scratch, publisher PDFs, temporary screenshots and oversized development artefacts.
With --sdist / --wheel / --app it lists the members of a built artefact and applies the same rules.
Exit 1 on any STOP finding; WARN findings are printed but do not fail.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tarfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

STOP_NAME_PATTERNS = [
    (r"(^|/)\.env(\..*)?$", "environment file"),
    (r"(^|/)(id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.pfx|.*\.keystore)$", "private key / certificate"),
    (r"(^|/)PRIVATE_REFERENCE_ONLY(/|$)", "publisher reference files"),
    (r"(^|/)(manuscript|Manuscript_|MakeMyFigure_manuscript|MakeMyFigure_submission)", "manuscript material"),
    (r"^(?!docs/manuals/).*\.(docx|pptx)$", "Office document (manuscript / slides) outside docs/manuals"),
    (r"(^|/)(claude_code|\.claude|clauderesume)(/|$)", "assistant session files"),
    (r"(^|/)CLAUDE(-[A-Za-z0-9]+)?\.md$", "assistant instruction file"),
    (r"(^|/)Suresh_.*", "personal file"),
]
WARN_NAME_PATTERNS = [
    (r"(^|/)(tmp|temp|scratch)(_[^/]*)?(/|$)", "scratch folder"),
    (r"(^|/)benchmarks/.*/(raw|scratch|_outputs)(/|$)", "benchmark scratch"),
    (r"(^|/)_outputs(/|$)", "generated outputs"),
    (r"\.(mov|mp4|mkv)$", "video file"),
    (r"^(?!docs/manuals/|tutorial/).*(^|/)screenshots?/.*\.(png|jpg)$", "screenshot outside the manuals / tutorial"),
    (r"^(?!docs/manuals/|benchmarks/)(?!.*mpl-data/).*\.pdf$", "PDF outside manuals / benchmark recreations (check it is not a publisher article)"),
]
CONTENT_PATTERNS = [
    (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}", "credential assignment"),
    (r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}", "GitHub token"),
    (r"sk-[A-Za-z0-9]{20,}", "API key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private key block"),
    (r"OneDrive - St\. Jude|/Users/[a-z0-9]+/|C:\\\\Users\\\\[A-Za-z0-9]+\\\\|/home/[a-z0-9]+/", "personal / OneDrive path"),
]
TEXT_EXT = {".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".csv", ".tsv", ".iss", ".spec", ".sh", ".ps1", ".html", ".svg"}
SIZE_WARN_MB = 25
# Paths that legitimately mention personal-looking paths in documentation about NOT shipping them.
CONTENT_EXEMPT = (".agents/makemyfigure-release-manager/reports/", "docs/releases/", "reports/", "tests/", "CHANGELOG.md", "docs/RELEASE_NOTES", "docs/manuals/audit/")


def classify(relpath: str):
    for pat, why in STOP_NAME_PATTERNS:
        if re.search(pat, relpath):
            return "STOP", why
    for pat, why in WARN_NAME_PATTERNS:
        if re.search(pat, relpath):
            return "WARN", why
    return None, ""


def scan_content(relpath: str, data: bytes):
    if os.path.splitext(relpath)[1].lower() not in TEXT_EXT:
        return []
    if any(relpath.startswith(p) or f"/{p}" in relpath for p in CONTENT_EXEMPT):
        return []
    text = data.decode("utf-8", errors="ignore")
    hits = []
    for pat, why in CONTENT_PATTERNS:
        m = re.search(pat, text)
        if m:
            hits.append((why, m.group(0)[:60]))
    return hits


def tree_files():
    tracked = C.git("ls-files").splitlines()
    untracked = [l[3:] for l in C.git("status", "--porcelain", "-uall").splitlines() if l.startswith("??")]
    return tracked, untracked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", action="store_true", help="scan the working tree (default when no artefact given)")
    ap.add_argument("--sdist"); ap.add_argument("--wheel"); ap.add_argument("--app", help="PyInstaller output folder")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "private_file_check.json"))
    a = ap.parse_args()
    findings = []

    def check(relpath, size, data_reader=None):
        level, why = classify(relpath)
        if level:
            findings.append({"level": level, "path": relpath, "reason": why})
        if size > SIZE_WARN_MB * 1024 * 1024:
            findings.append({"level": "WARN", "path": relpath, "reason": f"large file {size / 1e6:.0f} MB"})
        if data_reader and size < 5_000_000:
            for why, snippet in scan_content(relpath, data_reader()):
                findings.append({"level": "STOP" if "path" not in why else "WARN", "path": relpath, "reason": f"{why}: {snippet}"})

    scanned = 0
    if a.sdist:
        with tarfile.open(a.sdist) as tf:
            for m in tf.getmembers():
                if m.isfile():
                    scanned += 1
                    check(m.name, m.size, lambda m=m, tf=tf: tf.extractfile(m).read())
    if a.wheel:
        with zipfile.ZipFile(a.wheel) as zf:
            for i in zf.infolist():
                scanned += 1
                check(i.filename, i.file_size, lambda i=i, zf=zf: zf.read(i))
    if a.app:
        for dp, _, fns in os.walk(a.app):
            for fn in fns:
                p = os.path.join(dp, fn); rel = os.path.relpath(p, a.app).replace(os.sep, "/")
                scanned += 1
                check(rel, os.path.getsize(p), None)   # binaries: names and sizes only
    if a.tree or not (a.sdist or a.wheel or a.app):
        tracked, untracked = tree_files()
        for rel in tracked:
            p = os.path.join(C.ROOT, rel)
            if os.path.isfile(p):
                scanned += 1
                check(rel, os.path.getsize(p), lambda p=p: open(p, "rb").read())
        for rel in untracked:
            p = os.path.join(C.ROOT, rel)
            if os.path.isfile(p):
                scanned += 1
                level, why = classify(rel)
                findings.append({"level": level or "INFO", "path": rel, "reason": (why or "untracked file present in the working tree") + " [untracked]"})
    stops = [f for f in findings if f["level"] == "STOP"]
    warns = [f for f in findings if f["level"] == "WARN"]
    C.write_json(a.json, {"generated": C.now_iso(), "scanned": scanned, "findings": findings, "stop": len(stops), "warn": len(warns)})
    print(f"private-file check: {scanned} files scanned, {len(stops)} STOP, {len(warns)} WARN, {len(findings) - len(stops) - len(warns)} INFO")
    for f in sorted(findings, key=lambda f: {"STOP": 0, "WARN": 1}.get(f["level"], 2))[:60]:
        print(f"  {f['level']:4s} {f['path']}  - {f['reason']}")
    return 1 if stops else 0


if __name__ == "__main__":
    raise SystemExit(main())
