# gee_scripts/

GEE JavaScript 处理脚本。GEE Code Editor 没有模块导入机制，这些文件需要按顺序整段粘贴进同一个脚本里运行，不是各自独立可执行的文件。

## 私有 GEE 资产依赖

`regions_config.js` 里的 `china` 边界数据指向私有资产 `projects/my-project-11626-475607/assets/China`。没有该资产访问权限时，脚本会在第一步报权限错误。

文件顶部给出了三种重建方式：自建同名资产 / 换成公开数据源 / 转成 GeoJSON 本地加载。在该依赖解决之前，代码逻辑可复现，但边界数据源需要自行准备。

## 加载顺序

1. `region_pipeline.js` — 核心工厂函数 `makeRegionPipeline`，定义 `WETLAND_CODES`、`WETLAND_TYPE_NAMES`、`REGIONAL_SCALE`、`CITY_SCALE` 等全局共用常量，必须最先加载
2. `regions_config.js` — 三大区域边界定义 + 实例化 `pipeYRD`/`pipeGBA`/`pipeBTH`
3. 以下导出脚本，按需加载（依赖上面两个文件已经在同一个 session 中）

## 模块

- [x] `region_pipeline.js`（工厂函数 + 按年份记忆化缓存 + 全局常量唯一定义）
- [x] `regions_config.js`（区域边界 + 三条独立管线实例化 + 共用年份常量）
- [x] `fvc_dynamic_endmember.js`（36 年动态端元 FVC 导出 + 城市节点 + 空间制图）
- [x] `fvc_fixed_endmember.js`（固定端元敏感性验证）
- [x] `wetland_fate_group.js`（命运分组；`lost` 在区间起始年取值，`persistent`/`gained` 在区间结束年取值）
- [x] `trend_classification.js`（5 级趋势分类 + 六类面积-功能转化图；避免重复计算 slope）
- [x] `wetland_transition_structure.js`（转出/转入结构统计，独立于 FVC 主线）
- [x] `wetland_type_fvc.js`（按湿地类型 FVC 统计）

`WETLAND_TYPE_NAMES` 唯一定义在 `region_pipeline.js`。尺度使用命名常量 `REGIONAL_SCALE` / `CITY_SCALE`（500 / 30）。`processIndices()` 与 `getAnnualCompositeRobust()` 按年份缓存（`compositeCache` / `indicesCache`）。

全部 8 个脚本已在 GEE Code Editor 实际跑通（2026-08-16 验证：三区域面积打印正确，YRD 35.9万/GBA 5.68万/BTH 21.68万 万km²，42 个导出任务无报错提交）。

## 一次性整体运行版本

`run_all_combined.js` 是把上面 8 个文件按依赖顺序拼接成的单文件合并版，用于一次性粘贴进 GEE Code Editor。

**该文件由 `build_combined.sh` 自动生成，不是权威版本。** 改逻辑时改对应模块化文件，然后在 `gee_scripts/` 目录下运行：

```bash
bash build_combined.sh
```

不要直接改 `run_all_combined.js`，下次重新生成时会被覆盖。

## 运行与导出

在 GEE Code Editor 新建脚本，粘贴 `run_all_combined.js` 全部内容即可运行（前提是 `regions_config.js` 里的私有资产依赖已按上方说明自行解决）。

预期会提交约 42 个导出任务（单区域 14 个：4+2+1+4+2+1，×3 个区域），全部存进 Drive 的 `Wetland_FVC_Exports` 文件夹。确认脚本能无报错地跑到打印并提交 Task 即可；在 Tasks 标签中批准导出。

字段说明见 [`../docs/data_schema.md`](../docs/data_schema.md)。
