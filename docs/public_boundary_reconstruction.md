# Public boundary reconstruction protocol

## Purpose

The reviewed tables were generated with a private mainland China city-boundary asset plus FAO GAUL features for Hong Kong and Macao. Replacing that asset is necessary for raw-pipeline reproducibility, but a new boundary source can change wetland area, valid area, and area-weighted FVC. A public reconstruction must therefore be evaluated as a new experiment, not silently substituted.

## Candidate construction

1. Obtain an openly accessible prefecture-level boundary source with documented version and license.
2. Build the same study units:
   - YRD: 40 mainland prefecture-level cities plus Shanghai as one dissolved unit;
   - GBA: nine Pearl River Delta mainland cities, Hong Kong, and Macao;
   - BTH: 11 Hebei prefecture-level cities plus Beijing and Tianjin as dissolved units.
3. Normalize a stable `name` field and retain the original source identifier in a separate property.
4. Repair invalid geometries, record the coordinate reference system, and avoid simplifying boundaries before the comparison run.
5. Upload the candidate collection to GEE under a new asset name; do not overwrite the historical asset reference.

## Required acceptance checks

| Check | Required output |
| --- | --- |
| Unit inventory | Expected name list, missing names, duplicates, and final unit count |
| Geometry validity | Invalid/empty geometry count and any repair log |
| Area comparison | Old versus candidate area by city and region, absolute and percentage difference |
| Wetland-mask intersection | 1985, 2000, and 2020 wetland area under both boundary sets |
| FVC comparison | Regional annual FVC differences for at least 1985, 2000, 2013, and 2020 |
| City comparison | Baseline and 2020 FVC/area differences for every matched city |
| Conclusion stability | Whether regional trend direction/significance or city direction classification changes |

## Decision rule

The candidate boundary can become the default only after all mismatches are explained and the comparison tables are published. If a regional or city conclusion changes, both versions must remain traceable and the difference must be attributed to the boundary experiment rather than described as ecological change.

## Current status

The GADM 4.1 outlines used on the public map are visual reference lines only. They have not passed the acceptance checks above and therefore do not replace the private boundary asset used for the reviewed statistics.
