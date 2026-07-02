"""License classification for reuse / text-and-data-mining decisions.

We only treat a paper's assets as downloadable for figure reuse + TDM when the
license is one of CC BY, CC BY-SA, or CC0. Everything else (CC BY-NC*, CC
BY-ND*, "all rights reserved", publisher-specific, or unknown) is treated as
NOT clearly permissive and is recorded as license-blocked rather than guessed.

This is a conservative, defensible policy. It is NOT legal advice; downstream
users remain responsible for honoring each publisher's terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LicenseClass(str, Enum):
    PERMISSIVE = "permissive"        # CC BY / CC BY-SA / CC0 -> reuse + TDM OK
    NONCOMMERCIAL = "noncommercial"  # CC BY-NC* -> non-commercial only
    NODERIV = "noderivatives"        # CC BY-ND* -> no derivatives
    RESTRICTED = "restricted"        # all rights reserved / subscription
    UNKNOWN = "unknown"              # missing or unrecognized


# Licenses we will actually download figure/data assets for.
PERMISSIVE_CLASSES = {LicenseClass.PERMISSIVE}


@dataclass
class LicenseInfo:
    raw: Optional[str]
    klass: LicenseClass
    normalized: Optional[str]   # e.g. "CC BY", "CC0"
    permits_reuse: bool         # figure reuse + redistribution
    permits_tdm: bool           # text/data mining
    note: str


def _normalize(raw: str) -> str:
    s = raw.strip().lower()
    s = s.replace("creative commons", "cc").replace("attribution", "by")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def classify_license(raw: Optional[str]) -> LicenseInfo:
    """Classify a free-text or code license string conservatively."""
    if not raw or not str(raw).strip():
        return LicenseInfo(raw, LicenseClass.UNKNOWN, None, False, False,
                           "No license string supplied; treated as unknown.")

    s = _normalize(str(raw))
    tokens = set(s.split())

    has_cc = "cc" in tokens or "cc0" in tokens or s.startswith("cc")
    nc = "nc" in tokens or "noncommercial" in s.replace(" ", "")
    nd = "nd" in tokens or "noderiv" in s.replace(" ", "")

    # CC0 / public domain.
    if "cc0" in s or "publicdomain" in s.replace(" ", "") or "pdm" in tokens:
        return LicenseInfo(raw, LicenseClass.PERMISSIVE, "CC0", True, True,
                           "Public-domain dedication; reuse and TDM permitted.")

    if has_cc and "by" in tokens:
        if nd:
            return LicenseInfo(raw, LicenseClass.NODERIV, "CC BY-ND", False, True,
                               "No-derivatives: figures may not be modified; not downloaded for reuse.")
        if nc:
            return LicenseInfo(raw, LicenseClass.NONCOMMERCIAL, "CC BY-NC", False, True,
                               "Non-commercial only; not downloaded under the permissive policy.")
        if "sa" in tokens:
            return LicenseInfo(raw, LicenseClass.PERMISSIVE, "CC BY-SA", True, True,
                               "Attribution-ShareAlike; reuse and TDM permitted.")
        return LicenseInfo(raw, LicenseClass.PERMISSIVE, "CC BY", True, True,
                           "Attribution; reuse and TDM permitted.")

    if "subscription" in s or "all rights reserved" in str(raw).lower() or s in ("s",):
        return LicenseInfo(raw, LicenseClass.RESTRICTED, None, False, False,
                           "Subscription / all rights reserved; not downloadable for reuse.")

    return LicenseInfo(raw, LicenseClass.UNKNOWN, None, False, False,
                       f"Unrecognized license '{raw}'; treated as unknown (not downloaded).")


def is_permissive(raw: Optional[str]) -> bool:
    return classify_license(raw).klass in PERMISSIVE_CLASSES
