/**
 * Landsat 7/8 overlap-period validation for the reviewed Stage 5 method.
 *
 * Run this block after stage5_final_method_qa.js in the same GEE Code Editor
 * script. It reuses CFG, prep(), wetAt(), and empty from that file.
 *
 * For each region and year from 2013–2020, it builds separate L7 and L8
 * growing-season median composites and compares them only on wetland pixels
 * valid in both composites. This common-support design avoids confusing a
 * sensor difference with a difference in cloud-free spatial coverage.
 *
 * Output: Stage5_QA_L7_L8_CommonSupport_2013_2020.csv (24 rows expected).
 * The output is diagnostic evidence; it does not apply a harmonization.
 */

var OVERLAP_YEARS = ee.List.sequence(2013, 2020).getInfo();

function sensorCollection(roi, y, sm, em, id, is8) {
  var start = ee.Date.fromYMD(y, sm, 1);
  var end = ee.Date.fromYMD(y, em, 1).advance(1, 'month');
  return ee.ImageCollection(id)
    .filterBounds(roi)
    .filterDate(start, end)
    .map(function(im) { return prep(im, is8); });
}

function safeNumber(dictionary, key) {
  return ee.Number(ee.Algorithms.If(
    ee.Algorithms.IsEqual(dictionary.get(key), null), 0, dictionary.get(key)
  ));
}

var overlapRows = [];
CFG.forEach(function(c) {
  var roi = c.cities.geometry().dissolve();
  OVERLAP_YEARS.forEach(function(y) {
    var l7 = sensorCollection(roi, y, c.sm, c.em, 'LANDSAT/LE07/C02/T1_L2', false);
    var l8 = sensorCollection(roi, y, c.sm, c.em, 'LANDSAT/LC08/C02/T1_L2', true);
    var n7 = l7.size(), n8 = l8.size();
    var ndvi7 = ee.Image(ee.Algorithms.If(n7.gt(0), l7.median(), empty)).rename('NDVI_L7');
    var ndvi8 = ee.Image(ee.Algorithms.If(n8.gt(0), l8.median(), empty)).rename('NDVI_L8');
    var wet = wetAt(y).selfMask();
    var common = wet.updateMask(ndvi7.mask()).updateMask(ndvi8.mask());
    var fvc7 = ndvi7.subtract(c.soil).divide(c.veg - c.soil).clamp(0, 1).rename('FVC_L7');
    var fvc8 = ndvi8.subtract(c.soil).divide(c.veg - c.soil).clamp(0, 1).rename('FVC_L8');
    var area = ee.Image.pixelArea().divide(1e6);
    var sums = ee.Image.cat([
      area.updateMask(wet).rename('wetland_area'),
      area.updateMask(common.mask()).rename('common_area'),
      ndvi7.multiply(area).updateMask(common.mask()).rename('ndvi7_weighted'),
      ndvi8.multiply(area).updateMask(common.mask()).rename('ndvi8_weighted'),
      fvc7.multiply(area).updateMask(common.mask()).rename('fvc7_weighted'),
      fvc8.multiply(area).updateMask(common.mask()).rename('fvc8_weighted')
    ]).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: roi, scale: 30,
      maxPixels: 1e13, tileScale: 8
    });
    var wetArea = safeNumber(sums, 'wetland_area');
    var commonArea = safeNumber(sums, 'common_area');
    var ndvi7Mean = ee.Algorithms.If(commonArea.gt(0), safeNumber(sums, 'ndvi7_weighted').divide(commonArea), null);
    var ndvi8Mean = ee.Algorithms.If(commonArea.gt(0), safeNumber(sums, 'ndvi8_weighted').divide(commonArea), null);
    var fvc7Mean = ee.Algorithms.If(commonArea.gt(0), safeNumber(sums, 'fvc7_weighted').divide(commonArea), null);
    var fvc8Mean = ee.Algorithms.If(commonArea.gt(0), safeNumber(sums, 'fvc8_weighted').divide(commonArea), null);
    overlapRows.push(ee.Feature(null, {
      region: c.id, year: y, scale_m: 30,
      l7_scenes: n7, l8_scenes: n8,
      wetland_area_km2: wetArea,
      common_valid_area_km2: commonArea,
      common_valid_fraction: ee.Algorithms.If(wetArea.gt(0), commonArea.divide(wetArea), null),
      ndvi_l7: ndvi7Mean, ndvi_l8: ndvi8Mean,
      ndvi_l8_minus_l7: ee.Algorithms.If(commonArea.gt(0), ee.Number(ndvi8Mean).subtract(ee.Number(ndvi7Mean)), null),
      fvc_l7: fvc7Mean, fvc_l8: fvc8Mean,
      fvc_l8_minus_l7: ee.Algorithms.If(commonArea.gt(0), ee.Number(fvc8Mean).subtract(ee.Number(fvc7Mean)), null),
      soil_endpoint: c.soil, veg_endpoint: c.veg,
      comparison_support: 'SAME_YEAR_COMMON_VALID_WETLAND_PIXELS'
    }));
  });
});

var overlapOut = ee.FeatureCollection(overlapRows);
print('L7/L8 overlap validation; expected rows: 24', overlapOut.size());
Export.table.toDrive({
  collection: overlapOut,
  description: 'Stage5_QA_L7_L8_CommonSupport_2013_2020',
  folder: EXPORT_FOLDER,
  fileNamePrefix: 'Stage5_QA_L7_L8_CommonSupport_2013_2020',
  fileFormat: 'CSV'
});
