"""Write benchmark_summary_table.csv + report from the current manifest."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import json, pipeline as P
if __name__ == "__main__":
    man = json.load(open(os.path.join(P.BENCH_DIR, "manifest.json")))
    print("summary:", P.evaluate(man)); print("report:", P.write_report(man))
