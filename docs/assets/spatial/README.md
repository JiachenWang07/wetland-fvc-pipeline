# Continuous 2020 FVC maps

These three regional panels and the repository hero use the reviewed 2020 `ALL` display exports:

- `SRDP_FVC_2020_YRD_ALL.tif`
- `SRDP_FVC_2020_GBA_ALL.tif`
- `SRDP_FVC_2020_BTH_ALL.tif`

The rasters contain continuous FVC values in `[0, 1]` at 120 m display resolution. All figures use the same continuous palette, `PowerNorm(gamma=0.62)`, and fixed 0–1 color limits. The power transform affects color rendering only; it does not alter the stored FVC values or the 30 m statistical tables. Thin reference outlines come from GADM 4.1 level-2 boundaries; the boundary source is visually overlaid and is not used to calculate FVC.

No five-level or other categorical FVC classification is used. The individual images retain projected coordinates and distribution summaries; the triptych removes repeated axes for a cleaner cross-region overview.

The source rasters are not committed because they are upstream GEE display exports. Regenerate individual panels with `spatial_fvc_map.py`, or generate the shared-scale triptych with:

```bash
python python_analysis/src/spatial_fvc_map.py \
  --triptych YRD_2020.tif GBA_2020.tif BTH_2020.tif \
  --triptych-output docs/assets/fvc_continuous_2020_triptych.png \
  --city-boundaries gadm41_CHN_2.shp
```

GADM 4.1 is available for academic and other non-commercial use from the [GADM download page](https://gadm.org/download_country.html). The boundary files are not redistributed here.
