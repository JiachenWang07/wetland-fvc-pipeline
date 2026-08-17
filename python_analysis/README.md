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
- [ ] 四象限图（面积×质量）——需要额外的城市级数据拼表逻辑，`data_loader.py`目前还没接入
- [ ] BNU独立端元对比图——对比的是第三方数据集，不是`gee_scripts/`的产出，不适合套用现有的`load_csv()`模式
- [ ] `tests/`——目前只做过用合成假数据的手动冒烟测试（确认逻辑跑得通、边界情况不崩溃），没有正式的pytest用例

5个核心脚本已经用结构正确的合成数据实际跑通过（不是只做了语法检查），包括故意测试了
"部分产品文件缺失"这种情况下`plotting.py`是否会优雅跳过而不是整体崩溃——结果符合预期。

**尚未做的验证**：还没有拿`gee_scripts/`真实导出的CSV跑过——因为`outputs/`目前还是空的
（GEE导出任务还没有真正跑到完成并review进仓库）。等`outputs/`里有真实数据后，需要重新跑一遍
这几个脚本，确认真实数据的列名、取值范围跟`docs/data_schema.md`里的预期一致（尤其是
`City_FVC_8Nodes.csv`这类列名有不确定性的产出，见`data_schema.md`里的具体标注）。

## 依赖

```bash
pip install -r requirements.txt
```

## 用法

每个脚本可以独立运行（假设`../outputs/`里已经有对应的CSV/TIF文件）：

```bash
cd src/
python trend_analysis.py
python six_category_area_stats.py
python cross_validation.py
python plotting.py
```

默认从`../outputs/`读取数据，可以用环境变量`WETLAND_DATA_DIR`指向别的目录（比如GEE导出后
还没review进`outputs/`之前的本地临时目录）。
