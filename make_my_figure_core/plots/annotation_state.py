"""Shared interactive point-annotation state (frontend-agnostic).

Both the Streamlit and desktop UIs use this single model to manage which points are
labelled and where each label sits, then serialize it into the PlotSpec mapping keys
the renderers already consume:

  * ``selected_labels`` — the labelled point ids (volcano / MA / scatter / lollipop).
  * ``label_offsets``   — JSON ``{label: [dx, dy]}`` of *manually moved* labels only,
    in points; unmoved labels are omitted so the renderer auto-places them (repel).

Operations: add / toggle / select / deselect / move / set_offset / reset / delete.
Moving affects only the selected label — never the others. Pure Python; no GUI, no
Matplotlib. Round-trips through the mapping so manual placement persists on export.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Baseline offset (points) a label gets the first time it is moved, so the very first
# nudge produces a visible, leader-lined displacement near the point (not a huge jump).
_BASE_OFFSET = (8.0, 8.0)


@dataclass
class PointAnnotation:
    label_text: str
    offset_x_points: Optional[float] = None   # None => auto-placed (repel)
    offset_y_points: Optional[float] = None
    visible: bool = True

    @property
    def moved(self) -> bool:
        return self.offset_x_points is not None or self.offset_y_points is not None

    def offset(self) -> Tuple[float, float]:
        return (self.offset_x_points if self.offset_x_points is not None else _BASE_OFFSET[0],
                self.offset_y_points if self.offset_y_points is not None else _BASE_OFFSET[1])


@dataclass
class AnnotationState:
    """Ordered set of labelled points + a single 'selected' label for movement."""
    annotations: Dict[str, PointAnnotation] = field(default_factory=dict)
    selected: Optional[str] = None

    # --- membership ---------------------------------------------------------
    def labels(self) -> List[str]:
        return [a.label_text for a in self.annotations.values() if a.visible]

    def add(self, label: str) -> None:
        label = str(label)
        self.annotations.setdefault(label, PointAnnotation(label))
        self.annotations[label].visible = True
        self.selected = label

    def remove(self, label: str) -> None:
        label = str(label)
        self.annotations.pop(label, None)
        if self.selected == label:
            self.selected = None

    delete = remove

    def toggle(self, label: str) -> bool:
        """Add if absent, remove if present. Returns True if now labelled."""
        label = str(label)
        if label in self.annotations and self.annotations[label].visible:
            self.remove(label)
            return False
        self.add(label)
        return True

    # --- selection ----------------------------------------------------------
    def select(self, label: Optional[str]) -> None:
        self.selected = str(label) if (label is not None and str(label) in self.annotations) else None

    def deselect(self) -> None:
        self.selected = None

    # --- movement (selected label only) -------------------------------------
    def move(self, dx: float, dy: float) -> None:
        """Nudge the selected label by (dx, dy) points. No-op if nothing selected."""
        if not self.selected or self.selected not in self.annotations:
            return
        a = self.annotations[self.selected]
        cx, cy = a.offset()
        a.offset_x_points = float(cx) + float(dx)
        a.offset_y_points = float(cy) + float(dy)

    def set_offset(self, label: str, x: float, y: float) -> None:
        label = str(label)
        if label in self.annotations:
            self.annotations[label].offset_x_points = float(x)
            self.annotations[label].offset_y_points = float(y)

    def reset(self, label: Optional[str] = None) -> None:
        """Reset a label (or the selected one) back to auto-placement."""
        target = str(label) if label is not None else self.selected
        if target and target in self.annotations:
            self.annotations[target].offset_x_points = None
            self.annotations[target].offset_y_points = None

    # --- serialization ------------------------------------------------------
    def to_mapping(self) -> Dict[str, Any]:
        """Spec mapping fragment: selected_labels + label_offsets (moved labels only)."""
        labels = self.labels()
        offsets = {a.label_text: [a.offset_x_points, a.offset_y_points]
                   for a in self.annotations.values() if a.visible and a.moved}
        out: Dict[str, Any] = {"selected_labels": labels}
        if offsets:
            out["label_offsets"] = json.dumps(offsets)
        return out

    @classmethod
    def from_mapping(cls, mapping: Optional[Dict[str, Any]]) -> "AnnotationState":
        mapping = mapping or {}
        offsets = mapping.get("label_offsets") or {}
        if isinstance(offsets, str):
            try:
                offsets = json.loads(offsets)
            except Exception:  # noqa: BLE001
                offsets = {}
        st = cls()
        for lab in (mapping.get("selected_labels") or []):
            st.annotations[str(lab)] = PointAnnotation(str(lab))
        for lab, off in offsets.items():
            a = st.annotations.setdefault(str(lab), PointAnnotation(str(lab)))
            try:
                a.offset_x_points, a.offset_y_points = float(off[0]), float(off[1])
            except Exception:  # noqa: BLE001
                pass
        return st
