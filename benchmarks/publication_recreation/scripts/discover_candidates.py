"""List the license-verified dataset candidates (provenance registry)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import benchmark_lib as B
if __name__ == "__main__":
    for ds in B.DATASETS.values():
        print(f"{ds.id:12s} {ds.data_license:20s} {ds.doi or ds.source_url}")
