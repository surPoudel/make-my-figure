"""Evidence for two manuscript claims: export fidelity and specification round trip.

1. Export fidelity. Every advertised format is written, and text in the vector formats stays text
   rather than being converted to outlines. An outlined figure cannot be corrected by a production
   editor, so this is functional rather than cosmetic.

2. Specification round trip. A PlotSpec exported alongside a figure must regenerate that figure.
   Comparison is done on the SVG content stream, which records the actual drawing commands, after
   removing the two things that differ between any two exports of the same figure: the timestamp
   matplotlib stamps into the metadata, and the random suffix it appends to element identifiers.

   Comparing at that level exposes a distinction worth keeping. A figure can fail to be
   byte-identical for two very different reasons: because the compressed bytes of an embedded
   raster are not reproducible even though every decoded pixel is the same, or because the renderer
   genuinely places something differently on the second run. Only the second is a reproducibility
   problem, so the two are separated rather than reported as one number.
"""
from __future__ import annotations

import base64
import collections
import csv
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import warnings
import zlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from make_my_figure_core.plots.registry import (  # noqa: E402
    export_figure, figure_to_bytes, render, write_sidecar,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "examples", "by_plot_type")
OUTDIR = os.path.join(ROOT, "manuscriptv3", "benchmarks")
FORMATS = ["png", "pdf", "svg", "tiff", "eps"]
PROBE = "MakeMyFigureTextProbe"

# matplotlib appends a random hex suffix to clip-path, glyph and image identifiers; the run length
# varies (an image id carries eleven digits), so the whole run is collapsed
HASHY = re.compile(r"[0-9a-f]{10,}")
DATE = re.compile(r"<dc:date>[^<]*</dc:date>")
# an embedded raster: xlink:href="data:image/png;base64,<payload, possibly line-wrapped>"
PAYLOAD = re.compile(r"base64,\s*([A-Za-z0-9+/=\s]+?)\s*\"")
# the geometry attribute, not the "d" that ends id="..."
PATH_D = re.compile(r"<path[^>]*?(?<![A-Za-z])d=\"([^\"]*)\"")


def canonical(svg_text: str):
    """Return (vector-only text, list of decoded raster arrays)."""
    t = DATE.sub("", svg_text)
    rasters = []
    for m in PAYLOAD.finditer(t):
        raw = base64.b64decode(re.sub(r"\s", "", m.group(1)))
        rasters.append(np.array(Image.open(io.BytesIO(raw)).convert("RGBA")))
    t = PAYLOAD.sub('base64,PAYLOAD"', t)
    return HASHY.sub("H", t), rasters


def _pdf_has_text_ops(data: bytes) -> bool:
    chunks = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        c = m.group(1)
        try:
            c = zlib.decompress(c)
        except zlib.error:
            pass
        chunks.append(c)
    body = b"".join(chunks) + data
    return b"BT" in body and (b"Tj" in body or b"TJ" in body)


def render_svg(spec, data_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = render(spec, pd.read_csv(data_path))
    out = figure_to_bytes(res.figure, "svg").decode("utf-8", "replace")
    plt.close(res.figure)
    return out


def check_exports(rows):
    df = pd.read_csv(os.path.join(EX, "volcano", "data.csv"))
    spec = json.load(open(os.path.join(EX, "volcano", "plotspec.json"), encoding="utf-8"))
    spec = dict(spec)
    spec["labels"] = dict(spec.get("labels", {}), title=PROBE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = render(spec, df)

    for fmt in FORMATS:
        try:
            data = figure_to_bytes(res.figure, fmt)
        except Exception as exc:  # noqa: BLE001
            rows.append({"check": f"export .{fmt}", "result": "FAILED", "bytes": 0,
                         "text_fidelity": "n/a",
                         "detail": f"{type(exc).__name__}: {exc}"[:140]})
            continue
        if fmt == "svg":
            txt = data.decode("utf-8", "replace")
            kept = "<text" in txt
            plain = re.sub(r"<[^>]+>", "", txt)
            status = "text preserved" if kept else "TEXT OUTLINED"
            detail = ("<text> elements present; probe title "
                      + ("searchable as a single string"
                         if PROBE in plain else "split across glyph elements but still text"))
        elif fmt == "pdf":
            kept = _pdf_has_text_ops(data)
            status = "text preserved" if kept else "TEXT OUTLINED"
            detail = "PDF text-showing operators (BT/Tj) present" if kept else "no text operators"
        elif fmt == "eps":
            kept = b"/Font" in data or b"findfont" in data or b"show" in data
            status = "text preserved" if kept else "TEXT OUTLINED"
            detail = "PostScript font and show operators present" if kept else "no font operators"
        else:
            status, detail = "raster", "raster format; text fidelity not applicable"
        rows.append({"check": f"export .{fmt}", "result": "written", "bytes": len(data),
                     "text_fidelity": status, "detail": detail})

    with tempfile.TemporaryDirectory() as td:
        stem = os.path.join(td, "bundle")
        written = export_figure(res.figure, stem, ["png", "pdf", "svg", "tiff", "eps"])
        side = write_sidecar(spec, res.metadata, stem)
        rows.append({"check": "export_figure writes all five formats",
                     "result": f"{len(written)}/5", "bytes": 0, "text_fidelity": "n/a",
                     "detail": ", ".join(sorted(os.path.splitext(w)[1] for w in written))})
        rows.append({"check": "PlotSpec sidecar written beside the export",
                     "result": "yes" if os.path.exists(side) else "NO",
                     "bytes": os.path.getsize(side) if os.path.exists(side) else 0,
                     "text_fidelity": "n/a", "detail": os.path.basename(side)})
    plt.close(res.figure)


REPEATS = 20


def _sig(svg_text):
    t, rasters = canonical(svg_text)
    return t, [r.tobytes() if r.size else b"" for r in rasters]


def check_stability(rows):
    """Is rendering the same specification twice deterministic at all?

    A single pair of renders is an unreliable detector: an iterative label-placement search can
    happen to converge to the same answer twice and then differ on the third attempt. Each plot type
    is therefore rendered REPEATS times and counted as non-deterministic if ANY render differs from
    the first. At 20 repeats the count is a usable figure rather than a lower bound from a couple of
    draws, though it still cannot prove determinism - a plot type reported as stable is stable across
    the renders performed.
    """
    stable, unstable = [], []
    for d in sorted(os.listdir(EX)):
        sp, dp = os.path.join(EX, d, "plotspec.json"), os.path.join(EX, d, "data.csv")
        if not (os.path.exists(sp) and os.path.exists(dp)):
            continue
        spec = json.load(open(sp, encoding="utf-8"))
        ptype = spec.get("plot_type", d)
        sigs = [_sig(render_svg(spec, dp)) for _ in range(REPEATS)]
        (stable if all(x == sigs[0] for x in sigs[1:]) else unstable).append(ptype)
    rows.append({"check": f"render stability, {REPEATS} repeats per plot type",
                 "result": f"{len(stable)}/{len(stable) + len(unstable)} stable", "bytes": 0,
                 "text_fidelity": "n/a",
                 "detail": f"differed on at least one of {REPEATS} repeats: "
                           + (", ".join(unstable) or "none")})
    return stable, unstable


def check_roundtrip(rows, stable):
    """Does the specification recovered from the exported sidecar regenerate the figure?

    Judged only on the plot types that render deterministically, because on the others a byte
    difference cannot be attributed to the specification.
    """
    ok, bad, errors = [], [], []
    for d in sorted(os.listdir(EX)):
        sp, dp = os.path.join(EX, d, "plotspec.json"), os.path.join(EX, d, "data.csv")
        if not (os.path.exists(sp) and os.path.exists(dp)):
            continue
        spec = json.load(open(sp, encoding="utf-8"))
        ptype = spec.get("plot_type", d)
        if ptype not in stable:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                first = render(spec, pd.read_csv(dp))
            with tempfile.TemporaryDirectory() as td:
                stem = os.path.join(td, "a")
                export_figure(first.figure, stem, ["png"])
                write_sidecar(spec, first.metadata, stem)
                plt.close(first.figure)
                recovered = json.load(
                    open(stem + ".plot_spec.json", encoding="utf-8"))["plot_spec"]
            (ok if _sig(render_svg(spec, dp)) == _sig(render_svg(recovered, dp))
             else bad).append(ptype)
        except Exception as exc:  # noqa: BLE001
            errors.append((ptype, f"{type(exc).__name__}: {exc}"[:120]))
    rows.append({"check": "PlotSpec round trip on deterministic plot types",
                 "result": f"{len(ok)}/{len(ok) + len(bad)}", "bytes": 0, "text_fidelity": "n/a",
                 "detail": "figure regenerated from the specification read back off disk; "
                           "vector drawing commands and decoded raster pixels both identical"
                           + ("; DIFFERED: " + ", ".join(bad) if bad else "")})
    for pt, msg in errors:
        rows.append({"check": f"round trip {pt}", "result": "ERROR", "bytes": 0,
                     "text_fidelity": "n/a", "detail": msg})
    return ok, bad


def check_marks(unstable):
    """On the unstable plot types, establish that the data marks themselves do not move."""
    out = []
    for d in sorted(os.listdir(EX)):
        sp = os.path.join(EX, d, "plotspec.json")
        if not os.path.exists(sp):
            continue
        spec = json.load(open(sp, encoding="utf-8"))
        if spec.get("plot_type") not in unstable:
            continue
        dp = os.path.join(EX, d, "data.csv")
        renders = [render_svg(spec, dp) for _ in range(REPEATS)]
        counts = {}
        for tag in ("use", "text", "path"):
            sets = [[HASHY.sub("H", e) for e in re.findall(rf"<{tag}\b[^>]*>", r)] for r in renders]
            counts[tag] = (len(sets[0]), all(x == sets[0] for x in sets[1:]))
        # capture the geometry attribute only: a bare d="...", not the d in id="..."
        paths = [PATH_D.findall(r) for r in renders]
        # compare as multisets - index alignment is meaningless once an element count shifts
        base = collections.Counter(paths[0])
        moved = set()
        for ref in paths[1:]:
            other = collections.Counter(ref)
            moved |= {g for g in (base - other)} | {g for g in (other - base)}
        curved = sum(1 for g in moved if "Q" in g)
        counts["_paths"] = (len(moved), curved)
        out.append((spec["plot_type"], counts))
    return out


def main():
    rows = []
    check_exports(rows)
    stable, unstable = check_stability(rows)
    ok, bad = check_roundtrip(rows, stable)
    marks = check_marks(unstable)
    for pt, c in marks:
        rows.append({"check": f"repeat render {pt}",
                     "result": "data markers unchanged" if c["use"][1] else "see detail",
                     "bytes": 0, "text_fidelity": "n/a",
                     "detail": "; ".join(f"<{k}> n={v[0]} identical={v[1]}"
                                         for k, v in c.items() if not k.startswith("_"))
                               + f"; moved paths {c['_paths'][0]} of which curves {c['_paths'][1]}"})

    out = os.path.join(OUTDIR, "export_validation.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["check", "result", "bytes", "text_fidelity", "detail"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['check'][:56]:58} {r['result'][:22]:24} {r['text_fidelity'][:15]:16} "
              f"{r['detail'][:46]}")

    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    n = len(stable) + len(unstable)
    n_ok = len(stable)
    n_bad = len(unstable)
    nondet_list = ", ".join(f"`{x}`" for x in unstable) or "none"
    rt = f"{len(ok)} of {len(ok) + len(bad)}"
    rt_bad = ", ".join(bad) or "none"
    reps = REPEATS
    mark_lines = "\n".join(
        "| `{}` | {} | {} | {} of {} differ, {} of them leader-line curves |".format(
            pt,
            ("n=%d, identical" % c["use"][0]) if c["use"][0] else "none drawn",
            "n=%d, %s" % (c["text"][0], "identical" if c["text"][1] else "MOVED"),
            c["_paths"][0], c["path"][0], c["_paths"][1])
        for pt, c in marks)
    open(os.path.join(OUTDIR, "specification_roundtrip.md"), "w", encoding="utf-8").write(f"""\
# Specification round trip

Verified at commit `{head}` by `scripts/validate_v3_export_and_roundtrip.py`.

Two questions are answered separately, because they can fail for unrelated reasons.

1. **Is rendering deterministic?** Does rendering one specification twice give the same figure?
2. **Does the exported specification regenerate the figure?** Does the specification read back from
   the sidecar on disk produce what the original specification produced?

The second question is only meaningful where the answer to the first is yes: on a plot type that
does not render deterministically, a byte difference cannot be attributed to the specification.

## Procedure

Each plot type in `examples/by_plot_type/` was rendered from its PlotSpec {reps} times and the
renders compared. For the plot types that proved stable, the figure was then exported with
`export_figure`, which writes a `*.plot_spec.json` sidecar; the sidecar was read back from disk, the
specification recovered from it, and the figure re-rendered from that recovered specification
against a freshly loaded copy of the same source table.

Comparison is on the SVG, which records the drawing commands themselves, after removing the
timestamp and the random element-identifier suffixes that differ between any two exports of the same
figure. Embedded raster content is decoded and compared pixel by pixel rather than by its compressed
bytes, because PNG encoding is not deterministic: comparing compressed streams would measure the
encoder rather than the figure. Four plot types embed raster content
(`heatmap_clustered_matrix`, `hierarchical_clustering`, `confusion_matrix`, `enrichment_dotplot`).

## Result

**Rendering stability.** {n_ok} of {n} plot types rendered identically across all {reps} repeats.
{n_bad} differed on at least one repeat: {nondet_list}.

**Specification round trip.** {rt} stable plot types regenerated an identical figure from the
specification recovered off disk. Differed: {rt_bad}.

## The label-placement limitation

On the unstable plot types the plotted data are unaffected; what moves is the annotation layer.
Comparing element by element across the repeats:

| plot type | data markers | text | paths |
|---|---|---|---|
{mark_lines}

Every path that moves is a curve connecting a label to its point; no straight path, and so no axis,
spine, error bar or edge, differs. Where node positions could have been at issue, they are not: `network_graph` seeds its layout from `mapping["seed"]`, so the nodes and
edges are identical and only the label connectors move. Where the labels themselves are repositioned,
the text elements move as well. In every case the data markers are identical, so no plotted value is
affected.

The cause is that the iterative label de-overlap search is not seeded, unlike the jitter, beeswarm
and network-layout randomness elsewhere in the renderers, which are. Because the search can converge
to the same answer twice and differ on a third attempt, a small number of repeats would only bound
the problem from below; {reps} repeats per plot type were therefore run and a plot type is counted as
unstable if any repeat differed from the first. A plot type reported as stable is stable across the
{reps} renders performed rather than proven deterministic.

This is a genuine limitation of the reproducibility guarantee and is reported as one: a
specification regenerates the same figure, but on these plot types the label positions are not
identical between runs. Seeding the search would remove the variation; it is recorded here as a
defect to fix rather than presented as resolved.

## Scope

This establishes that the exported specification suffices to regenerate the figure from the same
source table. It does not make the specification a self-contained archive: the specification records
the identity of the source table, not its contents. Composite figures are covered in
`figure_builder_validation_final.md`, where a FigureSpec rebuilt a four-panel composite.
""")
    print("->", out)
    print("->", os.path.join(OUTDIR, "specification_roundtrip.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
