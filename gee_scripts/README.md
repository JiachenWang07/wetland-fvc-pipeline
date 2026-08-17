# gee_scripts/

GEE JavaScript 代码，独立重新实现版本（非直接搬运原协作代码）。

GEE Code Editor 没有模块导入机制，这些文件需要按顺序整段粘贴进同一个脚本里运行，
不是各自独立可执行的文件。

## ⚠️ 已知限制：私有GEE资产依赖（尚未解决，发布前必读）

`regions_config.js` 里的 `china` 边界数据指向本人私有的GEE资产
（`projects/my-project-11626-475607/assets/China`），**任何clone这个仓库的人都无法访问**，
脚本会在第一步就报权限错误。这是遥感类可复现代码里常见的坑，目前**没有掩盖，如实标注在
`regions_config.js`文件顶部**，并给出了三种重建方式（自建同名资产/换成公开数据源/转成
GeoJSON本地加载）。在这个问题被实际解决之前，"reproducible pipeline"这个定位准确来说是
"代码逻辑可复现，但边界数据源目前需要自行准备"，不是"clone下来直接能跑"。

## 加载顺序
1. `region_pipeline.js` — 核心工厂函数 `makeRegionPipeline`，定义 `WETLAND_CODES`、
   `WETLAND_TYPE_NAMES`、`REGIONAL_SCALE`、`CITY_SCALE` 等全局共用常量，必须最先加载
2. `regions_config.js` — 三大区域边界定义 + 实例化 `pipeYRD`/`pipeGBA`/`pipeBTH`
3. 以下导出脚本，按需加载（依赖上面两个文件已经在同一个session中）

## 进度
- [x] `region_pipeline.js`（工厂函数核心架构 + 按年份记忆化缓存 + 全局常量唯一定义）
- [x] `regions_config.js`（区域边界 + 三条独立管线实例化 + 共用年份常量）
- [x] `fvc_dynamic_endmember.js`（36年动态端元FVC导出 + 城市节点 + 空间制图）
- [x] `fvc_fixed_endmember.js`（固定端元敏感性验证）
- [x] `wetland_fate_group.js`（命运分组，含年份口径修复）
- [x] `trend_classification.js`（5级趋势分类 + 六类面积-功能转化图，避免重复计算slope）
- [x] `wetland_transition_structure.js`（转出/转入结构统计，独立于FVC主线）
- [x] `wetland_type_fvc.js`（按湿地类型FVC统计，报告3.11节）

全部8个脚本已在GEE Code Editor实际跑通（2026-08-16验证：三区域面积打印正确，
YRD 35.9万/GBA 5.68万/BTH 21.68万 万km²，42个导出任务无报错提交）。

## 外部代码审查（两轮独立review）已修复的问题
- **命名去重**：`WETLAND_TYPE_NAMES`（湿地类型代码→名称）此前在3个文件里各自重复声明，
  现在唯一定义在`region_pipeline.js`，`wetland_type_fvc.js`和`wetland_transition_structure.js`
  改为引用它，不再重复硬编码
- **魔法数字**：`scale: 500`/`scale: 30`全部替换成命名常量`REGIONAL_SCALE`/`CITY_SCALE`
- **重复计算**：`processIndices()`和`getAnnualCompositeRobust()`加入按年份的记忆化缓存
  （`compositeCache`/`indicesCache`），避免同一年份被多个导出脚本各自重新计算一遍
- **"auto-assembled"措辞对不上实际情况**：之前`run_all_combined.js`声称自动拼装，但仓库里
  没有对应的构建脚本。现在补了`build_combined.sh`，这个声明是真实可验证的

## 仍未处理、记录在案但不阻塞发布的问题
- **零测试覆盖**：GEE端本身不便写传统单测，`python_analysis/`那边的Python统计逻辑
  （Sen's slope/Mann-Kendall判断、45%分类、六类归并）已用真实数据验证过多轮，但仍没有
  正式pytest用例，计划中，未开始
- **无配置驱动**：城市名单、固定端元数值目前硬编码在源码里，不是"改一个配置文件就能
  换研究区域"的通用框架。README定位已避免使用"config-driven"这类会造成落差感的措辞
- **无边界情况防御**：`getDynamicEndpoints`如果某年百分位数算出`null`（极端云污染年份），
  下游`processIndices`的行为未做显式处理
- **数据契约文档**：见 [`../docs/data_schema.md`](../docs/data_schema.md)，各CSV产出的
  字段名、类型、取值范围已有说明

## 一次性整体运行版本
`run_all_combined.js` 是把上面8个文件按依赖顺序拼接成的**单文件合并版**，专门用于
一次性粘贴进GEE Code Editor跑完整个pipeline，不用来回切换文件。

**这份文件由`build_combined.sh`自动生成，不是权威版本**——以后如果要改逻辑，改对应的
模块化文件（比如`region_pipeline.js`），然后在`gee_scripts/`目录下运行：
```bash
bash build_combined.sh
```
不要直接改`run_all_combined.js`本身，下次重新生成时会被覆盖。

## 验证记录
在GEE Code Editor新建脚本，直接粘贴 `run_all_combined.js` 全部内容即可运行（前提是
`regions_config.js`里的私有资产依赖已按上方说明自行解决）。

预期会提交约42个导出任务（单区域14个：4+2+1+4+2+1，×3个区域），全部存进Drive的
`Wetland_FVC_Exports`文件夹（原来是`GEE_Wetland_v4`这类带版本号的命名，已统一清理）。
不需要真的点开每个Task去Run（会消耗真实GEE配额和时间），确认脚本能无报错地跑到
"打印+提交Task"这一步即可。
