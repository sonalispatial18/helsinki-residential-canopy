#!/usr/bin/env bash
# 02_download_2024_data.sh
# ---------------------------------------------------------------------------
# Helsinki Urban Nature Inequality
#
# Downloads and prepares 2024 inputs only:
#   1. Helsinki osa-alue boundaries
#   2. HSY mature tree-canopy layers (vegetation >= 10 m)
#   3. Helsinki 2024 median equivalised disposable household income
#
# Outputs:
#   data/interim/helsinki_osa_alueet_2024.gpkg
#   data/interim/helsinki_mature_canopy_2024.gpkg
#   data/raw/helsinki_income_2024.csv
#
# Run:
#   bash scripts/02_download_2024_data.sh
# ---------------------------------------------------------------------------

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

RAW_DIR="$PROJECT_DIR/data/raw"
INTERIM_DIR="$PROJECT_DIR/data/interim"

mkdir -p "$RAW_DIR" "$INTERIM_DIR"

# ---------------------------------------------------------------------------
# Input locations identified in Step 1
# ---------------------------------------------------------------------------

BOUNDARY_GPKG="$RAW_DIR/helsinki_district_boundaries/Helsingin-piirijakorajat-eri-vuosilta-gpkg/v2024.gpkg"
BOUNDARY_LAYER="Piirijako_osaalue"
BOUNDARIES_OUT="$INTERIM_DIR/helsinki_osa_alueet_2024.gpkg"

HSY_WFS="https://kartta.hsy.fi/geoserver/wfs"

# Helsinki city extent in EPSG:3879, based on official osa-alue boundaries.
HELSINKI_BBOX="25487917.144,6645439.071,25514074.175,6687278.623,EPSG:3879"

CANOPY_OUT="$INTERIM_DIR/helsinki_mature_canopy_2024.gpkg"

# Tree canopy is defined here as vegetation at least 10 metres high.
declare -A CANOPY_LAYERS
CANOPY_LAYERS["canopy_10_15m_2024"]="asuminen_ja_maankaytto:maanpeite_puusto_10_15m_2024"
CANOPY_LAYERS["canopy_15_20m_2024"]="asuminen_ja_maankaytto:maanpeite_puusto_15_20m_2024"
CANOPY_LAYERS["canopy_over_20m_2024"]="asuminen_ja_maankaytto:maanpeite_puusto_yli20m_2024"

INCOME_API="https://stat.hel.fi/api/v1/fi/Aluesarjat/alu_astul_006f.px"
INCOME_QUERY="$RAW_DIR/helsinki_income_2024_query.json"
INCOME_CSV="$RAW_DIR/helsinki_income_2024.csv"

# ---------------------------------------------------------------------------
# 1. Extract Helsinki osa-alue boundaries
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "1. Helsinki osa-alue boundaries, 2024"
echo "================================================================"

if [ ! -f "$BOUNDARY_GPKG" ]; then
    echo "❌ Boundary GeoPackage not found:"
    echo "   $BOUNDARY_GPKG"
    echo "   Run 01_discover_sources.sh first."
    exit 1
fi

rm -f "$BOUNDARIES_OUT"

ogr2ogr \
    -f "GPKG" \
    "$BOUNDARIES_OUT" \
    "$BOUNDARY_GPKG" \
    "$BOUNDARY_LAYER" \
    -nln "osa_alueet_2024" \
    -nlt PROMOTE_TO_MULTI \
    -a_srs EPSG:3879

echo "✅ Created: $BOUNDARIES_OUT"

# ---------------------------------------------------------------------------
# 2. Download mature canopy layers for Helsinki
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "2. HSY mature tree-canopy layers, 2024"
echo "================================================================"

rm -f "$CANOPY_OUT"

FIRST_LAYER=true

for OUTPUT_LAYER in "${!CANOPY_LAYERS[@]}"; do
    WFS_LAYER="${CANOPY_LAYERS[$OUTPUT_LAYER]}"
    GEOJSON_FILE="$RAW_DIR/${OUTPUT_LAYER}.geojson"

    echo ""
    echo "⬇️  Downloading: $WFS_LAYER"

    curl -G --fail --silent --show-error \
        --data-urlencode "service=WFS" \
        --data-urlencode "version=2.0.0" \
        --data-urlencode "request=GetFeature" \
        --data-urlencode "typeNames=$WFS_LAYER" \
        --data-urlencode "outputFormat=application/json" \
        --data-urlencode "srsName=EPSG:3879" \
        --data-urlencode "bbox=$HELSINKI_BBOX" \
        --data-urlencode "count=100000" \
        "$HSY_WFS" \
        -o "$GEOJSON_FILE"

    if ! grep -q '"features"' "$GEOJSON_FILE"; then
        echo "❌ Download does not appear to be valid GeoJSON:"
        echo "   $GEOJSON_FILE"
        head -c 500 "$GEOJSON_FILE"
        exit 1
    fi

    FEATURE_COUNT=$(grep -o '"type":"Feature"' "$GEOJSON_FILE" | wc -l | tr -d ' ')
    echo "   Retrieved approximately $FEATURE_COUNT features"

    if [ "$FIRST_LAYER" = true ]; then
        ogr2ogr \
            -f "GPKG" \
            "$CANOPY_OUT" \
            "$GEOJSON_FILE" \
            -nln "$OUTPUT_LAYER" \
            -nlt PROMOTE_TO_MULTI \
            -a_srs EPSG:3879

        FIRST_LAYER=false
    else
        ogr2ogr \
            -f "GPKG" \
            -update \
            "$CANOPY_OUT" \
            "$GEOJSON_FILE" \
            -nln "$OUTPUT_LAYER" \
            -nlt PROMOTE_TO_MULTI \
            -a_srs EPSG:3879
    fi

    echo "✅ Added layer: $OUTPUT_LAYER"
done

echo ""
echo "✅ Created canopy GeoPackage:"
echo "   $CANOPY_OUT"

# ---------------------------------------------------------------------------
# 3. Download 2024 equivalised disposable median income
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "3. Helsinki income data, 2024"
echo "================================================================"

cat > "$INCOME_QUERY" <<'JSON'
{
  "query": [
    {
      "code": "Alue",
      "selection": {
        "filter": "all",
        "values": ["*"]
      }
    },
    {
      "code": "Elinvaihe",
      "selection": {
        "filter": "item",
        "values": ["ALL"]
      }
    },
    {
      "code": "Vuosi",
      "selection": {
        "filter": "item",
        "values": ["2024"]
      }
    },
    {
      "code": "Tiedot",
      "selection": {
        "filter": "item",
        "values": ["Median_ktukyk"]
      }
    }
  ],
  "response": {
    "format": "csv"
  }
}
JSON

echo "⬇️  Downloading 2024 median equivalised disposable income..."

curl -L --fail --silent --show-error \
    -X POST \
    -H "Content-Type: application/json" \
    --data-binary "@$INCOME_QUERY" \
    "$INCOME_API" \
    -o "$INCOME_CSV"

if [ ! -s "$INCOME_CSV" ]; then
    echo "❌ Income CSV is empty."
    exit 1
fi

echo "✅ Created: $INCOME_CSV"
echo ""
echo "Preview:"
head -5 "$INCOME_CSV"

# ---------------------------------------------------------------------------
# 4. Verification
# ---------------------------------------------------------------------------

echo ""
echo "================================================================"
echo "Verification"
echo "================================================================"

echo ""
echo "Osa-alue boundaries:"
ogrinfo -so "$BOUNDARIES_OUT" "osa_alueet_2024" | grep -E "Feature Count|Layer name|KOKOTUNNUS|NIMI_FI"

echo ""
echo "Canopy layers:"
ogrinfo -ro -q "$CANOPY_OUT"

echo ""
echo "🎉 Step 2 complete."
echo ""
echo "Next step:"
echo "  Calculate mature canopy area and canopy percentage per osa-alue,"
echo "  then join the 2024 income data using KOKOTUNNUS = Alue."