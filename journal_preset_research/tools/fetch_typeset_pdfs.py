"""Fetch typeset open-access PDFs for the Nature-family corpus papers and render their figures.

Usage: python fetch_typeset_pdfs.py CORPUS_DIR [--delay 4] [--limit N]

Only Nature-family articles (DOI prefix 10.1038) are fetched: nature.com serves the typeset PDF of
an open-access article at https://www.nature.com/articles/<id>.pdf to ordinary clients. Science and
Cell Press PDFs sit behind interactive bot checks; those are NOT fetched (we do not work around
access controls) and their figures are measured from the web-resolution JPEGs with ESTIMATED
scale instead.

Each paper gets PRIVATE_REFERENCE_ONLY/corpus/<PMCID>/typeset/ with the PDF, per-figure PNG at
600 dpi and sidecar JSON (see typeset_figures_from_pdf.py). A log line per paper goes to
typeset_fetch_log.csv in the corpus directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typeset_figures_from_pdf import render_figures  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")


def fetch(url: str, dest: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"not a PDF ({ctype}, {len(data)} bytes)")
    with open(dest, "wb") as fh:
        fh.write(data)
    return ctype


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("--delay", type=float, default=4.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args()
    log_path = os.path.join(a.corpus_dir, "typeset_fetch_log.csv")
    done = set()
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as fh:
            done = {r["pmcid"] for r in csv.DictReader(fh) if r["status"] == "ok"}
    new_file = not os.path.exists(log_path)
    n = 0
    with open(log_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["pmcid", "doi", "journal", "status", "n_figures", "widths_mm", "detail"])
        for pmcid in sorted(os.listdir(a.corpus_dir)):
            meta_path = os.path.join(a.corpus_dir, pmcid, "metadata.json")
            if not os.path.exists(meta_path) or pmcid in done:
                continue
            meta = json.load(open(meta_path, encoding="utf-8"))
            doi = str(meta.get("doi", ""))
            if not doi.startswith("10.1038/"):
                continue
            if a.limit and n >= a.limit:
                break
            n += 1
            art = doi.split("/", 1)[1]
            url = f"https://www.nature.com/articles/{art}.pdf"
            out_dir = os.path.join(a.corpus_dir, pmcid, "typeset")
            os.makedirs(out_dir, exist_ok=True)
            pdf = os.path.join(out_dir, f"{art}.pdf")
            try:
                if not os.path.exists(pdf):
                    fetch(url, pdf)
                    time.sleep(a.delay)
                recs = render_figures(pdf, out_dir, dpi=a.dpi)
                widths = ";".join(str(r["typeset_width_mm"]) for r in recs)
                w.writerow([pmcid, doi, meta.get("journal", ""), "ok", len(recs), widths, url])
            except Exception as exc:  # noqa: BLE001 - one failure must not stop the batch
                w.writerow([pmcid, doi, meta.get("journal", ""), "fail", 0, "", str(exc)[:200]])
                time.sleep(a.delay)
            fh.flush()
            print(pmcid, doi, "done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
