"""Recreate each panel through Make My Figure (Publication style) with QC loop."""
import json
import os
import _lib

if __name__ == "__main__":
    if not os.path.exists(os.path.join(_lib.PROC, "panel_A_bill_dimensions.csv")):
        _lib.curate()
    cfgs = _lib.panel_configs()
    records = {}
    for pid, cfg in cfgs.items():
        rec = _lib.recreate_panel(pid, cfg)
        records[pid] = rec
        print(f"[panel {pid}] {cfg['plot_type']}: sci={rec['scientific_qc_pass']} "
              f"vis={rec['visual_qc_pass']} iters={len(rec['iterations'])} "
              f"exports={rec['exports_ok']}")
    with open(os.path.join(_lib.BASE, "qc", "_panel_records.json"), "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    npass = sum(1 for r in records.values() if r["scientific_qc_pass"] and r["visual_qc_pass"])
    print(f"PANELS PASSED (sci+vis): {npass}/{len(records)}")
