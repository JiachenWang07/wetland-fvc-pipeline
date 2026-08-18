# outputs/

Reviewed validation evidence published from this project. This is not the full set of approximately 42 GEE export tasks that `gee_scripts/` can produce. Raw Landsat/GLC source rasters and workflow GeoTIFF exports remain on Google Drive and are not distributed in Git.

Published files here fall into two roles: **core inputs** that a fresh clone can use to rerun the documented trend-analysis path, and **analysis/validation evidence** (reviewed derived tables). The latter are not a substitute for every upstream raster or GEE table needed to recompute those results from scratch.

---

## core/ — Published regional core CSVs (trend-analysis inputs)

These are reviewed GEE-side aggregated CSV products, not raw Landsat/GLC data: region-level 36-year FVC/EVI/NDMI time series plus fixed-endmember region means. They are sufficient for the publicly reproducible trend-analysis workflow documented in [`../README.md`](../README.md) (`trend_analysis.py`, `report_comparison.py`, and the FVC-trend portion of `plotting.py`). They do not include the GeoTIFFs or WetlandTransitionStructure tables required by `six_category_area_stats.py` and `cross_validation.py`.

| File | Source script | Content |
| --- | --- | --- |
| `{region}_Indices_36Years.csv` | `gee_scripts/fvc_dynamic_endmember.js` | 36 rows per region (1985–2020), dynamic-endmember FVC/EVI/NDMI under both the dynamic and 1985-fixed wetland masks, plus the endmember values themselves |
| `{region}_FVC_FixedEndmember_PixelLevel.csv` | `gee_scripts/fvc_fixed_endmember.js` | 36 rows per region, region-mean FVC recomputed pixel-by-pixel using the region's fixed (36-year mean) endmember |

Field definitions: [`../docs/data_schema.md`](../docs/data_schema.md).

---

## analysis/ — Reviewed derived results (not a complete upstream archive)

Tables in this directory are reviewed analysis outputs computed during the project workflow. Their presence does **not** mean that every upstream raster or GEE export needed to regenerate them from scratch is included in this repository.

| File | Source script | Content | `methodology_notes.md` | Known limitations |
| --- | --- | --- | --- | --- |
| `sen_mk_segmented_primary.csv` | `python_analysis/src/trend_analysis.py` | 24 rows: 4 indicators (FVC_Dynamic / FVC_Fixed1985 / EVI_Dynamic / NDMI_Dynamic) × 3 regions × 2 segments (1985–2005, 2005–2020), Sen's slope + Mann-Kendall. The deprecated full-period (1985–2020) results have been excluded from this file — that test was formally abandoned for endmember sensitivity and exists only as a text record in `methodology_notes.md`, not as a published output | 第四轮③、第五轮 | 2 of the 6 FVC_Dynamic region×segment results are sensitive to endmember-method choice (YRD 1985–2005 loses significance, BTH 2005–2020 flips sign) — see `EndmemberMethod_Sensitivity_Summary.csv` and 第五轮 |
| `ReportComparison_Section3_1.csv` | `python_analysis/src/report_comparison.py` | 6 rows: the team's final report's section 3.1 p-values/directions (hardcoded from the report table) vs. this rewritten pipeline's actual recomputed results, with `direction_match`/`p_value_consistent` flags per row | 第四轮③ | None |

---

## validation/ — Reviewed validation evidence

These CSVs document checks already performed on the reviewed workflow. They are evidence of those comparisons, not a claim that a fresh public clone contains every input required to repeat every check from raw GEE exports. In particular, `six_category_validation.csv` records the 18/18 (max `abs_difference_km2` = 0.0 km²) raster-vs-reference comparison; the GeoTIFF inputs used to compute the Python side of that check are not in Git.

| File | Source | Content | `methodology_notes.md` | Known limitations |
| --- | --- | --- | --- | --- |
| `six_category_validation.csv` | `python_analysis/src/six_category_area_stats.py` | 18 rows (3 regions × 6 categories). **This compares the Python raster recomputation (this rewrite's `six_category_area_stats.py`, run on real historical rasters) against the historical aligned reference results (`SixCategory_AreaStats_ALIGNED.csv`) — it is not a comparison against the current GEE-side `SixCategory_AreaStats` export**, which is a separate, not-yet-cross-checked product (see note below). 18/18 published values match, with max `abs_difference_km2` = 0.0 at the serialized CSV precision. The original in-memory comparison retained sub-CSV floating-point differences of ~10⁻⁷–10⁻⁶ km²; see 第六轮 in `methodology_notes.md` | 第六轮（CLOSED） | None — this investigation is closed |
| `EndmemberMethod_Sensitivity_Summary.csv` | `python_analysis/src/endmember_method_sensitivity.py` | 3 rows: one region-level classification per region, synthesizing the two segmented comparisons (1985–2005 and 2005–2020). The classification distinguishes robust / sensitive / unstable outcomes; segment-level sign and significance differences are used as classification evidence rather than represented as separate rows. Classification thresholds are stated explicitly in the source code | 第五轮（CLOSED），四层裁决A/B/C/D | BTH 2005–2020 is the one genuinely conclusion-unstable case. YRD 1985–2005 was previously misclassified as unstable because an earlier implementation compared pymannkendall's significance-dependent `trend` labels rather than Sen-slope signs; the classifier has since been corrected, and YRD is now classified as sensitive because the slope direction agrees while significance differs |
| `YRD_FixedEndmember_v4_vs_current_validation.csv` | Independent code-path audit (external review), value-by-value comparison | 36 rows: YRD's fixed-endmember export from the current rewritten pipeline vs. the historical `_v4` export, year by year. Max difference 2.22×10⁻¹⁶ (floating-point precision) | 第五轮 A层事实#2 | This specific value-level re-export comparison was only done for YRD. GBA/BTH's fixed-endmember data used elsewhere in this analysis reuses the historical `_v4` files directly (the underlying computation logic is unchanged and code-path-audited, but has not been independently re-exported and numerically re-checked the way YRD was) — see [`../docs/limitations.md`](../docs/limitations.md) |

**Note on `six_category_validation.csv` scope:** `gee_scripts/trend_classification.js` also exports a GEE-side `{region}_SixCategory_AreaStats` product, computed server-side rather than by the local Python raster pipeline this validation file covers. Whether the GEE-side and Python-side six-category numbers agree with each other has not yet been checked — that would be a separate, currently unperformed cross-check, not something this file demonstrates.

### Cross-validation inputs (not in `core/`)

`python_analysis/src/cross_validation.py` is not runnable from `outputs/core/` alone. It needs regional `{region}_WetlandTransitionStructure.csv` files plus SixCategory area stats as either:

- per-region `{region}_SixCategory_AreaStats.csv` (legacy / GEE filename), or
- combined `SixCategory_AreaStats.csv` (the file written by `six_category_area_stats.py`; v1.0.1 adds a compatibility fallback that filters this table by the `region` column)

`six_category_area_stats.py` itself needs four GeoTIFFs per region (`{region}_RawLandCover_1985.tif`, `{region}_RawLandCover_2020.tif`, `{region}_FVC_2020_30m.tif`, `{region}_FVC_TrendClass_5Level.tif`). Those rasters are not distributed in Git.

---

## Why not all ~42 GEE products

1. Some products have not completed real-data validation yet (e.g. `FateGroup_FVC` currently has partial regional coverage; `WetlandTransitionStructure` is affected by a known code issue — see [`../docs/limitations.md`](../docs/limitations.md)). Unvalidated products are not published here.
2. Intermediate diagnostics are not conclusion evidence. Exploratory CSVs generated during debugging are recorded in [`../docs/methodology_notes.md`](../docs/methodology_notes.md) rather than kept as standalone files here.
3. Raw/intermediate rasters and other large files are excluded by `.gitignore` and kept on Google Drive. This directory holds only small aggregated CSVs. That is a distribution choice: `six_category_area_stats.py` therefore cannot be recomputed from the public clone without those additional GeoTIFF exports.
