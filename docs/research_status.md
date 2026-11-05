# Research status and evidence boundary

## Current result basis

The quantitative comparison presented by this repository is the reviewed Stage 5 branch: strict Landsat Collection 2 Level 2 QA, growing-season median composites, pixelwise NDVI and FVC, fixed regional endpoints, 30 m effective-area weighting, and missing observations retained as missing.

The dimidiate-pixel equation is

\[
FVC = \mathrm{clip}\left(\frac{NDVI-NDVI_{soil}}{NDVI_{veg}-NDVI_{soil}}, 0, 1\right).
\]

FVC is calculated per valid pixel before area-weighted aggregation. Applying the equation to already averaged NDVI would be a different statistic and is not used here.

## Evidence tiers

| Tier | Contents | Interpretation |
| --- | --- | --- |
| A — reviewed result | Regional and city 30 m tables plus canonical derived tables in `outputs/stage5_final/analysis/` | Basis for quantitative comparisons |
| B — robustness evidence | Scale comparison, endpoint percentiles, direction agreement, and validation tables | Tests dependence on implementation choices |
| C — display products | Selected PNG/PDF figures and 120 m 2020 maps | Communication and spatial context only |
| D — historical record | 500 m, dynamic-endpoint, fallback, and five-class OLS outputs | Provenance and diagnostics only |

## Claims that should not be made

- GBA has no reviewed 1985 observation and must not be included in a three-region 1985 ranking.
- A regional mean does not establish that every wetland changed in the same direction.
- The 120 m maps cannot replace the reviewed 30 m tables or support pixelwise trend inference.
- The historical five-level OLS map is not a significance map.
- A change around 2013 cannot automatically be attributed to ecology because sensor transition is a competing explanation.
- No city remains significant under the documented within-region FDR screen; city patterns are descriptive.

## Reproduction boundary

The committed aggregate tables reproduce the public statistical figures. Recomputing from raw imagery requires Google Earth Engine, source imagery, and a replacement for the private city-boundary asset. Raw imagery and large raster exports are not redistributed. This is a transparent partial-reproducibility boundary, not a claim of raw-data self-containment.

## Highest-value future validation

The strongest next additions would be independent boundary reconstruction, overlap-year cross-sensor harmonization, reference-site or field validation of endpoints, annual uncertainty propagation, and a minimum-observation rule for any future pixelwise trend product. These are open extensions, not silently assumed complete.
