/**
 * ==============================================================================
 * wetland_type_fvc.js
 *
 * Breaks FVC down by the 7 specific GLC_FCS30D wetland subtypes (report
 * section 3.11), rather than treating "wetland" as one undifferentiated
 * mask as the other scripts do. Three snapshot years (1985 / 2000 / 2020)
 * rather than the full 36-year series — this is a lighter, lower-risk
 * addition run late in the project, not part of the core trend analysis.
 *
 * Uses getRawLandCover() (specific class codes) rather than
 * getWetlandMask() (binary wetland/not) — the binary mask can't
 * distinguish Mangrove from Swamp, which is the whole point here.
 *
 * Requires: region_pipeline.js and regions_config.js already loaded
 * (provides regionPipelines, and WETLAND_TYPE_NAMES which this script
 * reuses rather than redeclaring — see region_pipeline.js for why that
 * consolidation matters).
 * ==============================================================================
 */

var EXPORT_FOLDER = 'Wetland_FVC_Exports';
var SNAPSHOT_YEARS = [1985, 2000, 2020];

function exportByWetlandType(pipeline, regionName) {
  var rows = [];

  SNAPSHOT_YEARS.forEach(function (year) {
    var fvcImg = pipeline.processIndices(year).all.select('FVC');
    var rawLandCover = pipeline.getRawLandCover(year);

    Object.keys(WETLAND_TYPE_NAMES).forEach(function (codeStr) {
      var code = parseInt(codeStr, 10);
      var typeMask = rawLandCover.eq(code);
      var stat = fvcImg.updateMask(typeMask).reduceRegion({
        reducer: ee.Reducer.mean(), geometry: pipeline.roi, scale: REGIONAL_SCALE, maxPixels: 1e13, tileScale: 8
      });
      rows.push(ee.Feature(null, {
        region: regionName,
        year: year,
        wetland_code: code,
        wetland_type: WETLAND_TYPE_NAMES[code],
        FVC_mean: stat.get('FVC')
      }));
    });
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(rows),
    description: regionName + '_FVC_ByWetlandType',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

// ---------------- Run for all three regions ----------------
Object.keys(regionPipelines).forEach(function (regionName) {
  exportByWetlandType(regionPipelines[regionName], regionName);
  print('Submitted by-wetland-type FVC export for ' + regionName + '.');
});

print('All regions submitted. Run the tasks in the Tasks tab under the ' + EXPORT_FOLDER + ' folder.');
