# outputs/

Real validation evidence published from this project — not all ~42 GEE export tasks
`gee_scripts/` can theoretically produce, but the minimal, auditable set that backs
the claims made in the root README. Raw and intermediate products remain on Google
Drive and are not part of this repository.

不是`gee_scripts/`理论上能产出的全部约42个task，是能支撑根目录README核心声明的最小、
可审计证据集。原始/中间产物继续留在Google Drive，不进本仓库。

---

## core/ — Core processed outputs used by the downstream Python analyses

**These are not raw Landsat/GLC data** — they are GEE-side aggregated outputs
(region-level 36-year FVC/EVI/NDMI time series) that every downstream analysis in
`analysis/` and `validation/` is computed from.

**这些不是原始Landsat/GLC数据**——是GEE端聚合后的产出（区域级36年FVC/EVI/NDMI时间序列），
`analysis/`和`validation/`里的所有结果都是基于这些文件算出来的。

| File | Source script | Content |
|---|---|---|
| `{region}_Indices_36Years.csv` | `gee_scripts/fvc_dynamic_endmember.js` | 36 rows per region (1985-2020), dynamic-endmember FVC/EVI/NDMI under both the dynamic and 1985-fixed wetland masks, plus the endmember values themselves |
| `{region}_FVC_FixedEndmember_PixelLevel.csv` | `gee_scripts/fvc_fixed_endmember.js` | 36 rows per region, region-mean FVC recomputed pixel-by-pixel using the region's fixed (36-year mean) endmember |

Field definitions: [`../docs/data_schema.md`](../docs/data_schema.md).

---

## analysis/ — Core research results

| File | Source script | Content | `methodology_notes.md` | Known limitations |
|---|---|---|---|---|
| `sen_mk_segmented_primary.csv` | `python_analysis/src/trend_analysis.py` | 24 rows: 4 indicators (FVC_Dynamic / FVC_Fixed1985 / EVI_Dynamic / NDMI_Dynamic) × 3 regions × 2 segments (1985-2005, 2005-2020), Sen's slope + Mann-Kendall. The deprecated full-period (1985-2020) results have been excluded from this file — that test was formally abandoned for endmember sensitivity and exists only as a text record in `methodology_notes.md`, not as a published output | 第四轮③、第五轮 | 2 of the 6 FVC_Dynamic region×segment results are sensitive to endmember-method choice (YRD 1985-2005 loses significance, BTH 2005-2020 flips sign) — see `EndmemberMethod_Sensitivity_Summary.csv` and 第五轮 |
| `ReportComparison_Section3_1.csv` | `python_analysis/src/report_comparison.py` | 6 rows: the team's final report's section 3.1 p-values/directions (hardcoded from the report table) vs. this rewritten pipeline's actual recomputed results, with `direction_match`/`p_value_consistent` flags per row | 第四轮③ | None |

---

## validation/ — Reproduction and reference-comparison evidence

| File | Source | Content | `methodology_notes.md` | Known limitations |
|---|---|---|---|---|
| `six_category_validation.csv` | `python_analysis/src/six_category_area_stats.py` | 18 rows (3 regions × 6 categories). **This compares the Python raster recomputation (this rewrite's `six_category_area_stats.py`, run on real historical rasters) against the historical aligned reference results (`SixCategory_AreaStats_ALIGNED.csv`) — it is not a comparison against the current GEE-side `SixCategory_AreaStats` export**, which is a separate, not-yet-cross-checked product (see note below). 18/18 published values match, with max `abs_difference_km2` = 0.0 at the serialized CSV precision. The original in-memory comparison retained sub-CSV floating-point differences of ~10⁻⁷–10⁻⁶ km²; see 第六轮 in `methodology_notes.md` | 第六轮（CLOSED） | None — this investigation is closed |
| `EndmemberMethod_Sensitivity_Summary.csv` | `python_analysis/src/endmember_method_sensitivity.py` | 3 rows: one region-level classification per region, synthesizing the two segmented comparisons (1985-2005 and 2005-2020). The classification distinguishes robust / sensitive / unstable outcomes; segment-level sign and significance differences are used as classification evidence rather than represented as separate rows. Classification thresholds are stated explicitly in the source code | 第五轮（CLOSED），四层裁决A/B/C/D | BTH 2005-2020 is the one genuinely conclusion-unstable case. YRD 1985-2005 was previously misclassified as unstable because an earlier implementation compared pymannkendall's significance-dependent `trend` labels rather than Sen-slope signs; the classifier has since been corrected, and YRD is now classified as sensitive because the slope direction agrees while significance differs |
| `YRD_FixedEndmember_v4_vs_current_validation.csv` | Independent code-path audit (external review), value-by-value comparison | 36 rows: YRD's fixed-endmember export from the current rewritten pipeline vs. the historical `_v4` export, year by year. Max difference 2.22×10⁻¹⁶ (floating-point precision) | 第五轮 A层事实#2 | This specific value-level re-export comparison was only done for YRD. GBA/BTH's fixed-endmember data used elsewhere in this analysis reuses the historical `_v4` files directly (the underlying computation logic is unchanged and code-path-audited, but has not been independently re-exported and numerically re-checked the way YRD was) — see [`../docs/limitations.md`](../docs/limitations.md) |

**Note on `six_category_validation.csv`'s scope**: `gee_scripts/trend_classification.js` also exports a GEE-side `{region}_SixCategory_AreaStats` product, computed server-side rather than by the local Python raster pipeline this validation file covers. Whether the GEE-side and Python-side six-category numbers agree with each other has not yet been checked — that would be a separate, currently unperformed cross-check, not something this file demonstrates.

**关于`six_category_validation.csv`的验证范围，必须说清楚**：`gee_scripts/trend_classification.js`本身也会导出一份GEE端算出来的`{region}_SixCategory_AreaStats`（服务端聚合，不是这份验证文件所覆盖的本地Python栅格pipeline）。GEE端结果和Python端结果是否一致，目前**没有核实过**——这是一项尚未进行的、独立的交叉检查，不是这份文件已经证明的内容。

---

## Why not all ~42 GEE products

1. **Some products haven't completed real-data validation yet** (e.g. `FateGroup_FVC` currently has partial regional coverage; `WetlandTransitionStructure` is affected by a known code issue — see [`../docs/limitations.md`](../docs/limitations.md)). Unvalidated products aren't published here to avoid implying they've been checked.
2. **Intermediate diagnostics are not the same as conclusion evidence** — exploratory CSVs generated during debugging (e.g. data behind a hypothesis that was later disproven, or per-year detail tables superseded by a summary) are recorded in the prose of [`../docs/methodology_notes.md`](../docs/methodology_notes.md) rather than kept as standalone files here.
3. **Raw rasters and large files don't go in Git** — excluded by `.gitignore`, kept on Google Drive; this directory holds only small aggregated CSVs.
