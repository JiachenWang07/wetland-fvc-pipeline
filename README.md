# wetland-fvc-pipeline

A reproducible geospatial pipeline for analyzing long-term wetland vegetation change with Google Earth Engine and Python.

**Case study:** Yangtze River Delta (YRD), Greater Bay Area (GBA), and Beijing–Tianjin–Hebei (BTH), 1985–2020.

![YRD FVC trend classification](docs/assets/yrd_fvc_trend_classification_1985_2020.png)

> 中文简介：这是一个从本科科研中的湿地植被分析工作发展而来的地理空间数据项目，使用 Google Earth Engine 和 Python 处理 1985–2020 年 Landsat 时序数据。仓库主要关注可复现的数据处理、趋势分析和结果验证，而不仅是最终的遥感制图结果。

## Overview

This project examines Fractional Vegetation Cover (FVC) change in wetlands across three Chinese urban agglomerations: YRD, GBA, and BTH.

The workflow includes:

- Landsat time-series processing in Google Earth Engine
- dynamic and fixed-endmember FVC estimation
- wetland fate classification (persistent / gained / lost)
- Sen's slope and Mann-Kendall trend analysis
- raster-based area statistics
- cross-method validation and diagnostic checks

The project originated from the vegetation-analysis part of an undergraduate research project. This repository contains the independently implemented and validated workflow developed from that work.

## Pipeline

```text
Landsat + GLC_FCS30D
        │
        ▼
Google Earth Engine
  ├─ Landsat preprocessing
  ├─ NDVI / EVI / NDMI
  ├─ FVC estimation
  ├─ wetland masks
  └─ spatial exports
        │
        ▼
   Google Drive
        │
        ▼
      Python
  ├─ Sen's slope
  ├─ Mann-Kendall
  ├─ six-category statistics
  ├─ sensitivity analysis
  └─ validation / figures
```

Earth Engine runs server-side, so the GEE and Python stages are connected through exported files rather than a local subprocess.

Each study region is instantiated through `makeRegionPipeline(roi, startMonth, endMonth)`, which keeps regional state isolated while reusing the same processing logic.

## Running the project

### 1. Google Earth Engine

Run [`gee_scripts/run_all_combined.js`](gee_scripts/run_all_combined.js) in the Earth Engine Code Editor. This is the recommended combined entry script and currently creates approximately 42 export tasks.

A modular alternative (load scripts in order) is documented in [`gee_scripts/README.md`](gee_scripts/README.md).

The region-construction module depends on a private administrative-boundary asset. See [`gee_scripts/README.md`](gee_scripts/README.md) and [`docs/limitations.md`](docs/limitations.md).

### 2. Export

Approve the generated tasks in the GEE Tasks tab. Exports go to the Google Drive folder `Wetland_FVC_Exports`.

### 3. Python analysis

Install dependencies:

```bash
pip install -r python_analysis/requirements.txt
```

### Reproducible from the public repository

The published `outputs/core/` CSVs are sufficient to rerun:

- `trend_analysis.py`
- regional Sen's slope / Mann–Kendall analysis
- `report_comparison.py` and the documented 6/6 comparison
- the FVC-trend portion of `plotting.py`

From the repository root:

```bash
WETLAND_DATA_DIR=outputs/core python python_analysis/src/trend_analysis.py
```

Not every Python script can run from `outputs/core/` alone. Script-specific working directories, additional analyses, and the `WETLAND_DATA_DIR=../../outputs/core` form used from `python_analysis/src/` are documented in [`python_analysis/README.md`](python_analysis/README.md).

### Requires additional upstream GEE outputs

- `six_category_area_stats.py` requires the regional GeoTIFF products used by the raster workflow and therefore cannot be recomputed from the public clone alone.
- `cross_validation.py` requires WetlandTransitionStructure inputs in addition to SixCategory inputs.
- The repository publishes reviewed validation evidence for those analyses, but not every upstream raster/table required to recompute them from scratch.

## What went wrong (and what I fixed)

### 1. Cross-region state leakage

An early version used a shared mutable `roi`. Functions created while `roi` pointed to one region could later evaluate against another region after reassignment, so results depended on execution order. The factory function `makeRegionPipeline(roi, startMonth, endMonth)` isolates each region's parameters.

### 2. Comparing statistics that were not equivalent

An initial SixCategory vs transition-area comparison showed an approximately 1.7–2.2× discrepancy. Cloud-gap and wetland-definition hypotheses were tested and did not explain the gap. The root issue was mismatched statistical quantities. After aligning the compared quantities, the cross-check converged to <10%.

### 3. Measuring lost wetlands in the wrong year

An end-year dynamic-mask approach produced empty or incorrect lost-wetland results because those pixels were no longer classified as wetland at the end of the period. The final implementation evaluates lost wetlands before conversion.

More debugging and methodology notes are in [`docs/methodology_notes.md`](docs/methodology_notes.md).

## Validation

| Check | Result |
| --- | --- |
| Regional FVC/EVI/NDMI series | 3 regions × 36 years exported and loaded |
| Report trend comparison | 6/6 region-period cases matched in direction and p-value |
| YRD fixed-endmember rerun | max difference ≈ `2.22×10⁻¹⁶` |
| Six-category validation | 18/18 published values matched; public CSV max difference = `0.0 km²` |
| Endmember sensitivity | YRD: sensitive · GBA: sensitive · BTH: unstable |

The six-category validation also showed only floating-point-scale differences (~10^-7–10^-6 km²) before CSV serialization.

Full validation history, including rejected hypotheses, is documented in [`docs/methodology_notes.md`](docs/methodology_notes.md).

## Repository structure

```text
wetland-fvc-pipeline/
├── gee_scripts/            # Earth Engine processing
├── python_analysis/        # trend analysis, validation, figures
├── outputs/
│   ├── core/               # reviewed regional time series
│   ├── analysis/           # trend, six-category, and sensitivity tables
│   └── validation/         # report-comparison and six-category checks
├── docs/                   # architecture, schema, methodology, limitations
├── report/                 # reserved; full report not included
└── README.md
```

## Data and reproducibility

Raw Landsat and GLC_FCS30D imagery are not committed. [`outputs/`](outputs/) contains aggregated reviewed evidence (CSV tables), not raw raster data.

A private administrative-boundary GEE asset is the current reproducibility gap. Reconstruction instructions are in [`gee_scripts/regions_config.js`](gee_scripts/regions_config.js).

## Known limitations

Known methodological and implementation limitations are tracked in [`docs/limitations.md`](docs/limitations.md).

## Project context

This repository grew out of the vegetation/FVC module of a larger undergraduate wetland research project.

AI tools were used for conversational debugging and code review during development. The repository reflects the implementation, failure cases, validation results, and methodological decisions tested against the project's actual data.

## License

Code in this repository is released under the [MIT License](LICENSE).

External datasets (Landsat, GLC_FCS30D, and related products) remain under their original licenses and terms of use.
