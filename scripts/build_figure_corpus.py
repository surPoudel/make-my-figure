#!/usr/bin/env python3
"""Build the open-access figure corpus described in
journal_preset_research/corpus_sampling_protocol.md.

Usage:  python scripts/build_figure_corpus.py [--families nature,science,cell]
                                              [--manifest-only]

Stores publisher material ONLY under PRIVATE_REFERENCE_ONLY/corpus/<PMCID>/ (git-ignored).
Writes journal_preset_research/corpus_manifest_expanded.csv and corpus_expansion_log.md.
"""
import argparse, csv, glob, io, json, os, re, sys, time, zipfile, collections, datetime
from urllib.parse import urlsplit
import requests
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "PRIVATE_REFERENCE_ONLY", "corpus")
SCREEN_CACHE = os.path.join(CORPUS, "_screening_cache")
RESEARCH = os.path.join(ROOT, "journal_preset_research")
PRIOR_LIB = os.path.normpath(os.path.join(ROOT, "..", "make_my_plot", "figure_library"))
STATE_FILE = os.path.join(CORPUS, "_build_state.json")

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = "make_my_plot-corpus-builder/1.0 (academic research; contact sureshbt42@gmail.com)"
DATE_FROM, DATE_TO = "2023-01-01", "2026-09-15"
FAMILY_TARGET, CAP_FRACTION, SCREEN_BUDGET = 50, 0.40, 120
SLEEP_EPMC, SLEEP_PMC = 0.7, 0.6

FAMILIES = {
    "nature": [("Nature", "Nature"), ("Nat Methods", "Nature Methods"),
               ("Nat Biotechnol", "Nature Biotechnology"), ("Nat Cell Biol", "Nature Cell Biology"),
               ("Nat Commun", "Nature Communications")],
    "science": [("Science", "Science"), ("Sci Adv", "Science Advances"),
                ("Sci Transl Med", "Science Translational Medicine")],
    "cell": [("Cell", "Cell"), ("Cancer Cell", "Cancer Cell"), ("Cell Metab", "Cell Metabolism"),
             ("Cell Syst", "Cell Systems"), ("Mol Cell", "Molecular Cell"), ("Cell Rep", "Cell Reports")],
}
FAMILY_DISPLAY = {"nature": "Nature", "science": "Science", "cell": "Cell"}
XL = "{http://www.w3.org/1999/xlink}href"

# ---------------------------------------------------------------- caption rules (protocol s5, s8)
I = re.IGNORECASE
STRONG = [r"quantif", r"\bn\s*=\s*\d", r"\bP\s*[<=>]", r"p\s*-?\s*values?", r"mean\s*[±+]|mean\s*\+/-|±\s*s\.?[de]\.?m?",
          r"\bs\.?e\.?m\.?\b|\bs\.?d\.?\b", r"box\s*plot|boxplot|violin", r"heat\s*map", r"kaplan|survival",
          r"volcano", r"\bPCA\b|principal component", r"\bUMAP\b|t-?SNE", r"bar\s*(chart|graph|plot)|bars?\s+(represent|show|indicate)",
          r"scatter", r"regression|correlation|Pearson|Spearman|\bR\^?2\b|\br\s*=\s*[-0-9.]", r"dose[- ]response|IC50|EC50",
          r"fold[- ]change|log2", r"error bars?", r"two-?sided|one-?sided|t-test|t test|Wilcoxon|Mann[- ]Whitney|ANOVA|Kruskal|chi-?square|log-?rank|Fisher",
          r"\*\s*P\b|\*\*", r"confidence interval|95%\s*CI|hazard ratio|odds ratio|forest plot", r"\bAUC\b|\bROC\b",
          r"enrichment|GSEA|GO term", r"time[- ]course|over time|kinetics"]
WEAK = [r"percentage|%\s*of", r"distribution", r"frequency", r"expression level", r"\bratio", r"number of", r"\bcounts?\b",
        r"density", r"abundance", r"\bscore"]
NONQUANT = r"micrograph|immunofluorescence|confocal|staining|representative image|schematic|model|cartoon|workflow|overview|cryo-?EM|structure|density map|western blot|gel"
STAT_TEST = r"two-?sided|one-?sided|t-test|t test|Wilcoxon|Mann[- ]Whitney|ANOVA|Kruskal|chi-?square|log-?rank|Fisher|\bP\s*[<=>]|p\s*-?\s*values?"

PLOT_FAMILIES = [
    ("scatter/regression", r"scatter|regression|correlat|Pearson|Spearman|\bR\^?2\b|\br\s*=\s*[-0-9.]|linear fit"),
    ("line/time-course", r"time[- ]course|over time|kinetic|trajector|growth curve|dose[- ]response|IC50|EC50|line (graph|plot)|curve|longitudinal|days? (after|post)|hours? (after|post)|\bdpi\b|\bh\s*p\.?i\.?\b"),
    ("bar/group comparison", r"bar (chart|graph|plot)|bars?\s+(represent|show|indicate|denote)|relative (expression|abundance|level)|fold[- ]change|normali[sz]ed to|compared (with|to) control|mean\s*[±+]|\bs\.?e\.?m\.?\b|\bs\.?d\.?\b|quantification of"),
    ("box/violin", r"box\s*plot|boxplot|box[- ]and[- ]whisker|violin|median|interquartile|whisker"),
    ("PCA/UMAP", r"\bPCA\b|principal component|\bUMAP\b|t-?SNE|\bPC\s?1\b|embedding|dimensionality reduction|cluster(ing)? (analysis|of cells)"),
    ("volcano/MA", r"volcano|\bMA plot|differentially expressed|log2\s*\(?fold|-?log10\s*\(?\s*(P|adj|FDR|q)\b"),
    ("heatmap", r"heat\s*map|hierarchical clustering|z-?score|row[- ]scaled|colou?r scale (indicates|represents)|\bmatrix\b"),
    ("survival", r"kaplan|survival (curve|analysis|probability)|log-?rank|overall survival|progression-free|hazard ratio|\bHR\s*="),
    ("forest/effect-size", r"forest plot|effect size|odds ratio|\bOR\s*=|hazard ratio|95%\s*CI|confidence interval|meta-analysis|coefficient"),
    ("dot/bubble", r"dot plot|bubble|circle size|size of (the )?(dot|circle|point)s? (indicates|represents|reflects)|individual (data )?points|each (dot|point) represents"),
    ("categorical/composition", r"stacked|proportion|percentage of|composition|pie chart|fraction of|distribution of|alluvial|Sankey|donut|contingency"),
    ("microscopy/other", r"micrograph|immunofluorescen|confocal|stain|representative image|schematic|cartoon|workflow|diagram|cryo-?EM|crystal structure|density map|western blot|immunoblot|\bgel\b|FACS plot|flow cytometry plot|model of"),
]
NUMERIC_MARKER = r"\d"

def norm(s):
    return " ".join((s or "").split())

def caption_is_quantitative(cap):
    strong = [p for p in STRONG if re.search(p, cap, I)]
    weak = [p for p in WEAK if re.search(p, cap, I)]
    ok = bool(strong) or len(weak) >= 2
    return ok, strong, weak

def classify_caption(cap):
    fams = [name for name, pat in PLOT_FAMILIES if re.search(pat, cap, I)]
    # "versus|vs." only counts for scatter together with a numeric marker
    if "scatter/regression" not in fams and re.search(r"\bversus\b|\bvs\.", cap, I) and re.search(r"\br\s*=|R\^?2|correlat", cap, I):
        fams.insert(0, "scatter/regression")
    note = ""
    quant, _, _ = caption_is_quantitative(cap)
    if not fams:
        if quant and re.search(STAT_TEST, cap, I):
            fams, note = ["bar/group comparison"], "no explicit family keyword; stat-test present"
        else:
            fams, note = ["microscopy/other"], ("unclassified-quantitative" if quant else "no quantitative marker")
    return fams, note

# ---------------------------------------------------------------- HTTP
S = requests.Session(); S.headers["User-Agent"] = UA
def get(url, sleep, **kw):
    for attempt in range(3):
        try:
            r = S.get(url, timeout=90, **kw); time.sleep(sleep)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code}")
            return r
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1) + sleep)

def epmc_query(journal, auth_man):
    q = f'JOURNAL:"{journal}" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[{DATE_FROM} TO {DATE_TO}]'
    return q + (" AND AUTH_MAN:y" if auth_man else " AND NOT AUTH_MAN:y")

def search_candidates(journal, auth_man, want):
    q = epmc_query(journal, auth_man); out, cursor, hit = [], "*", None
    while len(out) < want:
        r = get(f"{EPMC}/search", SLEEP_EPMC, params={"query": q, "format": "json", "pageSize": 100,
                                                      "resultType": "lite", "sort": "P_PDATE_D desc", "cursorMark": cursor})
        d = r.json(); hit = d.get("hitCount", 0)
        res = d.get("resultList", {}).get("result", [])
        out += [x for x in res if x.get("pmcid")]
        nxt = d.get("nextCursorMark")
        if not res or not nxt or nxt == cursor:
            break
        cursor = nxt
    out.sort(key=lambda x: (x.get("firstPublicationDate", ""), int(x["pmcid"][3:])), reverse=True)
    return q, hit, out[:want]

# ---------------------------------------------------------------- XML
def fetch_xml(pmcid):
    os.makedirs(SCREEN_CACHE, exist_ok=True)
    p = os.path.join(SCREEN_CACHE, f"{pmcid}.xml")
    if os.path.exists(p):
        return open(p, "rb").read()
    for attempt in range(4):  # non-200 answers are retried: they proved transient under load
        try:
            r = get(f"{EPMC}/{pmcid}/fullTextXML", SLEEP_EPMC)
        except Exception:
            r = None
        if r is not None and r.status_code == 200 and r.content.lstrip().startswith(b"<"):
            open(p, "wb").write(r.content.lstrip()); return r.content.lstrip()  # some records start with a newline
        if r is not None and r.status_code == 404:
            break
        time.sleep(3 * (attempt + 1))
    return None

def in_excluded_context(fig):
    for anc in fig.iterancestors():
        if anc.tag in ("supplementary-material", "app", "app-group", "back"):
            return True
        if anc.tag == "sec" and (anc.get("sec-type") or "").startswith("supplementary"):
            return True
    return False

def parse_article(xml_bytes):
    root = etree.fromstring(xml_bytes, parser=etree.XMLParser(recover=True, huge_tree=True))
    if root is None or root.tag != "article":
        return None
    info = {"article_type": root.get("article-type"), "license_text": "", "license_url": "", "figures": [],
            "is_author_manuscript": (root.find(".//article-id[@pub-id-type='manuscript']") is not None
                                     or any((g.get(XL) or "").lower().startswith("nihms") for g in root.iter("graphic")))}
    lic = root.find(".//license")
    if lic is not None:
        info["license_text"] = norm(" ".join(lic.itertext()))
        hrefs = [e.get(XL) for e in lic.iter() if e.get(XL)] + [lic.get(XL)]
        hrefs = [h for h in hrefs if h]
        m = re.search(r"https?://creativecommons\.org/[^\s)]+", info["license_text"])
        info["license_url"] = hrefs[0] if hrefs else (m.group(0).rstrip(".") if m else "")
        if "creativecommons" not in info["license_url"]:
            t = info["license_text"]
            mm = re.search(r"Creative Commons Attribution(?:[- ](Non ?Commercial))?(?:[- ](No ?Derivatives?|NoDerivs))?(?:[- ](ShareAlike))?\s*(\d\.\d)", t, I)
            if mm:
                code = "by" + ("-nc" if mm.group(1) else "") + ("-nd" if mm.group(2) else "") + ("-sa" if mm.group(3) else "")
                info["license_url"] = f"https://creativecommons.org/licenses/{code}/{mm.group(4)}/ (URL inferred from license text)"
            elif re.search(r"CC0|public domain", t, I):
                info["license_url"] = "https://creativecommons.org/publicdomain/zero/1.0/ (inferred from license text)"
    info["license_is_cc"] = "creativecommons" in (info["license_url"] + info["license_text"])
    seen = set()
    for fig in root.iter("fig"):
        if in_excluded_context(fig):
            continue
        lab = norm(" ".join(fig.find("label").itertext())) if fig.find("label") is not None else ""
        m = re.match(r"^(Fig\.?|Figure)\s*(\d+)\s*[.:]?\s*$", lab, I)
        if not m:
            if lab == "" and re.fullmatch(r"(F|Fig|fig|f)0*(\d+)", fig.get("id", "")):
                num = int(re.fullmatch(r"(F|Fig|fig|f)0*(\d+)", fig.get("id", "")).group(2))
            else:
                continue
        else:
            num = int(m.group(2))
        if num in seen:
            continue
        g = fig.find(".//graphic")
        if g is None or not g.get(XL):
            continue
        cap = norm(" ".join(fig.find("caption").itertext())) if fig.find("caption") is not None else ""
        seen.add(num)
        quant, strong, weak = caption_is_quantitative(cap)
        fams, note = classify_caption(cap)
        info["figures"].append({"figure_number": num, "label": lab, "graphic_href": g.get(XL), "caption": cap,
                                "quantitative": quant, "strong_hits": len(strong), "weak_hits": len(weak),
                                "plot_family": fams, "class_note": note,
                                "nonquant_only": (not quant) and bool(re.search(NONQUANT, cap, I))})
    info["figures"].sort(key=lambda f: f["figure_number"])
    return info

TITLE_EXCLUDE = r"^(author |publisher )?correction|^erratum|^retraction|^reply to|^response to|^correspondence|^comment on|protocol for|^a protocol|^protocols? "
def eligibility(rec, info):
    title = rec.get("title", "") or ""
    if info is None:
        return "no-xml"
    if info["article_type"] != "research-article":
        return f"article-type={info['article_type']}"
    if "review" in (rec.get("pubType") or "").lower():
        return "pubType review"
    if re.search(TITLE_EXCLUDE, title, I):
        return "title excluded (correction/protocol/comment)"
    if not info["license_text"]:
        return "no license element"
    n = len(info["figures"]); nq = sum(f["quantitative"] for f in info["figures"])
    if n < 2:
        return f"main figures={n} (<2)"
    if nq < 2:
        return f"quantitative figures={nq} of {n} (<2)"
    return "eligible"

# ---------------------------------------------------------------- images
IMG_RE = re.compile(r'https://cdn\.ncbi\.nlm\.nih\.gov/pmc/blobs/[^"\'\s<>]+', I)
EXT_RANK = {".webp": 0, ".png": 1, ".jpg": 2, ".jpeg": 2, ".tif": 3, ".gif": 9}
def ext_rank(name):
    return EXT_RANK.get(os.path.splitext(name)[1].lower(), 5)
def pmc_image_map(pmcid):
    r = get(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/", SLEEP_PMC)
    if r.status_code != 200:
        return {}
    m = {}
    for url in sorted(set(IMG_RE.findall(r.text)), key=ext_rank, reverse=True):  # best extension written last, wins
        base = os.path.basename(urlsplit(url).path)
        m[base] = url; m[os.path.splitext(base)[0]] = url
    return m

def download_figures(pmcid, info, figdir):
    os.makedirs(figdir, exist_ok=True)
    imap = pmc_image_map(pmcid); missing = []
    for f in info["figures"]:
        href = f["graphic_href"]; base = os.path.basename(href); stem = os.path.splitext(base)[0]
        url = imap.get(base) or imap.get(stem)
        f["image_url"] = url; f["local_file"] = None
        if not url:
            missing.append(f); continue
        ext = os.path.splitext(urlsplit(url).path)[1] or ".jpg"
        dest = os.path.join(figdir, f"Fig{f['figure_number']}{ext}")
        # NOTE: existing files are never removed or renamed (reviewer batches reference exact paths);
        # a full-size rendition is written alongside any earlier thumbnail and the manifest points at the best one.
        if not os.path.exists(dest):
            r = get(url, SLEEP_PMC)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                open(dest, "wb").write(r.content)
            else:
                missing.append(f); continue
        f["local_file"] = os.path.relpath(dest, ROOT).replace(os.sep, "/")
    for f in info["figures"]:
        have = sorted(glob.glob(os.path.join(figdir, f"Fig{f['figure_number']}.*")), key=ext_rank)
        if have:
            f["local_file"] = os.path.relpath(have[0], ROOT).replace(os.sep, "/")
            f["thumbnail_only"] = have[0].lower().endswith(".gif")
            if f in missing:
                missing.remove(f)
    if missing:  # fallback: Europe PMC supplementaryFiles zip (main-figure members only)
        try:
            r = S.get(f"{EPMC}/{pmcid}/supplementaryFiles", timeout=300, stream=True)
            cl = int(r.headers.get("content-length") or 0)
            if r.status_code == 200 and cl < 150_000_000:
                z = zipfile.ZipFile(io.BytesIO(r.content)); names = {}
                for n in sorted(z.namelist(), key=ext_rank, reverse=True):
                    names[os.path.splitext(n)[0]] = n  # best extension wins
                for f in missing:
                    stem = os.path.splitext(os.path.basename(f["graphic_href"]))[0]
                    n = names.get(stem)
                    if n:
                        dest = os.path.join(figdir, f"Fig{f['figure_number']}{os.path.splitext(n)[1]}")
                        open(dest, "wb").write(z.read(n))
                        f["local_file"] = os.path.relpath(dest, ROOT).replace(os.sep, "/"); f["image_url"] = "europepmc supplementaryFiles zip"
                        f["thumbnail_only"] = n.lower().endswith(".gif")
            time.sleep(SLEEP_EPMC)
        except Exception as e:
            info.setdefault("errors", []).append(f"supplementaryFiles fallback: {e}")
    return [f["figure_number"] for f in info["figures"] if not f["local_file"]]

# ---------------------------------------------------------------- thumbnail repair (coordinator request; protocol s12)
REPAIR_FILE = os.path.join(CORPUS, "_thumbnail_repair.json")
MIN_WIDTH = 300

def repair_thumbnails():
    """For every stored figure narrower than MIN_WIDTH px, fetch a full-size rendition and save it
    alongside (never deleting/renaming existing files). Records results in REPAIR_FILE."""
    from PIL import Image
    results = []
    for pdir in sorted(glob.glob(os.path.join(CORPUS, "PMC*"))):
        pmcid = os.path.basename(pdir); figdir = os.path.join(pdir, "figures"); mp = os.path.join(pdir, "metadata.json")
        if not os.path.isdir(figdir) or not os.path.exists(mp):
            continue
        meta = json.load(open(mp, encoding="utf-8")); changed = False
        small = {}
        for f in glob.glob(os.path.join(figdir, "Fig*.*")):
            try:
                w = Image.open(f).size[0]
            except Exception:
                w = 0
            n = int(re.match(r"Fig(\d+)", os.path.basename(f)).group(1))
            if w < MIN_WIDTH:
                small.setdefault(n, []).append((f, w))
        # a figure is only a problem if it has NO rendition >= MIN_WIDTH
        need = {}
        for n, lst in small.items():
            allf = glob.glob(os.path.join(figdir, f"Fig{n}.*"))
            if not any((Image.open(x).size[0] if True else 0) >= MIN_WIDTH for x in allf):
                need[n] = lst
        if not need:
            continue
        imap = pmc_image_map(pmcid); zipnames = None; z = None
        for n, lst in sorted(need.items()):
            fig = next((x for x in meta["figures"] if x["figure_number"] == n), None)
            href = fig["graphic_href"] if fig else ""
            stem = os.path.splitext(os.path.basename(href))[0]
            cands = [u for k, u in imap.items() if os.path.splitext(k)[0] == stem and not u.lower().endswith(".gif")]
            if not cands and href:  # same href with .jpg on the CDN path of the thumbnail (if we know it)
                thumb = (fig or {}).get("image_url") or ""
                if thumb.startswith("https://cdn.ncbi") and thumb.lower().endswith(".gif"):
                    cands = [thumb[:-4] + ".jpg"]
            saved = None; tried = []
            for url in sorted(set(cands), key=ext_rank):
                tried.append(url)
                try:
                    r = get(url, SLEEP_PMC)
                except Exception:
                    continue
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    ext = os.path.splitext(urlsplit(url).path)[1] or ".jpg"
                    dest = os.path.join(figdir, f"Fig{n}{ext}")
                    if os.path.exists(dest):  # never overwrite an existing path
                        dest = os.path.join(figdir, f"Fig{n}_fullsize{ext}")
                    open(dest, "wb").write(r.content)
                    if Image.open(dest).size[0] >= MIN_WIDTH:
                        saved = dest; break
                    os.remove(dest)  # our own just-written file, still too small
            if not saved:  # fallback: Europe PMC supplementaryFiles zip, non-gif member with the same stem
                try:
                    if z is None:
                        rz = S.get(f"{EPMC}/{pmcid}/supplementaryFiles", timeout=300)
                        if rz.status_code == 200 and len(rz.content) < 150_000_000:
                            z = zipfile.ZipFile(io.BytesIO(rz.content)); zipnames = z.namelist()
                        else:
                            zipnames = []
                        time.sleep(SLEEP_EPMC)
                    for nm in sorted([x for x in (zipnames or []) if os.path.splitext(os.path.basename(x))[0] == stem and not x.lower().endswith(".gif")], key=ext_rank):
                        tried.append("zip:" + nm)
                        ext = os.path.splitext(nm)[1]; dest = os.path.join(figdir, f"Fig{n}{ext}")
                        if os.path.exists(dest):
                            dest = os.path.join(figdir, f"Fig{n}_fullsize{ext}")
                        open(dest, "wb").write(z.read(nm))
                        if Image.open(dest).size[0] >= MIN_WIDTH:
                            saved = dest; break
                        os.remove(dest)
                except Exception as e:
                    tried.append(f"zip error: {e}")
            rel = os.path.relpath(saved, ROOT).replace(os.sep, "/") if saved else None
            results.append({"pmcid": pmcid, "journal": meta.get("journal"), "figure_number": n, "small_files": [(os.path.basename(f), w) for f, w in lst],
                            "fixed": bool(saved), "new_file": rel, "new_width": Image.open(saved).size[0] if saved else None, "tried": tried[:4]})
            if fig and saved:
                fig["local_file"] = rel; fig["thumbnail_only"] = False; fig["image_url"] = tried[-1]; changed = True
            elif fig:
                fig["thumbnail_only"] = True; changed = True
            print(f"  repair {pmcid} Fig{n}: {'fixed -> ' + rel if saved else 'UNFIXABLE'}", flush=True)
        if changed:
            json.dump(meta, open(mp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(results, open(REPAIR_FILE, "w"), indent=1)
    return results

# ---------------------------------------------------------------- selection
def prior_harvest_papers():
    papers = []
    for d in sorted(glob.glob(os.path.join(PRIOR_LIB, "*", "*", ""))):
        mp = os.path.join(d, "paper_metadata.json")
        if not os.path.exists(mp):
            continue
        m = json.load(open(mp, encoding="utf-8"))
        figs = []
        for cj in sorted(glob.glob(os.path.join(d, "figures", "fig*.json"))):
            c = json.load(open(cj, encoding="utf-8"))
            img = os.path.join(d, "figures", os.path.basename(c.get("image_local_path") or ""))
            figs.append({"index": c.get("index"), "caption": norm(c.get("caption") or ""), "image": img if os.path.exists(img) else None})
        m["_dir"] = d; m["_figs"] = figs
        papers.append(m)
    return papers

def quotas_for(family, n_new_target):
    js = FAMILIES[family]; base, rem = divmod(n_new_target, len(js))
    return {j[0]: base + (1 if i < rem else 0) for i, j in enumerate(js)}

def run_family(family, n_new_target, skip, state, log):
    cap = int(FAMILY_TARGET * CAP_FRACTION)
    quotas = quotas_for(family, n_new_target)
    js = [j for j, _ in FAMILIES[family]]
    cand = {}; pos = {j: 0 for j in js}; selected = {j: [] for j in js}
    for j in js:  # candidate lists: publisher first then author manuscripts
        lst = []
        for am in (False, True):
            q, hit, res = search_candidates(j, am, SCREEN_BUDGET)
            log["queries"].append({"family": family, "journal": j, "author_manuscript": am, "query": q, "hitCount": hit, "retrieved": len(res)})
            lst += [(x, am) for x in res]
        cand[j] = lst
    def fill(j, n):
        while len(selected[j]) < n and pos[j] < len(cand[j]):
            rec, am = cand[j][pos[j]]; pos[j] += 1; pmcid = rec["pmcid"]
            if pmcid in skip or pmcid in state["seen"]:
                log["screen"].append({"journal": j, "pmcid": pmcid, "result": "skipped (prior harvest / already seen)"}); continue
            state["seen"].append(pmcid)
            try:
                info = parse_article(fetch_xml(pmcid) or b"") if fetch_xml(pmcid) else None
            except Exception as e:
                info = None; log["failures"].append(f"{pmcid}: xml parse {e}")
            verdict = eligibility(rec, info)
            log["screen"].append({"journal": j, "pmcid": pmcid, "am": am, "date": rec.get("firstPublicationDate"), "result": verdict})
            if verdict != "eligible":
                continue
            pdir = os.path.join(CORPUS, pmcid); os.makedirs(pdir, exist_ok=True)
            open(os.path.join(pdir, "fulltext.xml"), "wb").write(fetch_xml(pmcid))
            try:
                missing = download_figures(pmcid, info, os.path.join(pdir, "figures"))
            except Exception as e:
                missing = [f["figure_number"] for f in info["figures"]]; log["failures"].append(f"{pmcid}: image download {e}")
            if len(missing) == len(info["figures"]):
                log["failures"].append(f"{pmcid}: no figure image could be downloaded; paper dropped"); continue
            meta = {"paper_id": pmcid, "pmcid": pmcid, "pmid": rec.get("pmid"), "doi": rec.get("doi"), "title": rec.get("title"),
                    "authors": rec.get("authorString"), "journal_query": j, "journal": dict(FAMILIES[family])[j], "journal_family": FAMILY_DISPLAY[family],
                    "year": rec.get("pubYear"), "first_publication_date": rec.get("firstPublicationDate"), "pub_type": rec.get("pubType"),
                    "article_type": info["article_type"], "author_manuscript": bool(am or info["is_author_manuscript"]),
                    "license_text": info["license_text"], "license_url": info["license_url"], "license_is_cc": info["license_is_cc"], "source_xml": f"{EPMC}/{pmcid}/fullTextXML",
                    "figures": info["figures"], "missing_figures": missing, "errors": info.get("errors", []), "downloaded": datetime.date.today().isoformat()}
            json.dump(meta, open(os.path.join(pdir, "metadata.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            open(os.path.join(pdir, "LICENSE.txt"), "w", encoding="utf-8").write(f"{info['license_url']}\n{info['license_text']}\nSource: {EPMC}/{pmcid}/fullTextXML\n")
            selected[j].append(pmcid); print(f"  [{family}/{j}] {len(selected[j])}/{n} {pmcid} {rec.get('firstPublicationDate')} AM={am} figs={len(info['figures'])} missing={missing}", flush=True)
            json.dump(state, open(STATE_FILE, "w"))
    for j in js:
        fill(j, quotas[j])
    # redistribution (protocol s6)
    for _ in range(20):
        total = sum(len(v) for v in selected.values())
        if total >= n_new_target:
            break
        movable = [j for j in js if len(selected[j]) < cap and pos[j] < len(cand[j])]
        if not movable:
            log["notes"].append(f"{family}: could not reach target {n_new_target}; got {total}"); break
        j = movable[0]; extra = min(cap - len(selected[j]), n_new_target - total)
        log["notes"].append(f"{family}: redistributing {extra} to {j}"); fill(j, len(selected[j]) + extra)
    log["selected"][family] = {j: selected[j] for j in js}
    log["screened_pos"][family] = {j: pos[j] for j in js}
    log["cand_counts"][family] = {j: len(cand[j]) for j in js}
    return selected

# ---------------------------------------------------------------- manifest / log
COLS = ["paper_id", "authors", "year", "journal", "journal_family", "DOI", "article_type", "figure_number", "panel", "plot_family",
        "local_source", "license", "usable_for_measurement", "notes"]

def write_manifest(prior, log):
    rows = []
    for m in prior:
        fam = FAMILY_DISPLAY.get(m.get("journal_group"), m.get("journal_group"))
        is_corr = bool(re.search(TITLE_EXCLUDE, m.get("title", ""), I))
        nq = sum(caption_is_quantitative(f["caption"])[0] for f in m["_figs"])
        elig = "eligible" if (len(m["_figs"]) >= 2 and nq >= 2 and not is_corr) else f"prior-harvest not eligible by s5 (figs={len(m['_figs'])}, quant={nq}, corr={is_corr})"
        for f in m["_figs"]:
            fams, cnote = classify_caption(f["caption"]); quant = caption_is_quantitative(f["caption"])[0]
            rel = os.path.relpath(f["image"], ROOT).replace(os.sep, "/") if f["image"] else ""
            usable = "no" if not f["image"] else ("yes" if quant and fams != ["microscopy/other"] else "partial")
            rows.append({"paper_id": m["pmcid"], "authors": m.get("authors", ""), "year": m.get("year"), "journal": (m.get("journal") or "").title().replace("Iscience", "iScience"),
                         "journal_family": fam, "DOI": m.get("doi", ""), "article_type": "research-article", "figure_number": f["index"], "panel": "all",
                         "plot_family": "|".join(fams), "local_source": rel, "license": f"{m.get('license_normalized','')} (raw: {m.get('license_raw','')})",
                         "usable_for_measurement": usable, "notes": "; ".join(x for x in ["prior_harvest (make_my_plot/figure_library, scripts/harvest_library.py)", elig if elig != "eligible" else "", cnote, "caption-based classification"] if x)})
    selected = {p for fam in log["selected"].values() for lst in fam.values() for p in lst}
    for mp in sorted(glob.glob(os.path.join(CORPUS, "PMC*", "metadata.json"))):
        m = json.load(open(mp, encoding="utf-8"))
        deselected = bool(selected) and m["pmcid"] not in selected
        atype = m["article_type"] + (" (author manuscript)" if m["author_manuscript"] else "")
        for f in m["figures"]:
            fams = f["plot_family"]
            if deselected or not f["local_file"] or f.get("thumbnail_only"):
                usable = "no"
            elif m["author_manuscript"] or not f["quantitative"] or fams == ["microscopy/other"]:
                usable = "partial"
            else:
                usable = "yes"
            notes = [x for x in [("deselected on re-screen: run-1 selection depended on transient Europe PMC XML failures; after re-screening in deterministic order this paper falls outside the first-N quota of its journal (folder kept in place)" if deselected else ""),
                                 ("author manuscript; figures not publisher-typeset" if m["author_manuscript"] else ""), f.get("class_note", ""),
                                 ("image missing" if not f["local_file"] else ""), ("thumbnail only (full-size image not served)" if f.get("thumbnail_only") else ""),
                                 ("" if m.get("license_is_cc", True) else "non-CC publisher license (see license column); private reference only"), "caption-based classification"] if x]
            rows.append({"paper_id": m["paper_id"], "authors": m["authors"], "year": m["year"], "journal": m["journal"], "journal_family": m["journal_family"],
                         "DOI": m["doi"], "article_type": atype, "figure_number": f["figure_number"], "panel": "all", "plot_family": "|".join(fams),
                         "local_source": f["local_file"] or "", "license": f"{m['license_url']} {m['license_text']}".strip(),
                         "usable_for_measurement": usable, "notes": "; ".join(notes)})
    rows.sort(key=lambda r: (r["journal_family"], r["journal"], str(r["paper_id"]), int(r["figure_number"])))
    with open(os.path.join(RESEARCH, "corpus_manifest_expanded.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    return rows

def write_log(rows, prior, log):
    L = []; A = L.append
    A("# Corpus expansion log\n"); A(f"Generated {datetime.datetime.now().isoformat(timespec='minutes')} by `scripts/build_figure_corpus.py` following `corpus_sampling_protocol.md`.\n")
    A("## Data sources\n")
    A("* Europe PMC REST search + fullTextXML (open-access subset, `OPEN_ACCESS:y`). `SRC:PMC` was dropped (returns 0 for these journals; PubMed-indexed articles are `SRC:MED`).")
    A("* Figure bitmaps: `https://europepmc.org/articles/{PMCID}/bin/...` returned HTTP 403 (Cloudflare JavaScript challenge) on 2026-09-16 and was not bypassed. Images were taken from PubMed Central's CDN (URL read from `https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/`, `<img class=\"graphic\">`, matched by file name to the JATS `graphic/@xlink:href`). Fallback: Europe PMC `supplementaryFiles` zip.")
    A(f"* Prior harvest: 16 papers / 77 figures already present in `{os.path.relpath(PRIOR_LIB, ROOT)}` (harvested earlier by `scripts/harvest_library.py` of make_my_plot). They are referenced in place (not copied) and were skipped in the new download; they count toward family targets.\n")
    A("## Run history\n")
    A("* Run 1 (2026-09-16, three families in parallel, 0.34 s pacing) was audited and discarded: 276 of 797 stored images were 100-px GIF thumbnails (stem matching picked the wrong rendition) and ~140 candidates were rejected as 'no-xml' because Europe PMC answered non-200 under concurrent load (all returned XML on re-query). Its logs are kept in `PRIVATE_REFERENCE_ONLY/corpus/_run1_logs/`.")
    A("* Run 2 (this log) re-screened every candidate in the deterministic order with the v1.1 amendments of the protocol (section 12). It selected exactly the same 135 papers as run 1 and rejected the same 142 candidates as 'no-xml'. Post-hoc diagnosis: those Europe PMC responses are HTTP 200 but begin with a newline before `<!DOCTYPE`, and the script's sanity check `content.startswith(b'<')` rejected them. This is a script bug, not a server failure; it systematically excludes newer (JATS 1.4 DTD) records, which are mostly the most recent 2026 papers of each journal. The check has been fixed (`lstrip()`), but the selection in this log still EXCLUDES those 142 candidates; a run 3 with the fix would re-rank them ahead of many currently selected papers (see Known biases). Papers that fell out of a re-screen selection are left in place (no folder was moved, renamed or deleted; existing thumbnail files were kept and full-size renditions added alongside) and are marked `deselected on re-screen` with usable_for_measurement=no in the manifest.\n")
    A("## Queries\n"); A("| Family | Journal | Version class | hitCount | retrieved | Query |"); A("|---|---|---|---|---|---|")
    for q in log["queries"]:
        A(f"| {q['family']} | {q['journal']} | {'author manuscript' if q['author_manuscript'] else 'publisher'} | {q['hitCount']} | {q['retrieved']} | `{q['query']}` |")
    A("\nCandidates were re-sorted locally by (firstPublicationDate desc, PMCID desc) and screened in that order; screening budget 120 per journal per version class.\n")
    A("## Screening and selection per journal\n"); A("| Family | Journal | candidates | screened | eligible+selected | of which author manuscripts | rejected (reason: n) |"); A("|---|---|---|---|---|---|---|")
    scr = collections.defaultdict(list)
    for s in log["screen"]:
        scr[s["journal"]].append(s)
    for fam, js in log["selected"].items():
        for j, sel in js.items():
            rej = collections.Counter(re.sub(r"=\d+.*", "", s["result"]) for s in scr[j] if s["result"] != "eligible")
            am = sum(1 for s in scr[j] if s["result"] == "eligible" and s.get("am") and s["pmcid"] in sel)
            A(f"| {fam} | {j} | {log['cand_counts'][fam][j]} | {log['screened_pos'][fam][j]} | {len(sel)} | {am} | {'; '.join(f'{k}: {v}' for k, v in rej.most_common())} |")
    A("\n## Papers and figures per family (prior harvest + new)\n")
    papers = collections.defaultdict(set); figs = collections.Counter(); usable = collections.Counter()
    desel = sum(1 for r in rows if r["notes"].startswith("deselected"))
    rows = [r for r in rows if not r["notes"].startswith("deselected")]
    A(f"Rows marked `deselected on re-screen` (excluded from all counts below): {desel}\n")
    for r in rows:
        papers[r["journal_family"]].add(r["paper_id"]); figs[r["journal_family"]] += 1; usable[(r["journal_family"], r["usable_for_measurement"])] += 1
    A("| Family | papers | figure rows | usable=yes | partial | no |"); A("|---|---|---|---|---|---|")
    for fam in ["Nature", "Science", "Cell"]:
        A(f"| {fam} | {len(papers[fam])} | {figs[fam]} | {usable[(fam,'yes')]} | {usable[(fam,'partial')]} | {usable[(fam,'no')]} |")
    pj = collections.Counter(); fj = collections.Counter(); seenp = set()
    for r in rows:
        fj[(r["journal_family"], r["journal"])] += 1
        if (r["paper_id"]) not in seenp:
            seenp.add(r["paper_id"]); pj[(r["journal_family"], r["journal"])] += 1
    A("\n| Family | Journal | papers | figure rows | share of family papers |"); A("|---|---|---|---|---|")
    for (fam, j), n in sorted(pj.items()):
        A(f"| {fam} | {j} | {n} | {fj[(fam, j)]} | {100*n/len(papers[fam]):.0f}% |")
    A("\n## Selected papers (one row per paper; PMCID for the follow-up NCBI OA-package / publisher-PDF fetch)\n")
    A("| PMCID | family | journal | version | first pub date | DOI | main figs | figs downloaded | license URL | source |"); A("|---|---|---|---|---|---|---|---|---|---|")
    selected = {p for fam in log["selected"].values() for lst in fam.values() for p in lst}
    for mp in sorted(glob.glob(os.path.join(CORPUS, "PMC*", "metadata.json"))):
        m = json.load(open(mp, encoding="utf-8")); nd = sum(1 for f in m["figures"] if f.get("local_file") and not f.get("thumbnail_only"))
        status = "new download" if (not selected or m["pmcid"] in selected) else "DESELECTED on re-screen (folder kept; excluded from counts)"
        A(f"| {m['pmcid']} | {m['journal_family']} | {m['journal']} | {'author manuscript' if m['author_manuscript'] else 'publisher'} | {m['first_publication_date']} | {m['doi']} | {len(m['figures'])} | {nd} | {m['license_url']} | {status} |")
    for m in prior:
        if not m["_figs"]:
            continue
        A(f"| {m['pmcid']} | {FAMILY_DISPLAY.get(m.get('journal_group'), m.get('journal_group'))} | {(m.get('journal') or '').title().replace('Iscience','iScience')} | publisher | {m.get('first_publication_date')} | {m.get('doi')} | {len(m['_figs'])} | {sum(1 for f in m['_figs'] if f['image'])} | {m.get('license_normalized')} | prior harvest (figure_library) |")
    A("\n## Plot-family counts (caption-based; a figure can carry several)\n"); A("| plot_family | Nature | Science | Cell | total |"); A("|---|---|---|---|---|")
    pf = collections.Counter()
    for r in rows:
        for f in r["plot_family"].split("|"):
            pf[(f, r["journal_family"])] += 1
    for f, _ in PLOT_FAMILIES:
        A(f"| {f} | {pf[(f,'Nature')]} | {pf[(f,'Science')]} | {pf[(f,'Cell')]} | {sum(pf[(f, x)] for x in ['Nature','Science','Cell'])} |")
    dates = sorted(x["date"] for x in log["screen"] if x.get("result") == "eligible" and x.get("date"))
    A("\n## Date range achieved\n")
    A(f"* Newly downloaded papers: {dates[0] if dates else 'n/a'} to {dates[-1] if dates else 'n/a'} (first publication date). Prior harvest: 2025-11 to 2025-12.")
    yrs = collections.Counter(str(r["year"]) for r in rows); A(f"* Figure rows by year: {dict(sorted(yrs.items()))}\n")
    A("## License distribution (figure rows)\n")
    lic = collections.Counter()
    for r in rows:
        m = re.search(r"creativecommons\.org/(licenses/[a-z-]+/\d\.\d|publicdomain/zero/1\.0)", r["license"], I)
        lic[("CC " + m.group(1).replace("licenses/", "").replace("/", " ").upper()) if m else ("CC BY (prior harvest normalized)" if r["license"].startswith("CC BY") else "non-CC: " + r["license"][:70])] += 1
    for k, v in lic.most_common():
        A(f"* {k}: {v}")
    if os.path.exists(REPAIR_FILE):
        rep_ = json.load(open(REPAIR_FILE)); fixed = [r for r in rep_ if r["fixed"]]; bad = [r for r in rep_ if not r["fixed"]]
        A(f"\n## Thumbnail repair pass (images narrower than {MIN_WIDTH} px)\n")
        A(f"* Figures examined with only a thumbnail rendition: {len(rep_)}; fixed (full-size file saved alongside, original kept): {len(fixed)}; unfixable: {len(bad)}.")
        A("\n| PMCID | journal | figure | thumbnail file(s) | result | new file | width |"); A("|---|---|---|---|---|---|---|")
        for r in rep_:
            A(f"| {r['pmcid']} | {r['journal']} | Fig{r['figure_number']} | {', '.join(f'{a} ({w}px)' for a, w in r['small_files'])} | {'fixed' if r['fixed'] else 'UNFIXABLE'} | {r['new_file'] or ''} | {r['new_width'] or ''} |")
    A("\n## Failures\n")
    for f in log["failures"] or ["none"]:
        A(f"* {f}")
    A("\n## Redistribution / notes\n")
    for n in log["notes"] or ["none"]:
        A(f"* {n}")
    A("\n## Known biases\n")
    A("* OA-subset selection: Nature, Science, Cell, Cancer Cell, Cell Metabolism, Molecular Cell publish mostly non-OA content; the OA subset is enriched for funder-mandated papers and author manuscripts.")
    A("* Author manuscripts (flagged `partial`) dominate Science, Science Translational Medicine and several Cell Press titles; their figures are author-supplied, not publisher-typeset.")
    A("* Date-descending ordering concentrates the corpus in 2025-2026.")
    A("* Caption-based plot-family assignment over-detects `bar/group comparison` (generic SEM/SD language) and under-detects families that captions do not name; to be refined visually.")
    A("* The prior harvest adds journals outside the target list (Communications Biology, Scientific Reports, iScience) to the Nature and Cell families.")
    A("* Europe PMC `JOURNAL:` matches the MEDLINE abbreviation exactly; alternative title strings are missed.")
    A("* SELECTION BUG (runs 1-2): 142 candidates whose full-text XML begins with a newline were rejected as 'no-xml' by a too-strict sanity check. They are disproportionately the newest records (JATS 1.4 DTD, 2026). The stored selection is therefore 'first N eligible among candidates whose XML starts with `<`', not strictly 'first N eligible'. The check is fixed in the script; re-running the selection (run 3) would deselect a substantial share of the current papers in favour of newer ones and is pending the coordinator's decision because reviewers already work from the current folders.")
    open(os.path.join(RESEARCH, "corpus_expansion_log.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

def load_logs():
    log = {"queries": [], "screen": [], "failures": [], "notes": [], "selected": {}, "screened_pos": {}, "cand_counts": {}}
    for lp in sorted(glob.glob(os.path.join(CORPUS, "_build_log_*.json"))):
        l = json.load(open(lp))
        for k in ("queries", "screen", "failures", "notes"):
            log[k] += l.get(k, [])
        for k in ("selected", "screened_pos", "cand_counts"):
            log[k].update(l.get(k, {}))
    return log

def main():
    global STATE_FILE
    ap = argparse.ArgumentParser(); ap.add_argument("--families", default="nature,science,cell"); ap.add_argument("--manifest-only", action="store_true"); ap.add_argument("--repair-thumbnails", action="store_true")
    a = ap.parse_args(); os.makedirs(CORPUS, exist_ok=True)
    prior = prior_harvest_papers(); skip = {m["pmcid"] for m in prior}
    prior_count = collections.Counter(m["journal_group"] for m in prior if m["_figs"] and not re.search(TITLE_EXCLUDE, m.get("title", ""), I))
    if not a.manifest_only:
        for fam in a.families.split(","):
            logp = os.path.join(CORPUS, f"_build_log_{fam}.json"); STATE_FILE = os.path.join(CORPUS, f"_build_state_{fam}.json")
            log = {"queries": [], "screen": [], "failures": [], "notes": [], "selected": {}, "screened_pos": {}, "cand_counts": {}}
            state = {"seen": []}
            n_new = FAMILY_TARGET - prior_count.get(fam, 0)
            print(f"== family {fam}: prior={prior_count.get(fam,0)} new target={n_new} quotas={quotas_for(fam, n_new)}", flush=True)
            try:
                run_family(fam, n_new, skip, state, log)
            finally:
                json.dump(log, open(logp, "w"), indent=1)
    if a.repair_thumbnails:
        repair_thumbnails()
    log = load_logs(); rows = write_manifest(prior, log); write_log(rows, prior, log)
    print(f"manifest rows: {len(rows)}")

if __name__ == "__main__":
    main()
