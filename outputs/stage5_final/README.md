# Stage 5 final results

This directory contains the aggregate data used in the 2026 completion report.

## Primary inputs

- `Stage5_Final_Regional30m_36Years_{YRD,GBA,BTH}.csv`: annual 30 m effective-area-weighted regional results.
- `Stage5_QA_City_FVC_8Nodes_30m.csv`: 64 cities × 8 node years, including wetland area, valid FVC area, valid fraction, and FVC.
- `Stage5_QA_Endpoint_Percentiles.csv`: annual wetland NDVI percentile diagnostics against fixed endpoints.
- `Stage5_QA_Scale_30_100_250_500m.csv`: multi-scale comparison for representative years.

## Derived analysis

The `analysis/` directory contains segmented trend results, city endpoint-sensitivity results, city area–FVC change details, and wetland-transition tables.

## Important interpretation notes

- GBA 1985 is missing and is not replaced by 1986.
- Primary regional and city results use 30 m statistics.
- Fixed endpoints define the primary reporting scale; dynamic endpoints are used for sensitivity analysis.
- The city table contains 64 cities because Macao did not return a valid geometry in the final export.
- GeoTIFF products are not distributed in Git.
