/**
 * ==============================================================================
 * wetland_fate_group.js
 *
 * For each of the 7 adjacent 5-year intervals (1985-1990, ..., 2015-2020),
 * classifies every pixel into persistent / gained / lost wetland (see
 * getFateMasks() in region_pipeline.js) and computes each group's mean FVC.
 *
 * Year convention (the one detail in this script most worth reading
 * carefully):
 *   - persistent, gained -> FVC measured at yB (the interval's end year),
 *     since these pixels ARE wetland at yB.
 *   - lost -> FVC measured at yA (the interval's START year), NOT yB.
 *     A "lost" pixel is by definition no longer wetland at yB, so
 *     measuring it at yB would describe whatever land cover replaced the
 *     wetland (cropland, built-up, etc.), not the wetland itself. The
 *     question this analysis asks is "what did FVC look like on wetlands
 *     right before they were converted?" — which only yA can answer.
 *
 * An earlier version of this script used yB for all three groups. Under
 * yB + the dynamic wetland mask, "lost" pixels are masked out by
 * definition, so the group came back empty. A later fix removed the mask
 * (using the unmasked `.all` index) but still measured at yB — this ran
 * without error, but silently measured the wrong thing: FVC of the new
 * land cover, not of the wetland being lost. Switching lost to yA is the
 * version used here; the underlying finding (lost wetlands generally were
 * not lower-FVC than persistent ones before conversion) held up and, if
 * anything, came out stronger after the fix — this fix did not manufacture
 * the result, so we're not reporting a difference that only exists because
 * of tuning.
 *
 * Requires: region_pipeline.js and regions_config.js already loaded
 * (provides regionPipelines, nodeYears).
 * ==============================================================================
 */

var EXPORT_FOLDER = 'Wetland_FVC_Exports';

function exportFateGroupFVC(pipeline, regionName) {
  var fateFeatures = [];

  for (var i = 0; i < nodeYears.length - 1; i++) {
    var yA = nodeYears[i];
    var yB = nodeYears[i + 1];
    var fate = pipeline.getFateMasks(yA, yB);

    // persistent/gained: measured at yB (they are wetland at yB)
    var indicesAtB = pipeline.processIndices(yB).all.select('FVC');
    // lost: measured at yA (they were wetland at yA, not at yB)
    var indicesAtA = pipeline.processIndices(yA).all.select('FVC');

    var groups = [
      { type: 'persistent', img: indicesAtB },
      { type: 'gained', img: indicesAtB },
      { type: 'lost', img: indicesAtA }
    ];

    groups.forEach(function (group) {
      var stat = group.img.updateMask(fate[group.type]).reduceRegion({
        reducer: ee.Reducer.mean(), geometry: pipeline.roi, scale: REGIONAL_SCALE, maxPixels: 1e13, tileScale: 8
      });
      fateFeatures.push(ee.Feature(null, {
        region: regionName,
        interval: yA + '-' + yB,
        type: group.type,
        FVC_mean: stat.get('FVC')
      }));
    });
  }

  Export.table.toDrive({
    collection: ee.FeatureCollection(fateFeatures),
    description: regionName + '_FateGroup_FVC',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

// ---------------- Run for all three regions ----------------
Object.keys(regionPipelines).forEach(function (regionName) {
  exportFateGroupFVC(regionPipelines[regionName], regionName);
  print('Submitted fate-group FVC export for ' + regionName + '.');
});

print('All regions submitted. Run the tasks in the Tasks tab under the ' + EXPORT_FOLDER + ' folder.');
