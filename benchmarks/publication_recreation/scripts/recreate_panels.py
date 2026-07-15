"""Recreate every panel through Make My Figure + run scientific/visual QC."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pipeline as P
if __name__ == "__main__":
    out = P.run_full(offline_ok="--require-net" not in sys.argv)
    print(f"PASSED {out['n_passed']}/{out['n_entries']}")
