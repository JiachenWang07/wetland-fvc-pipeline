/**
 * ==============================================================================
 * regions_config.js
 *
 * Defines the three study-area boundaries and instantiates one independent
 * pipeline per region via makeRegionPipeline() (region_pipeline.js).
 *
 * Load order in the GEE Code Editor: paste region_pipeline.js first, then
 * this file, in the same script.
 *
 * ⚠️ REPRODUCIBILITY WARNING — read before running:
 * `china` below points to a PRIVATE GEE asset under this project's own
 * Google Cloud account. It will NOT be accessible to anyone else who
 * clones this repo — the script will fail on line 1 with a permissions
 * error. This is a known, unresolved gap, not an oversight left
 * undocumented: administrative boundary data with the exact fields this
 * pipeline filters on (`name`, matching Chinese city/district names) was
 * originally sourced this way and has not yet been re-packaged as a
 * public, redistributable dataset.
 *
 * To actually run this pipeline yourself:
 *   1. Obtain a Chinese administrative-boundary dataset with a `name`
 *      field at city/district level (e.g. from GADM, or China's Ministry
 *      of Natural Resources public boundary releases — check each
 *      source's own redistribution terms before use).
 *   2. Upload it as a GEE asset under your own account, or convert it to
 *      a local GeoJSON and load it via `ee.FeatureCollection(ee.Geometry(...))`
 *      instead of the Asset reference below.
 *   3. Replace the `china` variable below with your version. The city
 *      name lists further down (cityFC_YRD / cityFC_GBA / cityFC_BTH)
 *      should not need to change if your dataset's `name` field uses the
 *      same Chinese administrative names.
 * ==============================================================================
 */

var china = ee.FeatureCollection('projects/my-project-11626-475607/assets/China');
var gaul = ee.FeatureCollection('FAO/GAUL_SIMPLIFIED_500m/2015/level2');

// ---------------- Yangtze River Delta (YRD) ----------------
var cityFC_YRD = china.filter(ee.Filter.inList('name', [
  '黄浦区', '徐汇区', '长宁区', '静安区', '普陀区', '虹口区', '杨浦区', '闵行区',
  '宝山区', '嘉定区', '浦东新区', '金山区', '松江区', '青浦区', '奉贤区', '崇明区',
  '南京市', '无锡市', '徐州市', '常州市', '苏州市', '南通市', '连云港市', '淮安市',
  '盐城市', '扬州市', '镇江市', '泰州市', '宿迁市',
  '杭州市', '宁波市', '嘉兴市', '湖州市', '绍兴市', '金华市', '舟山市', '台州市',
  '温州市', '衢州市', '丽水市',
  '合肥市', '芜湖市', '蚌埠市', '淮南市', '马鞍山市', '淮北市', '铜陵市', '安庆市',
  '黄山市', '滁州市', '阜阳市', '宿州市', '六安市', '亳州市', '池州市', '宣城市'
]));
var roi_YRD = cityFC_YRD.geometry().dissolve().simplify(1000);

// ---------------- Greater Bay Area (GBA) — 9 mainland cities + HK + Macao ----------------
var cityFC_GBA = (function () {
  var mainlandNine = china.filter(ee.Filter.or(
    ee.Filter.inList('name', [
      '广州市', '深圳市', '珠海市', '佛山市', '惠州市', '东莞市', '中山市', '江门市', '肇庆市'
    ]),
    ee.Filter.inList('adcode', [440100, 440300, 440400, 440600, 441300, 441900, 442000, 440700, 441200])
  ));
  var hongKong = gaul.filter(ee.Filter.eq('ADM0_NAME', 'Hong Kong')).map(function (f) {
    return f.set('name', '香港');
  });
  var macao = gaul.filter(ee.Filter.eq('ADM0_NAME', 'Macao')).map(function (f) {
    return f.set('name', '澳门');
  });
  return mainlandNine.merge(hongKong).merge(macao);
})();
var roi_GBA = cityFC_GBA.geometry().dissolve().simplify(1000);

// ---------------- Beijing-Tianjin-Hebei (BTH) ----------------
var cityFC_BTH = china.filter(ee.Filter.inList('name', [
  '东城区', '西城区', '朝阳区', '丰台区', '石景山区', '海淀区',
  '门头沟区', '房山区', '通州区', '顺义区', '昌平区', '大兴区',
  '怀柔区', '平谷区', '密云区', '延庆区',
  '和平区', '河东区', '河西区', '南开区', '河北区', '红桥区',
  '东丽区', '西青区', '津南区', '北辰区', '武清区', '宝坻区',
  '滨海新区', '宁河区', '静海区', '蓟州区',
  '石家庄市', '唐山市', '秦皇岛市', '邯郸市', '邢台市',
  '保定市', '张家口市', '承德市', '沧州市', '廊坊市', '衡水市'
]));
var roi_BTH = cityFC_BTH.geometry().dissolve().simplify(1000);

// ---------------- Instantiate one independent pipeline per region ----------------
// Growing-season windows differ by region: YRD/GBA/BTH sit at different
// latitudes and have different vegetation phenology.
var pipeYRD = makeRegionPipeline(roi_YRD, 5, 10);
var pipeGBA = makeRegionPipeline(roi_GBA, 4, 11);
var pipeBTH = makeRegionPipeline(roi_BTH, 5, 9);

var regionPipelines = { YRD: pipeYRD, GBA: pipeGBA, BTH: pipeBTH };
var cityCollections = { YRD: cityFC_YRD, GBA: cityFC_GBA, BTH: cityFC_BTH };

// ---------------- Shared year constants, used across all export scripts ----------------
var nodeYears = [1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]; // 5-year interval nodes
var years36 = [];
for (var y = 1985; y <= 2020; y++) { years36.push(y); }

// ---------------- Sanity check: areas must be clearly distinct ----------------
// Expected order of magnitude (万 km², i.e. x10^4 km²): YRD ~35, GBA ~5-6, BTH ~21.
// If any two regions print near-identical areas, something upstream leaked
// (e.g. a stale roi reused from a previous pipeline) — stop and check before
// running any exports.
Object.keys(regionPipelines).forEach(function (name) {
  print(name + ' roi area (万 km²):', regionPipelines[name].roi.area().divide(1e10));
});
