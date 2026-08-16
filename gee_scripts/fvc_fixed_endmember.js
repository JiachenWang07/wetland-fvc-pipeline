/**
 * ==============================================================================
 * fvc_fixed_endmember.js
 *
 * Sensitivity check for the dynamic-endmember method used in
 * fvc_dynamic_endmember.js: recomputes FVC using ONE fixed endmember pair
 * per region (that region's 36-year mean of the dynamic endmembers) instead
 * of a fresh endmember every year. If the resulting trend agrees with the
 * dynamic-endmember version, the trend is unlikely to be an artifact of
 * endmember drift. Where they disagree, that disagreement is itself a
 * finding worth reporting (see docs/methodology_notes.md — this is why the
 * full-period 1985-2020 Mann-Kendall test was ultimately abandoned in favor
 * of segmented testing).
 *
 * FIXED_ENDMEMBERS values are each region's 36-year mean of NDVI_p5_soil /
 * NDVI_p95_veg, computed from the CSV output of fvc_dynamic_endmember.js
 * (in Colab: indices_df['NDVI_p5_soil'].mean(), etc.) — not arbitrary
 * constants.
 *
 * Requires: region_pipeline.js and regions_config.js already loaded
 * (provides regionPipelines, cityCollections, nodeYears, years36).
 * ==============================================================================
 */

var EXPORT_FOLDER = 'Wetland_FVC_Exports';

var FIXED_ENDMEMBERS = {
  YRD: { soil: 0.0905, veg: 0.7897 },
  GBA: { soil: 0.1351, veg: 0.7911 },
  BTH: { soil: 0.2080, veg: 0.7539 }
};

/** Region-level 36-year FVC time series using the fixed endmember pair. */
function exportRegionFixedFVC(pipeline, regionName) {
  var endmember = FIXED_ENDMEMBERS[regionName];

  var rows = years36.map(function (year) {
    var rawImg = pipeline.getAnnualCompositeRobust(year);
    var ndvi = rawImg.normalizedDifference(['NIR', 'RED']).rename('NDVI');
    var fvcFixed = ndvi.subtract(ee.Number(endmember.soil))
      .divide(ee.Number(endmember.veg).subtract(ee.Number(endmember.soil)))
      .clamp(0, 1).rename('FVC_Fixed');

    var dynamicMask = pipeline.getWetlandMask(year).selfMask();
    var stat = fvcFixed.updateMask(dynamicMask).reduceRegion({
      reducer: ee.Reducer.mean(), geometry: pipeline.roi, scale: REGIONAL_SCALE, maxPixels: 1e13, tileScale: 8
    });

    return ee.Feature(null, {
      region: regionName,
      year: year,
      FVC_FixedEndmember_Pixel: stat.get('FVC_Fixed')
    });
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(rows),
    description: regionName + '_FVC_FixedEndmember_PixelLevel',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

/** City-level FVC at the 8 five-year nodes using the fixed endmember pair —
 *  the fixed-endmember counterpart to exportCityNodeFVC() in
 *  fvc_dynamic_endmember.js. Used to re-verify the area-vs-quality
 *  four-quadrant result under a method that cannot be accused of drifting
 *  endmembers between years. */
function exportCityFixedFVC(pipeline, cityFC, regionName) {
  var endmember = FIXED_ENDMEMBERS[regionName];

  var cityYearFeatures = nodeYears.map(function (year) {
    var rawImg = pipeline.getAnnualCompositeRobust(year);
    var ndvi = rawImg.normalizedDifference(['NIR', 'RED']).rename('NDVI');
    var fvcFixed = ndvi.subtract(ee.Number(endmember.soil))
      .divide(ee.Number(endmember.veg).subtract(ee.Number(endmember.soil)))
      .clamp(0, 1).rename('FVC_Fixed');

    var dynamicMask = pipeline.getWetlandMask(year).selfMask();
    var maskedFvc = fvcFixed.updateMask(dynamicMask);

    return maskedFvc.reduceRegions({
      collection: cityFC, reducer: ee.Reducer.mean(), scale: CITY_SCALE, tileScale: 8
    }).map(function (f) {
      return f.set('year', year, 'region', regionName);
    });
  }).reduce(function (a, b) {
    return ee.FeatureCollection(a).merge(b);
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(cityYearFeatures),
    description: regionName + '_City_FixedFVC_8Nodes',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

// ---------------- Run for all three regions ----------------
Object.keys(regionPipelines).forEach(function (regionName) {
  var pipeline = regionPipelines[regionName];
  var cityFC = cityCollections[regionName];

  exportRegionFixedFVC(pipeline, regionName);
  exportCityFixedFVC(pipeline, cityFC, regionName);

  print('Submitted 2 fixed-endmember export tasks for ' + regionName + '.');
});

print('All regions submitted. Run the tasks in the Tasks tab under the ' + EXPORT_FOLDER + ' folder.');
