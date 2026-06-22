#!/usr/bin/env bash
# 02c_rebuild_canopy_gpkg.sh
# ---------------------------------------------------------------------------
# Rebuilds the mature-canopy GeoPackage from already downloaded GeoJSON pages.
# No new WFS downloads are made.
# ---------------------------------------------------------------------------

set -euo pipefail
shopt -s nullglob

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RAW_DIR="$PROJECT_DIR/data/raw"
INTERIM_DIR="$PROJECT_DIR/data/interim"

CANOPY_OUT="$INTERIM_DIR/helsinki_mature_canopy_2024.gpkg"

LAYER_NAMES=(
    "canopy_10_15m_2024"
    "canopy_15_20m_2024"
    "canopy_over_20m_2024"
)

echo ""
echo "================================================================"
echo "Rebuilding mature-canopy GeoPackage from downloaded pages"
echo "================================================================"

rm -f "$CANOPY_OUT"

FIRST_LAYER=true

for LAYER in "${LAYER_NAMES[@]}"; do
    PAGES=( "$RAW_DIR"/"${LAYER}"_page_*.geojson )

    if [ "${#PAGES[@]}" -eq 0 ]; then
        echo "❌ No downloaded pages found for: $LAYER"
        exit 1
    fi

    # Sort page_1, page_2, page_10 correctly.
    mapfile -t SORTED_PAGES < <(printf '%s\n' "${PAGES[@]}" | sort -V)

    echo ""
    echo "🌳 Building layer: $LAYER"
    echo "   Pages found: ${#SORTED_PAGES[@]}"

    for PAGE_INDEX in "${!SORTED_PAGES[@]}"; do
        PAGE_FILE="${SORTED_PAGES[$PAGE_INDEX]}"
        PAGE_NAME="$(basename "$PAGE_FILE")"

        if [ "$FIRST_LAYER" = true ]; then
            # Create the GeoPackage with the first canopy layer.
            ogr2ogr \
                -f "GPKG" \
                "$CANOPY_OUT" \
                "$PAGE_FILE" \
                -nln "$LAYER" \
                -nlt PROMOTE_TO_MULTI

            FIRST_LAYER=false

        elif [ "$PAGE_INDEX" -eq 0 ]; then
            # Create a new layer inside the existing GeoPackage.
            ogr2ogr \
                -f "GPKG" \
                -update \
                "$CANOPY_OUT" \
                "$PAGE_FILE" \
                -nln "$LAYER" \
                -nlt PROMOTE_TO_MULTI

        else
            # Append later pages to the existing layer.
            ogr2ogr \
                -f "GPKG" \
                -update \
                -append \
                "$CANOPY_OUT" \
                "$PAGE_FILE" \
                -nln "$LAYER" \
                -nlt PROMOTE_TO_MULTI
        fi

        echo "   ✅ Added: $PAGE_NAME"
    done
done

echo ""
echo "================================================================"
echo "Verification"
echo "================================================================"

echo ""
echo "Layers in GeoPackage:"
ogrinfo -ro -q "$CANOPY_OUT"

for LAYER in "${LAYER_NAMES[@]}"; do
    echo ""
    echo "$LAYER:"
    ogrinfo -so "$CANOPY_OUT" "$LAYER" | grep -E "Layer name|Feature Count"
done

echo ""
echo "🎉 GeoPackage rebuilt successfully:"
echo "   $CANOPY_OUT"