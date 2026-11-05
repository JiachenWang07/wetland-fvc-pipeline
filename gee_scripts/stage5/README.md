# Stage 5 final reporting workflow

`stage5_final_method_qa.js` is the reporting-standard GEE script used to produce the aggregate tables under `outputs/stage5_final/`.

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
