"""PlotSpec loading and validation against the bundled JSON schema.

The canonical schema lives at ``schemas/plot_spec.schema.json`` at the repo
root. We validate against it with ``jsonschema`` and add a few app-level
checks (known plot type, known journal style) that the bare schema does not
encode, so users get actionable messages.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import jsonschema

from make_my_figure_core.resources import resource_path

_SCHEMA_PATH = resource_path("schemas", "plot_spec.schema.json")


class SpecValidationError(Exception):
    """Raised when a PlotSpec fails schema or app-level validation.

    Carries a list of human-readable messages in ``errors``.
    """

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@lru_cache(maxsize=1)
def load_schema(path: Optional[str] = None) -> Dict[str, Any]:
    schema_path = path or _SCHEMA_PATH
    with open(schema_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def default_output_block(formats: Optional[List[str]] = None, width_mm: float = 89.0,
                         height_mm: float = 70.0, dpi: int = 300) -> Dict[str, Any]:
    """A sensible default ``output`` block (single-column-ish, 300 dpi)."""
    return {
        "formats": formats or ["svg", "png", "pdf"],
        "width_mm": float(width_mm),
        "height_mm": float(height_mm),
        "dpi": int(dpi),
    }


def validate_plot_spec(
    spec: Dict[str, Any],
    *,
    known_plot_types: Optional[List[str]] = None,
    known_styles: Optional[List[str]] = None,
    schema_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate ``spec`` and return it unchanged on success.

    Raises :class:`SpecValidationError` with all collected messages otherwise.
    """
    if not isinstance(spec, dict):
        raise SpecValidationError(["PlotSpec must be a JSON object."])

    schema = load_schema(schema_path)
    validator = jsonschema.Draft202012Validator(schema)

    errors: List[str] = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{location}: {err.message}")

    # App-level checks layered on top of the permissive base schema.
    if known_plot_types is not None and spec.get("plot_type") not in known_plot_types:
        errors.append(
            f"plot_type: '{spec.get('plot_type')}' is not a supported plot type. "
            f"Supported: {sorted(known_plot_types)}"
        )

    if known_styles is not None and spec.get("journal_style") not in known_styles:
        errors.append(
            f"journal_style: '{spec.get('journal_style')}' is not a known style profile. "
            f"Known: {sorted(known_styles)}"
        )

    if errors:
        raise SpecValidationError(errors)
    return spec
