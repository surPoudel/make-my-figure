"""Download the CC0 associated data for the one-publication pilot.

Publication: Gorman KB, Williams TD, Fraser WR (2014) PLoS ONE 9(3):e90081
(CC BY 4.0). Data: Palmer Station LTER penguin measurements, released CC0 via
the palmerpenguins project. We fetch the CC0 tidied release; the measurements
are Gorman et al. 2014 (this is NOT scraped from the paper PDF).

Offline-safe: skips any file already present. Writes SHA-256 checksums.
"""

from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw_data")

SOURCES = {
    # tidy analysis-ready table (CC0)
    "penguins.csv": "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv",
    # fuller raw table with study metadata (CC0)
    "penguins_raw.csv": "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins_raw.csv",
}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    os.makedirs(RAW, exist_ok=True)
    checksums = {}
    for name, url in SOURCES.items():
        dest = os.path.join(RAW, name)
        if os.path.exists(dest):
            print(f"[cached] {name}")
        else:
            try:
                import requests

                print(f"[download] {name} <- {url}")
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                with open(dest, "wb") as fh:
                    fh.write(r.content)
            except Exception as exc:  # offline / network blocked
                print(f"[skip] could not download {name}: {exc}")
                continue
        checksums[name] = {"sha256": _sha256(dest), "source_url": url,
                           "license": "CC0-1.0", "bytes": os.path.getsize(dest)}
    with open(os.path.join(RAW, "checksums.json"), "w", encoding="utf-8") as fh:
        json.dump(checksums, fh, indent=2)
    print(f"wrote {len(checksums)} checksum record(s) -> raw_data/checksums.json")


if __name__ == "__main__":
    main()
