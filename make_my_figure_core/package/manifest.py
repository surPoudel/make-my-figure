"""Constants, checksum helpers, environment record and manifest validation."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import platform
import sys
from functools import lru_cache
from typing import Any, Dict, List

from make_my_figure_core.resources import resource_path
from make_my_figure_core.version import __version__, build_info

PACKAGE_FORMAT = "make_my_figure.figure_package"
PACKAGE_FORMAT_VERSION = 1
SUPPORTED_FORMAT_VERSIONS = (1,)
PACKAGE_EXTENSION = ".mmfpackage"
MANIFEST_NAME = "manifest.json"
ENVIRONMENT_PATH = "environment/environment.json"

PRIVACY_NOTICE = (
    "This figure package contains the data required to reproduce the figure: a frozen copy "
    "of every table the plot was drawn from (and, when available, the original source file), "
    "the plot specification, statistics, preprocessing records and preview images. Share it "
    "only with people who may see these data."
)

# Human-readable one-liners used by both frontends so the three artifacts are never confused.
ARTIFACT_DESCRIPTIONS = {
    "plot_spec": "Plot specification (.plot_spec.json): the recipe for one plot. Specification only — "
                 "the source data are required to reopen it.",
    "figure_preset": "Figure preset (.mmfpreset.json): reusable appearance/configuration, no data.",
    "figure_package": "Reproducible figure package (.mmfpackage): specification + frozen data + "
                      "statistics/preprocessing records + previews. Reopens anywhere without the "
                      "original files.",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def environment_record() -> Dict[str, Any]:
    """Software/library versions in effect when the package was written."""
    info = build_info()
    libs: Dict[str, str] = {}
    for mod in ("numpy", "pandas", "matplotlib", "scipy", "statsmodels", "openpyxl", "jsonschema"):
        try:
            libs[mod] = __import__(mod).__version__
        except Exception:  # noqa: BLE001
            libs[mod] = "not installed"
    return {
        "application": "Make My Figure",
        "version": __version__,
        "commit": info.get("commit"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "matplotlib_backend": info.get("backend"),
        "libraries": libs,
    }


@lru_cache(maxsize=1)
def load_manifest_schema() -> Dict[str, Any]:
    with open(resource_path("schemas", "figure_package_manifest.schema.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_manifest(manifest: Dict[str, Any]) -> List[str]:
    """Return a list of schema violations (empty when valid)."""
    import jsonschema

    validator = jsonschema.Draft202012Validator(load_manifest_schema())
    errors = []
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


def json_bytes(obj: Any) -> bytes:
    """Stable, human-readable JSON (used for every spec file inside the package)."""
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False, default=_default).encode("utf-8")


def _default(o: Any) -> Any:
    import numpy as np

    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if hasattr(o, "to_dict"):
        return o.to_dict()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def safe_basename_for_zip(name: str) -> str:
    """Basename made safe for a package member path."""
    from make_my_figure_core.package.security import safe_basename

    return safe_basename(name)
