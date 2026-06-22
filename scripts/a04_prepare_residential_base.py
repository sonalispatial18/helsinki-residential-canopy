from pathlib import Path
import json
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

INTERIM_DIR = PROJECT_DIR / "data" / "interim"
PROPERTY_FILE = (
    PROJECT_DIR
    / "Residential_grids"
    / "Property_boundaries_HMA_edited_dis.shp"
)

BOUNDARY_FILE = INTERIM_DIR / "helsinki_osa_alueet_2024.gpkg"
BOUNDARY_LAYER = "osa_alueet_2024"

AREA_OUTPUT = INTERIM_DIR / "helsinki_osa_alue_income_residential_2024.gpkg"
MASK_OUTPUT = INTERIM_DIR / "helsinki_residential_mask_2024.gpkg"
INCOME_OUTPUT = INTERIM_DIR / "helsinki_income_osa_alue_2024.csv"

INCOME_API = "https://stat.hel.fi/api/v1/fi/Aluesarjat/alu_astul_006f.px"

RESIDENTIAL_TYPES = [
    "Detached houses",
    "Blocks of flats",
]


# ---------------------------------------------------------------------
# Income data
# ---------------------------------------------------------------------

def download_income_data() -> pd.DataFrame:
    """Download 2024 median equivalised disposable income by osa-alue."""

    query = {
        "query": [
            {
                "code": "Alue",
                "selection": {"filter": "all", "values": ["*"]},
            },
            {
                "code": "Elinvaihe",
                "selection": {"filter": "item", "values": ["ALL"]},
            },
            {
                "code": "Vuosi",
                "selection": {"filter": "item", "values": ["2024"]},
            },
            {
                "code": "Tiedot",
                "selection": {
                    "filter": "item",
                    "values": ["Median_ktukyk"],
                },
            },
        ],
        "response": {"format": "json-stat2"},
    }

    request = Request(
        INCOME_API,
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request) as response:
        dataset = json.load(response)

    category = dataset["dimension"]["Alue"]["category"]
    area_index = category["index"]
    area_labels = category["label"]
    values = dataset["value"]

    rows = []

    for area_code, position in area_index.items():
        rows.append(
            {
                "KOKOTUNNUS": str(area_code),
                "income_area_label": area_labels.get(area_code),
                "median_equiv_income_eur": values[position],
            }
        )

    income = pd.DataFrame(rows)

    income["median_equiv_income_eur"] = pd.to_numeric(
        income["median_equiv_income_eur"],
        errors="coerce",
    )

    return income


# ---------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------

print("\n==============================================================")
print("Preparing Helsinki income and residential-land base, 2024")
print("==============================================================")

print("\n1. Reading Helsinki osa-alue boundaries...")

areas = gpd.read_file(BOUNDARY_FILE, layer=BOUNDARY_LAYER)
areas["KOKOTUNNUS"] = areas["KOKOTUNNUS"].astype(str)

if areas.crs is None:
    raise RuntimeError("Boundary layer has no coordinate reference system.")

areas["osa_alue_area_m2"] = areas.geometry.area

print(f"   Osa-alueet: {len(areas)}")
print(f"   CRS: {areas.crs}")

print("\n2. Downloading income data...")

income = download_income_data()

income.to_csv(
    INCOME_OUTPUT,
    index=False,
    encoding="utf-8-sig",
)

areas = areas.merge(
    income[
        [
            "KOKOTUNNUS",
            "income_area_label",
            "median_equiv_income_eur",
        ]
    ],
    on="KOKOTUNNUS",
    how="left",
)

areas["income_available"] = (
    areas["median_equiv_income_eur"].notna()
)

print(
    "   Areas with matched income: "
    f"{areas['income_available'].sum()}/{len(areas)}"
)

print("\n3. Reading residential property polygons...")

properties = gpd.read_file(PROPERTY_FILE)

properties = properties[
    properties["Build_use"].isin(RESIDENTIAL_TYPES)
].copy()

properties = properties[
    properties.geometry.notna()
    & ~properties.geometry.is_empty
].copy()

properties = properties[
    properties.geometry.is_valid
].copy()

properties = properties.to_crs(areas.crs)

print(f"   Residential property fragments: {len(properties):,}")

print("\n4. Clipping residential properties to Helsinki osa-alueet...")

property_parts = gpd.overlay(
    properties[
        [
            "Build_use",
            "geometry",
        ]
    ],
    areas[
        [
            "KOKOTUNNUS",
            "geometry",
        ]
    ],
    how="intersection",
    keep_geom_type=True,
)

property_parts = property_parts[
    property_parts.geometry.notna()
    & ~property_parts.geometry.is_empty
].copy()

print(f"   Intersected property fragments: {len(property_parts):,}")

print("\n5. Creating a unioned residential-land mask per osa-alue...")

# Dissolve removes duplicated or overlapping property fragments.
# Both housing types are combined because this is the main denominator.
residential_mask = property_parts[
    [
        "KOKOTUNNUS",
        "geometry",
    ]
].dissolve(
    by="KOKOTUNNUS",
    as_index=False,
)

residential_mask["residential_property_m2"] = (
    residential_mask.geometry.area
)

print(f"   Osa-alueet with residential land: {len(residential_mask)}")

areas = areas.merge(
    residential_mask[
        [
            "KOKOTUNNUS",
            "residential_property_m2",
        ]
    ],
    on="KOKOTUNNUS",
    how="left",
)

areas["residential_property_m2"] = (
    areas["residential_property_m2"]
    .fillna(0)
)

areas["residential_land_available"] = (
    areas["residential_property_m2"] > 0
)

areas["residential_share_of_osa_pct"] = (
    areas["residential_property_m2"]
    / areas["osa_alue_area_m2"]
    * 100
)

print(
    "   Areas with both income and residential land: "
    f"{(areas['income_available'] & areas['residential_land_available']).sum()}"
)

print("\n6. Saving clean intermediate datasets...")

if AREA_OUTPUT.exists():
    AREA_OUTPUT.unlink()

if MASK_OUTPUT.exists():
    MASK_OUTPUT.unlink()

areas.to_file(
    AREA_OUTPUT,
    layer="osa_alue_income_residential_2024",
    driver="GPKG",
)

residential_mask.to_file(
    MASK_OUTPUT,
    layer="residential_mask_2024",
    driver="GPKG",
)

print(f"   Area-level base: {AREA_OUTPUT}")
print(f"   Residential mask: {MASK_OUTPUT}")
print(f"   Income table: {INCOME_OUTPUT}")

print("\n==============================================================")
print("Step 1 complete")
print("==============================================================")