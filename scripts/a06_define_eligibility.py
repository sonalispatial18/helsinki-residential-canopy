from pathlib import Path

import geopandas as gpd


PROJECT_DIR = Path(__file__).resolve().parent.parent

INTERIM_DIR = PROJECT_DIR / "data" / "interim"
DERIVED_DIR = PROJECT_DIR / "data" / "derived"

INPUT_GPKG = (
    INTERIM_DIR
    / "helsinki_osa_alue_income_residential_canopy_2024.gpkg"
)

INPUT_LAYER = "osa_alue_income_residential_canopy_2024"

ALL_AREAS_OUTPUT = (
    DERIVED_DIR
    / "helsinki_osa_alue_residential_eligibility_2024.gpkg"
)

ELIGIBLE_OUTPUT = (
    DERIVED_DIR
    / "helsinki_eligible_osa_alue_income_canopy_2024.gpkg"
)

ELIGIBLE_CSV = (
    DERIVED_DIR
    / "helsinki_eligible_osa_alue_income_canopy_2024.csv"
)

# Include only areas with at least 5 hectares of mapped
# detached-house + block-of-flats property land.
MIN_RESIDENTIAL_AREA_M2 = 50_000


print("\n==============================================================")
print("Defining eligible Helsinki residential analysis areas")
print("==============================================================")

print("\n1. Reading residential canopy dataset...")

areas = gpd.read_file(INPUT_GPKG, layer=INPUT_LAYER)

print(f"   Osa-alueet loaded: {len(areas)}")

print("\n2. Applying inclusion criteria...")

areas["residential_property_ha"] = (
    areas["residential_property_m2"] / 10_000
)

areas["has_income"] = (
    areas["median_equiv_income_eur"].notna()
)

areas["has_sufficient_residential_land"] = (
    areas["residential_property_m2"] >= MIN_RESIDENTIAL_AREA_M2
)

areas["eligible_for_analysis"] = (
    areas["has_income"]
    & areas["has_sufficient_residential_land"]
)

areas["exclusion_reason"] = "Included"

areas.loc[
    ~areas["has_income"]
    & ~areas["has_sufficient_residential_land"],
    "exclusion_reason",
] = "Missing income and insufficient residential land"

areas.loc[
    ~areas["has_income"]
    & areas["has_sufficient_residential_land"],
    "exclusion_reason",
] = "Missing income"

areas.loc[
    areas["has_income"]
    & ~areas["has_sufficient_residential_land"],
    "exclusion_reason",
] = "Insufficient residential land"

eligible = areas[
    areas["eligible_for_analysis"]
].copy()

print(f"   Minimum residential-property area: {MIN_RESIDENTIAL_AREA_M2:,} m²")
print(f"   Eligible osa-alueet: {len(eligible)}")
print(f"   Excluded osa-alueet: {len(areas) - len(eligible)}")

print("\n3. Exclusion summary...")

print(
    areas["exclusion_reason"]
    .value_counts()
    .to_string()
)

print("\n4. Saving outputs...")

for output_file in [ALL_AREAS_OUTPUT, ELIGIBLE_OUTPUT]:
    if output_file.exists():
        output_file.unlink()

areas.to_file(
    ALL_AREAS_OUTPUT,
    layer="osa_alue_residential_eligibility_2024",
    driver="GPKG",
)

eligible.to_file(
    ELIGIBLE_OUTPUT,
    layer="eligible_osa_alue_income_canopy_2024",
    driver="GPKG",
)

eligible.drop(columns="geometry").to_csv(
    ELIGIBLE_CSV,
    index=False,
    encoding="utf-8-sig",
)

print(f"   All areas + eligibility: {ALL_AREAS_OUTPUT}")
print(f"   Eligible analytical sample: {ELIGIBLE_OUTPUT}")
print(f"   Eligible CSV: {ELIGIBLE_CSV}")

print("\n==============================================================")
print("Step 3 complete")
print("==============================================================")

print("\nEligible-area summary:")

print(
    eligible[
        [
            "NIMI_FI",
            "median_equiv_income_eur",
            "residential_property_ha",
            "residential_mature_canopy_share_pct",
        ]
    ]
    .describe()
    .round(2)
)