# Helsinki Urban Nature Inequality

**Does a neighbourhood's median income predict access to mature tree canopy on residential land in Helsinki?**

This project measures how much **mature tree canopy** (vegetation ≥ 10 m) grows on **residential land** in each Helsinki sub-district (*osa-alue*), and tests whether that varies with the **sub-district's median household income**. The unit of analysis is the sub-district, so this is an *area-level* comparison — not a claim about individual households. It builds a fully reproducible pipeline from official open data, computes a canopy-share metric per sub-district, and screens for areas facing a "double disadvantage" — both lower income *and* lower residential canopy.

> **Headline result:** Across eligible sub-districts, the city-wide relationship between income and residential mature canopy is essentially flat (Spearman ρ ≈ 0.01, N = 109). Income alone does **not** explain residential tree cover in Helsinki. However, a tercile-based screening still isolates a small set of sub-districts that are *both* lower-income and lower-canopy — natural priority candidates for urban greening.

---
## Why this matters

Tree canopy provides shade, cooling, stormwater retention, and wellbeing benefits. If greener residential neighbourhoods cluster with higher incomes, that points to an *environmental equity* gap. This analysis deliberately restricts the canopy denominator to **residential property land** (detached houses + blocks of flats) rather than whole districts, so large parks and forests don't inflate the green credentials of a neighbourhood where people actually live.

---

## Key concepts

| Term | Definition used here |
|---|---|
| **Mature canopy** | HSY land-cover vegetation classes ≥ 10 m tall (10–15 m, 15–20 m, > 20 m) |
| **Residential land** | Dissolved property polygons classified as *Detached houses* or *Blocks of flats* |
| **Canopy share (%)** | Mature canopy area inside residential land ÷ residential land area × 100 |
| **Income** | Sub-district **median** of equivalised disposable household income, all households, 2024 |
| **Eligible area** | Sub-district with income data **and** ≥ 5 ha (50,000 m²) of mapped residential land |
| **Screening terciles** | "Lower" = bottom third of eligible areas for income / canopy respectively |

---

## Data sources

All inputs are official open data for the year **2024**, in **EPSG:3879** (ETRS-GK25FIN).

| Dataset | Source | Access |
|---|---|---|
| Sub-district (*osa-alue*) boundaries | City of Helsinki | `kartta.hel.fi` district-boundaries GeoPackage (`Piirijako_osaalue`, `v2024.gpkg`) |
| Tree-canopy land cover | Helsinki Region Environmental Services (HSY) | WFS `kartta.hsy.fi/geoserver/wfs`, layers `maanpeite_puusto_*` |
| Median household income (per sub-district) | Helsinki Region Statistics (Aluesarjat) | PxWeb API table `alu_astul_006f.px`, variable `Median_ktukyk` |
| Residential property boundaries | Provided locally (`Property_boundaries_HMA_edited_dis.shp`) | Not redistributed in this repo — see note below |

> **Note on the property layer:** the residential property boundaries are not downloaded by the scripts; place the shapefile under `Residential_grids/` before running the Python steps.

---

## Methodology

The pipeline moves from raw open data to final maps in eight steps:

1. **Discover sources** — inspect the WFS capabilities and PxWeb metadata to lock in exact layer names and variable codes (reproducibility first).
2. **Download 2024 data** — fetch boundaries, the three canopy height layers, and income.
3. **Paginated canopy download** — re-fetch canopy in 50,000-feature pages to stay under the WFS 100,000-feature cap, then rebuild a clean GeoPackage from the pages.
4. **Prepare residential base** — clip residential property polygons to each sub-district and dissolve them into a single residential-land mask; join 2024 income.
5. **Calculate residential canopy** — intersect each mature-canopy height layer with the residential mask and compute canopy share per sub-district.
6. **Define eligibility** — keep only sub-districts with income data and ≥ 5 ha of residential land; record exclusion reasons.
7. **Analyse** — compute income/canopy terciles, assign screening categories, and calculate the Spearman correlation.
8. **Create maps** — render the canopy choropleth, income choropleth, screening map, and the income–canopy scatterplot.

---

## Repository structure

```
.
├── scripts/
│   ├── a01_discover_sources.sh             # Inspect WFS + PxWeb metadata
│   ├── a02_download_2024_data.sh           # Download boundaries, canopy, income
│   ├── a02_1_redownload_canopy_paginated.sh# Paginated canopy download (recommended)
│   ├── a03_rebuild_canopy_gpkg.sh          # Rebuild canopy GPKG from pages
│   ├── a04_prepare_residential_base.py     # Residential mask + income join
│   ├── a05_calculate_residential_canopy.py # Canopy share per sub-district
│   ├── a06_define_eligibility.py           # Inclusion criteria
│   ├── a07_analyse_eligible_areas.py       # Terciles, screening, correlation
│   └── a08_create_final_maps.py            # Final maps + scatterplot
├── Residential_grids/                      # Place the property shapefile here
├── data/
│   ├── raw/                                # Downloaded inputs (git-ignored)
│   ├── interim/                            # Intermediate GeoPackages
│   └── derived/                            # Analysis-ready outputs
└── outputs/
    ├── maps/                               # Choropleths + screening map
    └── figures/                            # Scatterplot
```

---
> **Portability note:** `a01_discover_sources.sh` includes a Windows/Git Bash convenience step (`cygpath` + `powershell.exe`) only to pretty-print the income metadata. It is not required for the analysis itself; the downstream Python downloads income directly via the PxWeb API.

---
## How to run

Run from the project root, in order:

```bash
# 1. Inspect sources (optional but recommended)
bash scripts/a01_discover_sources.sh

# 2. Download 2024 boundaries + income (and a first canopy attempt)
bash scripts/a02_download_2024_data.sh

# 3. Robust canopy download (paginated) + rebuild
bash scripts/a02_1_redownload_canopy_paginated.sh
bash scripts/a03_rebuild_canopy_gpkg.sh

# 4–8. Analysis and maps
python scripts/a04_prepare_residential_base.py
python scripts/a05_calculate_residential_canopy.py
python scripts/a06_define_eligibility.py
python scripts/a07_analyse_eligible_areas.py
python scripts/a08_create_final_maps.py
```

Final maps and figures land in `outputs/maps/` and `outputs/figures/`.

---

## Outputs

| File | Description |
|---|---|
| `outputs/maps/01_residential_mature_canopy_2024.png` | Quantile choropleth of canopy share on residential land |
| `outputs/maps/02_median_income_2024.png` | Quantile choropleth of median income |
| `outputs/maps/03_income_canopy_screening_2024.png` | Four-category income–canopy screening map |
| `outputs/figures/income_vs_residential_mature_canopy_2024.png` | Scatterplot with trend line and Spearman ρ |
| `data/derived/helsinki_eligible_osa_alue_analysis_2024.gpkg` | QGIS-ready analytical dataset |
| `data/derived/*.csv` | Tabular versions of the derived data |

---


## Limitations and caveats

- **Cross-sectional, single year (2024).** No trend or causal claims — this is a descriptive snapshot.
- **Ecological inference.** Sub-district averages can mask within-district variation; an area-level correlation says nothing about individual households.
- **Definitional sensitivity.** Results depend on the ≥ 10 m canopy threshold, the residential-land definition, the 5 ha minimum, and tercile cut-points. These are reasonable but adjustable choices.
- **Boundary/source alignment.** Canopy, income, and property layers come from different providers; minor geometric mismatches are possible despite shared CRS.
- **Income coverage.** Sub-districts without published income (e.g. very small populations) are excluded, not zero.

---

## Future directions

- **Finer canopy from the city tree register.** Helsinki maintains a register of street and park trees. Combining HSY's polygon canopy with point-level tree data would sharpen estimates and capture younger, recently planted trees that have not yet reached the 10 m maturity threshold.
- **From canopy to heat exposure.** Adding land-surface temperature / urban-heat-island data would let the analysis target *shade where heat is actually worst*, connecting canopy to its cooling function rather than treating canopy share as the goal in itself.
- **Beyond income — multi-dimensional vulnerability.** Layering in age structure (young children, residents 75+), population density, or health indicators would prioritise greening where heat vulnerability is highest, not only where income is lower.
- **Temporal change.** HSY publishes land cover for several years. Comparing residential canopy across years would show whether the gap between greener and barer neighbourhoods is widening or narrowing.
- **Interactive web map.** Exporting the screening results to a Leaflet or Kepler.gl map would make priority sub-districts explorable by planners, NGOs, and residents without any GIS software.


## License

This code is released under the **MIT License** (see `LICENSE`).
Underlying datasets remain governed by their original licenses — City of Helsinki, HSY, and Helsinki Region Statistics open-data terms.

---

## Acknowledgments

- **City of Helsinki** — sub-district boundaries
- **Helsinki Region Environmental Services (HSY)** — land-cover / canopy data
- **Helsinki Region Statistics (Aluesarjat)** — income statistics

---

## Author

**Sonali Sharma** — Geospatial Analyst & Urban Ecologist
[ssonalipduoh@gmail.com](mailto:ssonalipduoh@gmail.com) · [GitHub](https://github.com/sonalispatial18) · [LinkedIn](https://www.linkedin.com/in/sonali-sharma-50220210b/)
