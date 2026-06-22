from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

DERIVED_DIR = PROJECT_DIR / "data" / "derived"
MAP_DIR = PROJECT_DIR / "outputs" / "maps"
FIGURE_DIR = PROJECT_DIR / "outputs" / "figures"

MAP_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

ELIGIBLE_GPKG = (
    DERIVED_DIR
    / "helsinki_eligible_osa_alue_analysis_2024.gpkg"
)

ELIGIBLE_LAYER = "eligible_osa_alue_analysis_2024"


# ---------------------------------------------------------------------
# Plot settings
# ---------------------------------------------------------------------

MAP_FIGSIZE = (14, 10)
MAP_WIDTH_RATIO = [4.8, 1.35]

MAP_EDGE_COLOUR = "white"
MAP_EDGE_WIDTH = 0.50

TITLE_FONT_SIZE = 19
LEGEND_FONT_SIZE = 11
LEGEND_TITLE_SIZE = 12


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def format_range(lower, upper, decimals=1, minimum=None):
    """Format numerical class ranges for legends."""

    if minimum is not None:
        lower = max(lower, minimum)

    if decimals == 0:
        return f"{lower:,.0f} – {upper:,.0f}"

    return f"{lower:.{decimals}f} – {upper:.{decimals}f}"


def set_map_extent(ax, data, padding_fraction=0.03):
    """Apply a small geographic padding around map data."""

    minx, miny, maxx, maxy = data.total_bounds

    x_padding = (maxx - minx) * padding_fraction
    y_padding = (maxy - miny) * padding_fraction

    ax.set_xlim(minx - x_padding, maxx + x_padding)
    ax.set_ylim(miny - y_padding, maxy + y_padding)


def create_quantile_map(
    data,
    value_column,
    colour_map,
    legend_title,
    map_title,
    output_file,
    decimals=1,
    n_classes=5,
    colour_start=0.18,
    colour_end=0.95,
    minimum_value=None,
):
    """
    Create a quantile choropleth map with a dedicated legend panel
    on the right side.
    """

    plot_data = data.copy()

    class_codes, bin_edges = pd.qcut(
        plot_data[value_column],
        q=n_classes,
        labels=False,
        retbins=True,
        duplicates="drop",
    )

    plot_data["class_code"] = class_codes.astype(int)

    class_count = len(bin_edges) - 1

    base_cmap = plt.get_cmap(colour_map)

    class_colours = base_cmap(
        np.linspace(
            colour_start,
            colour_end,
            class_count,
        )
    )

    plot_data["plot_colour"] = [
        class_colours[int(class_code)]
        for class_code in plot_data["class_code"]
    ]

    fig, (ax, legend_ax) = plt.subplots(
        ncols=2,
        figsize=MAP_FIGSIZE,
        gridspec_kw={
            "width_ratios": MAP_WIDTH_RATIO,
            "wspace": 0.03,
        },
    )

    plot_data.plot(
        ax=ax,
        color=plot_data["plot_colour"],
        edgecolor=MAP_EDGE_COLOUR,
        linewidth=MAP_EDGE_WIDTH,
    )

    set_map_extent(ax, plot_data)

    ax.set_axis_off()
    ax.set_aspect("equal")

    legend_handles = []

    for index in range(class_count):

        lower = bin_edges[index]
        upper = bin_edges[index + 1]

        label = format_range(
            lower=lower,
            upper=upper,
            decimals=decimals,
            minimum=minimum_value,
        )

        legend_handles.append(
            Patch(
                facecolor=class_colours[index],
                edgecolor="none",
                label=label,
            )
        )

    legend_ax.set_axis_off()

    legend = legend_ax.legend(
        handles=legend_handles,
        title=legend_title,
        loc="center left",
        frameon=False,
        fontsize=LEGEND_FONT_SIZE,
        title_fontsize=LEGEND_TITLE_SIZE,
        labelspacing=0.8,
        handlelength=1.8,
        handleheight=1.0,
    )

    legend.get_title().set_fontweight("bold")

    fig.suptitle(
        map_title,
        fontsize=TITLE_FONT_SIZE,
        fontweight="bold",
        y=0.96,
    )

    fig.subplots_adjust(
        top=0.86,
        bottom=0.06,
        left=0.03,
        right=0.98,
    )

    fig.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.12,
    )

    plt.close(fig)


# ---------------------------------------------------------------------
# Read and clean analytical dataset
# ---------------------------------------------------------------------

print("\n==============================================================")
print("Creating final Helsinki income and canopy maps")
print("==============================================================")

print("\n1. Reading eligible analytical dataset...")

eligible = gpd.read_file(
    ELIGIBLE_GPKG,
    layer=ELIGIBLE_LAYER,
)

eligible = eligible[
    eligible["NIMI_FI"].ne("Aluemeri")
].dropna(
    subset=[
        "median_equiv_income_eur",
        "residential_mature_canopy_share_pct",
        "screening_category",
    ]
).copy()

print(f"   Final mapped osa-alueet: {len(eligible)}")


# ---------------------------------------------------------------------
# Screening thresholds
# ---------------------------------------------------------------------

income_threshold = eligible[
    "median_equiv_income_eur"
].quantile(1 / 3)

canopy_threshold = eligible[
    "residential_mature_canopy_share_pct"
].quantile(1 / 3)


# ---------------------------------------------------------------------
# Map 1: Mature canopy within residential land
# ---------------------------------------------------------------------

print("\n2. Creating residential mature-canopy map...")

create_quantile_map(
    data=eligible,
    value_column="residential_mature_canopy_share_pct",
    colour_map="YlGn",
    legend_title=(
        "Mature canopy within\n"
        "residential land (%)"
    ),
    map_title=(
        "Mature Tree Canopy within Residential Land\n"
        "Helsinki Sub-Districts, 2024"
    ),
    output_file=(
        MAP_DIR
        / "01_residential_mature_canopy_2024.png"
    ),
    decimals=1,
    n_classes=5,
    colour_start=0.18,
    colour_end=0.95,
    minimum_value=0,
)


# ---------------------------------------------------------------------
# Map 2: Median income
# ---------------------------------------------------------------------

print("\n3. Creating median-income map...")

create_quantile_map(
    data=eligible,
    value_column="median_equiv_income_eur",
    colour_map="Blues",
    legend_title=(
        "Median equivalised\n"
        "disposable income (€)"
    ),
    map_title=(
        "Median Equivalised Disposable Income\n"
        "Helsinki Sub-Districts, 2024"
    ),
    output_file=(
        MAP_DIR
        / "02_median_income_2024.png"
    ),
    decimals=0,
    n_classes=5,
    colour_start=0.12,
    colour_end=0.95,
)


# ---------------------------------------------------------------------
# Map 3: Income and canopy screening map
# ---------------------------------------------------------------------

print("\n4. Creating screening map...")

category_order = [
    "Neither lower income nor lower canopy",
    "Lower income only",
    "Lower canopy only",
    "Lower income + lower canopy",
]

category_colours = {
    "Neither lower income nor lower canopy": "#D9D9D9",
    "Lower income only": "#F4A261",
    "Lower canopy only": "#74ADD1",
    "Lower income + lower canopy": "#D73027",
}

category_labels = {
    "Neither lower income nor lower canopy": (
        "Neither lower income\n"
        "nor lower canopy"
    ),
    "Lower income only": "Lower income only",
    "Lower canopy only": "Lower canopy only",
    "Lower income + lower canopy": (
        "Lower income +\n"
        "lower canopy"
    ),
}

screening = eligible.copy()

screening["screening_category"] = pd.Categorical(
    screening["screening_category"],
    categories=category_order,
    ordered=True,
)

screening["plot_colour"] = screening[
    "screening_category"
].map(category_colours)

fig, (ax, legend_ax) = plt.subplots(
    ncols=2,
    figsize=MAP_FIGSIZE,
    gridspec_kw={
        "width_ratios": MAP_WIDTH_RATIO,
        "wspace": 0.03,
    },
)

screening.plot(
    ax=ax,
    color=screening["plot_colour"],
    edgecolor=MAP_EDGE_COLOUR,
    linewidth=MAP_EDGE_WIDTH,
)

set_map_extent(ax, screening)

ax.set_axis_off()
ax.set_aspect("equal")

legend_handles = [
    Patch(
        facecolor=category_colours[category],
        edgecolor="none",
        label=category_labels[category],
    )
    for category in category_order
]

legend_ax.set_axis_off()

legend = legend_ax.legend(
    handles=legend_handles,
    title="Income–canopy screening",
    loc="upper left",
    frameon=False,
    fontsize=LEGEND_FONT_SIZE,
    title_fontsize=LEGEND_TITLE_SIZE,
    labelspacing=0.9,
    handlelength=1.8,
    handleheight=1.0,
)

legend.get_title().set_fontweight("bold")

legend_ax.text(
    0.03,
    0.36,
    (
        "Lower category threshold\n\n"
        f"Income ≤ €{income_threshold:,.0f}\n"
        f"Canopy ≤ {canopy_threshold:.1f}%"
    ),
    transform=legend_ax.transAxes,
    fontsize=10.5,
    va="top",
)

fig.suptitle(
    (
        "Lower Income and Lower Mature Canopy\n"
        "within Residential Land"
    ),
    fontsize=TITLE_FONT_SIZE,
    fontweight="bold",
    y=0.96,
)

fig.subplots_adjust(
    top=0.86,
    bottom=0.06,
    left=0.03,
    right=0.98,
)

fig.savefig(
    MAP_DIR / "03_income_canopy_screening_2024.png",
    dpi=300,
    bbox_inches="tight",
    pad_inches=0.12,
)

plt.close(fig)


# ---------------------------------------------------------------------
# Figure 4: Income–canopy scatterplot
# ---------------------------------------------------------------------

print("\n5. Creating scatterplot...")

rho = eligible[
    [
        "median_equiv_income_eur",
        "residential_mature_canopy_share_pct",
    ]
].corr(method="spearman").iloc[0, 1]

fig, ax = plt.subplots(figsize=(10.5, 6.8))

for category in category_order:

    category_data = eligible[
        eligible["screening_category"] == category
    ]

    ax.scatter(
        category_data["median_equiv_income_eur"],
        category_data["residential_mature_canopy_share_pct"],
        color=category_colours[category],
        label=category_labels[category],
        s=58,
        alpha=0.85,
        edgecolor="white",
        linewidth=0.55,
    )

x = eligible["median_equiv_income_eur"].to_numpy()
y = eligible["residential_mature_canopy_share_pct"].to_numpy()

slope, intercept = np.polyfit(x, y, 1)

x_line = np.linspace(
    x.min(),
    x.max(),
    150,
)

ax.plot(
    x_line,
    slope * x_line + intercept,
    color="#333333",
    linewidth=1.6,
)

ax.axvline(
    income_threshold,
    linestyle="--",
    linewidth=1.0,
    color="#555555",
)

ax.axhline(
    canopy_threshold,
    linestyle="--",
    linewidth=1.0,
    color="#555555",
)

ax.set_xlabel(
    "Median equivalised disposable income (€), 2024",
    fontsize=11,
)

ax.set_ylabel(
    "Mature canopy within residential land (%)",
    fontsize=11,
)

ax.set_title(
    "Income and Mature Residential Tree Canopy in Helsinki",
    fontsize=15,
    fontweight="bold",
    pad=12,
)

ax.grid(
    True,
    alpha=0.22,
    linewidth=0.6,
)

ax.set_axisbelow(True)

ax.text(
    0.03,
    0.97,
    (
        f"Spearman ρ = {rho:.2f}\n"
        f"N = {len(eligible)}"
    ),
    transform=ax.transAxes,
    va="top",
    fontsize=10.5,
    bbox={
        "facecolor": "white",
        "edgecolor": "#BDBDBD",
        "alpha": 0.90,
        "pad": 5,
    },
)

legend = ax.legend(
    title="Screening category",
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=False,
    fontsize=10,
    title_fontsize=11,
)

legend.get_title().set_fontweight("bold")

fig.subplots_adjust(
    right=0.74,
    left=0.11,
    bottom=0.12,
    top=0.88,
)

fig.savefig(
    FIGURE_DIR / "income_vs_residential_mature_canopy_2024.png",
    dpi=300,
    bbox_inches="tight",
    pad_inches=0.12,
)

plt.close(fig)


print("\n==============================================================")
print("Final maps created")
print("==============================================================")

print("\nOutputs:")
print(MAP_DIR / "01_residential_mature_canopy_2024.png")
print(MAP_DIR / "02_median_income_2024.png")
print(MAP_DIR / "03_income_canopy_screening_2024.png")
print(FIGURE_DIR / "income_vs_residential_mature_canopy_2024.png")