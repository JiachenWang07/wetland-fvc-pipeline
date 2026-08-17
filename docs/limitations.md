# Known Limitations 已知局限

This document lists limitations honestly rather than hiding them, including items surfaced by external code review that are confirmed real but **not yet fixed in code** as of this writing — the review-and-triage process (see `methodology_notes.md`) intentionally happened before any code changes, so this list reflects the current, unmodified state of `gee_scripts/`.

Status legend: 🔴 confirmed issue, not yet fixed · 🟡 needs empirical validation before deciding whether to fix · ⚪ documented tradeoff, not planned to change

---

## Confirmed issues, not yet fixed (🔴)

| Issue | Where | Why it matters |
|---|---|---|
| `filterDate` end date is exclusive, so growing-season and full-year windows silently drop the last few days of the range | `region_pipeline.js` → `fetchCollection` | May slightly change which scenes are included in the annual composite; effect on results not yet quantified |
| `wetland_transition_structure.js` passes an `ee.Number` where `ee.Dictionary.get()` requires a string key | `wetland_transition_structure.js` | Confirmed against official GEE documentation; could cause this export to fail at task-execution time even though it submits without error |
| Endmember percentiles have no null/degenerate-value guard before being used as a division denominator | `region_pipeline.js` → `getDynamicEndpoints` / `processIndices` | An empty or heavily cloud-contaminated year could silently produce an invalid or unstable FVC value rather than a clear error |
| Six-category map can silently drop pixels that lack a valid trend value or valid 2020 FVC (they resolve to class `0` and are removed by `.selfMask()`) | `trend_classification.js` → `exportSixCategoryMap` | The map is described as covering "all wetland change," but is not currently guaranteed to be exhaustive |
| 36-year per-pixel OLS trend has no minimum-observation or temporal-coverage requirement | `trend_classification.js` | A slope fit from a handful of cloud-free years is assigned the same categorical weight as one fit from all 36 |
| 5-level trend classification is masked to **2020** wetland extent rather than restricted to wetland present at **both** 1985 and 2020 | `trend_classification.js` → `exportTrendClassification` | A pixel that was, e.g., impervious surface until 2019 and became wetland in 2020 can register an artificially steep "recovery" slope that actually reflects land-cover conversion, not vegetation change on a stable wetland |
| Grouped `reduceRegion` results are passed directly to `.map()` without a null guard | `trend_classification.js`, `wetland_transition_structure.js` | An interval/region with no matching pixels can return `null` instead of an empty list, which can fail the export rather than producing an explicit zero |
| "42 export tasks submitted without error" has been used as the current validation status | `gee_scripts/README.md` | Task submission succeeding is not the same as task execution succeeding — none of the exports above have actually been run to completion and checked |

## Needs empirical validation before deciding whether to change (🟡)

These are real, plausible risks raised by external review, but the direction and magnitude are not yet measured. Sensitivity experiments are planned before any of these trigger a code or method change.

| Issue | Concern | Planned validation |
|---|---|---|
| QA_PIXEL cloud mask only checks bits 3–4 (cloud, cloud shadow) | Misses dilated cloud, cirrus (Landsat 8), snow/ice, and radiometric saturation, which can contaminate composites and percentile-based endmembers | Re-run with a stricter mask, compare FVC/trend outputs before and after |
| No cross-sensor harmonization between Landsat 5/7 and Landsat 8 (switch happens in 2013) | Could introduce a systematic discontinuity in the 36-year series that a linear/Sen's-slope trend would absorb as a false trend | Compare NDVI/FVC statistics in overlap or adjacent years across sensors before assuming a specific correction is needed |
| `normalizedDifference()` masks a pixel when either input band is negative (confirmed GEE behavior); Landsat C2 L2's `-0.2` reflectance offset can produce negative inputs | Could silently remove dark/water-adjacent pixels — disproportionately relevant near wetlands | Measure the percentage of pixels masked for this reason, per region/year, before deciding whether to switch to an `expression()`-based computation |
| Dynamic endmembers (5th/95th NDVI percentile) are computed over the **whole ROI**, not restricted to wetland or a stable reference surface | Water bodies can pull the soil endmember down; dense non-wetland forest can pull the vegetation endmember up | Documented as a known tradeoff already (fixed-endmember cross-validation exists as a partial mitigation); a wetland-restricted endmember experiment is a possible future refinement, not a near-term change |
| `REGIONAL_SCALE` (500m) vs `CITY_SCALE` (30m) — the code comment stating 500m "doesn't affect the result" has already been identified as overstated | Scale can affect aggregated statistics, especially for narrow/fragmented wetlands | 30m vs 100m vs 250m vs 500m comparison for representative years/regions |
| Boundary `.simplify(1000)` (1km tolerance) applied before 30m raster analysis | Could add or remove real area along coastlines, estuaries, and narrow wetland strips | Compare simplified vs. unsimplified boundary area and wetland statistics |
| GBA's Hong Kong/Macao features (from FAO GAUL, district-level) merged with mainland prefecture-city features | Possible unit-of-analysis mismatch in city-level tables (e.g., four-quadrant analysis) | Inspect actual feature count/level in `cityFC_GBA` before assuming consistency |

## Documented tradeoffs, not planned to change (⚪)

| Item | Rationale |
|---|---|
| GLC_FCS30D pre-2000 wetland extent uses 5-year-interval maps (1985/1990/1995), not annual data; some requested years (e.g. 1988) use a later epoch's classification | Limitation of the upstream dataset, not a pipeline design choice. Documented here rather than presented as annual resolution. |
| "Fate group `lost`" FVC is measured at the interval's earlier endpoint (`yA`), described as "before conversion" | The exact conversion date within the 5-year interval is unknown — GLC products provide endpoint states only. The more precise framing is "FVC at the earlier endpoint among pixels absent at the later endpoint." |
| `persistent` wetland (in both the fate-group and six-category logic) means "wetland at both 1985 and 2020," not "wetland continuously for all 36 years" | A pixel that left and re-entered the wetland class between the two endpoints is still counted as persistent under this definition. This is "endpoint-persistent," not continuously persistent. |
| BNU independent 30m FVC product cross-validation shows a systematic 0.07–0.09 vegetation-endmember offset, with the soil endmember direction reversed specifically in BTH | Cause not deeply investigated; recorded as an open question rather than explained away |
| GBA 2000 Swamp-subtype FVC shows an unexplained anomalous peak | Cause not investigated |
| 45% FVC threshold (new-wetland low/high cover split) traced to SL 190-2007 (水利部, water-resources industry standard, not a national GB/T standard) via a secondary academic citation, not independently verified against the primary standard text | Treated as well-supported but not fully verified — see `methodology_notes.md` for the verification trail |
| Zero automated test coverage | GEE itself is not well suited to conventional unit testing. `python_analysis/` now exists and has been manually smoke-tested against synthetic data (confirmed the core logic runs and handles missing-file cases gracefully), but no formal `pytest` suite has been written yet — the kind of assertions that would actually matter (FVC always in [0,1], six-category areas summing to the expected total, etc.) are not yet codified as tests |

---

## A note on how this list was produced

This project was reviewed by four independent AI-assisted code/methodology reviews before publication (see `methodology_notes.md` for the full triage). Not every finding here was accepted at face value — several were downgraded from an initial "definite error" claim to "needs empirical validation" after independent verification against official documentation or first-principles reasoning, and at least one specific fix recommendation was rejected outright as unsuitable for this project's constraints. The goal of this list is to state what is actually known, and to be explicit about what is not yet known, rather than to project more confidence than the current evidence supports.
