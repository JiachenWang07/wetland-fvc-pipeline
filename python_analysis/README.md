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

每个脚本可以独立运行。输入默认来自仓库根目录的 `outputs/`（**不是** `python_analysis/outputs/`；参见 `data_loader.py` 里 `DEFAULT_DATA_DIR` 的解析结果）。

从**仓库根目录**执行：

```bash
cd python_analysis/src/
python trend_analysis.py
python six_category_area_stats.py
python cross_validation.py
python plotting.py
```

默认读取路径是仓库根目录下的 `outputs/`（不随 `cd` 到 `src/` 而改变；`data_loader.py` 基于脚本文件位置往上三层解析，不是当前工作目录的相对路径）。可用环境变量 `WETLAND_DATA_DIR` 指向别的目录（例如 GEE 导出后尚未 review 进 `outputs/` 的本地临时目录）。

### Published evidence workflow

仓库内已审阅的发布输入在 `<repo>/outputs/core/`。要从该证据集复现分析，请显式设置 `WETLAND_DATA_DIR`。

```bash
cd python_analysis/src
WETLAND_DATA_DIR=../../outputs/core python trend_analysis.py
```

使用同一套区域核心 CSV 的脚本可以用相同的 `WETLAND_DATA_DIR=../../outputs/core` 前缀。`outputs/core/` 中的文件是处理后的 GEE 产出，不是原始 Landsat/GLC 数据。
