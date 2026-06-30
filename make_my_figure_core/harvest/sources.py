"""HTTPS data sources for the harvesting pipeline.

Every network call here is HTTPS, uses a descriptive User-Agent with a contact
address, applies a timeout, and is rate-limited by the caller. No ftp:// is
used. These endpoints are public and intended for programmatic access; we only
*download* assets after the license check in ``pipeline`` passes.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CONTACT = "sureshbt42@gmail.com"
USER_AGENT = f"MakeMyFigure-harvester/0.1 (research; mailto:{CONTACT})"

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
OA_FCGI = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
PMC_ARTICLE = "https://pmc.ncbi.nlm.nih.gov/articles"

DEFAULT_TIMEOUT = 45


class FetchError(Exception):
    pass


def _request(url: str, *, timeout: int = DEFAULT_TIMEOUT, binary: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            return (data if binary else data.decode("utf-8", "replace")), ctype, resp.status
    except Exception as exc:  # urllib raises various error types
        raise FetchError(f"GET {url} failed: {exc}") from exc


# --- Europe PMC search ------------------------------------------------------

@dataclass
class PaperRecord:
    pmcid: Optional[str]
    pmid: Optional[str]
    doi: Optional[str]
    title: Optional[str]
    journal: Optional[str]
    year: Optional[int]
    first_author: Optional[str]
    author_string: Optional[str]
    license_raw: Optional[str]
    is_open_access: bool
    first_pub_date: Optional[str]
    source_urls: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


def search_europepmc(query: str, *, page_size: int = 25,
                     cursor: str = "*", timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    params = {
        "query": query,
        "format": "json",
        "resultType": "core",
        "pageSize": str(page_size),
        "cursorMark": cursor,
    }
    url = f"{EPMC}/search?{urllib.parse.urlencode(params)}"
    text, _, _ = _request(url, timeout=timeout)
    return json.loads(text)


def _first_author(author_string: Optional[str]) -> Optional[str]:
    if not author_string:
        return None
    # "Smith J, Doe A, ..." -> surname of first author
    first = author_string.split(",")[0].strip()
    surname = first.split(" ")[0].strip()
    return re.sub(r"[^A-Za-z0-9]", "", surname) or None


def parse_record(r: Dict[str, Any]) -> PaperRecord:
    year = None
    fpd = r.get("firstPublicationDate")
    if fpd and len(fpd) >= 4 and fpd[:4].isdigit():
        year = int(fpd[:4])
    elif r.get("pubYear") and str(r["pubYear"]).isdigit():
        year = int(r["pubYear"])

    urls: List[str] = []
    for u in r.get("fullTextUrlList", {}).get("fullTextUrl", []):
        if u.get("url"):
            urls.append(u["url"])
    if r.get("doi"):
        urls.append(f"https://doi.org/{r['doi']}")

    return PaperRecord(
        pmcid=r.get("pmcid"),
        pmid=r.get("pmid"),
        doi=r.get("doi"),
        title=r.get("title"),
        journal=(r.get("journalInfo", {}) or {}).get("journal", {}).get("title")
        or r.get("journalTitle"),
        year=year,
        first_author=_first_author(r.get("authorString")),
        author_string=r.get("authorString"),
        license_raw=r.get("license"),
        is_open_access=str(r.get("isOpenAccess", "")).upper() == "Y",
        first_pub_date=fpd,
        source_urls=list(dict.fromkeys(urls)),
        raw=r,
    )


# --- NCBI OA service: independent license + asset confirmation --------------

def oa_service_license(pmcid: str, *, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Return {'license':..., 'has_package':bool, 'package_ftp':...} or error."""
    url = f"{OA_FCGI}?id={urllib.parse.quote(pmcid)}"
    text, _, _ = _request(url, timeout=timeout)
    if "<error" in text:
        m = re.search(r'code="([^"]+)"', text)
        return {"available": False, "error": m.group(1) if m else "error", "license": None}
    lic = re.search(r'license="([^"]*)"', text)
    pkg = re.search(r'href="(ftp://[^"]+\.tar\.gz)"', text)
    return {
        "available": True,
        "license": lic.group(1) if lic else None,
        "package_ftp": pkg.group(1) if pkg else None,
        "retracted": 'retracted="yes"' in text,
    }


# --- NCBI BioC: full text, figure captions, image filenames -----------------

@dataclass
class FigureCaption:
    fig_id: str
    title: Optional[str]
    caption: Optional[str]
    image_filename: Optional[str]


def fetch_bioc(pmcid: str, *, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    url = f"{BIOC}/{urllib.parse.quote(pmcid)}/unicode"
    text, _, _ = _request(url, timeout=timeout)
    return json.loads(text)


def extract_figures_from_bioc(bioc: Any) -> List[FigureCaption]:
    """Collapse BioC FIG passages into one record per figure id."""
    try:
        doc = (bioc[0] if isinstance(bioc, list) else bioc)["documents"][0]
    except (KeyError, IndexError, TypeError):
        return []
    by_id: Dict[str, FigureCaption] = {}
    for p in doc.get("passages", []):
        inf = p.get("infons", {})
        if inf.get("section_type") != "FIG":
            continue
        fid = inf.get("id") or inf.get("file") or f"fig{len(by_id)+1}"
        rec = by_id.setdefault(fid, FigureCaption(fid, None, None, inf.get("file")))
        if not rec.image_filename and inf.get("file"):
            rec.image_filename = inf["file"]
        ptype = inf.get("type", "")
        txt = (p.get("text") or "").strip()
        if "title" in ptype:
            rec.title = txt
        elif "caption" in ptype:
            rec.caption = (rec.caption + " " + txt).strip() if rec.caption else txt
        elif txt:
            rec.caption = (rec.caption + " " + txt).strip() if rec.caption else txt
    return list(by_id.values())


def bioc_full_text_present(bioc: Any) -> bool:
    try:
        doc = (bioc[0] if isinstance(bioc, list) else bioc)["documents"][0]
        return len(doc.get("passages", [])) > 0
    except (KeyError, IndexError, TypeError):
        return False


# --- PMC article page: resolve real CDN figure-image URLs -------------------

def fetch_figure_image_urls(pmcid: str, *, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, str]:
    """Map ``image_filename -> https CDN url`` by scraping the PMC article page.

    Returns only image URLs that contain a known figure filename. Empty dict if
    the page cannot be parsed (caller records this as 'images unavailable').
    """
    url = f"{PMC_ARTICLE}/{urllib.parse.quote(pmcid)}/"
    try:
        html, _, _ = _request(url, timeout=timeout)
    except FetchError:
        return {}
    urls = re.findall(r'https://cdn\.ncbi\.nlm\.nih\.gov/pmc/blobs/[^"\'\s]+\.(?:jpg|jpeg|png|gif)', html)
    out: Dict[str, str] = {}
    for u in urls:
        fname = u.rsplit("/", 1)[-1]
        out[fname] = u
    return out


# --- EPMC supplementary files (source data) ---------------------------------

def fetch_supplementary_zip(pmcid: str, *, timeout: int = DEFAULT_TIMEOUT) -> Optional[bytes]:
    """Return the supplementary-files zip bytes, or None if none available."""
    url = f"{EPMC}/{urllib.parse.quote(pmcid)}/supplementaryFiles"
    try:
        data, ctype, status = _request(url, timeout=timeout, binary=True)
    except FetchError:
        return None
    if status == 200 and data and (b"PK" == data[:2] or "zip" in (ctype or "")):
        return data
    return None


def download_binary(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    data, ctype, status = _request(url, timeout=timeout, binary=True)
    if status != 200:
        raise FetchError(f"GET {url} returned HTTP {status}")
    return data


def polite_sleep(seconds: float = 1.0) -> None:
    """Rate-limit between requests to be a good API citizen."""
    time.sleep(seconds)
