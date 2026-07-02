"""Harvest orchestration: verify -> license-gate -> download -> extract -> store.

Folder layout per accepted paper:

    figure_library/{journal_slug}/{year}_{first_author}_{short_title}/
        paper_metadata.json      # title, journal, year, doi, license, urls
        license.txt              # normalized license + reuse/TDM determination
        provenance.json          # full provenance for the paper
        full_text/bioc.json      # legal TDM full-text artifact (if permissive)
        figures/figNN.json       # caption + panel labels + image provenance
        figures/<image files>    # only CC BY/CC0 figure bitmaps
        supplementary/...        # source/supplementary data when HTTPS-available
        figures/provenance.json  # per-figure provenance index

Nothing is fabricated. Missing items are recorded as null / "unavailable", and
figure<->source-data links are recorded as "uncertain".
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from make_my_figure_core.harvest import sources as src
from make_my_figure_core.harvest.licensing import classify_license

# Nature / Science / Cell families. Flagship Nature/Science/Cell are almost
# never CC BY; the license gate will naturally surface their OA sister journals.
# Ordered as a family round-robin so a 10-paper run represents all three families
# (nature / cell / science), including the Cell-family iScience and Cell Reports.
DEFAULT_JOURNALS = [
    "Nature Communications",   # nature
    "iScience",                # cell
    "Science Advances",        # science
    "Cell Reports",            # cell
    "Communications Biology",  # nature
    "Cell Reports Medicine",   # cell
    "Scientific Reports",      # nature
    "Communications Medicine", # nature
    "npj Genomic Medicine",    # nature
]

JOURNAL_GROUP = {
    "Nature Communications": "nature",
    "Communications Biology": "nature",
    "Communications Medicine": "nature",
    "Scientific Reports": "nature",
    "npj Genomic Medicine": "nature",
    "Science Advances": "science",
    "iScience": "cell",
    "Cell Reports": "cell",
    "Cell Reports Medicine": "cell",
}


@dataclass
class HarvestConfig:
    out_dir: str
    target_papers: int = 10
    min_year: int = 2021               # strictly post-2020
    journals: List[str] = field(default_factory=lambda: list(DEFAULT_JOURNALS))
    per_journal_cap: int = 3           # diversity: cap accepted per journal
    download_figures: bool = True
    download_supplementary: bool = True
    request_delay: float = 1.0
    search_page_size: int = 25


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", (text or "").strip()).strip("_").lower()
    return s[:max_len] or "untitled"


_JOURNAL_GROUP_LC = {k.lower(): v for k, v in JOURNAL_GROUP.items()}


def _journal_group(journal: Optional[str]) -> str:
    return _JOURNAL_GROUP_LC.get((journal or "").strip().lower(), "other")


def _build_query(journal: str, min_year: int) -> str:
    # LICENSE field must be unquoted for Europe PMC (quoting returns 0 hits).
    return (
        f'OPEN_ACCESS:y AND LICENSE:cc by AND JOURNAL:"{journal}" '
        f'AND PUB_YEAR:[{min_year} TO 2025] AND IN_EPMC:y'
    )


_PANEL_RE = re.compile(r"(?:^|[.;)]\s+)([a-z])\s+(?=[A-Z(])")


def extract_panel_labels(caption: Optional[str]) -> Dict[str, Any]:
    """Heuristically extract panel labels (a, b, c, ...) from caption text.

    Marked low-confidence because we have caption text, not structured panel
    markup. Returns labels in detected order plus a confidence flag.
    """
    if not caption:
        return {"labels": [], "confidence": "none", "method": "no_caption"}
    found: List[str] = []
    for m in _PANEL_RE.finditer(caption):
        lab = m.group(1)
        if lab not in found:
            found.append(lab)
    # Only trust it if it looks like a sequential run starting at 'a'.
    sequential = found[: max(len(found), 1)] == [chr(ord("a") + i) for i in range(len(found))]
    confidence = "heuristic_medium" if (found and sequential and len(found) >= 2) else (
        "heuristic_low" if found else "none")
    return {"labels": found, "confidence": confidence, "method": "caption_regex"}


@dataclass
class HarvestResult:
    accepted: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    out_dir: str = ""


# Non-research notices we exclude from a *figure* library (quality, not fabrication).
_NON_ARTICLE_RE = re.compile(
    r"^\s*(author correction|publisher correction|correction|corrigendum|erratum|"
    r"retraction|retraction note|editorial expression of concern|comment on|reply to|"
    r"addendum)\b[:\s]", re.IGNORECASE)


def _verify_and_gate(rec: src.PaperRecord, cfg: HarvestConfig) -> Dict[str, Any]:
    """Run the verification + license checks. Returns a decision dict."""
    reasons: List[str] = []
    # 0. exclude corrections / errata / retractions (not useful for a figure library)
    if rec.title and _NON_ARTICLE_RE.match(rec.title):
        reasons.append("not a primary research article (correction/erratum/retraction/comment)")
    # 1-2. metadata + post-2020
    if not rec.pmcid:
        reasons.append("no PMCID (cannot fetch OA assets over HTTPS)")
    if not rec.doi:
        reasons.append("missing DOI")
    if not rec.year or rec.year < cfg.min_year:
        reasons.append(f"not post-2020 (year={rec.year})")
    if not rec.is_open_access:
        reasons.append("not open access")

    # 3. license must be clearly permissive, confirmed by EPMC AND OA service.
    epmc_lic = classify_license(rec.license_raw)
    oa_info = None
    oa_lic = None
    if rec.pmcid:
        try:
            oa_info = src.oa_service_license(rec.pmcid)
            oa_lic = classify_license(oa_info.get("license"))
            if oa_info.get("retracted"):
                reasons.append("retracted")
        except src.FetchError as exc:
            reasons.append(f"OA-service check failed: {exc}")

    permissive = epmc_lic.permits_reuse and (oa_lic is None or oa_lic.permits_reuse)
    if not epmc_lic.permits_reuse:
        reasons.append(f"EPMC license not permissive ({epmc_lic.normalized or rec.license_raw})")
    if oa_lic is not None and not oa_lic.permits_reuse:
        reasons.append(f"OA-service license not permissive ({oa_info.get('license')})")

    return {
        "accept": not reasons,
        "reasons": reasons,
        "epmc_license": asdict(epmc_lic),
        "oa_service": oa_info,
        "permissive": bool(permissive and not reasons),
    }


def _write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def _process_paper(rec: src.PaperRecord, decision: Dict[str, Any],
                   cfg: HarvestConfig) -> Dict[str, Any]:
    """Download permitted assets and write the folder for an accepted paper."""
    group = _journal_group(rec.journal)
    folder_name = f"{rec.year}_{rec.first_author or 'unknown'}_{_slug(rec.title)}"
    paper_dir = os.path.join(cfg.out_dir, group, folder_name)
    os.makedirs(paper_dir, exist_ok=True)
    os.makedirs(os.path.join(paper_dir, "figures"), exist_ok=True)

    epmc_lic = decision["epmc_license"]

    # license.txt
    with open(os.path.join(paper_dir, "license.txt"), "w", encoding="utf-8") as fh:
        fh.write(
            f"Journal: {rec.journal}\nDOI: {rec.doi}\n"
            f"License (raw): {rec.license_raw}\n"
            f"License (normalized): {epmc_lic['normalized']}\n"
            f"Class: {epmc_lic['klass']}\n"
            f"Permits reuse: {epmc_lic['permits_reuse']}\n"
            f"Permits TDM: {epmc_lic['permits_tdm']}\n"
            f"Note: {epmc_lic['note']}\n"
            "This determination is a conservative automated classification, "
            "not legal advice. Honor the publisher's terms.\n"
        )

    # paper_metadata.json
    metadata = {
        "title": rec.title,
        "journal": rec.journal,
        "journal_group": group,
        "year": rec.year,
        "doi": rec.doi,
        "pmcid": rec.pmcid,
        "pmid": rec.pmid,
        "first_author": rec.first_author,
        "authors": rec.author_string,
        "license_raw": rec.license_raw,
        "license_normalized": epmc_lic["normalized"],
        "is_open_access": rec.is_open_access,
        "first_publication_date": rec.first_pub_date,
        "source_urls": rec.source_urls,
    }
    _write_json(os.path.join(paper_dir, "paper_metadata.json"), metadata)

    downloads: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # Full text (legal TDM artifact).
    figures_meta: List[Dict[str, Any]] = []
    bioc = None
    try:
        src.polite_sleep(cfg.request_delay)
        bioc = src.fetch_bioc(rec.pmcid)
        if src.bioc_full_text_present(bioc):
            _write_json(os.path.join(paper_dir, "full_text", "bioc.json"), bioc)
            downloads.append({"kind": "full_text_bioc", "status": "downloaded",
                              "path": "full_text/bioc.json"})
        else:
            warnings.append("BioC returned no passages; full text unavailable.")
    except src.FetchError as exc:
        warnings.append(f"BioC fetch failed: {exc}")

    # Figure captions + panel labels + bitmaps.
    fig_caps = src.extract_figures_from_bioc(bioc) if bioc else []
    image_urls = {}
    if cfg.download_figures and fig_caps:
        try:
            src.polite_sleep(cfg.request_delay)
            image_urls = src.fetch_figure_image_urls(rec.pmcid)
        except src.FetchError as exc:
            warnings.append(f"Figure-URL resolution failed: {exc}")

    for i, fc in enumerate(fig_caps, start=1):
        panels = extract_panel_labels(fc.caption)
        fig_record: Dict[str, Any] = {
            "figure_id": fc.fig_id,
            "index": i,
            "title": fc.title,
            "caption": fc.caption,
            "panel_labels": panels["labels"],
            "panel_label_confidence": panels["confidence"],
            "panel_label_method": panels["method"],
            "image_filename": fc.image_filename,
            "image_source_url": None,
            "image_downloaded": False,
            "image_local_path": None,
            "associated_source_data": "uncertain",
            "associated_data_note": (
                "Figure-to-source-data linkage not confidently established; "
                "supplementary files are stored at the paper level."
            ),
            "license_normalized": epmc_lic["normalized"],
            "doi": rec.doi,
        }
        # Try to fetch the real CDN bitmap (CC BY/CC0 only — already gated).
        url = None
        if fc.image_filename and fc.image_filename in image_urls:
            url = image_urls[fc.image_filename]
        elif fc.image_filename:
            # match by stem (CDN filename can include a hash dir but same basename)
            for fname, u in image_urls.items():
                if fc.image_filename.rsplit(".", 1)[0] in fname:
                    url = u
                    break
        if url and cfg.download_figures:
            fig_record["image_source_url"] = url
            try:
                src.polite_sleep(cfg.request_delay)
                data = src.download_binary(url)
                ext = url.rsplit(".", 1)[-1].lower()
                local = os.path.join("figures", f"fig{i:02d}_{fc.fig_id}.{ext}")
                with open(os.path.join(paper_dir, local), "wb") as fh:
                    fh.write(data)
                fig_record["image_downloaded"] = True
                fig_record["image_local_path"] = local
                fig_record["image_bytes"] = len(data)
                downloads.append({"kind": "figure_image", "figure": fc.fig_id,
                                  "status": "downloaded", "path": local, "url": url})
            except src.FetchError as exc:
                fig_record["image_note"] = f"download failed: {exc}"
                warnings.append(f"Figure {fc.fig_id} image download failed.")
        else:
            fig_record["image_note"] = (
                "No HTTPS bitmap URL resolved from the PMC article page; "
                "raw image not downloaded (not fabricated)."
            )

        _write_json(os.path.join(paper_dir, "figures", f"fig{i:02d}_{fc.fig_id}.json"),
                    fig_record)
        figures_meta.append(fig_record)

    # Supplementary / source data (HTTPS, where available).
    supp_summary: Dict[str, Any] = {"available": False, "files": []}
    if cfg.download_supplementary and rec.pmcid:
        try:
            src.polite_sleep(cfg.request_delay)
            zbytes = src.fetch_supplementary_zip(rec.pmcid)
        except src.FetchError:
            zbytes = None
        if zbytes:
            try:
                zf = zipfile.ZipFile(io.BytesIO(zbytes))
                names = [n for n in zf.namelist() if not n.endswith("/")]
                supp_dir = os.path.join(paper_dir, "supplementary")
                os.makedirs(supp_dir, exist_ok=True)
                for n in names:
                    safe = os.path.basename(n) or "file"
                    with open(os.path.join(supp_dir, safe), "wb") as fh:
                        fh.write(zf.read(n))
                supp_summary = {"available": True, "files": [os.path.basename(n) for n in names]}
                downloads.append({"kind": "supplementary", "status": "downloaded",
                                  "count": len(names)})
            except zipfile.BadZipFile:
                warnings.append("Supplementary archive was not a valid zip; skipped.")
        else:
            supp_summary["note"] = "No supplementary files exposed via Europe PMC (HTTPS)."

    # Per-figure provenance index.
    _write_json(os.path.join(paper_dir, "figures", "provenance.json"), {
        "pmcid": rec.pmcid,
        "doi": rec.doi,
        "n_figures": len(figures_meta),
        "figures": [{k: f.get(k) for k in (
            "figure_id", "image_filename", "image_downloaded", "image_source_url",
            "panel_labels", "panel_label_confidence", "associated_source_data")}
            for f in figures_meta],
    })

    # Paper-level provenance.
    provenance = {
        "harvested_by": "make_my_figure_core.harvest (HTTPS-only, license-aware)",
        "contact": src.CONTACT,
        "paper": metadata,
        "license_determination": {
            "epmc": decision["epmc_license"],
            "oa_service": decision["oa_service"],
            "policy": "Download figures/data only for CC BY / CC BY-SA / CC0.",
        },
        "sources": {
            "metadata": "Europe PMC REST (core)",
            "license_confirmation": ["Europe PMC", "NCBI PMC OA service"],
            "full_text": "NCBI BioC (pmcoa.cgi)",
            "figure_image_urls": "NCBI PMC article page (cdn.ncbi.nlm.nih.gov)",
            "supplementary": "Europe PMC supplementaryFiles",
        },
        "downloads": downloads,
        "figures": [{k: f.get(k) for k in (
            "figure_id", "title", "panel_labels", "panel_label_confidence",
            "image_downloaded", "image_source_url", "image_local_path",
            "associated_source_data")} for f in figures_meta],
        "supplementary": supp_summary,
        "warnings": warnings,
        "transport": "https-only",
        "fabrication": "none — missing items recorded as null/unavailable",
    }
    _write_json(os.path.join(paper_dir, "provenance.json"), provenance)

    return {
        "pmcid": rec.pmcid,
        "doi": rec.doi,
        "journal": rec.journal,
        "journal_group": group,
        "year": rec.year,
        "title": rec.title,
        "folder": os.path.relpath(paper_dir, cfg.out_dir),
        "n_figures": len(figures_meta),
        "n_figure_images": sum(1 for f in figures_meta if f["image_downloaded"]),
        "supplementary_files": len(supp_summary.get("files", [])),
        "license": epmc_lic["normalized"],
        "warnings": warnings,
    }


def harvest_library(cfg: HarvestConfig) -> HarvestResult:
    """Run the pipeline until ``target_papers`` are accepted (or sources exhaust)."""
    result = HarvestResult(out_dir=cfg.out_dir)
    os.makedirs(cfg.out_dir, exist_ok=True)
    per_journal: Dict[str, int] = {}
    seen_pmcids: set = set()

    for journal in cfg.journals:
        if len(result.accepted) >= cfg.target_papers:
            break
        cursor = "*"
        for _page in range(4):  # bounded paging per journal
            if len(result.accepted) >= cfg.target_papers:
                break
            if per_journal.get(journal, 0) >= cfg.per_journal_cap:
                break
            try:
                src.polite_sleep(cfg.request_delay)
                data = src.search_europepmc(_build_query(journal, cfg.min_year),
                                            page_size=cfg.search_page_size, cursor=cursor)
            except src.FetchError as exc:
                result.rejected.append({"journal": journal, "reason": f"search failed: {exc}"})
                break

            records = data.get("resultList", {}).get("result", [])
            if not records:
                break
            for r in records:
                if len(result.accepted) >= cfg.target_papers:
                    break
                if per_journal.get(journal, 0) >= cfg.per_journal_cap:
                    break
                rec = src.parse_record(r)
                if rec.pmcid in seen_pmcids:
                    continue
                seen_pmcids.add(rec.pmcid)

                decision = _verify_and_gate(rec, cfg)
                if not decision["accept"]:
                    result.rejected.append({
                        "pmcid": rec.pmcid, "doi": rec.doi, "journal": rec.journal,
                        "year": rec.year, "reasons": decision["reasons"],
                    })
                    continue
                try:
                    summary = _process_paper(rec, decision, cfg)
                except Exception as exc:  # never let one paper kill the run
                    result.rejected.append({
                        "pmcid": rec.pmcid, "journal": rec.journal,
                        "reasons": [f"processing error: {exc}"]})
                    continue
                result.accepted.append(summary)
                per_journal[journal] = per_journal.get(journal, 0) + 1

            cursor = data.get("nextCursorMark", cursor)
            if not data.get("nextCursorMark"):
                break

    _write_report(cfg, result)
    return result


def _write_report(cfg: HarvestConfig, result: HarvestResult) -> None:
    report = {
        "target_papers": cfg.target_papers,
        "accepted_count": len(result.accepted),
        "rejected_count": len(result.rejected),
        "min_year": cfg.min_year,
        "transport": "https-only",
        "license_policy": "CC BY / CC BY-SA / CC0 only",
        "journals_queried": cfg.journals,
        "accepted": result.accepted,
        "rejected_sample": result.rejected[:50],
    }
    _write_json(os.path.join(cfg.out_dir, "provenance_report.json"), report)
