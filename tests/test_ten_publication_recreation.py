"""Validate the publication figure-recreation benchmark.

Offline-safe: checks the committed manifest + per-publication artifacts (no
network). Each entry must reproduce a figure KIND confirmed present in its source
paper; a real published figure may be stored ONLY under a permissive license and
must ship a license.txt. No overclaiming, no journal-style names.
"""

import glob
import json
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BASE = os.path.join(_ROOT, "benchmarks", "ten_publication_recreation")
_MANIFEST = os.path.join(_BASE, "manifest.json")

pytestmark = pytest.mark.skipif(not os.path.exists(_MANIFEST),
                                reason="publication recreation manifest missing")

_FORBIDDEN_STYLE = ("nature-like", "science-like", "cell-like", "journal-like")
_PERMISSIVE = ("cc by", "cc0", "cc-by", "public domain", "creativecommons.org")


def _manifest():
    return json.load(open(_MANIFEST, encoding="utf-8"))


def _pubs():
    return _manifest()["publications"]


def test_manifest_valid_and_nonempty():
    man = _manifest()
    assert isinstance(man.get("publications"), list)
    assert man["n_publications"] == len(man["publications"]) >= 1


def test_every_entry_matches_a_published_figure():
    # The benchmark only contains panels whose KIND was confirmed in the paper.
    for p in _pubs():
        assert p.get("matches_published_figure") is True, p["id"]


@pytest.mark.parametrize("pub", _pubs() if os.path.exists(_MANIFEST) else [],
                         ids=lambda p: p["id"])
def test_publication_artifacts_complete(pub):
    d = os.path.join(_BASE, "publications", pub["id"])
    assert os.path.isdir(d), f"missing publication dir {pub['id']}"
    assert os.path.exists(os.path.join(d, "source", "provenance.json"))
    assert str(pub.get("doi_or_url", "")).strip() not in ("", "?", "None")
    assert str(pub.get("article_license", "")).strip() not in ("", "?", "None")
    plotspecs = glob.glob(os.path.join(d, "recreated_panels", "*", "plotspec.json"))
    assert plotspecs, f"no plotspec for {pub['id']}"
    panel = os.path.dirname(plotspecs[0])
    for ext in ("png", "svg", "pdf"):
        f = os.path.join(panel, f"recreated.{ext}")
        assert os.path.exists(f) and os.path.getsize(f) > 0, f"empty/missing {ext} for {pub['id']}"
    assert os.path.exists(os.path.join(panel, "scientific_qc.md"))
    assert os.path.exists(os.path.join(panel, "visual_qc.md"))
    assert (glob.glob(os.path.join(d, "raw_data", "*")) or
            glob.glob(os.path.join(d, "processed_data", "*"))), f"no data for {pub['id']}"


def test_stored_reference_figures_are_licensed():
    # A raw published figure may be committed ONLY under a permissive license and
    # must have a license.txt beside it naming that license.
    for imgdir in glob.glob(os.path.join(_BASE, "publications", "*", "reference_figures", "*")):
        imgs = [f for f in glob.glob(os.path.join(imgdir, "*"))
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg", ".pdf"))]
        if not imgs:
            continue
        lic = os.path.join(imgdir, "license.txt")
        assert os.path.exists(lic), f"stored figure without license.txt: {imgdir}"
        txt = open(lic, encoding="utf-8").read().lower()
        assert any(k in txt for k in _PERMISSIVE), f"non-permissive/unclear license: {lic}"
    # manifest's reference_image_stored flag must match reality
    for p in _pubs():
        rd = os.path.join(_BASE, "publications", p["id"], "reference_figures")
        has = bool(glob.glob(os.path.join(rd, "*", "*.png")) +
                   glob.glob(os.path.join(rd, "*", "*.jpg")))
        assert bool(p.get("reference_image_stored")) == has, p["id"]


def test_no_exact_reproduction_claim():
    for p in _pubs():
        assert "exact reproduction" not in str(p["classification"]).lower(), p["id"]


def test_no_journal_style_names_in_text_artifacts():
    hits = []
    for path in glob.glob(os.path.join(_BASE, "**", "*"), recursive=True):
        if not path.endswith((".json", ".md", ".py", ".csv", ".txt")):
            continue
        try:
            text = open(path, encoding="utf-8").read().lower()
        except (OSError, UnicodeDecodeError):
            continue
        for bad in _FORBIDDEN_STYLE:
            if bad in text:
                hits.append(f"{os.path.relpath(path, _ROOT)}: {bad}")
    assert not hits, "journal-style names in benchmark artifacts:\n" + "\n".join(hits)


def test_summary_table_exists_with_rows():
    csv_path = os.path.join(_BASE, "reports", "summary_table.csv")
    assert os.path.exists(csv_path)
    lines = [ln for ln in open(csv_path, encoding="utf-8").read().splitlines() if ln.strip()]
    assert len(lines) >= 2  # header + >=1 row
