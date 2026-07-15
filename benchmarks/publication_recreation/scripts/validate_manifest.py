"""Validate manifest.json structure + license/provenance completeness."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import json
if __name__ == "__main__":
    import pipeline as P
    man = json.load(open(os.path.join(P.BENCH_DIR, "manifest.json")))
    req = ["benchmark_id","doi_or_url","data_license","license_verified","plot_type",
           "scientific_qc_pass","visual_qc_pass","plotspec_path","qc_path"]
    bad = [e["benchmark_id"] for e in man["benchmarks"] if any(k not in e for k in req)]
    npass = sum(1 for e in man["benchmarks"] if e["passed"])
    assert not bad, f"entries missing keys: {bad}"
    assert npass >= 10, f"only {npass} passing (<10)"
    print(f"manifest OK: {man['n_entries']} entries, {npass} passing")
