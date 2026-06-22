from pathlib import Path

import geopandas as gpd
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent
INTERIM_DIR = PROJECT_DIR / "data" / "interim"

AREA_BASE_FILE = INTERIM_DIR / "helsinki_osa_alue_income_residential_2024.gpkg"
AREA_BASE_LAYER = "osa_alue_income_residential_2024"

RESIDENTIAL_MASK_FILE = INTERIM_DIR / "helsinki_residential_mask_2024.gpkg"
RESIDENTIAL_MASK_LAYER = "residential_mask_2024"

CANOPY_FILE = INTERIM_DIR / "helsinki_mature_canopy_2024.gpkg"

CANOPY_LAYERS = {
    "canopy_10_15m_2024": "canopy_10_15m_m2",
    "canopy_15_20m_2024": "canopy_15_20m_m2",
    "canopy_over_20m_2024": "canopy_over_20m_m2",
}

OUTPUT_GPKG = INTERIM_DIR / "helsinki_osa_alue_income_residential_canopy_2024.gpkg"
OUTPUT_CSV = INTERIM_DIR / "helsinki_osa_alue_income_residential_canopy_2024.csv"


# ---------------------------------------------------------------------
# Canopy calculation
# ---------------------------------------------------------------------

def calculate_canopy_within_residential_mask(
    canopy_layer: str,
    output_column: str,
    residential_mask: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Calculate canopy area from one height layer inside the unioned
    detached-house + block-of-flats residential mask of each osa-alue.
    """

    print(f"\n   Reading canopy layer: {canopy_layer}")

    canopy = gpd.read_file(CANOPY_FILE, layer=canopy_layer)

    canopy = canopy[
        canopy.geometry.notna()
        & ~canopy.geometry.is_empty
    ].copy()

    if canopy.crs != residential_mask.crs:
        canopy = canopy.to_crs(residential_mask.crs)

    print(f"   Canopy polygons: {len(canopy):,}")

    candidates = gpd.sjoin(
        canopy[["geometry"]],
        residential_mask[["KOKOTUNNUS", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    print(f"   Candidate intersections: {len(candidates):,}")

    target_geometries = gpd.GeoSeries(
        residential_mask.geometry.loc[
            candidates["index_right"]
        ].to_numpy(),
        index=candidates.index,
        crs=residential_mask.crs,
    )

    candidates[output_column] = (
        candidates.geometry
        .intersection(target_geometries)
        .area
    )

    return (
        candidates.groupby("KOKOTUNNUS", as_index=False)[output_column]
        .sum()
    )


# ---------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------

print("\n==============================================================")
print("Calculating mature canopy within residential land")
print("==============================================================")

print("\n1. Reading area-level residential base...")

areas = gpd.read_file(
    AREA_BASE_FILE,
    layer=AREA_BASE_LAYER,
)

areas["KOKOTUNNUS"] = areas["KOKOTUNNUS"].astype(str)

print(f"   Osa-alueet: {len(areas)}")

print("\n2. Reading unioned residential-land mask...")

residential_mask = gpd.read_file(
    RESIDENTIAL_MASK_FILE,
    layer=RESIDENTIAL_MASK_LAYER,
)

residential_mask["KOKOTUNNUS"] = (
    residential_mask["KOKOTUNNUS"].astype(str)
)

residential_mask = residential_mask.reset_index(drop=True)

print(f"   Osa-alueet with residential land: {len(residential_mask)}")

print("\n3. Intersecting mature canopy with residential land...")

for canopy_layer, output_column in CANOPY_LAYERS.items():

    canopy_summary = calculate_canopy_within_residential_mask(
        canopy_layer=canopy_layer,
        output_column=output_column,
        residential_mask=residential_mask,
    )

    areas = areas.merge(
        canopy_summary,
        on="KOKOTUNNUS",
        how="left",
    )

    areas[output_column] = areas[output_column].fillna(0)

canopy_columns = list(CANOPY_LAYERS.values())

areas["residential_mature_canopy_m2"] = (
    areas[canopy_columns].sum(axis=1)
)

areas["residential_mature_canopy_share_pct"] = pd.NA

has_residential_land = areas["residential_property_m2"] > 0

areas.loc[
    has_residential_land,
    "residential_mature_canopy_share_pct",
] = (
    areas.loc[
        has_residential_land,
        "residential_mature_canopy_m2",
    ]
    / areas.loc[
        has_residential_land,
        "residential_property_m2",
    ]
    * 100
)

areas["residential_mature_canopy_share_pct"] = pd.to_numeric(
    areas["residential_mature_canopy_share_pct"],
    errors="coerce",
)

print("\n4. Quality checks...")

over_100 = areas[
    areas["residential_mature_canopy_share_pct"] > 100.01
]

if len(over_100) > 0:
    print("   WARNING: canopy share above 100% in:")
    print(
        over_100[
            [
                "NIMI_FI",
                "residential_property_m2",
                "residential_mature_canopy_m2",
                "residential_mature_canopy_share_pct",
            ]
        ].to_string(index=False)
    )
else:
    print("   ✓ No canopy shares above 100%.")

print(
    "   Areas with residential canopy estimates: "
    f"{areas['residential_mature_canopy_share_pct'].notna().sum()}"
)

print("\n5. Saving outputs...")

if OUTPUT_GPKG.exists():
    OUTPUT_GPKG.unlink()

areas.to_file(
    OUTPUT_GPKG,
    layer="osa_alue_income_residential_canopy_2024",
    driver="GPKG",
)

areas.drop(columns="geometry").to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig",
)

print(f"   GeoPackage: {OUTPUT_GPKG}")
print(f"   CSV: {OUTPUT_CSV}")

print("\n==============================================================")
print("Step 2 complete")
print("==============================================================")

print(
    areas[
        [
            "NIMI_FI",
            "median_equiv_income_eur",
            "residential_property_m2",
            "residential_mature_canopy_m2",
            "residential_mature_canopy_share_pct",
        ]
    ]
    .sort_values("residential_mature_canopy_share_pct")
    .head(10)
    .to_string(index=False)
)