# Figure set

These figures were regenerated from the reviewed Stage 5 tables on 5 November 2026. All labels are in English and the visual system uses a restrained teal, terracotta, and slate palette.

| File | Content | Statistical boundary |
|---|---|---|
| `breakpoint_stability` | Sen slopes across candidate 2011–2015 breakpoints | Robustness diagnostic only; does not estimate an optimal breakpoint or identify a sensor effect |
| `fvc_overview` | Annual regional FVC, segmented trends, city distributions, and scale sensitivity | Regional values use effective-area weighting; 30 m is the reporting scale |
| `city_fvc_change_ranking` | Cities with the largest positive and negative endpoint differences | Includes only cities with at least 50% valid baseline coverage; missing years are not filled |
| `wetland_transition_1995_2000` | Recorded sources of wetland gain and destinations of wetland loss | Ribbon width represents product-recorded area; it is not direct evidence of ecological recovery |

PNG files are intended for the repository and presentations. Matching PDF files retain vector text and are preferable for print.

The three-region continuous map is stored one level above as `fvc_continuous_2020_triptych.png`; full-size regional panels are in `../spatial/`. They use 120 m spatial display exports and actual FVC values from 0 to 1 without class thresholds. A continuous power stretch is used only to improve visibility; reviewed regional and city statistics remain based on the 30 m tables.

## Reproduction

```bash
python python_analysis/src/publication_figures.py
python python_analysis/src/breakpoint_stability.py
```
