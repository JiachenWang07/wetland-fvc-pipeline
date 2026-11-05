# Stage 5 30 m Results Update and Repository Audit

## Purpose

This update aligns the public repository with the method and results used in the 2026 completion report. The earlier repository remains useful as a record of pipeline development, debugging, and historical validation, but several earlier defaults are no longer the reporting standard.

## Current reporting standard

- Landsat Collection 2 Level 2 surface reflectance
- QA masking for fill, dilated cloud, cirrus, cloud, cloud shadow, snow, and radiometric saturation
- regional growing-season median composite
- no adjacent-year image substitution
- pixelwise FVC calculation clipped to 0–1
- fixed regional endmembers for the primary time series
- 30 m effective-area-weighted regional and city statistics
- missing observations retained as missing
- trend analysis split at the 2013 sensor transition
- dynamic endmembers used as a sensitivity comparison rather than the primary reporting scale

## Repository assessment

| Existing result or component | Decision | Reason |
| --- | --- | --- |
| Regional pipeline factory and region isolation | Keep | The factory design prevents cross-region state leakage and remains sound. |
| Landsat and GLC-FCS30D data sources | Keep | These are unchanged in the final workflow. |
| Existing 500 m regional CSVs | Keep as legacy evidence | They document the earlier workflow but are not interchangeable with the final 30 m results. |
| Dynamic-endmember regional time series | Keep as sensitivity evidence | Dynamic endpoints can absorb part of the interannual signal. The final report uses fixed endpoints as the primary scale. |
| Adjacent-year image fallback | Retire from final reporting | The final workflow preserves missing years instead of substituting neighboring years. |
| Earlier cloud mask using only cloud and shadow bits | Replace | The Stage 5 mask also removes fill, dilated cloud, cirrus, snow, and saturated pixels. |
| Full-period or 2005-break trend narrative | Replace | The final analysis separates 1985–2012 and 2013–2020 because of the Landsat sensor transition. |
| Five-level per-pixel OLS trend map | Do not use as a headline final result | It lacks a uniform minimum-observation rule and is masked to 2020 wetland extent. |
| Six-category map and historical validation | Keep as historical validation | The raster/Python comparison is valid for that workflow, but it is not the core evidence for the final 30 m report. |
| Wetland-subtype FVC means | Keep as exploratory | The historical table lacks subtype area, valid area, valid fraction, and pixel count. |
| 2020 spatial FVC display | Keep with a clear label | It is a 120 m display product and does not replace the 30 m statistical tables. |
| Sankey and transition-structure presentation | Reuse the visual form | The visual form is effective, but interpretations must acknowledge the 1995–2000 classification-product boundary. |

## Results added in this update

- three 36-year regional 30 m FVC tables
- 64-city, eight-node FVC and wetland-area table
- 30/100/250/500 m scale comparison
- annual endpoint percentile diagnostics
- segmented Sen slope, Mann–Kendall, and TFPW results
- city fixed/dynamic endpoint direction agreement and FDR results
- updated publication figures under `docs/assets/stage5/`
- the Stage 5 GEE QA/export script under `gee_scripts/stage5/`

## Main findings supported by the added data

1. The 500 m and 30 m regional statistics are not equivalent. Across 14 valid region-year comparisons, the mean absolute difference was 0.022383 and the maximum difference was 0.058985.
2. GBA 1985 has no valid Stage 5 observation and is not filled from 1986.
3. Before 2013, GBA and BTH show significant declining trends, while YRD does not show a significant monotonic trend. From 2013 to 2020, none of the three regions shows a significant monotonic trend.
4. Under the 50% city baseline-coverage screen, fixed and dynamic endpoints give the same trend direction for 75.0% of cities. Sixteen cities change direction and are treated as method-sensitive cases.
5. No city remains significant after within-region FDR correction, so city results are presented as spatial heterogeneity rather than a list of significantly recovering or degrading cities.

## Figure use

The original report's strongest visual forms remain useful: aligned regional maps, small multiples, annual line charts, stacked transition structure, Sankey diagrams, and ranked city-change plots. They should be regenerated from the Stage 5 data rather than copied from the earlier report.

The recommended public figure set is:

1. `regional_fvc_30m.png`
2. `regional_fvc_area_coverage.png`
3. `standardized_fvc_anomaly.png`
4. `segmented_sen_trends.png`
5. `city_fvc_node_boxplots.png`
6. `city_area_fvc_quadrant.png`
7. `endpoint_percentile_diagnostic.png`
8. `spatial_fvc_2020.png`
9. `wetland_transition_structure.png`

## Distribution limits

Raw Landsat imagery, GLC-FCS30D source rasters, private administrative boundaries, and the full report are not published in this repository. The public repository contains aggregate CSV results, code, validation records, and selected figures. The 2020 display rasters remain outside Git because of size and distribution scope.
