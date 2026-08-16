/**
 * ==============================================================================
 * trend_classification.js
 *
 * Two related spatial products, both built on a per-pixel linear trend of
 * FVC over the full 1985-2020 series:
 *
 *   1. A 5-level trend classification (severe degradation -> significant
 *      recovery), masked to the region's 2020 wetland extent.
 *   2. A 6-category area-function transition map that layers the trend
 *      classification on top of the wetland fate masks (lost / gained /
 *      persistent), producing categories like "persistent wetland,
 *      degraded" or "newly gained wetland, low cover".
 *
 * Method note: the per-pixel slope here is an ordinary least-squares (OLS)
 * linear fit (ee.Reducer.linearFit()), not Sen's slope. Sen's slope is used
 * for the final reported REGIONAL trend results — a 36-value annual time
 * series of the whole-region mean FVC per region, not a per-pixel
 * computation (see colab_analysis/). GEE's built-in linear-fit reducer used
 * here is OLS, applied per-pixel as a spatial screening tool serving a
 * different, coarser purpose than the regional Sen's-slope result. This
 * raster is therefore not the final trend-significance result — that
 * distinction should stay visible wherever this map is shown.
 *
 * The 5-level class thresholds (±0.001, ±0.005 slope per year) are fixed
 * empirical cut points, not derived from the data distribution. That's a
 * real limitation worth stating plainly rather than implying they were
 * calibrated.
 *
 * Requires: region_pipeline.js and regions_config.js already loaded
 * (provides regionPipelines, years36).
 * ==============================================================================
 */

var EXPORT_FOLDER = 'Wetland_FVC_Exports';

var TREND_CLASS_LABELS = {
  1: 'Severe Degradation', 2: 'Mild Degradation', 3: 'Stable',
  4: 'Mild Recovery', 5: 'Significant Recovery'
};

var SIX_CATEGORY_LABELS = {
  1: 'Wetland Lost', 2: 'Vegetation Degraded', 3: 'Basically Stable',
  4: 'Vegetation Improved', 5: 'New Low-Cover Wetland (<45%)', 6: 'New High-Cover Wetland (>=45%)'
};

/** Per-pixel OLS slope of FVC over the full 36-year series, computed in
 *  memory each time it's needed (not read from a previously exported
 *  Asset) — an earlier version read a placeholder Asset path that didn't
 *  exist, which is the simpler failure mode to avoid. */
function computeTrendSlope(pipeline) {
  var yearlyFVC = years36.map(function (year) {
    var fvcImg = pipeline.processIndices(year).all.select('FVC');
    return fvcImg.set('year', year).set('system:time_start', ee.Date.fromYMD(year, 6, 1).millis());
  });
  var fvcCollection = ee.ImageCollection(yearlyFVC);

  var fitInput = fvcCollection.map(function (img) {
    var yearBand = ee.Image.constant(img.get('year')).toFloat().rename('year');
    return img.addBands(yearBand);
  });

  return fitInput.select(['year', 'FVC']).reduce(ee.Reducer.linearFit()).select('scale').rename('FVC_slope');
}

/** Maps a continuous slope image to the 5-level class defined above. */
function classifySlope(slope) {
  return slope.expression(
    '(s < -0.005) ? 1 : (s < -0.001) ? 2 : (s <= 0.001) ? 3 : (s <= 0.005) ? 4 : 5',
    { s: slope }
  ).rename('TrendClass').toByte();
}

/** Product 1: 5-level trend classification raster + per-class area (km²).
 *  Takes the already-computed slope and trendClass images rather than
 *  recomputing them — the caller (the per-region loop at the bottom of
 *  this file) computes both once and passes them to both this function
 *  and exportSixCategoryMap(), consistent with the "don't recompute the
 *  expensive 36-year linear fit" principle stated above. classifySlope()
 *  itself is cheap (a pixel-wise expression, not a reduction), so calling
 *  it twice wouldn't have been a real performance problem — but doing so
 *  would have been inconsistent with that stated principle, and easy for
 *  a reviewer to notice and question. */
function exportTrendClassification(pipeline, regionName, slope, trendClass) {
  var mask2020 = pipeline.getWetlandMask(2020).selfMask();
  var trendClassMasked = trendClass.updateMask(mask2020);
  var slopeMasked = slope.updateMask(mask2020);

  Export.image.toDrive({
    image: trendClassMasked,
    description: regionName + '_FVC_TrendClass_5Level',
    folder: EXPORT_FOLDER, region: pipeline.roi, scale: CITY_SCALE, maxPixels: 1e13
  });
  Export.image.toDrive({
    image: slopeMasked.toFloat(),
    description: regionName + '_FVC_Slope_Raw',
    folder: EXPORT_FOLDER, region: pipeline.roi, scale: CITY_SCALE, maxPixels: 1e13
  });

  var pixelAreaKm2 = ee.Image.pixelArea().divide(1e6);
  var areaStats = pixelAreaKm2.addBands(trendClassMasked).reduceRegion({
    reducer: ee.Reducer.sum().group({ groupField: 1, groupName: 'class_id' }),
    geometry: pipeline.roi, scale: CITY_SCALE, maxPixels: 1e13, tileScale: 8
  });

  var labels = ee.Dictionary(TREND_CLASS_LABELS);
  var areaFeatures = ee.List(areaStats.get('groups')).map(function (d) {
    d = ee.Dictionary(d);
    var classId = ee.Number(d.get('class_id'));
    return ee.Feature(null, {
      region: regionName,
      class_id: classId,
      class_label: labels.get(classId.format()),
      area_km2: d.get('sum')
    });
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(areaFeatures),
    description: regionName + '_FVC_TrendClass_AreaStats',
    folder: EXPORT_FOLDER, fileFormat: 'CSV'
  });
}

/**
 * Product 2: 6-category area-function transition map, combining fate
 * (lost/gained/persistent between 1985 and 2020) with the trend class for
 * persistent wetland, and a 45% FVC threshold for newly gained wetland to
 * split "low-cover" from "high-cover":
 *   1 Wetland Lost              — wetland in 1985, not in 2020
 *   2 Vegetation Degraded       — persistent, trend class 1-2
 *   3 Basically Stable          — persistent, trend class 3
 *   4 Vegetation Improved       — persistent, trend class 4-5
 *   5 New Low-Cover Wetland     — gained, 2020 FVC < 45%
 *   6 New High-Cover Wetland    — gained, 2020 FVC >= 45%
 *
 * 45% threshold: corresponds to the boundary between "moderate-low" and
 * "moderate" vegetation cover in the 5-level classification of SL 190-2007
 * (中华人民共和国水利部, 《土壤侵蚀分类分级标准》 — a water-resources industry
 * standard, not a national GB/T standard): 0-30% / 30-45% / 45-60% / 60-75% /
 * 75-100%. This classification table is confirmed via a secondary academic
 * citation of the standard, not a direct reading of the primary standard
 * text — treat it as well-supported but not independently verified against
 * the original document.
 *
 * Cross-validated against wetland_transition_structure.js's transition
 * matrix — see docs/methodology_notes.md for the full three-round
 * diagnosis of an earlier ~1.7-2.2x discrepancy between the two, which
 * turned out to be a scope mismatch (this map counts ALL wetland change;
 * the transition matrix's core analysis counts only cropland + built-up
 * conversions) rather than a computation error in either script.
 */
function exportSixCategoryMap(pipeline, regionName, trendClass) {
  var mask1985 = pipeline.getWetlandMask(1985);
  var mask2020 = pipeline.getWetlandMask(2020);
  var fvc2020 = pipeline.processIndices(2020).all.select('FVC');

  var lost = mask1985.and(mask2020.not());
  var gained = mask1985.not().and(mask2020);
  var persistent = mask1985.and(mask2020);

  var persistentDegraded = persistent.and(trendClass.lte(2));
  var persistentStable = persistent.and(trendClass.eq(3));
  var persistentImproved = persistent.and(trendClass.gte(4));

  var gainedLowCover = gained.and(fvc2020.lt(0.45));
  var gainedHighCover = gained.and(fvc2020.gte(0.45));

  var sixClass = ee.Image(0)
    .where(lost, 1)
    .where(persistentDegraded, 2)
    .where(persistentStable, 3)
    .where(persistentImproved, 4)
    .where(gainedLowCover, 5)
    .where(gainedHighCover, 6)
    .rename('SixClass')
    .selfMask();

  var pixelAreaKm2 = ee.Image.pixelArea().divide(1e6);
  var areaStats = pixelAreaKm2.addBands(sixClass).reduceRegion({
    reducer: ee.Reducer.sum().group({ groupField: 1, groupName: 'class_id' }),
    geometry: pipeline.roi, scale: CITY_SCALE, maxPixels: 1e13, tileScale: 8
  });

  var labels = ee.Dictionary(SIX_CATEGORY_LABELS);
  var areaFeatures = ee.List(areaStats.get('groups')).map(function (d) {
    d = ee.Dictionary(d);
    var classId = ee.Number(d.get('class_id'));
    return ee.Feature(null, {
      region: regionName,
      class_id: classId,
      class_label: labels.get(classId.format()),
      area_km2: d.get('sum')
    });
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(areaFeatures),
    description: regionName + '_SixCategory_AreaStats',
    folder: EXPORT_FOLDER, fileFormat: 'CSV'
  });
}

// ---------------- Run for all three regions ----------------
Object.keys(regionPipelines).forEach(function (regionName) {
  var pipeline = regionPipelines[regionName];
  // Computed once, shared by both exports below — this is the expensive
  // step (36-year per-pixel linear fit), so it must not be recomputed.
  var slope = computeTrendSlope(pipeline);
  var trendClass = classifySlope(slope);

  exportTrendClassification(pipeline, regionName, slope, trendClass);
  exportSixCategoryMap(pipeline, regionName, trendClass);
  print('Submitted trend-classification + six-category exports for ' + regionName + '.');
});

print('All regions submitted. Run the tasks in the Tasks tab under the ' + EXPORT_FOLDER + ' folder.');
