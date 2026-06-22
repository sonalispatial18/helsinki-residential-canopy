#!/usr/bin/env bash
# 02b_redownload_canopy_paginated.sh
# ---------------------------------------------------------------------------
# Re-downloads Helsinki mature-canopy layers in pages to avoid the WFS
# server's 100,000-feature limit.
#
# Mature canopy definition:
#   vegetation >= 10 m:
#   - 10–15 m
#   - 15–20 m
#   - >20 m
# ---------------------------------------------------------------------------

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RAW_DIR="$PROJECT_DIR/data/raw"
INTERIM_DIR="$PROJECT_DIR/data/interim"

mkdir -p "$RAW_DIR" "$INTERIM_DIR"

HSY_WFS="https://kartta.hsy.fi/geoserver/wfs"

# Official Helsinki osa-alue extent, EPSG:3879
HELSINKI_BBOX="25487917.144,6645439.071,25514074.175,6687278.623,EPSG:3879"

CANOPY_OUT="$INTERIM_DIR/helsinki_mature_canopy_2024.gpkg"

# 50,000 is safely below the apparent WFS maximum.
PAGE_SIZE=50000

LAYER_NAMES=(
    "canopy_10_15m_2024"
    "canopy_15_20m_2024"
    "canopy_over_20m_2024"
)

WFS_LAYERS=(
    "asuminen_ja_maankaytto:maanpeite_puusto_10_15m_2024"
    "asuminen_ja_maankaytto:maanpeite_puusto_15_20m_2024"
    "asuminen_ja_maankaytto:maanpeite_puusto_yli20m_2024"
)

echo ""
echo "================================================================"
echo "Re-downloading 2024 mature canopy with pagination"
echo "================================================================"

rm -f "$CANOPY_OUT"

for i in "${!LAYER_NAMES[@]}"; do

    OUTPUT_LAYER="${LAYER_NAMES[$i]}"
    WFS_LAYER="${WFS_LAYERS[$i]}"

    echo ""
    echo "🌳 Processing: $OUTPUT_LAYER"
    echo "   Source: $WFS_LAYER"

    START_INDEX=0
    PAGE_NUMBER=1
    FIRST_PAGE=true
    TOTAL_FEATURES=0

    while true; do

        PAGE_FILE="$RAW_DIR/${OUTPUT_LAYER}_page_${PAGE_NUMBER}.geojson"

        echo "   ⬇️  Downloading page $PAGE_NUMBER, startIndex=$START_INDEX ..."

        curl -G --fail --silent --show-error \
            --data-urlencode "service=WFS" \
            --data-urlencode "version=2.0.0" \
            --data-urlencode "request=GetFeature" \
            --data-urlencode "typeNames=$WFS_LAYER" \
            --data-urlencode "outputFormat=application/json" \
            --data-urlencode "srsName=EPSG:3879" \
            --data-urlencode "bbox=$HELSINKI_BBOX" \
            --data-urlencode "count=$PAGE_SIZE" \
            --data-urlencode "startIndex=$START_INDEX" \
            "$HSY_WFS" \
            -o "$PAGE_FILE"

        if ! grep -q '"features"' "$PAGE_FILE"; then
            echo "❌ Invalid GeoJSON response:"
            head -c 500 "$PAGE_FILE"
            exit 1
        fi

        PAGE_FEATURES=$(grep -o '"type":"Feature"' "$PAGE_FILE" | wc -l | tr -d ' ')

        echo "      Retrieved $PAGE_FEATURES features"

        if [ "$PAGE_FEATURES" -eq 0 ]; then
            rm -f "$PAGE_FILE"
            break
        fi

        if [ "$FIRST_PAGE" = true ]; then
            ogr2ogr \
                -f "GPKG" \
                "$CANOPY_OUT" \
                "$PAGE_FILE" \
                -nln "$OUTPUT_LAYER" \
                -nlt PROMOTE_TO_MULTI

            FIRST_PAGE=false
        else
            ogr2ogr \
                -f "GPKG" \
                -update \
                -append \
                "$CANOPY_OUT" \
                "$PAGE_FILE" \
                -nln "$OUTPUT_LAYER" \
                -nlt PROMOTE_TO_MULTI
        fi

        TOTAL_FEATURES=$((TOTAL_FEATURES + PAGE_FEATURES))

        # A partial page means we reached the end.
        if [ "$PAGE_FEATURES" -lt "$PAGE_SIZE" ]; then
            break
        fi

        START_INDEX=$((START_INDEX + PAGE_SIZE))
        PAGE_NUMBER=$((PAGE_NUMBER + 1))
    done

    echo "   ✅ Added $TOTAL_FEATURES features to $OUTPUT_LAYER"
done

echo ""
echo "================================================================"
echo "Verification"
echo "================================================================"

for LAYER in "${LAYER_NAMES[@]}"; do
    echo ""
    echo "$LAYER:"
    ogrinfo -so "$CANOPY_OUT" "$LAYER" | grep -E "Layer name|Feature Count"
done

echo ""
echo "✅ Complete canopy GeoPackage:"
echo "   $CANOPY_OUT"