# Helsinki Residential Tree Canopy and Income

## Overview

This project examines mature tree-canopy provision across Helsinki residential environments and its relationship with area-level income.

Mature canopy is measured only within mapped residential land classified as **detached houses** or **blocks of flats**. This avoids including sea, industrial land, infrastructure, and other non-residential land in the canopy denominator.

## Research question

Across Helsinki sub-districts (*osa-alueet*), is median equivalised disposable income associated with mature tree-canopy share within residential land?

## Main result

The analysis included **109 Helsinki sub-districts** with:

* available 2024 income data; and
* at least **5 hectares** of mapped residential property land.

The relationship between median equivalised disposable income and mature canopy share within residential land was close to zero:

**Spearman ρ = 0.008**

This suggests that mature residential canopy does not follow a simple city-wide income gradient in Helsinki. Instead, local residential morphology, development history, and land-use context may shape canopy provision.

## Data

* Helsinki official sub-district boundaries (`osa-alueet`)
* Helsinki 2024 median equivalised disposable household income
* HSY 2024 vegetation layers representing canopy at least 10 m high:

  * 10–15 m
  * 15–20 m
  * over 20 m
* Residential property polygons classified as:

  * Detached houses
  * Blocks of flats

## Method

1. Select detached-house and block-of-flats property polygons.

2. Intersect them with Helsinki sub-district boundaries.

3. Union residential property land within each sub-district.

4. Intersect mature-canopy polygons with that residential-land mask.

5. Calculate:

   `mature canopy area within residential land / residential land area × 100`

6. Retain sub-districts with income data and at least 50,000 m² of residential property land.

7. Analyse the area-level association between income and mature canopy.

## Outputs

* `outputs/maps/01_residential_mature_canopy_2024.png`
  Mature tree-canopy share within residential land.

* `outputs/maps/02_median_income_2024.png`
  Median equivalised disposable income.

* `outputs/maps/03_income_canopy_screening_2024.png`
  Exploratory screening of lower-income and lower-canopy overlap areas.

* `outputs/figures/income_vs_residential_mature_canopy_2024.png`
  Income–canopy scatterplot.

## Interpretation

Income is measured at the Helsinki sub-district level, while mature canopy is derived from fine-resolution canopy and residential-property data. The findings therefore describe **sub-district-level associations**, not household-level or individual-level inequalities.

Mature canopy share is also not a measure of public access, quality, biodiversity, safety, or actual use of green space.

## Reproducibility

The workflow is organised into sequential scripts:

1. Source discovery and data download
2. Residential-land mask preparation
3. Mature-canopy intersection
4. Eligibility screening
5. Income–canopy analysis
6. Final map and figure creation
