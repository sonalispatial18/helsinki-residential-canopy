#!/usr/bin/env bash
# 01_discover_sources.sh
# ---------------------------------------------------------------------------
# Helsinki Urban Nature Inequality
#
# Step 1: Download / inspect the official sources needed for:
#   - Helsinki osa-alue boundaries
#   - 2024 HSY canopy / land-cover layers
#   - Helsinki household-income statistics
#
# This script deliberately DOES NOT run the analysis yet.
# It first discovers the exact available WFS layer names and PxWeb variable
# codes, so the processing script can be robust and reproducible.
#
# Prerequisites:
#   - curl
#   - unzip
#   - GDAL / ogrinfo
#   - Python 3
#
# Run:
#   bash scripts/01_discover_sources.sh
# ---------------------------------------------------------------------------

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

RAW_DIR="$PROJECT_DIR/data/raw"
INTERIM_DIR="$PROJECT_DIR/data/interim"
DERIVED_DIR="$PROJECT_DIR/data/derived"
OUTPUT_DIR="$PROJECT_DIR/outputs"

mkdir -p "$RAW_DIR" "$INTERIM_DIR" "$DERIVED_DIR" "$OUTPUT_DIR/maps" "$OUTPUT_DIR/figures"

# ---------------------------------------------------------------------------
# Check basic dependencies
# ---------------------------------------------------------------------------

for CMD in curl unzip ogrinfo python3; do
    if ! command -v "$CMD" >/dev/null 2>&1; then
        echo "❌ Missing command: $CMD"
        echo "   Install it before continuing."
        exit 1
    fi
done

echo "✅ Required commands found."
echo "📁 Project directory: $PROJECT_DIR"

# ---------------------------------------------------------------------------
# Source URLs
# ---------------------------------------------------------------------------

# Official Helsinki district-boundaries package
BOUNDARY_URL="https://kartta.hel.fi/avoindata/Helsingin-piirijakorajat-eri-vuosilta-gpkg.zip"
BOUNDARY_ZIP="$RAW_DIR/helsinki_district_boundaries.gpkg.zip"
BOUNDARY_DIR="$RAW_DIR/helsinki_district_boundaries"

# HSY regional land-cover WFS
HSY_WFS="https://kartta.hsy.fi/geoserver/wfs"
CAPABILITIES_FILE="$RAW_DIR/hsy_landcover_wfs_capabilities.xml"
HSY_LAYER_LIST="$RAW_DIR/hsy_landcover_wfs_layers.txt"

# Helsinki regional statistics PxWeb API:
# income by area, household life stage, year, and indicator
INCOME_API="https://stat.hel.fi/api/v1/fi/Aluesarjat/alu_astul_006f.px"
INCOME_METADATA="$RAW_DIR/helsinki_income_metadata.json"

# ---------------------------------------------------------------------------
# 1. Download Helsinki district boundaries
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "1. Helsinki district boundaries"
echo "================================================================"

if [ -f "$BOUNDARY_ZIP" ]; then
    echo "⏭️  Already downloaded: $(basename "$BOUNDARY_ZIP")"
else
    echo "⬇️  Downloading Helsinki boundary GeoPackage package..."
    curl -L --fail --progress-bar \
        -o "$BOUNDARY_ZIP" \
        "$BOUNDARY_URL"
fi

mkdir -p "$BOUNDARY_DIR"

echo "📦 Extracting boundary files..."
unzip -oq "$BOUNDARY_ZIP" -d "$BOUNDARY_DIR"

echo ""
echo "🗺️  GeoPackages found:"
find "$BOUNDARY_DIR" -type f -iname "*.gpkg" -print

echo ""
echo "🔍 Available layers:"
find "$BOUNDARY_DIR" -type f -iname "*.gpkg" -print0 |
while IFS= read -r -d '' GPKG; do
    echo ""
    echo "----- $(basename "$GPKG") -----"
    ogrinfo -ro -q "$GPKG" | sed -n '1,40p'
done | tee "$RAW_DIR/helsinki_boundary_layers.txt"

echo ""
echo "📌 Likely osa-alue layers:"
grep -Ei "osa|alue" "$RAW_DIR/helsinki_boundary_layers.txt" || true

# ---------------------------------------------------------------------------
# 2. Download HSY WFS capabilities and list candidate canopy layers
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "2. HSY 2024 land-cover / canopy WFS"
echo "================================================================"

echo "⬇️  Downloading WFS capabilities..."

curl -G --fail --silent --show-error \
    --data-urlencode "service=WFS" \
    --data-urlencode "request=GetCapabilities" \
    --data-urlencode "version=2.0.0" \
    "$HSY_WFS" \
    -o "$CAPABILITIES_FILE"

FILE_SIZE=$(wc -c < "$CAPABILITIES_FILE" | tr -d ' ')
if [ "$FILE_SIZE" -lt 1000 ]; then
    echo "❌ WFS capabilities file looks too small ($FILE_SIZE bytes)."
    exit 1
fi

echo "✅ Saved WFS capabilities: $(basename "$CAPABILITIES_FILE")"

# Extract layer names from WFS XML.
grep -oE '<(wfs:)?Name>[^<]+' "$CAPABILITIES_FILE" \
    | sed -E 's/<(wfs:)?Name>//' \
    | sort -u \
    > "$HSY_LAYER_LIST"

echo ""
echo "🌳 Candidate layers containing land-cover / vegetation / canopy terms:"
grep -Ei "maanpeite|landcover|puusto|latvus|canopy|viher|vegetation|green" \
    "$HSY_LAYER_LIST" \
    | tee "$RAW_DIR/hsy_candidate_canopy_layers.txt" || true

echo ""
echo "📄 Full layer list saved to:"
echo "   $HSY_LAYER_LIST"

# ---------------------------------------------------------------------------
# 3. Retrieve metadata for the Helsinki income table
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "3. Helsinki household-income statistics"
echo "================================================================"

echo "⬇️  Downloading PxWeb metadata..."

curl -L --fail --silent --show-error \
    -o "$INCOME_METADATA" \
    "$INCOME_API"

echo "✅ Saved income-table metadata: $(basename "$INCOME_METADATA")"

echo ""
echo "📊 Variables and example values:"
# Convert Git Bash path (/e/...) into a Windows path (E:\...)
INCOME_METADATA_WIN=$(cygpath -w "$INCOME_METADATA")

powershell.exe -NoProfile -Command "
\$metadata = Get-Content -Raw '$INCOME_METADATA_WIN' | ConvertFrom-Json

foreach (\$variable in \$metadata.variables) {
    Write-Host ''
    Write-Host ('Variable: ' + \$variable.text)
    Write-Host ('Code:     ' + \$variable.code)

    \$n = [Math]::Min(10, \$variable.values.Count)

    for (\$i = 0; \$i -lt \$n; \$i++) {
        Write-Host ('  ' + \$variable.values[\$i] + '  ->  ' + \$variable.valueTexts[\$i])
    }

    if (\$variable.values.Count -gt 10) {
        Write-Host ('  ... ' + \$variable.values.Count + ' values in total')
    }
}
"

echo ""
echo "================================================================"
echo "Step 1 complete"
echo "================================================================"
echo ""
echo "Please check these files:"
echo "  1. data/raw/helsinki_boundary_layers.txt"
echo "  2. data/raw/hsy_candidate_canopy_layers.txt"
echo "  3. data/raw/helsinki_income_metadata.json"
echo ""
echo "Next, we will select:"
echo "  - the official Helsinki osa-alue layer,"
echo "  - the 2024 uncut-canopy / tree-cover layer,"
echo "  - 'all households' + 2024 median equivalised disposable income."