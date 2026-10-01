#!/usr/bin/env bash
# Fetch the Janesick et al. 2023 source data, verifying checksums.
#
# Nothing here downloads a whole archive. The Xenium bundle is 9.18 GB and the
# series tar is 31.78 GB; one member is pulled from the former with HTTP range
# requests (scripts/zip_member.py), and the Visium files are fetched per sample.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HERE/../raw}"
PY="${PYTHON:-python3}"
mkdir -p "$OUT"

GEO=https://ftp.ncbi.nlm.nih.gov/geo/samples
XEN_ZIP="$GEO/GSM7780nnn/GSM7780153/suppl/GSM7780153_Xenium_FFPE_Human_Breast_Cancer_Rep1_outs.zip"

if [ ! -f "$OUT/xenium_cells.csv.gz" ]; then
  echo "==> Xenium cell table (one member of a 9.18 GB archive)"
  "$PY" "$HERE/zip_member.py" "$XEN_ZIP" "outs/cells.csv.gz" "$OUT/xenium_cells.csv.gz"
fi
if [ ! -f "$OUT/xen_sup.csv.gz" ]; then
  echo "==> Xenium published cell-type annotations (Figures 1-5)"
  curl -fsSL -o "$OUT/xen_sup.csv.gz" \
    "$GEO/GSM7780nnn/GSM7780153/suppl/GSM7780153_Xenium_R1_Fig1-5_supervised.csv.gz"
fi
if [ ! -f "$OUT/GSM7782699_filtered_feature_bc_matrix.h5" ]; then
  echo "==> Visium filtered feature-barcode matrix"
  curl -fsSL -o "$OUT/GSM7782699_filtered_feature_bc_matrix.h5" \
    "$GEO/GSM7782nnn/GSM7782699/suppl/GSM7782699_filtered_feature_bc_matrix.h5"
fi
if [ ! -f "$OUT/tissue_positions.csv" ]; then
  echo "==> Visium spatial bundle"
  curl -fsSL -o "$OUT/spatial.tar.gz" \
    "$GEO/GSM7782nnn/GSM7782699/suppl/GSM7782699_spatial.tar.gz"
  tar xzf "$OUT/spatial.tar.gz" -C "$OUT" --strip-components=1 \
    spatial/tissue_positions.csv spatial/spatial_enrichment.csv spatial/scalefactors_json.json
  rm -f "$OUT/spatial.tar.gz"
fi

echo "==> verifying checksums"
cat <<SUMS | sha256sum -c -
8fc6f2b4c000c42ca97a1bb904a8d7608b33fa69ff86b1be0291016acbc2649c  $OUT/xenium_cells.csv.gz
1668413f78973816c8afee8003d073c9645d4f5eb9ec85f4e1bfc4cd62465c24  $OUT/xen_sup.csv.gz
6b00ec1f4abcafde2d2f140ea0456553dd47b8279c684a38eaa45adc09e72a4b  $OUT/GSM7782699_filtered_feature_bc_matrix.h5
fd8953276dad4f010ab1a876fb6eff78b7fca641e4ee1b268dd4d5e46fe33492  $OUT/tissue_positions.csv
44513fdbeda0187ed17a0e2a269f394170f2d5832e18c6e0fb0519064b0eb578  $OUT/spatial_enrichment.csv
SUMS
echo "OK"
