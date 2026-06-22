from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent

DERIVED_DIR = PROJECT_DIR / "data" / "derived"
FIGURE_DIR = PROJECT_DIR / "outputs" / "figures"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)

INPUT_GPKG = (
    DERIVED_DIR
    / "helsinki_eligible_osa_alue_income_canopy_2024.gpkg"
)

INPUT_LAYER = "eligible_osa_alue_income_canopy_2024"

OUTPUT_GPKG = (
    DERIVED_DIR
    / "helsinki_eligible_osa_alue_analysis_2024.gpkg"
)

OUTPUT_CSV = (
    DERIVED_DIR
    / "helsinki_eligible_osa_alue_analysis_2024.csv"
)

SCATTER_OUTPUT = (
    FIGURE_DIR
    / "income_vs_residential_mature_canopy_2024.png"
)


print("\n==============================================================")
print("Analysing income and residential mature canopy")
print("==============================================================")

print("\n1. Reading eligible osa-alue dataset...")

areas = gpd.read_file(INPUT_GPKG, layer=INPUT_LAYER)

analysis = areas.dropna(
    subset=[
        "median_equiv_income_eur",
        "residential_mature_canopy_share_pct",
    ]
).copy()

print(f"   Eligible osa-alueet: {len(analysis)}")

print("\n2. Calculating income and canopy thresholds...")

income_threshold = analysis["median_equiv_income_eur"].quantile(1 / 3)
canopy_threshold = analysis[
    "residential_mature_canopy_share_pct"
].quantile(1 / 3)

areas["low_income"] = (
    areas["median_equiv_income_eur"] <= income_threshold
)

areas["low_residential_canopy"] = (
    areas["residential_mature_canopy_share_pct"] <= canopy_threshold
)

areas["screening_category"] = "Neither lower income nor lower canopy"

areas.loc[
    areas["low_income"] & ~areas["low_residential_canopy"],
    "screening_category",
] = "Lower income only"

areas.loc[
    ~areas["low_income"] & areas["low_residential_canopy"],
    "screening_category",
] = "Lower canopy only"

areas.loc[
    areas["low_income"] & areas["low_residential_canopy"],
    "screening_category",
] = "Lower income + lower canopy"

areas["income_tercile"] = pd.qcut(
    areas["median_equiv_income_eur"],
    q=3,
    labels=["Lower income", "Middle income", "Higher income"],
)

areas["canopy_tercile"] = pd.qcut(
    areas["residential_mature_canopy_share_pct"],
    q=3,
    labels=["Lower canopy", "Middle canopy", "Higher canopy"],
)

# Convert categories to ordinary text before saving to GeoPackage.
areas["income_tercile"] = areas["income_tercile"].astype(str)
areas["canopy_tercile"] = areas["canopy_tercile"].astype(str)

rho = analysis[
    [
        "median_equiv_income_eur",
        "residential_mature_canopy_share_pct",
    ]
].corr(method="spearman").iloc[0, 1]

overlap_areas = areas[
    areas["screening_category"]
    == "Lower income + lower canopy"
].copy()

print(f"   Lower-income threshold: €{income_threshold:,.0f}")
print(f"   Lower-canopy threshold: {canopy_threshold:.2f}%")
print(f"   Spearman correlation: {rho:.3f}")
print(f"   Lower income + lower canopy areas: {len(overlap_areas)}")

print("\n3. Saving QGIS-ready analytical dataset...")

if OUTPUT_GPKG.exists():
    OUTPUT_GPKG.unlink()

areas.to_file(
    OUTPUT_GPKG,
    layer="eligible_osa_alue_analysis_2024",
    driver="GPKG",
)

areas.drop(columns="geometry").to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig",
)

print(f"   GeoPackage: {OUTPUT_GPKG}")
print(f"   CSV: {OUTPUT_CSV}")

print("\n4. Creating scatterplot...")

fig, ax = plt.subplots(figsize=(8, 6))

ax.scatter(
    analysis["median_equiv_income_eur"],
    analysis["residential_mature_canopy_share_pct"],
    alpha=0.75,
)

x = analysis["median_equiv_income_eur"].to_numpy()
y = analysis["residential_mature_canopy_share_pct"].to_numpy()

slope, intercept = np.polyfit(x, y, 1)
x_line = np.linspace(x.min(), x.max(), 100)

ax.plot(
    x_line,
    slope * x_line + intercept,
)

ax.axvline(income_threshold, linestyle="--", linewidth=0.8)
ax.axhline(canopy_threshold, linestyle="--", linewidth=0.8)

ax.set_xlabel("Median equivalised disposable income (€), 2024")
ax.set_ylabel("Mature canopy within residential property land (%)")

ax.set_title(
    "Income and Mature Residential Tree Canopy in Helsinki"
)

ax.text(
    0.03,
    0.97,
    f"Spearman ρ = {rho:.2f}\nN = {len(analysis)}",
    transform=ax.transAxes,
    va="top",
)

fig.savefig(
    SCATTER_OUTPUT,
    dpi=300,
    bbox_inches="tight",
)

plt.close(fig)

print(f"   Scatterplot: {SCATTER_OUTPUT}")

print("\n==============================================================")
print("Step 4 complete")
print("==============================================================")

print("\nAreas with lower income and lower canopy:")

print(
    overlap_areas[
        [
            "NIMI_FI",
            "median_equiv_income_eur",
            "residential_property_ha",
            "residential_mature_canopy_share_pct",
        ]
    ]
    .sort_values("median_equiv_income_eur")
    .to_string(index=False)
)