"""Download license-verified raw data (skips gracefully offline)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import benchmark_lib as B
if __name__ == "__main__":
    for ds in B.DATASETS.values():
        r = ds.acquire(offline_ok=True)
        print(f"{ds.id}: {'cached '+str(len(r))+' rows' if r is not None else 'skipped (offline)'} [{ds.data_license}]")
