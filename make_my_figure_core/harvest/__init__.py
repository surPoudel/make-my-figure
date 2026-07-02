"""License-aware open-access paper / figure harvesting pipeline (Milestone 3).

HTTPS-only. Sources used (all public, machine-access-friendly):

* Europe PMC REST  — search + metadata + license + supplementary files
* NCBI PMC OA service (oa.fcgi) — independent license confirmation
* NCBI BioC (pmcoa.cgi) — full text + figure captions + image filenames
* NCBI PMC article page — resolves real CDN figure-image URLs

Only files whose license clearly permits reuse + text/data mining
(CC BY, CC BY-SA, CC0) are downloaded. Everything else is recorded as
license-blocked. Nothing is fabricated: missing pieces are stored as null /
"unavailable", and figure<->source-data links are marked "uncertain".
"""

from make_my_figure_core.harvest.licensing import (
    classify_license,
    LicenseClass,
    is_permissive,
)
from make_my_figure_core.harvest.pipeline import harvest_library, HarvestConfig

__all__ = [
    "classify_license",
    "LicenseClass",
    "is_permissive",
    "harvest_library",
    "HarvestConfig",
]
