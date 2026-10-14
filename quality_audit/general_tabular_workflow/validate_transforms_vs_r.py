"""Write transformation_validation.csv: the table-transformation engine vs base R.

Reference: tests/fixtures/r_transform_reference.csv (r_validation/transforms.R,
17 significant digits). For every value R returns a finite result, ours must agree to
1e-14 relative. Where R returns -Inf / NaN / NA, ours must refuse by default and,
when told to record invalid values as missing, give a missing value - never a
plausible-looking number.
"""
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from make_my_figure_core.tabular import TableTransform, preview_transform  # noqa: E402

REF = os.path.join(ROOT, "tests", "fixtures", "r_transform_reference.csv")
OUT = os.path.join(os.path.dirname(__file__), "transformation_validation.csv")
REL = 1e-14


def main():
    # round_trip: pandas' default fast float parser does not reproduce 17-digit
    # values exactly (it turned R's 0.0014419741739063218 into ...063000).
    ref = pd.read_csv(REF, na_values=["NA"], float_precision="round_trip")
    rows = []
    for (method, offset), grp in ref.groupby(["method", "offset"], sort=False):
        df = pd.DataFrame({"x": grp["x"].to_numpy(float)})
        if method == "zscore_extreme":
            pv = preview_transform(df, TableTransform("x", "zscore"))
            r_vals = grp["r_value"].to_numpy(float)
            rows.append({"method": "zscore", "offset": 0, "x": "1e-300 .. 1e300", "case": "SD overflow",
                         "r_value": f"R returns {int(np.sum(r_vals == 0))} zeros (SD = Inf)",
                         "ours": "refused: " + " ".join(pv.problems)[:120], "rel_diff": "",
                         "pass": (not pv.can_apply) and bool(np.all(r_vals == 0))})
            continue
        strict = preview_transform(df, TableTransform("x", method, float(offset), "refuse"))
        lenient = preview_transform(df, TableTransform("x", method, float(offset), "missing"))
        r_vals = grp["r_value"].to_numpy(float)
        r_invalid = int(np.sum(~np.isfinite(r_vals) & np.isfinite(df["x"].to_numpy(float))))
        for x, rv, ov in zip(df["x"], r_vals, lenient.transformed):
            ours = float("nan") if ov is None else float(ov)
            if not np.isfinite(x):
                kind, ok = "missing input", ov is None
            elif np.isfinite(rv):
                kind = "valid"
                ok = ov is not None and (abs(ours - rv) <= REL * abs(rv) if rv != 0 else ours == 0.0)
            else:
                kind, ok = "undefined (R: -Inf/NaN)", ov is None
            rows.append({"method": method, "offset": offset, "x": repr(float(x)), "r_value": repr(float(rv)),
                         "ours": repr(ours), "case": kind,
                         "rel_diff": (abs(ours - rv) / abs(rv) if kind == "valid" and rv else (
                             abs(ours - rv) if kind == "valid" else "")),
                         "pass": ok})
        rows.append({"method": method, "offset": offset, "x": "(all)", "r_value": f"{r_invalid} undefined in R",
                     "ours": f"refused={not strict.can_apply}; n_invalid={strict.n_invalid}", "case": "invalid policy",
                     "rel_diff": "", "pass": (strict.n_invalid == r_invalid) and (strict.can_apply == (r_invalid == 0))})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    rel = pd.to_numeric(out["rel_diff"], errors="coerce")
    print(f"{int(out['pass'].sum())}/{len(out)} pass; worst relative difference {rel.max():.3g}; wrote {OUT}")


if __name__ == "__main__":
    main()
