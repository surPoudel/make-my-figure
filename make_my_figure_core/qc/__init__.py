"""Publication quality-control: scoring and non-destructive auto-fixes.

Advisory only — QC never blocks export. `score_publication` inspects a rendered
figure (and optionally its PlotSpec / stats) and returns a `PublicationScore`
with pass/warn/fail checks and suggested fixes; `auto_fix` turns selected fixes
into a new PlotSpec.
"""

from __future__ import annotations

from make_my_figure_core.qc.auto_fix import apply_fixes, suggest_fixes
from make_my_figure_core.qc.publication_score import (
    Check,
    PublicationScore,
    score_publication,
)

__all__ = [
    "Check",
    "PublicationScore",
    "score_publication",
    "suggest_fixes",
    "apply_fixes",
]
