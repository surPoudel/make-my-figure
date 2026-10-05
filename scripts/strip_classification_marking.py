"""Remove institutional information-protection markings from the manuscript .docx files.

The environment this manuscript is prepared in applies a Microsoft Purview classification label,
which writes ClassificationContentMarking* properties into docProps/custom.xml and a footer text
box reading "St. Jude - Confidential". The label is applied by institutional tooling, not by the
build, and is RE-APPLIED whenever a file is opened or synchronised in that environment — it was
observed reappearing on a file that was clean when written. This script is therefore a repeatable
check, and must be run again immediately before submission.

Run: python scripts/strip_classification_marking.py
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = glob.glob(os.path.join(ROOT, "manuscript", "final_verified_revision", "*.docx")) + \
    glob.glob(os.path.join(ROOT, "manuscript", "final_verified_revision", "supplementary", "*.docx"))
SUSPECT = re.compile(r"Confidential|ClassificationContentMarking", re.I)
EMPTY_FTR = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
             '<w:p/></w:ftr>')


def clean(path: str) -> int:
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    payload, changed = {}, 0
    for n in names:
        data = zin.read(n)
        if n.endswith(".xml"):
            txt = data.decode("utf-8", "ignore")
            if SUSPECT.search(txt):
                if n.startswith("word/footer"):
                    txt = EMPTY_FTR
                else:
                    txt = re.sub(r"<property[^>]*ClassificationContentMarking[^>]*>.*?</property>",
                                 "", txt, flags=re.S)
                    txt = re.sub(r"<[^>]*>[^<]*Confidential[^<]*</[^>]*>", "", txt)
                data = txt.encode("utf-8")
                changed += 1
        payload[n] = data
    zin.close()
    if changed:
        tmp = path + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                zout.writestr(n, payload[n])
        shutil.move(tmp, path)
    return changed


def verify(path: str):
    z = zipfile.ZipFile(path)
    return [n for n in z.namelist()
            if n.endswith(".xml") and SUSPECT.search(z.read(n).decode("utf-8", "ignore"))]


if __name__ == "__main__":
    for p in sorted(TARGETS):
        n = clean(p)
        left = verify(p)
        print(f"  {os.path.basename(p):52} stripped {n} part(s) -> "
              f"{'CLEAN' if not left else 'STILL PRESENT: ' + str(left)}")
