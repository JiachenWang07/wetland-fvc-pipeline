# Reviewed Stage 5 workflow

`stage5_final_method_qa.js` is the reviewed GEE script used to produce the aggregate tables under `outputs/stage5_final/`.

The script exports:

- regional annual 30 m FVC tables for YRD, GBA, and BTH;
- city FVC and wetland area for eight node years;
- 30/100/250/500 m scale comparisons;
- annual wetland NDVI percentile diagnostics against the fixed endpoints.

Key differences from the historical combined pipeline:

- strict QA masking, including saturation;
- median seasonal composites;
- no neighboring-year fallback;
- fixed regional endpoints for the primary FVC scale;
- pixelwise FVC before effective-area-weighted aggregation;
- missing years retained as missing.

The script still depends on the project's private Chinese administrative-boundary asset. Replace the `china` FeatureCollection with an equivalent city-level boundary dataset before running under another account.

## Cross-sensor validation

After the main Stage 5 block is loaded, append and run `sensor_overlap_validation.js`. It exports 24 same-year region–year comparisons for 2013–2020, using separate Landsat 7 and Landsat 8 median composites on their common valid wetland pixels. This is the preferred sensor diagnostic because it does not mistake different years or different valid-pixel footprints for a sensor effect.

Summarize the resulting CSV with:

```bash
python python_analysis/src/sensor_overlap_analysis.py \
  Stage5_QA_L7_L8_CommonSupport_2013_2020.csv \
  outputs/stage5_final/analysis/sensor_overlap_summary.csv
```

The comparison is diagnostic. A harmonization correction should not be applied unless the direction and magnitude of the difference are stable across years and regions and remain meaningful after coverage checks.
