/**
 * ==============================================================================
 * fvc_dynamic_endmember.js
 *
 * Core FVC outputs using the dynamic (per-year, per-region) endmember method.
 * Three export products per region:
 *   1. 36-year regional mean time series (dynamic-mask + fixed-1985-mask)
 *   2. City-level FVC at 8 five-year nodes (for the area-vs-quality
 *      four-quadrant analysis)
 *   3. Spatial FVC maps for 1985 and 2020 (30m)
 *
 * Requires: region_pipeline.js and regions_config.js already loaded in the
 * same GEE script (provides regionPipelines, cityCollections, nodeYears,
 * years36).
 * ==============================================================================
 */

var EXPORT_FOLDER = 'Wetland_FVC_Exports';

/** Product 1: 36-year regional mean FVC/EVI/NDMI, dynamic vs. fixed-1985 mask,
 *  plus the endmember values used each year (kept as columns for auditability —
 *  lets later analysis check whether a given year's endmembers look anomalous). */
function exportYearlyIndices(pipeline, regionName) {
  var yearlyFeatures = years36.map(function (year) {
    var result = pipeline.processIndices(year);
    var dynamicStats = result.dynamic.select(['NDVI', 'EVI', 'NDMI', 'FVC']).reduceRegion({
      reducer: ee.Reducer.mean(), geometry: pipeline.roi, scale: REGIONAL_SCALE, maxPixels: 1e13, tileScale: 8
    });
    var fixedStats = result.fixed.select(['NDVI', 'EVI', 'NDMI', 'FVC']).reduceRegion({
      reducer: ee.Reducer.mean(), geometry: pipeline.roi, scale: REGIONAL_SCALE, maxPixels: 1e13, tileScale: 8
    });
    return ee.Feature(null, {
      region: regionName,
      year: year,
      actual_imagery_year: result.actualImageryYear,
      FVC_Dynamic: dynamicStats.get('FVC'),
      EVI_Dynamic: dynamicStats.get('EVI'),
      NDMI_Dynamic: dynamicStats.get('NDMI'),
      FVC_Fixed1985: fixedStats.get('FVC'),
      EVI_Fixed1985: fixedStats.get('EVI'),
      NDMI_Fixed1985: fixedStats.get('NDMI'),
      NDVI_p5_soil: result.endmemberSoil,
      NDVI_p95_veg: result.endmemberVeg
    });
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(yearlyFeatures),
    description: regionName + '_Indices_36Years',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

/** Product 2: city-level FVC at the 8 five-year nodes — one row per city per
 *  node year, used for the area (wetland extent) vs. quality (FVC) four-
 *  quadrant comparison. Scale is 30m here (finer than the 500m used for
 *  regional means) because city polygons can be small enough that a coarser
 *  scale would miss them entirely. */
function exportCityNodeFVC(pipeline, cityFC, regionName) {
  var cityYearFeatures = nodeYears.map(function (year) {
    var fvcImg = pipeline.processIndices(year).dynamic.select('FVC');
    return fvcImg.reduceRegions({
      collection: cityFC, reducer: ee.Reducer.mean(), scale: CITY_SCALE, tileScale: 8
    }).map(function (f) {
      return f.set('year', year, 'region', regionName);
    });
  }).reduce(function (a, b) {
    return ee.FeatureCollection(a).merge(b);
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(cityYearFeatures),
    description: regionName + '_City_FVC_8Nodes',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

/** Product 3: spatial FVC maps for 1985 and 2020, 30m, dynamic-mask.
 *  These are the source rasters for QGIS visualization and for the trend-
 *  classification script (trend_classification.js), which derives a
 *  per-pixel slope from the full 36-year series rather than these two
 *  endpoint years alone. */
function exportSpatialFVC(pipeline, regionName) {
  var img1985 = pipeline.processIndices(1985).dynamic.select('FVC');
  var img2020 = pipeline.processIndices(2020).dynamic.select('FVC');

  Export.image.toDrive({
    image: img1985.toFloat(),
    description: regionName + '_FVC_1985_30m',
    folder: EXPORT_FOLDER, region: pipeline.roi, scale: CITY_SCALE, maxPixels: 1e13
  });
  Export.image.toDrive({
    image: img2020.toFloat(),
    description: regionName + '_FVC_2020_30m',
    folder: EXPORT_FOLDER, region: pipeline.roi, scale: CITY_SCALE, maxPixels: 1e13
  });
}

// ---------------- Run for all three regions ----------------
Object.keys(regionPipelines).forEach(function (regionName) {
  var pipeline = regionPipelines[regionName];
  var cityFC = cityCollections[regionName];

  exportYearlyIndices(pipeline, regionName);
  exportCityNodeFVC(pipeline, cityFC, regionName);
  exportSpatialFVC(pipeline, regionName);

  print('Submitted 4 export tasks for ' + regionName + ' (yearly indices, city nodes, FVC 1985, FVC 2020).');
});

print('All regions submitted. Run the tasks in the Tasks tab under the ' + EXPORT_FOLDER + ' folder.');
