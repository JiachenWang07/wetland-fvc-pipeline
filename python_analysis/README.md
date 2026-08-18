# python_analysis/

Python 统计分析与可视化代码，接在 `gee_scripts/` 导出的 CSV 之后。

历史脚本的演进关系和关键修正记录在 [`../docs/methodology_notes.md`](../docs/methodology_notes.md)（「第三轮：Python历史脚本核实」一节）。

## 状态

- [x] `src/data_loader.py`（公共数据读取：路径管理、读取容错、端元有效性检查）
- [x] `src/trend_analysis.py`（Sen's slope + Mann-Kendall；区分已弃用的全周期检验和主用的分段检验）
- [x] `src/six_category_area_stats.py`（湿地判断用 181–187 地类代码，按纬度逐行修正面积）
- [x] `src/cross_validation.py`（六类图 vs 转移矩阵交叉验证；保留「剔除水体」和「全类别」两个版本）
- [x] `src/plotting.py`（统一 PALETTE 配色：区域趋势、命运分组、六类图、净流量）
- [x] `src/sensor_switch_check.py`（2013 Landsat 传感器切换初步诊断，探索性筛查非正式统计检验；结果见 `methodology_notes.md`「第四轮：真实数据验证」）
- [x] `src/data_diagnostics.py`（端元年际稳定性图 + 回退年份使用统计 + FVC/EVI/NDMI 动态-固定一致性检查）
- [x] `src/report_comparison.py`（报告数值 vs pipeline 结果比对；报告数值硬编码自 3.1 节表格）
- [x] `src/endmember_behavior_check.py`（端元数值年际波动/相关性诊断）
- [x] `src/endmember_method_sensitivity.py`（动态端元 vs 固定端元敏感性实验，隔离 mask 效应；输出三区域 robust/sensitive/unstable 分类，标准写在代码中）
- [ ] 四象限图（面积×质量）——需要额外的城市级数据拼表逻辑，`data_loader.py` 目前还没接入
- [ ] BNU 独立端元对比图——对比的是第三方数据集，不是 `gee_scripts/` 的产出，不适合套用现有的 `load_csv()` 模式
- [ ] `tests/`——目前只做过用合成假数据的手动冒烟测试，没有正式的 pytest 用例

核心脚本已用结构正确的合成数据跑通，包括部分产品文件缺失时 `plotting.py` 跳过缺失输入而不整体崩溃。

**验证进展**：`trend_analysis.py` 用 YRD/GBA/BTH 三区域真实 GEE 导出数据跑通，Sen's slope/Mann-Kendall 结果与研究报告 6/6 组区域×分段检验一致。`six_category_area_stats.py` 用三区域真实历史栅格验证 18 个已发布的区域×类别数值：内存中的差异为浮点量级（~10⁻⁷–10⁻⁶ km²）；序列化后的公开 CSV 为 18/18 精确匹配，max `abs_difference_km2` = 0.0 km²。三区域该项调查均已 CLOSED。完整验证历史见 [`../docs/methodology_notes.md`](../docs/methodology_notes.md) 与 [`../outputs/README.md`](../outputs/README.md)。

## 依赖

Python >= 3.10（源码用了 `Path | str` 这类 3.10+ 才支持的类型标注语法）。

从**仓库根目录**执行：

```bash
pip install -r python_analysis/requirements.txt
```

## 在 Colab 里跑

Colab 新 session 的 `sys.path` 没有本仓库本地文件，`import trend_analysis` 会报 `ModuleNotFoundError`。做法：把对应脚本的完整代码内容复制粘贴进 Colab 代码块直接运行，不要 import。若要用 import，需先把文件写入 Colab 本地文件系统（例如 `%%writefile`）。

## 用法

每个脚本可以独立运行，但所需输入并不相同。输入默认来自仓库根目录的 `outputs/`（**不是** `python_analysis/outputs/`；参见 `data_loader.py` 里 `DEFAULT_DATA_DIR` 的解析结果）。哪些脚本能用公开的 `outputs/core/`、哪些还需要额外 GEE 产出，见下面两节。

从**仓库根目录**执行：

```bash
cd python_analysis/src/
python trend_analysis.py
python six_category_area_stats.py
python cross_validation.py
python plotting.py
```

默认读取路径是仓库根目录下的 `outputs/`（不随 `cd` 到 `src/` 而改变；`data_loader.py` 基于脚本文件位置往上三层解析，不是当前工作目录的相对路径）。可用环境变量 `WETLAND_DATA_DIR` 指向别的目录（例如 GEE 导出后尚未 review 进 `outputs/` 的本地临时目录）。

## 公开仓库可直接复现

`<repo>/outputs/core/` 存放已发布的区域核心 CSV（处理后的 GEE 产出，不是原始 Landsat/GLC 数据）。公开 clone 上已验证的流程：

```bash
cd python_analysis/src
WETLAND_DATA_DIR=../../outputs/core python trend_analysis.py
```

同一套已发布核心 CSV 也足以运行 `report_comparison.py`（文档中的 6/6 比对）。`plotting.py` 可以画出 FVC 趋势图；缺少所需产品的图组会跳过，而不是整次运行失败。

`outputs/core/` **不能**支撑全部 Python 分析。六类面积统计和交叉验证需要额外的上游 GEE 产出，见下一节。

## 需要额外 GEE 产出的分析

### six_category_area_stats.py

每个区域需要以下四个文件：

```text
{region}_RawLandCover_1985.tif
{region}_RawLandCover_2020.tif
{region}_FVC_2020_30m.tif
{region}_FVC_TrendClass_5Level.tif
```

这些 GeoTIFF 不随 Git 仓库分发。公开 clone 无法从零重算该栅格流程。

已发布的 [`../outputs/validation/six_category_validation.csv`](../outputs/validation/six_category_validation.csv)（18/18，max difference 0.0 km²）是审阅后的验证证据，不是公开仓库里可再跑一遍栅格计算的输入。

### cross_validation.py

需要：

```text
{region}_WetlandTransitionStructure.csv
```

以及下列二者之一：

```text
{region}_SixCategory_AreaStats.csv
```

或 `six_category_area_stats.py` 写出的合并表：

```text
SixCategory_AreaStats.csv
```

后者由 v1.0.1 的兼容回退支持：若按区域的 `{region}_SixCategory_AreaStats.csv` 不存在，则读取合并表并按 `region` 列筛选。转移矩阵仍只使用按区域的 `WetlandTransitionStructure` 文件。这些表也不在公开的 `outputs/core/` 中。
