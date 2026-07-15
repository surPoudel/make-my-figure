"""Curate raw -> processed CSVs (deterministic; writes provenance.json)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pipeline as P
if __name__ == "__main__":
    for b in P.BENCHMARKS:
        c = P.curate(b, offline_ok=True)
        print(f"{b.id}: {'curated' if c else 'skipped (offline)'}")
