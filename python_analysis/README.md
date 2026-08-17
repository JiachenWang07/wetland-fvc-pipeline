# python_analysis/

Python 统计分析与可视化代码，接在 `gee_scripts/` 导出的CSV之后（见根目录README的"How to Run"）。

独立重新实现版本——参考了4份历史Colab脚本（合计4200多行、含大量试错版本），梳理版本演进关系、
确认每个产出的最终定版逻辑之后重写，不是直接搬运。演进关系和几处关键修正记录在
[`../docs/methodology_notes.md`](../docs/methodology_notes.md)（"第三轮：Python历史脚本核实"一节）。

## 状态

- [x] `src/data_loader.py`（公共数据读取基础设施：路径管理、读取容错、端元有效性检查）
- [x] `src/trend_analysis.py`（Sen's slope + Mann-Kendall，明确区分已弃用的全周期检验和主用的分段检验）
- [x] `src/six_category_area_stats.py`（口径对齐版：湿地判断用181-187地类代码，按纬度逐行修正面积）
- [x] `src/cross_validation.py`（六类图 vs 转移矩阵交叉验证，同时保留"剔除水体"和"全类别"两个版本的对比）
- [x] `src/plotting.py`（统一PALETTE配色，覆盖4张核心图：区域趋势、命运分组、六类图、净流量）
- [x] `src/sensor_switch_check.py`（2013 Landsat传感器切换初步诊断，探索性筛查非正式统计检验，结果见`methodology_notes.md`"第四轮：真实数据验证"）
- [x] `src/data_diagnostics.py`（端元年际稳定性图 + 回退年份使用统计 + FVC/EVI/NDMI三指标动态-固定一致性检查，三项探索性筛查）
- [x] `src/report_comparison.py`（自动化"报告数值 vs 真实pipeline结果"比对，把此前手动核对的过程变成可复现脚本，报告数值硬编码自3.1节表格）
- [x] `src/endmember_behavior_check.py`（端元数值年际波动/相关性诊断，GBA异常排查Level 2，配合debugging budget原则——做不出结论就标记unresolved转向优先级更高的YRD传感器问题）
- [x] `src/endmember_method_sensitivity.py`（真正的动态端元vs固定端元敏感性实验，隔离mask效应，输出三区域robust/sensitive/unstable分类，分类标准显式写在代码里可复核）
- [ ] 四象限图（面积×质量）——需要额外的城市级数据拼表逻辑，`data_loader.py`目前还没接入
- [ ] BNU独立端元对比图——对比的是第三方数据集，不是`gee_scripts/`的产出，不适合套用现有的`load_csv()`模式
- [ ] `tests/`——目前只做过用合成假数据的手动冒烟测试（确认逻辑跑得通、边界情况不崩溃），没有正式的pytest用例

5个核心脚本已经用结构正确的合成数据实际跑通过（不是只做了语法检查），包括故意测试了
"部分产品文件缺失"这种情况下`plotting.py`是否会优雅跳过而不是整体崩溃——结果符合预期。

**验证进展**：不只是合成数据测试——`trend_analysis.py`用YRD/GBA/BTH三区域真实GEE导出数据跑通，
Sen's slope/Mann-Kendall结果与团队正式研究报告6/6组区域×分段检验一致；`six_category_area_stats.py`
用三区域真实历史栅格验证，6/6类别在浮点精度量级（~10⁻⁷ km²）复现历史参照结果，三区域投资调查均
已CLOSED。完整验证历史见根目录README的"Validation Status"章节和[`../docs/methodology_notes.md`](../docs/methodology_notes.md)。

## 依赖

Python >= 3.10（源码用了`Path | str`这类3.10+才支持的类型标注语法）。

从**仓库根目录**执行：

```bash
pip install -r python_analysis/requirements.txt
```

## ⚠️ 在Colab里跑，不要用`import`

Colab每次新notebook/新session都是全新环境，`sys.path`里没有本地文件，`import trend_analysis`这类写法会报`ModuleNotFoundError`——这个坑已经踩过至少两次了。正确做法：**把对应脚本的完整代码内容复制粘贴进Colab代码块直接运行**，不要import。如果确实想用import，需要先把整个文件内容写入Colab本地文件系统（比如用`%%writefile`），这个更麻烦，不推荐。

## 用法

每个脚本可以独立运行（假设仓库根目录的`outputs/`里已经有对应的CSV/TIF文件——**不是**`python_analysis/outputs/`，是仓库最外层那个`outputs/`，参见`data_loader.py`里`DEFAULT_DATA_DIR`的实际解析结果）：

从**仓库根目录**执行：

```bash
cd python_analysis/src/
python trend_analysis.py
python six_category_area_stats.py
python cross_validation.py
python plotting.py
```

默认读取路径是仓库根目录下的`outputs/`（不随你`cd`到`src/`而改变，`data_loader.py`内部用的是基于脚本文件自身位置往上三层解析出来的固定路径，不是当前工作目录的相对路径），可以用环境变量`WETLAND_DATA_DIR`指向别的目录（比如GEE导出后还没review进`outputs/`之前的本地临时目录）。
