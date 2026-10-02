"""Does every control actually change the figure?

A control that is offered but ignored is worse than a missing one: the author
changes it, sees nothing, and cannot tell whether the setting is broken or their
expectation is wrong. This renders each plot type twice per control - once at the
default, once at a changed value - and compares the resulting PNG bytes.

Three plot types do not render deterministically (unseeded label repulsion and
spring layout), so for those a same-vs-same render is taken first and anything
that cannot be distinguished from that noise is reported as INDETERMINATE rather
than as a pass or a failure.

    python quality_audit/option_efficacy.py            # all plot types
    python quality_audit/option_efficacy.py volcano_plot ...
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
import traceback
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EFFECTIVE, NO_EFFECT, INDETERMINATE, ERROR, SKIPPED = (
    "effective", "NO EFFECT", "indeterminate", "ERROR", "skipped")
# A control the plot type openly declares it does not support is not a bug: the
# app already tells the user so. Only a control that is offered, silently
# swallowed and never declared is a defect.
DECLARED = "declared-unsupported"
# The figure has nothing for this control to act on - no legend to resize, no
# annotations to restyle. Not a defect, and not evidence the control works.
NOT_EXERCISED = "not-exercised"

# Some controls need another setting switched on before they have anything to act
# on. The clustered heatmap's example ships with k=0, so it draws no cluster bars
# and every cluster-bar control looks dead; a facet control needs a facet column
# mapped. Without this the audit reports a precondition it failed to meet as a
# defect in the control.
PRECONDITIONS = {
    "heatmap_clustered_matrix": {"cluster_k_rows": 3, "cluster_k_columns": 3},
    "hierarchical_clustering": {"cluster_k_rows": 3},
}


# Which element a control needs before its effect can be judged.
CONTROL_REQUIRES = {
    "style.legend_pt": "legend", "style.legend_title_pt": "legend",
    "layout.legend_location": "legend",
    "style.annotation_pt": "annotation",
    "style.marker_size": "marker", "style.line_width_pt": "line",
    # A chord diagram, a Sankey and the spatial maps hide their axes on purpose:
    # there is no tick label to rotate, no spine to thicken and no axis label to
    # pad. Reporting those as dead controls invents a bug out of correct
    # behaviour, and buries the real findings in noise.
    "style.tick_label_pt": "ticks", "style.axis_font_pt": "axis_labels",
    "style.spine_width_pt": "spines", "style.grid": "ticks",
    "layout.x_tick_rotation": "ticks", "layout.y_tick_rotation": "ticks",
    "layout.x_tick_pad": "ticks", "layout.y_tick_pad": "ticks",
    "layout.x_label_pad": "axis_labels", "layout.y_label_pad": "axis_labels",
    "layout.title_pad": "title",
}

# Style controls that live on the StyleProfile rather than in a plot's option
# list. These, and only these, are patched into the spec's "style" block -
# ui_hints.Option.scope describes preset portability, not a spec location, so it
# must not be used to decide where a value is written.
GLOBAL_STYLE_CONTROLS = [
    ("palette_name", ["grayscale", "high_contrast"]),
    ("font_family", ["DejaVu Serif", "DejaVu Sans Mono"]),
    ("title_font_pt", [24.0, 7.0]),
    ("axis_font_pt", [22.0, 6.0]),
    ("tick_label_pt", [20.0, 5.0]),
    ("annotation_pt", [20.0, 5.0]),
    ("legend_pt", [20.0, 5.0]),
    ("legend_title_pt", [20.0, 5.0]),
    ("marker_size", [120.0, 4.0]),
    ("line_width_pt", [4.5, 0.3]),
    ("spine_width_pt", [4.0, 0.2]),
    ("text_color", ["#CC0000", "#00AA00"]),
    ("grid", [True, False]),
]

# Controls that only mean something as a set. ``explicit_figure_size`` is
# all-or-nothing by design, so patching width_mm alone and calling it dead was an
# audit artefact - it sent an agent looking for a bug that was not there. It did
# sit next to a real one (a half-pinned size was being discarded), but the audit
# has to ask the question the code actually answers.
COMBINED_LAYOUT_CONTROLS = [
    ("width_mm+height_mm", [{"width_mm": 101.6, "height_mm": 50.8},
                            {"width_mm": 220.0, "height_mm": 190.0}]),
    ("margins", [{"margin_left": 0.03, "margin_right": 0.65,
                  "margin_top": 0.99, "margin_bottom": 0.02}]),
]

LAYOUT_CONTROLS = [
    ("column_width", ["single", "double", "onehalf"]),
    ("width_mm", [101.6, 220.0]),
    ("height_mm", [50.8, 190.0]),
    ("margin_left", [0.03, 0.35]),
    ("margin_right", [0.65, 0.99]),
    ("margin_top", [0.60, 0.99]),
    ("margin_bottom", [0.02, 0.40]),
    ("x_tick_rotation", ["vertical", "45", "horizontal"]),
    ("y_tick_rotation", ["vertical", "45", "horizontal"]),
    ("title_pad", [30.0, 2.0]),
    # The real key names, checked against what base.py reads. An earlier run of
    # this audit asked for "axis_label_pad", which nothing reads, and so reported
    # 42 of 45 plot types as having a dead control. The key names in these tables
    # have to be verified against the code, or the audit invents its own bugs.
    ("x_label_pad", [25.0, 1.0]),
    ("y_label_pad", [25.0, 1.0]),
    ("x_tick_pad", [20.0, 0.5]),
    ("y_tick_pad", [20.0, 0.5]),
    ("legend_location", ["lower left", "upper right", "outside right"]),
]


def _seed_everything():
    """Pin the RNGs, for what it is worth.

    Not the whole story: ``adjustText`` already seeds itself at 42, and the label
    drift on three plot types comes from its iterative overlap resolution
    converging differently with canvas state, not from an RNG. That is why the
    comparison below measures a noise floor rather than trusting byte equality.
    """
    import random

    import numpy as np

    random.seed(0)
    np.random.seed(0)


def _digest(plot_type, spec_patch=None, style_patch=None, layout_patch=None):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    _seed_everything()
    table, aux, spec = examples.load_example(plot_type)
    spec = dict(spec)

    mapping_base = {**(spec.get("mapping") or {}),
                    **PRECONDITIONS.get(plot_type, {})}
    spec["mapping"] = mapping_base
    if spec_patch:
        spec["mapping"] = {**mapping_base, **spec_patch}
    if style_patch:
        spec["style"] = {**(spec.get("style") or {}), **style_patch}
    # Title controls cannot be judged on a figure with no title, and the title
    # lives in the layout block (that is where the GUI's Title field writes).
    base_layout = {"title": "Audit title for option efficacy",
                   **(spec.get("layout") or {})}
    spec["layout"] = {**base_layout, **(layout_patch or {})}
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    figure.canvas.draw()
    import numpy as np

    pixels = np.asarray(figure.canvas.buffer_rgba(), dtype=np.float32)
    plt.close(figure)
    return pixels


def _difference(a, b):
    """Mean absolute pixel difference, 0-255. 0 means the figures are identical."""
    import numpy as np

    if a.shape != b.shape:
        return 255.0                         # a size change is a real change
    return float(np.abs(a - b).mean())


def _changed_values(option):
    """Every value worth trying, not just the first alternative.

    Trying one value is enough to condemn a working control: the clustered
    heatmap's cluster_legend="rows" renders identically to its "auto" default
    when only the rows are clustered, and column_width="single" is already the
    default for several examples. A control counts as working if ANY candidate
    moves the figure.
    """
    default = option.default
    if option.kind == "bool":
        return [not bool(default)]
    if option.kind == "choice":
        return [c for c in (option.choices or []) if c != default]
    if option.kind == "number":
        lo = option.minimum if option.minimum is not None else 0.0
        hi = option.maximum if option.maximum is not None else (float(default or 0) + 10)
        try:
            cur = float(default if default is not None else lo)
        except (TypeError, ValueError):
            return []
        out = []
        for candidate in (hi, lo, (lo + hi) / 2.0):
            if candidate == cur:
                continue
            out.append(int(candidate) if (option.decimals or 0) == 0 else candidate)
        return out
    return []


def _elements_present(plot_type):
    """Which drawable elements the default figure actually has."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    present = set()
    table, aux, spec = examples.load_example(plot_type)
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    figure.canvas.draw()
    # Only the data axes. A colourbar carries its own tick labels, and counting
    # those makes a chord diagram or a Sankey - which hide their axes entirely -
    # look as though they have ticks for the tick controls to act on.
    data_axes = [a for a in figure.axes
                 if not getattr(a, "_colorbar", False)
                 and a.get_label() != "<colorbar>"] or figure.axes[:1]
    for ax in data_axes:
        if ax.get_legend() is not None or any(
                c.__class__.__name__ == "Legend" for c in ax.get_children()):
            present.add("legend")
        tick_texts = {t.get_text() for t in ax.get_xticklabels() + ax.get_yticklabels()}
        for txt in ax.texts:
            if txt.get_text().strip() and txt.get_text() not in tick_texts:
                present.add("annotation")
        if ax.collections or ax.patches:
            present.add("marker")
        if ax.lines or ax.collections:
            present.add("line")
        # ``ax.axison`` is the honest test. After ax.axis("off") matplotlib still
        # hands back tick-label objects with text and still reports the spines as
        # visible - they simply are not drawn - so asking those two questions
        # directly says a chord diagram has ticks when it plainly has none.
        if not ax.axison:
            continue
        if any(t.get_text().strip() and t.get_visible()
               for t in ax.get_xticklabels() + ax.get_yticklabels()):
            present.add("ticks")
        if ax.get_xlabel().strip() or ax.get_ylabel().strip():
            present.add("axis_labels")
        if any(sp.get_visible() for sp in ax.spines.values()):
            present.add("spines")
        if ax.get_title().strip():
            present.add("title")
    if getattr(figure, "_suptitle", None) is not None and \
            figure._suptitle.get_text().strip():
        present.add("title")
    plt.close(figure)
    return present


def audit_plot_type(plot_type):
    from make_my_figure_core import ui_hints

    rows = []
    try:
        base = _digest(plot_type)
        # Two more renders of the *same* thing give the noise floor: on the three
        # plot types whose labels drift, "different pixels" does not by itself mean
        # the control did anything.
        floor = max(_difference(base, _digest(plot_type)),
                    _difference(base, _digest(plot_type)))
    except Exception as exc:  # noqa: BLE001
        return [(plot_type, "<render>", "", ERROR,
                 f"{type(exc).__name__}: {exc}".replace("\n", " ")[:160])]

    # Comfortably above the drift, and still far below any visible change.
    threshold = max(floor * 4.0, 1e-4)
    try:
        present = _elements_present(plot_type)
    except Exception:  # noqa: BLE001
        present = set()

    def verdict(changed):
        delta = _difference(base, changed)
        if delta > threshold:
            return EFFECTIVE
        if floor > 0 and delta > 0:
            return INDETERMINATE          # moved, but within this plot's own drift
        return NO_EFFECT

    for option in ui_hints.options(plot_type):
        values = _changed_values(option)
        if not values:
            rows.append((plot_type, option.key, "", SKIPPED, "no alternative value"))
            continue
        best, chosen, error = NO_EFFECT, values[-1], None
        for value in values:
            try:
                result = verdict(_digest(plot_type, spec_patch={option.key: value}))
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}".replace("\n", " ")[:160]
                continue
            if result == EFFECTIVE:
                best, chosen = EFFECTIVE, value
                break
            if result == INDETERMINATE:
                best, chosen = INDETERMINATE, value
        if best == NO_EFFECT and error:
            rows.append((plot_type, option.key, repr(chosen), ERROR, error))
        else:
            rows.append((plot_type, option.key, repr(chosen), best,
                         f"drift floor {floor:.4f}" if floor else ""))

    try:
        from make_my_figure_core.styles.capabilities import warn_ignored_style_controls
    except Exception:  # noqa: BLE001
        warn_ignored_style_controls = None

    def declared_unsupported(key, value):
        """True when the app already warns that this control does not apply."""
        if warn_ignored_style_controls is None:
            return False
        try:
            return bool(warn_ignored_style_controls(plot_type, {key: value}))
        except Exception:  # noqa: BLE001
            return False

    def best_over_values(label, values, patch_name, capability_key=None,
                         full_label=""):
        """Try every candidate; the control works if any of them moves the figure."""
        best, best_value, error = NO_EFFECT, None, None
        for value in values:
            try:
                changed = _digest(plot_type, **{patch_name: {label: value}})
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}".replace("\n", " ")[:160]
                continue
            result = verdict(changed)
            if result == EFFECTIVE:
                return EFFECTIVE, value, ""
            if result == INDETERMINATE:
                best, best_value = INDETERMINATE, value
        if best == NO_EFFECT and capability_key and declared_unsupported(
                capability_key, values[0]):
            return DECLARED, values[0], "app warns this control does not apply"
        needs = CONTROL_REQUIRES.get(full_label)
        if best == NO_EFFECT and needs and needs not in present:
            return NOT_EXERCISED, values[0], f"this figure draws no {needs}"
        if best == NO_EFFECT and error:
            return ERROR, values[0], error
        return best, best_value if best_value is not None else values[-1], ""

    for key, values in GLOBAL_STYLE_CONTROLS:
        result, value, note = best_over_values(key, values, "style_patch",
                                               capability_key=key,
                                               full_label=f"style.{key}")
        rows.append((plot_type, f"style.{key}", repr(value), result, note))

    for key, values in LAYOUT_CONTROLS:
        result, value, note = best_over_values(key, values, "layout_patch",
                                               full_label=f"layout.{key}")
        rows.append((plot_type, f"layout.{key}", repr(value), result, note))

    for label, patches in COMBINED_LAYOUT_CONTROLS:
        best, chosen = NO_EFFECT, patches[-1]
        for patch in patches:
            try:
                if verdict(_digest(plot_type, layout_patch=patch)) == EFFECTIVE:
                    best, chosen = EFFECTIVE, patch
                    break
            except Exception as exc:  # noqa: BLE001
                best, chosen = ERROR, patch
                rows.append((plot_type, f"layout.{label}", repr(patch), ERROR,
                             f"{type(exc).__name__}: {exc}".replace("\n", " ")[:160]))
                break
        else:
            pass
        if best != ERROR:
            rows.append((plot_type, f"layout.{label}", repr(chosen), best, ""))
    return rows


def main(argv):
    from make_my_figure_core import examples

    targets = argv[1:] or sorted(examples.plot_types_with_examples())
    rows = []
    with ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 4)) as pool:
        for result in pool.map(audit_plot_type, targets):
            rows.extend(result)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "option_efficacy.csv")
    import csv
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["plot_type", "control", "changed_to", "verdict", "note"])
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row[3]] = counts.get(row[3], 0) + 1
    print(f"{len(rows)} control/plot combinations over {len(targets)} plot types")
    for k in (EFFECTIVE, DECLARED, NOT_EXERCISED, NO_EFFECT, INDETERMINATE,
              ERROR, SKIPPED):
        if counts.get(k):
            print(f"  {k:15s} {counts[k]}")

    dead = [r for r in rows if r[3] == NO_EFFECT]
    if dead:
        print(f"\nControls that changed nothing ({len(dead)}):")
        by_control = {}
        for pt, control, _v, _verd, _n in dead:
            by_control.setdefault(control, []).append(pt)
        for control, pts in sorted(by_control.items(), key=lambda kv: -len(kv[1])):
            shown = ", ".join(pts[:4]) + (f" +{len(pts) - 4} more" if len(pts) > 4 else "")
            print(f"  {control:34s} {len(pts):3d}  {shown}")
    errs = [r for r in rows if r[3] == ERROR]
    if errs:
        print(f"\nControls that raised ({len(errs)}):")
        for pt, control, value, _v, note in errs[:25]:
            print(f"  {pt}.{control}={value}: {note}")
    print(f"\nFull table: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
