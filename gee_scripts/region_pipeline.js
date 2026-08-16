/**
 * ==============================================================================
 * region_pipeline.js
 *
 * Factory function that builds a fully self-contained processing pipeline for
 * one region (YRD / GBA / BTH). Each call to makeRegionPipeline() creates a
 * new closure — the `roi` and all derived state are locked inside that closure
 * at call time, so pipelines for different regions can never leak into each
 * other, even if a global variable is later reassigned elsewhere in the script.
 *
 * This replaces an earlier architecture where all regions shared the same
 * top-level `roi` variable and a single set of functions. That version caused
 * a real bug: after computing YRD, reassigning `roi` to the GBA boundary and
 * re-running the same functions sometimes still evaluated against YRD's
 * extent, because a function defined earlier had already captured the old
 * `roi` in its closure. The factory pattern makes that class of bug
 * structurally impossible — every function here reads only the `roi`
 * parameter this particular pipeline was built with.
 *
 * Usage:
 *   var pipeYRD = makeRegionPipeline(roi_YRD, 5, 10);
 *   var pipeGBA = makeRegionPipeline(roi_GBA, 4, 11);
 *   var pipeBTH = makeRegionPipeline(roi_BTH, 5, 9);
 *
 * Requires: roi_YRD / roi_GBA / roi_BTH from regions_config.js to already be
 * defined in the same GEE script (GEE has no module import system; scripts
 * in this repo are meant to be read together, not executed as separate
 * files).
 * ==============================================================================
 */

var WETLAND_CODES = [181, 182, 183, 184, 185, 186, 187]; // GLC_FCS30D wetland subtypes

// Single source of truth for wetland-subtype labels. Previously this exact
// 181-187 -> name mapping was independently declared a second time in
// wetland_type_fvc.js and embedded a third time inside the larger land-cover
// dictionary in wetland_transition_structure.js — three copies that could
// silently drift out of sync if one were edited and the others weren't.
// Both of those files now build on this constant instead of restating it.
var WETLAND_TYPE_NAMES = {
  181: 'Swamp', 182: 'Wetland Meadow', 183: 'Floodplain Wetland',
  184: 'Saline Wetland', 185: 'Mangrove', 186: 'Salt Marsh', 187: 'Tidal Flat'
};

// Named scale constants, used across all export scripts instead of bare
// numbers. REGIONAL_SCALE (500m) is used for whole-region mean statistics,
// where the coarser scale is a deliberate speed/cost tradeoff and doesn't
// affect the result at that spatial aggregation. CITY_SCALE (30m) is used
// wherever individual city polygons are the unit of analysis — smaller
// cities were previously found to be silently dropped or biased at 500m —
// and is reused for raster exports (spatial FVC maps, trend classification)
// since 30m also happens to be Landsat's native pixel resolution, which is
// the same "don't lose fine spatial detail" reasoning applied to a
// different kind of output.
var REGIONAL_SCALE = 500;
var CITY_SCALE = 30;

/**
 * @param {ee.Geometry} roi - region boundary, dissolved and simplified upstream
 * @param {number} startMonth - growing-season window start month (region-specific)
 * @param {number} endMonth - growing-season window end month (region-specific)
 * @return {Object} pipeline - see the `return` block at the bottom for the
 *   full list of functions this pipeline exposes.
 */
function makeRegionPipeline(roi, startMonth, endMonth) {

  // ---- GLC_FCS30D land-cover sources, clipped once per region ----
  var imgAnnual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual')
    .mosaic().clip(roi);
  var img5Year = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five-years-map')
    .mosaic().clip(roi);

  // Per-year cache for the annual composite. getAnnualCompositeRobust(year)
  // was previously called independently by several export scripts for the
  // same year within a single run (dynamic-endmember export, fixed-endmember
  // export, and the trend-slope computation all need, e.g., year 2020),
  // each time rebuilding the same filter+merge+fallback computation graph
  // from scratch. Caching by year avoids that repeated graph construction
  // within a single pipeline's lifetime.
  var compositeCache = {};

  /**
   * GLC_FCS30D ships two products: a 5-year-interval map for 1985-1995,
   * and an annual map from 2000 onward. This resolves a requested year to
   * the correct source image + band.
   */
  function getBandInfo(year) {
    if (year < 2000) {
      var epochYear = (year < 1988) ? 1985 : (year < 1993) ? 1990 : 1995;
      return { img: img5Year, band: 'b' + ((epochYear - 1985) / 5 + 1) };
    }
    return { img: imgAnnual, band: 'b' + (year - 2000 + 1) };
  }

  /** Binary wetland mask (1 = wetland, 0 = not) for a given year. */
  function getWetlandMask(year) {
    var info = getBandInfo(year);
    return info.img.select(info.band)
      .remap(WETLAND_CODES, ee.List.repeat(1, WETLAND_CODES.length), 0)
      .rename('wetland_mask');
  }

  /** Raw GLC_FCS30D class code (not binarized) — used for transition analysis
   *  and per-wetland-type breakdowns, where the specific subtype matters. */
  function getRawLandCover(year) {
    var info = getBandInfo(year);
    return info.img.select(info.band).rename('landcover_class');
  }

  /**
   * Three-way fate classification between two years:
   *   persistent — wetland at both yA and yB
   *   lost       — wetland at yA, not at yB
   *   gained     — not wetland at yA, wetland at yB
   */
  function getFateMasks(yA, yB) {
    var maskA = getWetlandMask(yA);
    var maskB = getWetlandMask(yB);
    return {
      persistent: maskA.and(maskB).selfMask(),
      lost: maskA.and(maskB.not()).selfMask(),
      gained: maskA.not().and(maskB).selfMask()
    };
  }

  // ---- Landsat surface-reflectance prep (cloud mask + scale to reflectance) ----
  function prepSR_L57(image) {
    var qa = image.select('QA_PIXEL');
    var clear = qa.bitwiseAnd(1 << 4).eq(0).and(qa.bitwiseAnd(1 << 3).eq(0));
    var scaled = image.select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'])
      .multiply(0.0000275).add(-0.2);
    return scaled.rename(['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2'])
      .updateMask(clear)
      .copyProperties(image, ['system:time_start']);
  }

  function prepSR_L8(image) {
    var qa = image.select('QA_PIXEL');
    var clear = qa.bitwiseAnd(1 << 4).eq(0).and(qa.bitwiseAnd(1 << 3).eq(0));
    var scaled = image.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])
      .multiply(0.0000275).add(-0.2);
    return scaled.rename(['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2'])
      .updateMask(clear)
      .copyProperties(image, ['system:time_start']);
  }

  /** Landsat 5/7 before 2013, Landsat 8 from 2013 onward, filtered to [start, end]. */
  function fetchCollection(year, monthStart, monthEnd) {
    var start = ee.Date.fromYMD(year, monthStart, 1);
    var end = ee.Date.fromYMD(year, monthEnd, 28);
    if (year < 2013) {
      var l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
        .filterBounds(roi).filterDate(start, end).map(prepSR_L57);
      var l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
        .filterBounds(roi).filterDate(start, end).map(prepSR_L57);
      return l5.merge(l7);
    }
    return ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
      .filterBounds(roi).filterDate(start, end).map(prepSR_L8);
  }

  /**
   * Annual composite with a 4-level fallback, needed because some
   * region/year combinations (e.g. GBA 1985-1986) have zero usable Landsat
   * scenes within the growing-season window:
   *   1. this year, growing season
   *   2. this year, full year
   *   3. next year, growing season
   *   4. previous year, growing season
   * The image carries an `actual_imagery_year` property recording which
   * level was used, so downstream analysis can flag substituted years
   * rather than silently treating them as the requested year.
   */
  function getAnnualCompositeRobust(year) {
    if (compositeCache[year]) {
      return compositeCache[year];
    }

    var thisYearSeason = fetchCollection(year, startMonth, endMonth);
    var thisYearFull = fetchCollection(year, 1, 12);
    var nextYearSeason = fetchCollection(year + 1, startMonth, endMonth);
    var prevYearSeason = fetchCollection(year - 1, startMonth, endMonth);

    var n0 = thisYearSeason.size();
    var n1 = thisYearFull.size();
    var n2 = nextYearSeason.size();
    var n3 = prevYearSeason.size();

    var chosen = ee.ImageCollection(ee.Algorithms.If(n0.gt(0), thisYearSeason,
      ee.Algorithms.If(n1.gt(0), thisYearFull,
      ee.Algorithms.If(n2.gt(0), nextYearSeason,
      ee.Algorithms.If(n3.gt(0), prevYearSeason, thisYearFull)))));

    var actualYear = ee.Algorithms.If(n0.gt(0), year,
      ee.Algorithms.If(n1.gt(0), year,
      ee.Algorithms.If(n2.gt(0), year + 1,
      ee.Algorithms.If(n3.gt(0), year - 1, year))));

    var composite = ee.Image(chosen.median())
      .clip(roi)
      .set('year', year)
      .set('actual_imagery_year', actualYear);

    compositeCache[year] = composite;
    return composite;
  }

  /**
   * Per-year, per-region dynamic endmembers: the 5th/95th percentile of NDVI
   * across the whole region stand in for "pure soil" and "pure vegetation"
   * for that specific year's imagery. This avoids assuming a single fixed
   * NDVI value holds across 36 years of varying sensors and atmospheric
   * conditions. The tradeoff — endmembers themselves can be noisy in years
   * with few clear pixels — is why a fixed-endmember version exists
   * separately for sensitivity validation (see fvc_fixed_endmember.js).
   */
  function getDynamicEndpoints(ndviImage) {
    var percentiles = ndviImage.reduceRegion({
      reducer: ee.Reducer.percentile([5, 95]),
      geometry: roi, scale: REGIONAL_SCALE, bestEffort: true, tileScale: 8, maxPixels: 1e13
    });
    return {
      soil: ee.Number(percentiles.get('NDVI_p5')),
      veg: ee.Number(percentiles.get('NDVI_p95'))
    };
  }

  // Per-year cache for processIndices — this is the function actually
  // called repeatedly (with overlapping years) across fvc_dynamic_endmember.js,
  // trend_classification.js, wetland_fate_group.js, and wetland_type_fvc.js.
  // Caching the composite alone (above) helps, but the NDVI/EVI/FVC band
  // math and the endmember percentile reduction were still being rebuilt
  // on every call; this cache avoids that too.
  var indicesCache = {};

  /**
   * Computes NDVI / EVI / NDMI / FVC for a given year and returns three
   * masked variants:
   *   all       — no wetland mask (needed for fate-group analysis, where
   *               "lost" pixels are no longer wetland in the mask year)
   *   dynamic   — masked to that year's wetland extent
   *   fixed     — masked to the fixed 1985 wetland baseline
   */
  function processIndices(year) {
    if (indicesCache[year]) {
      return indicesCache[year];
    }

    var rawImg = ee.Image(getAnnualCompositeRobust(year));
    var actualYear = rawImg.get('actual_imagery_year');

    var ndvi = rawImg.normalizedDifference(['NIR', 'RED']).rename('NDVI');
    var evi = rawImg.expression(
      '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
      { NIR: rawImg.select('NIR'), RED: rawImg.select('RED'), BLUE: rawImg.select('BLUE') }
    ).clamp(-1, 2).rename('EVI');
    var ndmi = rawImg.normalizedDifference(['NIR', 'SWIR1']).rename('NDMI');

    var endpoints = getDynamicEndpoints(ndvi);
    var fvc = ndvi.subtract(ee.Image.constant(endpoints.soil))
      .divide(ee.Image.constant(endpoints.veg).subtract(ee.Image.constant(endpoints.soil)))
      .clamp(0, 1).rename('FVC');

    var allIndices = ndvi.addBands([evi, ndmi, fvc]);
    var dynamicMask = getWetlandMask(year).selfMask();
    var fixedMask = getWetlandMask(1985).selfMask();

    var result = {
      all: allIndices.set('year', year),
      dynamic: allIndices.updateMask(dynamicMask).set('year', year),
      fixed: allIndices.updateMask(fixedMask).set('year', year),
      endmemberSoil: endpoints.soil,
      endmemberVeg: endpoints.veg,
      actualImageryYear: actualYear
    };

    indicesCache[year] = result;
    return result;
  }

  return {
    roi: roi,
    getWetlandMask: getWetlandMask,
    getRawLandCover: getRawLandCover,
    getFateMasks: getFateMasks,
    getAnnualCompositeRobust: getAnnualCompositeRobust,
    processIndices: processIndices
  };
}
