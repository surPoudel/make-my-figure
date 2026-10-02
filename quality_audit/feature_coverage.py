"""Does every visual decision a renderer makes have a control?

The option audit (``option_efficacy.py``) answers a narrower question: does every
control that IS offered actually change the figure. It cannot see a feature the
renderer decides for itself - a colour, a dash pattern, a pad, a threshold baked
into the source with no way to reach it. Those are the figures an author cannot
finish without editing Python, and they are the gap between "the controls work"
and "you can control the figure".

This walks each renderer's source for styling literals passed to a drawing call,
and reports the ones that are neither read from the spec nor taken from the
style, together with whether a plausible option already exists.

    python quality_audit/feature_coverage.py                 # all plot types
    python quality_audit/feature_coverage.py volcano_plot    # one
    python quality_audit/feature_coverage.py --verbose        # list every hit

WHAT THIS DELIBERATELY DOES NOT FLAG
A literal is not automatically a missing control. Flagging every number in a
renderer produces a list nobody can act on, which is how the earlier option
audit wasted a day. Excluded, with the reason:

* structural arguments that are not appearance - ``zorder``, ``transform``,
  ``clip_on``, ``picker``, ``label``, ``aspect``, ``rotation_mode``, ``units``;
* ``0``, ``1``, ``0.0``, ``1.0`` and ``"none"``/``None`` - almost always "off",
  "full opacity" or "no colour", not a styling choice;
* anything inside a ``get_mapping``/``block.get``/``style.`` expression - it is
  already reachable, just written inline;
* the colours of a *semantic* scale (a significance class, a diverging midpoint)
  where the renderer already exposes a named option for it;
* helper and private functions whose arguments the caller supplies.
"""

from __future__ import annotations

import argparse
import ast
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PLOTS_DIR = os.path.join(ROOT, "make_my_figure_core", "plots")

# Keyword arguments that describe how something LOOKS. These are the ones an
# author legitimately wants to change.
APPEARANCE_KWARGS = {
    "color", "c", "facecolor", "fc", "edgecolor", "ec", "markerfacecolor",
    "markeredgecolor", "linecolor", "linestyle", "ls", "linewidth", "lw",
    "markeredgewidth", "mew", "marker", "markersize", "ms", "alpha", "hatch",
    "cmap", "s", "width", "height", "capsize", "elinewidth", "bins",
    "rotation", "ha", "va", "pad", "labelpad", "fontweight", "weight",
    "fontstyle", "bbox_to_anchor", "loc", "ncol", "frameon", "framealpha",
    "shadow", "fill", "whis", "notch", "showfliers", "showmeans", "vert",
    "orientation", "align", "bottom", "left", "stacked", "density", "cumulative",
    "antialiased", "joinstyle", "capstyle", "dash_capstyle",
}

# Appearance-shaped, but deliberately NOT a control:
#
# ``interpolation`` on a heatmap is "nearest" because a heatmap cell IS a datum.
#   Offering smoothing would let an author blur measured values into a picture
#   that implies data between the samples. That is a correctness decision the
#   tool should keep making.
# ``ha`` / ``va`` place text relative to its own anchor point. They are how a
#   label is attached, not how it looks, and exposing them produces labels that
#   detach from what they annotate.
NOT_A_CONTROL = {"interpolation", "ha", "va"}

# Not appearance: structure, identity, plumbing. Changing these is not styling.
STRUCTURAL_KWARGS = {
    "zorder", "transform", "clip_on", "picker", "label", "aspect", "units",
    "rotation_mode", "animated", "gid", "in_layout", "rasterized", "snap",
    "visible", "axes", "figure", "sharex", "sharey", "squeeze", "xy", "xytext",
    "textcoords", "xycoords", "arrowprops", "usetex", "math_fontfamily",
    "transform_rotates_text", "antialiaseds", "norm", "extend", "ax", "cax",
    "mappable", "handles", "labels", "title", "fontsize", "fontproperties",
    "family", "fontfamily", "fontname",
}

# Values that are "off"/"default"/"absent" rather than a styling choice.
NEUTRAL = {0, 1, 0.0, 1.0, True, False, None, "none", "None", "", "auto",
           "center", "data", "k"}

# Calls whose styling belongs to a control that is not per-plot. ``grid`` is
# governed by the global Grid checkbox and the style profile; giving each plot its
# own grid dash pattern would be a control nobody asked for and four more ways for
# one figure set to disagree with itself.
NOT_PER_PLOT_CALLS = {"grid", "tick_params"}

DRAW_CALLS = {
    "plot", "scatter", "bar", "barh", "hist", "boxplot", "violinplot", "errorbar",
    "fill_between", "fill_betweenx", "imshow", "pcolormesh", "contour",
    "contourf", "axhline", "axvline", "axhspan", "axvspan", "annotate", "text",
    "legend", "step", "stackplot", "pie", "hlines", "vlines", "add_patch",
    "add_collection", "set_facecolor", "colorbar", "stem", "eventplot",
    "tick_params", "grid", "axline", "arrow", "quiver",
}


def _module_plot_type(path):
    """``PLOT_TYPE`` declared by a renderer module, or None for a helper."""
    text = open(path, encoding="utf-8").read()
    match = re.search(r'^PLOT_TYPE\s*=\s*"([a-z0-9_]+)"', text, re.M)
    return match.group(1) if match else None


def _literal(node):
    """The constant value of ``node``, or a sentinel when it is not constant."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) \
            and isinstance(node.operand, ast.Constant):
        try:
            return -node.operand.value
        except TypeError:
            return _NOT_LITERAL
    return _NOT_LITERAL


_NOT_LITERAL = object()


def scan_module(path):
    """Appearance literals passed to drawing calls in one renderer."""
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(source)
    lines = source.splitlines()
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.attr if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", ""))
        if name not in DRAW_CALLS or name in NOT_PER_PLOT_CALLS:
            continue
        for kw in node.keywords:
            if kw.arg is None or kw.arg in STRUCTURAL_KWARGS:
                continue
            if kw.arg in NOT_A_CONTROL or kw.arg not in APPEARANCE_KWARGS:
                continue
            value = _literal(kw.value)
            if value is _NOT_LITERAL or value in NEUTRAL:
                continue
            if isinstance(value, str) and value.strip() == "":
                continue
            hits.append({
                "line": kw.lineno,
                "call": name,
                "kwarg": kw.arg,
                "value": repr(value),
                "source": (lines[kw.lineno - 1].strip()
                           if kw.lineno - 1 < len(lines) else ""),
            })
    return hits


def _declared_option_keys(plot_type):
    from make_my_figure_core import ui_hints

    keys = {o.key for o in ui_hints.options(plot_type)}
    # Spatial renderers also read their appearance from the spatial block.
    try:
        from make_my_figure_core.plots._spatial_shared import (
            GUI_SETTABLE_SPATIAL_KEYS)

        keys |= set(GUI_SETTABLE_SPATIAL_KEYS)
    except Exception:  # noqa: BLE001
        pass
    return keys


# A kwarg is considered covered when an option plausibly names it. Kept
# deliberately generous: the point is to find features with NO control, not to
# argue about naming.
COVER_HINTS = {
    "color": ("color", "palette", "colour"),
    "c": ("color", "palette", "colour"),
    "facecolor": ("color", "fill", "palette"),
    "fc": ("color", "fill", "palette"),
    "edgecolor": ("edge", "border", "outline", "color"),
    "ec": ("edge", "border", "outline", "color"),
    "linestyle": ("style", "dash", "line"),
    "ls": ("style", "dash", "line"),
    "linewidth": ("width", "line"),
    "lw": ("width", "line"),
    "marker": ("marker", "shape", "point"),
    "markersize": ("marker", "size", "point"),
    "ms": ("marker", "size", "point"),
    "alpha": ("alpha", "opacity", "transparen"),
    "cmap": ("cmap", "colormap", "palette"),
    "s": ("size", "marker", "point", "area"),
    "capsize": ("cap", "error"),
    "elinewidth": ("error", "width"),
    "bins": ("bin",),
    "hatch": ("hatch", "pattern"),
    "loc": ("location", "legend", "position"),
    "bbox_to_anchor": ("location", "legend", "position"),
    "ncol": ("column", "legend"),
    "rotation": ("rotation", "angle"),
    "pad": ("pad", "spacing", "gap"),
    "labelpad": ("pad", "label"),
    "width": ("width",),
    "height": ("height",),
    "showfliers": ("flier", "outlier", "points"),
    "notch": ("notch", "kind"),
    "whis": ("whisker", "whis"),
    "density": ("normal", "density"),
    "cumulative": ("cumulative",),
    "stacked": ("stack",),
    "fill": ("fill",),
    "frameon": ("frame", "legend"),
}


def covered(kwarg, option_keys):
    for needle in COVER_HINTS.get(kwarg, (kwarg,)):
        if any(needle in key for key in option_keys):
            return True
    return False


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("plot_types", nargs="*")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv[1:])

    from make_my_figure_core.plots import registry

    wanted = set(args.plot_types) or set(registry.available_plot_types())
    rows = []
    for fname in sorted(os.listdir(PLOTS_DIR)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        path = os.path.join(PLOTS_DIR, fname)
        plot_type = _module_plot_type(path)
        if plot_type is None or plot_type not in wanted:
            continue
        option_keys = _declared_option_keys(plot_type)
        for hit in scan_module(path):
            rows.append({
                "plot_type": plot_type, "module": fname, **hit,
                "covered": "yes" if covered(hit["kwarg"], option_keys) else "NO",
            })

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "feature_coverage.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "plot_type", "module", "line", "call", "kwarg", "value", "covered",
            "source"])
        writer.writeheader()
        writer.writerows(rows)

    uncovered = [r for r in rows if r["covered"] == "NO"]
    print(f"{len(rows)} appearance literals in drawing calls across "
          f"{len({r['plot_type'] for r in rows})} plot types")
    print(f"  with a plausible option : {len(rows) - len(uncovered)}")
    print(f"  with NO control         : {len(uncovered)}")

    by_plot = {}
    for row in uncovered:
        by_plot.setdefault(row["plot_type"], []).append(row)
    if by_plot:
        print(f"\nUncontrolled features, worst first:")
        for plot_type, items in sorted(by_plot.items(), key=lambda kv: -len(kv[1])):
            kinds = sorted({r["kwarg"] for r in items})
            print(f"  {plot_type:34s} {len(items):3d}  {', '.join(kinds[:7])}"
                  + (" ..." if len(kinds) > 7 else ""))
    if args.verbose:
        print()
        for row in uncovered:
            print(f"  {row['module']}:{row['line']}  {row['call']}("
                  f"{row['kwarg']}={row['value']})")
    print(f"\nFull table: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
