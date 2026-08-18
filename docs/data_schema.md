# Data Schema 数据契约

Column-level schema for every product exported by `gee_scripts/`. All exports land in a single Google Drive folder: `Wetland_FVC_Exports`. `{region}` is one of `YRD` / `GBA` / `BTH`.

None of these files are committed to this repository yet — `outputs/` is currently empty (see [`limitations.md`](limitations.md)). This document describes what the GEE scripts are designed to produce, based on the export code itself, not a verified sample.

---

## From `fvc_dynamic_endmember.js`

### `{region}_Indices_36Years.csv`
One row per year (1985–2020, 36 rows). Regional means at `REGIONAL_SCALE` (500m).

| Column | Type | Description |
|---|---|---|
| `region` | string | `YRD` / `GBA` / `BTH` |
| `year` | int | Requested year |
| `actual_imagery_year` | int | Year the Landsat composite actually came from, if the 4-level fallback substituted a different year |
| `FVC_Dynamic` | float [0,1] | Region-mean FVC, dynamic wetland mask, dynamic endmember |
| `EVI_Dynamic` | float | Region-mean EVI, dynamic mask |
| `NDMI_Dynamic` | float | Region-mean NDMI, dynamic mask |
| `FVC_Fixed1985` | float [0,1] | Region-mean FVC, masked to the 1985 wetland baseline |
| `EVI_Fixed1985` | float | Region-mean EVI, 1985 mask |
| `NDMI_Fixed1985` | float | Region-mean NDMI, 1985 mask |
| `NDVI_p5_soil` | float | That year's dynamic soil endmember (5th percentile NDVI) |
| `NDVI_p95_veg` | float | That year's dynamic vegetation endmember (95th percentile NDVI) |

### `{region}_City_FVC_8Nodes.csv`
One row per city × 8 node years (1985/1990/.../2020). Scale `CITY_SCALE` (30m).

✅ **Column naming — confirmed, not just expected**: `ee.Image.reduceRegions()` outputs the reducer's own name (`mean`), not the input band's name (`FVC`), **even when the band is explicitly renamed to `FVC` before the call** — this was verified against real output from the rewritten `fvc_dynamic_endmember.js` (2026-08-17: both `YRD_City_FVC_8Nodes.csv` and `GBA_City_FVC_8Nodes.csv` have a literal `mean` column, not `FVC`). Downstream Python code must rename it explicitly (`.rename(columns={'mean': 'FVC'})`), matching the pattern already used in historical analysis scripts for the equivalent table.

| Column (intended) | Type | Description |
|---|---|---|
| *(original city feature properties)* | — | Carried through from the source boundary FeatureCollection — includes at minimum a city `name`; exact property set depends on the boundary asset |
| `year` | int | Node year |
| `region` | string | `YRD` / `GBA` / `BTH` |
| `FVC` | float [0,1] | City-mean dynamic FVC — **verify actual column name once this export has been run**; may come out as `mean` instead, matching the pattern seen in earlier script versions |

### `{region}_FVC_1985_30m.tif` / `{region}_FVC_2020_30m.tif`
Single-band Float32 raster, band name `FVC`, values in [0,1], 30m, dynamic wetland mask, clipped to the region boundary.

---

## From `fvc_fixed_endmember.js`

### `{region}_FVC_FixedEndmember_PixelLevel.csv`
One row per year (1985–2020). Uses the region's fixed endmember pair instead of that year's dynamic one.

| Column | Type | Description |
|---|---|---|
| `region` | string | — |
| `year` | int | — |
| `FVC_FixedEndmember_Pixel` | float [0,1] | Region-mean FVC computed with the fixed endmember |

### `{region}_City_FixedFVC_8Nodes.csv`
Same shape as `{region}_City_FVC_8Nodes.csv` above, but the FVC column is computed with the fixed endmember pair instead of the dynamic one. Same confirmed column-naming behavior applies — the code names the band `FVC_Fixed` before `reduceRegions()`, but the actual output column will be `mean` (verified pattern, see above); rename explicitly downstream.

---

## From `wetland_fate_group.js`

### `{region}_FateGroup_FVC.csv`
One row per (interval × fate type) — 7 intervals × 3 types = 21 rows per region.

| Column | Type | Description |
|---|---|---|
| `region` | string | — |
| `interval` | string | e.g. `"1985-1990"` |
| `type` | string | `persistent` / `gained` / `lost` |
| `FVC_mean` | float [0,1] | Mean FVC for that fate group. **`persistent`/`gained` measured at the interval's end year; `lost` measured at the interval's start year** — see `wetland_fate_group.js` header comment for why |

---

## From `trend_classification.js`

### `{region}_FVC_TrendClass_5Level.tif`
Single-band Byte raster, values 1–5, masked to the 2020 wetland extent. 1=Severe Degradation, 2=Mild Degradation, 3=Stable, 4=Mild Recovery, 5=Significant Recovery. Class boundaries are OLS slope cutoffs (±0.001, ±0.005/year), not a significance test.

### `{region}_FVC_Slope_Raw.tif`
Single-band Float32 raster: the continuous per-pixel OLS slope value underlying the classification above.

### `{region}_FVC_TrendClass_AreaStats.csv`
One row per class (up to 5 rows per region).

| Column | Type | Description |
|---|---|---|
| `region` | string | — |
| `class_id` | int | 1–5 |
| `class_label` | string | e.g. `"Significant Recovery"` |
| `area_km2` | float | Class area within the region |

### `{region}_SixCategory_AreaStats.csv`
One row per class (up to 6 rows per region). See `trend_classification.js` for the exact category definitions (wetland lost / persistent-degraded / persistent-stable / persistent-improved / new low-cover / new high-cover).

| Column | Type | Description |
|---|---|---|
| `region` | string | — |
| `class_id` | int | 1–6 |
| `class_label` | string | e.g. `"Wetland Lost"` |
| `area_km2` | float | Class area |

---

## From `wetland_transition_structure.js`

### `{region}_WetlandTransitionStructure.csv`
One row per (interval × direction × land-cover class actually observed) — row count varies by how many distinct classes appear in each interval.

| Column | Type | Description |
|---|---|---|
| `region` | string | — |
| `interval` | string | e.g. `"1985-1990"` |
| `direction` | string | `out` (wetland → this class) or `in` (this class → wetland) |
| `converted_class_code` | int | GLC_FCS30D class code |
| `converted_class_name` | string | Human-readable class name |
| `area_km2` | float | Area of that specific transition |

### `{region}_City_WetlandArea_8Nodes.csv`
One row per city × 8 node years.

Same confirmed column-naming behavior as above: the code names the band `wetland_area_km2` before `reduceRegions()`, but the actual output column will be `sum` (the pattern is verified for `reduceRegions()` generally, not yet independently re-confirmed for this specific export, but there is no reason to expect it to behave differently).

| Column (intended) | Type | Description |
|---|---|---|
| *(original city feature properties)* | — | Same as `{region}_City_FVC_8Nodes.csv` |
| `year` | int | Node year |
| `region` | string | — |
| `wetland_area_km2` | float | City wetland area at that year — **verify actual column name once run**; may come out as `sum` |

---

## From `wetland_type_fvc.js`

### `{region}_FVC_ByWetlandType.csv`
One row per (snapshot year × wetland subtype) — 3 years × 7 subtypes = 21 rows per region.

| Column | Type | Description |
|---|---|---|
| `region` | string | — |
| `year` | int | 1985 / 2000 / 2020 |
| `wetland_code` | int | GLC_FCS30D subtype code, 181–187 |
| `wetland_type` | string | e.g. `"Mangrove"` |
| `FVC_mean` | float [0,1] | Mean FVC for that subtype |

---

## Not Yet Reviewed / Committed

The schemas documented above have mixed validation status. Several core products have now been run on real data, reviewed, and published under `outputs/`, including all three `{region}_Indices_36Years.csv` files and the fixed-endmember regional time series used by the downstream analyses. Their actual published schemas should be treated as the authoritative reference.

Other GEE exports documented here remain code-derived schemas only: task submission does not imply successful execution or real-data validation. See [`../outputs/README.md`](../outputs/README.md) for the published evidence set and [`limitations.md`](limitations.md) for product-specific validation status.
