#!/usr/bin/env bash
# Fetch the CNTools S1 Data and the CRC source dataset, verifying checksums.
# The CRC file is 223 MB and is not committed to the repository.
set -euo pipefail
OUT="${1:-$(cd "$(dirname "$0")/.." && pwd)/raw}"
mkdir -p "$OUT"

S1="$OUT/cntools_S1_Data.xlsx"
S1_SHA=e35d3272762ac489fb47765e33212a295a4fcb61def51d0fc23bb091079ca343
CRC="$OUT/CRC_clusters_neighborhoods_markers.csv"
CRC_SHA=416cc3926a7a900ce3b22a33be699535ca35ae85fca4585a8ba5dad6d7f3c677

if [ ! -f "$S1" ]; then
  echo "==> S1 Data (PLOS, CC BY 4.0)"
  curl -fsSL -o "$S1" \
    "https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1012344.s001&type=supplementary"
fi
if [ ! -f "$CRC" ]; then
  echo "==> CRC dataset (Mendeley, 223 MB)"
  URL=$(curl -fsSL "https://data.mendeley.com/public-api/datasets/mpjzbtfgfr/files?folder_id=root&version=1" \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["content_details"]["download_url"])')
  curl -fsSL -o "$CRC" "$URL"
fi

echo "==> verifying checksums"
echo "$S1_SHA  $S1"   | sha256sum -c -
echo "$CRC_SHA  $CRC" | sha256sum -c -
echo "OK"
