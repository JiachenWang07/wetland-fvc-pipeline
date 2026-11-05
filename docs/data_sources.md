# Data sources and access boundary

| Source | Identifier used in code | Role | Included in this repository |
| --- | --- | --- | --- |
| Landsat 5 Collection 2 Level 2 | `LANDSAT/LT05/C02/T1_L2` | Surface reflectance before 2013 | No; accessed through Google Earth Engine |
| Landsat 7 Collection 2 Level 2 | `LANDSAT/LE07/C02/T1_L2` | Surface-reflectance supplement before 2013 | No; accessed through Google Earth Engine |
| Landsat 8 Collection 2 Level 2 | `LANDSAT/LC08/C02/T1_L2` | Surface reflectance from 2013 | No; accessed through Google Earth Engine |
| GLC_FCS30D | `projects/sat-io/open-datasets/GLC-FCS30D/annual` and `/five-years-map` | Wetland mask and land-cover transitions | No; accessed through the community GEE catalog |
| FAO GAUL simplified level 2 | `FAO/GAUL_SIMPLIFIED_500m/2015/level2` | Hong Kong and Macao features in the GEE workflow | No; accessed through Google Earth Engine |
| Project city boundary asset | `projects/my-project-11626-475607/assets/China` | Mainland city geometry used by the reviewed export | No; private asset, replacement required for a fresh account |
| GADM 4.1 level 2 | downloaded separately from GADM | Reference outlines on the public 2020 maps only | No raw boundary file; rendered outlines are included |

The committed CSV files are processed aggregate outputs, not raw imagery. The 2020 map PNGs were rendered from 120 m display exports; the reviewed statistical tables use 30 m aggregation. External datasets remain subject to their own licenses and terms.

The private boundary asset is the largest obstacle to raw-pipeline reproduction. A replacement must provide equivalent city geometries and a stable city-name field, after which `regions_config.js` and the Stage 5 script can be adapted. Changing the boundary source can slightly change area-weighted results, so any replacement should be treated as a new reproducibility experiment rather than assumed identical.
