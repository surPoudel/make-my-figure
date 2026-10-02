"""The same spec and the same data must give the same figure.

Three plot types did not: volcano, network graph and lollipop produced a
different PNG every time. It was never a seeding problem - adjustText pins its
own RNG at 42 - but the solver defaults to a one-SECOND wall-clock budget and
iterates until the timer expires, so the number of passes depended on how fast
and how loaded the machine was.

The cost was real: a figure could not be regenerated from its .mmfpackage, which
is the guarantee that format exists for; golden-image regression testing was
impossible for those three; and the full suite went red at random.
"""

from __future__ import annotations

import hashlib
import io

import pytest

pytest.importorskip("matplotlib")

# Plot types that place labels with the overlap solver - the ones this is about.
LABEL_SOLVER_PLOTS = ["volcano_plot", "network_graph", "lollipop_mutation_plot"]


def _all_plot_types():
    from make_my_figure_core import examples

    return sorted(examples.plot_types_with_examples())


def _digest(plot_type):
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry
    import matplotlib.pyplot as plt

    table, aux, spec = examples.load_example(plot_type)
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    buffer = io.BytesIO()
    result.figure.savefig(buffer, format="png", dpi=90)
    plt.close(result.figure)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


@pytest.mark.parametrize("plot_type", _all_plot_types())
def test_the_same_spec_renders_the_same_figure_every_time(plot_type):
    digests = {_digest(plot_type) for _ in range(3)}
    assert len(digests) == 1, (
        f"{plot_type} rendered {len(digests)} different figures from identical "
        f"input, so it cannot be regenerated from a saved package")


@pytest.mark.parametrize("plot_type", LABEL_SOLVER_PLOTS)
def test_the_label_solver_is_bounded_by_iterations_not_by_a_clock(plot_type):
    """A wall-clock budget is a non-deterministic budget.

    Guards the actual mechanism rather than only its symptom: a renderer that
    called adjust_text without an iteration limit would pass the digest test on a
    quiet machine and fail it on a busy one.
    """
    import inspect

    from make_my_figure_core.plots import registry

    source = inspect.getsource(inspect.getmodule(registry._RENDERERS[plot_type]))
    assert "adjust_text(" in source, (
        f"{plot_type} no longer calls adjust_text; update this test")
    for chunk in source.split("adjust_text(")[1:]:
        # Match parentheses rather than stopping at the first ")" - these calls
        # contain tuples like expand_text=(1.05, 1.3), and a naive split cuts the
        # argument list in half.
        depth, end = 1, len(chunk)
        for i, ch in enumerate(chunk):
            depth += (ch == "(") - (ch == ")")
            if depth == 0:
                end = i
                break
        call = chunk[:end]
        assert "iter_lim" in call, (
            f"{plot_type} calls adjust_text without iter_lim, so it falls back to "
            f"the one-second wall-clock budget and stops being reproducible")


def test_the_iteration_budget_is_past_convergence():
    """Bounded is not enough; it has to be bounded somewhere sensible.

    On a crowded scatter the solver clears every overlap well before this, so the
    budget buys reproducibility without costing label quality.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from adjustText import adjust_text

    from make_my_figure_core.plots.base import LABEL_ADJUST_ITERATIONS

    rng = np.random.default_rng(3)
    xs, ys = rng.random(30), rng.random(30)
    figure, ax = plt.subplots(figsize=(4.3, 3.7))
    ax.scatter(xs, ys, s=8)
    texts = [ax.text(x, y, f"GENE{i:03d}", fontsize=7)
             for i, (x, y) in enumerate(zip(xs, ys))]
    adjust_text(texts, ax=ax, iter_lim=LABEL_ADJUST_ITERATIONS)
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in texts]
    overlapping = sum(1 for i in range(len(boxes)) for j in range(i + 1, len(boxes))
                      if boxes[i].overlaps(boxes[j]))
    plt.close(figure)
    assert overlapping == 0, (
        f"{overlapping} label pairs still overlap after "
        f"{LABEL_ADJUST_ITERATIONS} passes; the budget is too small")
