/**
 * ==============================================================================
 * wetland_transition_structure.js
 *
 * Independent of the FVC analysis line (fvc_*.js, wetland_fate_group.js,
 * trend_classification.js) — this script only needs wetland masks and raw
 * land-cover codes, not vegetation indices, so it runs as its own export
 * batch even though it shares the same pipelines.
 *
 * Two products per region:
 *   1. Transition structure: for each of the 7 adjacent 5-year intervals,
 *      what specific land-cover class did lost wetland convert INTO, and
 *      what specific land-cover class did gained wetland convert FROM.
 *      This is the finer-grained counterpart to the binary wetland mask —
 *      it answers "lost to what" rather than just "lost or not".
 *   2. City-level wetland area at the 8 five-year nodes, used alongside
 *      the FVC line's city-level FVC (fvc_dynamic_endmember.js) for the
 *      area-vs-quality four-quadrant analysis.
 *
 * Cross-check note: water body (class 210) typically accounts for the
 * large majority of raw transition-matrix totals (a known artifact —
 * suspected classification drift at wetland/water boundaries in
 * GLC_FCS30D, not real large-scale wetland-to-water conversion). Any
 * downstream analysis of this CSV should filter out class 210 before
 * interpreting "what wetland converted to", and the core cropland +
 * built-up conversion figures should be read as the higher-confidence
 * subset — not the full unfiltered total. See docs/methodology_notes.md
 * for the reasoning behind this filter and how it was cross-validated
 * against the six-category map in trend_classification.js.
 *
 * Requires: region_pipeline.js and regions_config.js already loaded
 * (provides regionPipelines, cityCollections, nodeYears, WETLAND_CODES,
 * and WETLAND_TYPE_NAMES — this script builds its class dictionary from
 * those rather than restating the 181-187 mapping a third time; see
 * region_pipeline.js for why that consolidation matters).
 * ==============================================================================
 */

var EXPORT_FOLDER = 'Wetland_FVC_Exports';
var WETLAND_CODES_LIST = ee.List(WETLAND_CODES);

// Full GLC_FCS30D class dictionary, used to label whatever class wetland
// pixels converted to/from — not just "wetland vs. not". Non-wetland
// classes are specific to this script (transition analysis is the only
// place they're needed); the wetland subtype names are pulled from
// WETLAND_TYPE_NAMES so there is exactly one place that mapping lives.
var NON_WETLAND_CLASS_NAMES = {
  10: 'Rainfed Cropland', 11: 'Herbaceous Cover Cropland', 12: 'Tree/Shrub Cover Cropland', 20: 'Irrigated Cropland',
  51: 'Open Evergreen Broadleaved Forest', 52: 'Closed Evergreen Broadleaved Forest',
  61: 'Open Deciduous Broadleaved Forest', 62: 'Closed Deciduous Broadleaved Forest',
  71: 'Open Evergreen Needle-Leaved Forest', 72: 'Closed Evergreen Needle-Leaved Forest',
  81: 'Open Deciduous Needle-Leaved Forest', 82: 'Closed Deciduous Needle-Leaved Forest',
  91: 'Open Mixed Leaf Forest', 92: 'Closed Mixed Leaf Forest',
  120: 'Shrubland', 121: 'Evergreen Shrubland', 122: 'Deciduous Shrubland',
  130: 'Grassland', 140: 'Lichens and Mosses', 150: 'Sparse Vegetation',
  152: 'Sparse Shrubland', 153: 'Sparse Herbaceous',
  190: 'Impervious Surface', 200: 'Bare Land', 201: 'Consolidated Bare Land', 202: 'Unconsolidated Bare Land',
  210: 'Water Body', 220: 'Permanent Snow/Ice'
};

function mergeDictionaries(a, b) {
  var merged = {};
  Object.keys(a).forEach(function (k) { merged[k] = a[k]; });
  Object.keys(b).forEach(function (k) { merged[k] = b[k]; });
  return merged;
}

var LANDCOVER_CLASS_NAMES = ee.Dictionary(mergeDictionaries(WETLAND_TYPE_NAMES, NON_WETLAND_CLASS_NAMES));

/** Product 1: for each interval, what wetland transitioned into (direction
 *  'out') and what became wetland from (direction 'in'), broken down by
 *  the specific land-cover class involved. */
function exportTransitionStructure(pipeline, regionName) {
  var rows = [];

  for (var i = 0; i < nodeYears.length - 1; i++) {
    var yA = nodeYears[i];
    var yB = nodeYears[i + 1];

    var lcA = pipeline.getRawLandCover(yA);
    var lcB = pipeline.getRawLandCover(yB);
    var wetA = lcA.remap(WETLAND_CODES_LIST, ee.List.repeat(1, WETLAND_CODES.length), 0);
    var wetB = lcB.remap(WETLAND_CODES_LIST, ee.List.repeat(1, WETLAND_CODES.length), 0);

    // out: wetland at yA, not wetland at yB -> record what it became (lcB)
    var outMask = wetA.eq(1).and(wetB.eq(0));
    var outStats = summarizeByClass(lcB.updateMask(outMask), pipeline.roi);
    rows.push(labelDirection(outStats, regionName, yA, yB, 'out'));

    // in: not wetland at yA, wetland at yB -> record what it came from (lcA)
    var inMask = wetA.eq(0).and(wetB.eq(1));
    var inStats = summarizeByClass(lcA.updateMask(inMask), pipeline.roi);
    rows.push(labelDirection(inStats, regionName, yA, yB, 'in'));
  }

  Export.table.toDrive({
    collection: ee.FeatureCollection(rows).flatten(),
    description: regionName + '_WetlandTransitionStructure',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

/** Groups a class-code image by pixel area (km²) within roi. */
function summarizeByClass(classImage, roi) {
  return ee.Image.pixelArea().divide(1e6).addBands(classImage).reduceRegion({
    reducer: ee.Reducer.sum().group({ groupField: 1, groupName: 'class' }),
    geometry: roi, scale: CITY_SCALE, maxPixels: 1e13, tileScale: 8
  });
}

/** Converts the grouped reduceRegion output into labeled Features. */
function labelDirection(stats, regionName, yA, yB, direction) {
  return ee.FeatureCollection(ee.List(stats.get('groups')).map(function (d) {
    d = ee.Dictionary(d);
    var code = ee.Number(d.get('class'));
    return ee.Feature(null, {
      region: regionName,
      interval: yA + '-' + yB,
      direction: direction,
      converted_class_code: code,
      converted_class_name: LANDCOVER_CLASS_NAMES.get(code, 'Unknown'),
      area_km2: d.get('sum')
    });
  }));
}

/** Product 2: city-level wetland area (km²) at the 8 five-year nodes —
 *  pairs with exportCityNodeFVC() in fvc_dynamic_endmember.js for the
 *  area-vs-quality four-quadrant analysis. */
function exportCityWetlandArea(pipeline, cityFC, regionName) {
  var rows = nodeYears.map(function (year) {
    var wetlandMask = pipeline.getWetlandMask(year);
    var areaImg = ee.Image.pixelArea().divide(1e6).updateMask(wetlandMask).rename('wetland_area_km2');
    return areaImg.reduceRegions({
      collection: cityFC, reducer: ee.Reducer.sum(), scale: CITY_SCALE, tileScale: 8
    }).map(function (f) {
      return f.set('year', year, 'region', regionName);
    });
  }).reduce(function (a, b) {
    return ee.FeatureCollection(a).merge(b);
  });

  Export.table.toDrive({
    collection: ee.FeatureCollection(rows),
    description: regionName + '_City_WetlandArea_8Nodes',
    folder: EXPORT_FOLDER,
    fileFormat: 'CSV'
  });
}

// ---------------- Run for all three regions ----------------
Object.keys(regionPipelines).forEach(function (regionName) {
  var pipeline = regionPipelines[regionName];
  var cityFC = cityCollections[regionName];

  exportTransitionStructure(pipeline, regionName);
  exportCityWetlandArea(pipeline, cityFC, regionName);

  print('Submitted transition-structure + city-wetland-area exports for ' + regionName + '.');
});

print('All regions submitted (' + Object.keys(regionPipelines).length * 2 + ' tasks). ' +
  'Run them in the Tasks tab under the ' + EXPORT_FOLDER + ' folder.');
