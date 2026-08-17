# wetland-fvc-pipeline

> **EN**: A reproducible geospatial data pipeline for analyzing multi-decadal wetland vegetation-cover change across three Chinese urban agglomerations (1985–2020)
> **中**：面向长时序遥感数据的可复现地理空间分析管线——三大城市群湿地植被覆盖变化案例（1985–2020）

![YRD FVC Trend Classification 1985–2020](docs/assets/yrd_fvc_trend_classification_1985_2020.png)
*Yangtze River Delta wetland FVC trend classification, 1985–2020 (pixel-level OLS fit).*

---

## Background 项目背景

**EN**: This repository analyzes **Fractional Vegetation Cover (FVC)** change in wetlands across three major Chinese urban agglomerations from 1985–2020, based on Landsat time-series and Google Earth Engine. It originated from an undergraduate research project; the analytical design and implementation here are independently developed.

Study area: Yangtze River Delta (YRD), Greater Bay Area (GBA), Beijing-Tianjin-Hebei (BTH), 1985–2020.

**中**：本仓库基于 Landsat 时序影像与 Google Earth Engine，分析 1985–2020 年三大城市群湿地植被覆盖度（FVC）变化。项目起源于一项本科生科研项目，其中的分析思路设计与代码实现均为独立完成。

研究对象：长三角(YRD)、粤港澳大湾区(GBA)、京津冀(BTH) 三大城市群，1985–2020年。

## What This Does 这个仓库解决什么问题

- **EN**: Computes region-level dynamic FVC from Landsat time series using a dimidiate pixel model
  **中**：基于 Landsat 时序影像与二分像元模型，动态计算区域级 FVC（植被覆盖度）
- **EN**: Independent processing pipelines for 3 regions via a factory-function pattern, preventing cross-region data contamination
  **中**：多区域（3个城市群）独立处理管线，避免跨区域数据串线（工厂函数架构）
- **EN**: Wetland fate classification (persistent / gained / lost) + trend testing (Sen's slope + Mann-Kendall)
  **中**：湿地命运分组（持续/新增/丧失）+ 趋势检验（Sen's slope + Mann-Kendall）
- **EN**: Cross-method validation (dynamic vs. fixed endmembers; six-category area stats vs. transition matrix)
  **中**：跨方法交叉验证（动态端元 vs 固定端元、六类图 vs 转移矩阵）
- **EN**: Built on Google Earth Engine (cloud-scale raster processing) + Python geospatial stack (rasterio, pandas)
  **中**：基于 Google Earth Engine（云端栅格计算）+ Python 地理空间技术栈（rasterio、pandas）搭建

## How to Run 如何运行

**EN**: This is a **two-stage pipeline** — Earth Engine has no local execution mode, so it cannot be run end-to-end with a single command. The stages run in different environments and are connected by Google Drive:

1. **GEE stage (cloud, raster processing)** — Paste [`gee_scripts/run_all_combined.js`](gee_scripts/run_all_combined.js) into the [GEE Code Editor](https://code.earthengine.google.com/) and run it. This submits ~42 export tasks to Google Drive. See [`gee_scripts/README.md`](gee_scripts/README.md) for load order if running the modular files individually instead of the combined bundle.
   ⚠️ Requires access to an administrative-boundary asset — see [Data & Reproducibility](#data--reproducibility-数据与复现说明) below before running.
2. **Export stage** — Approve the submitted tasks in the Code Editor's *Tasks* tab. Outputs land in a Google Drive folder named `Wetland_FVC_Exports`.
3. **Python stage (local/Colab, statistics & figures)** — Download the CSVs from Drive into `python_analysis/`, install dependencies (`pip install -r python_analysis/requirements.txt`), then run the scripts under `python_analysis/src/`. Core scripts (trend analysis, six-category area stats, cross-validation, plotting) are implemented and tested against synthetic data, but **not yet run against real GEE-exported CSVs** — see [`python_analysis/README.md`](python_analysis/README.md) for exact status and [Known Limitations](#known-limitations-已知局限) below.

**中**：这是一个**两阶段pipeline**——Earth Engine没有本地执行模式，无法用一条命令端到端跑通。两个阶段运行在不同环境里，通过Google Drive衔接：

1. **GEE阶段（云端，栅格处理）**——把 [`gee_scripts/run_all_combined.js`](gee_scripts/run_all_combined.js) 整份粘贴进 [GEE Code Editor](https://code.earthengine.google.com/) 运行，会提交约42个导出任务到Google Drive。如果想分模块单独加载而不是用合并版，加载顺序见 [`gee_scripts/README.md`](gee_scripts/README.md)。
   ⚠️ 运行前需要能访问一份行政边界资产——见下方[数据与复现说明](#data--reproducibility-数据与复现说明)。
2. **导出阶段**——在Code Editor的*Tasks*标签页里逐个批准提交的任务，产出会进入Google Drive上一个叫`Wetland_FVC_Exports`的文件夹。
3. **Python阶段（本地/Colab，统计与画图）**——把Drive里的CSV下载到`python_analysis/`，安装依赖（`pip install -r python_analysis/requirements.txt`），再跑`python_analysis/src/`下的脚本。核心脚本（趋势分析、六类面积统计、交叉验证、画图）已实现并用合成数据测试过，但**还没有拿真实GEE导出的CSV跑过**，具体状态见 [`python_analysis/README.md`](python_analysis/README.md) 和下方[已知局限](#known-limitations-已知局限)。

## Highlights: A Full Debugging & Validation Chain 亮点：一条完整的调试与验证链条

**EN**: The most valuable part of this project isn't the methods used — it's what actually broke in the data pipeline, and how it was diagnosed. Three representative examples:

**中**：这个项目最有价值的部分不是"用了什么方法"，而是数据管道真实出过的问题和排查过程，例如：

- **EN — Architecture fix**: A shared mutable `roi` variable across regions caused cross-region data contamination (the GBA/BTH scripts were actually computing YRD's geographic extent) → resolved by switching to a factory-function pattern for full isolation.
  **中 — 架构重构**：多区域共享可变 `roi` 变量导致跨区域数据串线（GBA/BTH 脚本实际算的是 YRD 的地理范围）→ 改用工厂函数模式彻底隔离

- **EN — Discrepancy diagnosis**: Six-category area stats diverged from the transition matrix by 1.7–2.2× → suspected cloud-gap noise (falsified) → suspected wetland-definition mismatch (partially falsified) → root cause: the two numbers were never meant to be directly comparable (different statistics) → cross-validation converged to <10% error once compared correctly.
  **中 — 口径不一致排查**：六类面积统计与转移矩阵结果偏差 1.7–2.2 倍 → 怀疑云缺失噪声（证伪）→ 怀疑湿地判断口径不一致（部分证伪）→ 最终定位为"两个统计量本来就不该直接比较" → 交叉验证误差收敛到 10% 以内

- **EN — Getting the year convention right**: Wetland "lost" pixels were originally measured at the interval's end year with a dynamic mask, which is empty by definition (a lost pixel is no longer wetland at that year) — the group came back empty. A later fix removed the mask but still measured the wrong year, silently describing the new land cover instead of the wetland being lost. The final fix measures "lost" wetland at the year *before* conversion — the only year that answers the actual question. The underlying finding held up after the fix, and if anything came out stronger — this correction did not manufacture the result it now supports.
  **中 — 年份口径修正**："丧失"湿地最初用带掩膜的转化后年份统计，掩膜下必然为空；后续版本去掉掩膜但年份仍不对，结果能跑但测的是错误的东西（新地类而非原湿地）。最终版改用转化前一年，这是唯一能回答"消失前植被状态如何"的年份。修复后核心结论不仅未被推翻，反而证据更强——这个修正没有制造它所支持的结论。

**EN — Multi-round external review**: Before publishing, the GEE codebase went through four independent code/methodology reviews (general code review, remote-sensing methodology review, and two rounds of software-architecture review). Not every finding was accepted as-is — several were downgraded from "confirmed bug" to "needs empirical validation" after independent verification, and at least one reviewer's specific fix recommendation was rejected as unsuitable for this project's 1985 start date. The full triage (accepted / needs validation / rejected, and why) is in [`docs/methodology_notes.md`](docs/methodology_notes.md).
**中 — 多轮外部审查**：正式发布前，GEE代码经过了四轮独立审查（通用代码审查、遥感方法学审查、两轮软件架构审查）。不是所有发现都被照单全收——多条建议在独立核实后从"确认bug"降级为"需要实验验证"，至少一条具体修复方案（某审查者建议改用某种替代规范）被判定为不适合本项目从1985年起始的时间跨度而拒绝采纳。完整的采纳/待验证/拒绝清单及理由见 [`docs/methodology_notes.md`](docs/methodology_notes.md)。

Full log 完整调试记录见 [`docs/methodology_notes.md`](docs/methodology_notes.md)。

## Repository Structure 仓库结构

```
├── gee_scripts/                        # GEE JavaScript — data processing & export (independently re-implemented)
│   ├── region_pipeline.js              #   Core factory function + shared constants
│   ├── regions_config.js               #   Region boundaries + pipeline instantiation
│   ├── fvc_dynamic_endmember.js        #   Primary FVC export (36-year series, city nodes, spatial maps)
│   ├── fvc_fixed_endmember.js          #   Fixed-endmember sensitivity check
│   ├── wetland_fate_group.js           #   Persistent / gained / lost wetland FVC
│   ├── trend_classification.js         #   5-level trend map + six-category area-function map
│   ├── wetland_transition_structure.js #   Land-cover transition structure + city wetland area
│   ├── wetland_type_fvc.js             #   FVC by wetland subtype
│   ├── build_combined.sh               #   Regenerates run_all_combined.js from the files above
│   └── run_all_combined.js             #   Generated single-paste bundle (not the source of truth)
│
├── python_analysis/                    # Python — statistical analysis & visualization
│   ├── src/
│   │   ├── data_loader.py              #   Shared CSV/path-loading utilities
│   │   ├── trend_analysis.py           #   Sen's slope + Mann-Kendall (regional, segmented)
│   │   ├── six_category_area_stats.py  #   Offline raster computation, area-aligned final version
│   │   ├── cross_validation.py         #   Six-category vs. transition-matrix cross-check
│   │   └── plotting.py                 #   Unified-palette figure generation
│   └── requirements.txt
│
├── outputs/                            # De-identified aggregated CSV results (no raw pixel/raster data)
│
├── report/                             # Whether to include the full report is undecided — see report/README.md
│
└── docs/
    ├── methodology_notes.md            # Full methodology, debugging log, and external-review triage
    ├── architecture.md                 # Data-flow diagram and pipeline design rationale
    ├── data_schema.md                  # Column-level schema for every exported CSV/raster product
    ├── limitations.md                  # Known limitations, including unresolved items from external review
    └── assets/                         # Figures referenced in this README
```

## Data & Reproducibility 数据与复现说明

**EN**: This repo does **not** include raw data. Landsat and GLC_FCS30D are public datasets with their own usage terms — code references them, but data itself must be obtained from official sources / GEE. `outputs/` contains only de-identified, region-level aggregated CSVs, no raw pixel-level data.

⚠️ **Known gap**: the administrative-boundary source (`china` in `gee_scripts/regions_config.js`) is currently a private GEE asset under this project's own account, and will not be accessible if you clone this repo and try to run the scripts as-is. See the warning comment at the top of `regions_config.js` for how to reconstruct it from public sources. This is documented rather than hidden — the pipeline logic itself is reproducible, the boundary data source is the part that currently isn't self-contained.

**中**：本仓库**不包含原始数据**（Landsat、GLC_FCS30D 均为有使用条款的公开数据集），代码中会说明数据来源，需自行在 GEE / 官方渠道获取。`outputs/` 中的 CSV 是脱敏后的区域级聚合结果，不含原始像元级数据。

⚠️ **已知缺口**：行政边界数据源（`gee_scripts/regions_config.js`里的`china`）目前指向本人私有GEE资产，clone本仓库后直接运行会因权限问题失败，`regions_config.js`文件顶部有详细的重建说明。这个问题选择如实标注而不是隐藏——pipeline的逻辑本身是可复现的，边界数据源这一环目前还不是开箱即用的。

## Known Limitations 已知局限

**EN**: This project documents its limitations rather than hiding them — including several identified during external code review that are confirmed real but not yet resolved (pending sensitivity experiments before deciding whether/how to fix). Full list, with severity and current status, in [`docs/limitations.md`](docs/limitations.md).

**中**：这个项目选择记录局限而不是隐藏——包括几项在外部代码审查中被确认真实存在、但尚未处理（等待敏感性实验结果再决定要不要改、怎么改）的问题。完整清单及当前状态见 [`docs/limitations.md`](docs/limitations.md)。

## Collaboration Note 协作声明

**EN**: The original analysis pipeline was developed collaboratively with AI-assisted (conversational) debugging as part of a team project. The code in this repository is an independent re-implementation, written after understanding every key design decision (why a factory-function pattern, why endmembers must be computed dynamically, why fate-group classification can't use a binary mask) rather than a direct copy of the original.

**中**：本项目分析流程最初在 AI 辅助（对话式调试）下与团队协作完成；本仓库中的代码是在理解每个关键设计决策（为什么用工厂函数、为什么端元要动态计算、为什么命运分组不能用二值掩膜）基础上重新独立实现的版本。

## License

MIT License (code). Underlying datasets follow their own original licenses and are out of scope for this repository.
