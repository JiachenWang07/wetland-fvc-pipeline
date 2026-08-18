# Architecture

## Data flow

```mermaid
flowchart LR
  subgraph sources ["Public / semi-public GEE datasets"]
    LS["Landsat 5/7/8<br/>Collection 2 T1_L2"]
    GLC["GLC_FCS30D<br/>annual + 5-year"]
    CHINA["China admin boundary<br/>(private GEE asset)"]
    GAUL["FAO GAUL<br/>Hong Kong / Macao"]
  end

  subgraph core ["makeRegionPipeline(roi, startMonth, endMonth)<br/>— one independent instance per region —"]
    COMP["4-level fallback<br/>annual composite"]
    NDVI["NDVI / EVI / NDMI"]
    FVC["Dimidiate-pixel FVC<br/>(dynamic endmember)"]
    MASK["Wetland masks:<br/>dynamic / fixed-1985 / fate / raw class"]
  end

  subgraph exports ["Drive folder: Wetland_FVC_Exports<br/>(~42 tasks across 3 regions)"]
    TS["36-year regional<br/>FVC/EVI/NDMI means"]
    CITY["City-level FVC &<br/>wetland area, 8 nodes"]
    MAPS["30m FVC rasters +<br/>5-level trend maps"]
    FATE["Fate-group<br/>FVC (persistent/gained/lost)"]
    TRANS["Land-cover<br/>transition structure"]
    TYPE["FVC by<br/>wetland subtype"]
  end

  subgraph offline ["python_analysis/ (local/Colab) — implemented, validated against real data"]
    PY["Sen's slope +<br/>Mann-Kendall (regional)"]
    SIXCAT["Six-category<br/>area stats (raster)"]
    PLOTS["Figures"]
  end

  CHINA --> core
  GAUL --> core
  LS --> COMP --> NDVI --> FVC
  GLC --> MASK
  FVC --> exports
  MASK --> exports
  exports --> PY --> PLOTS
  exports --> SIXCAT --> PLOTS
```

GEE performs server-side raster processing and exports intermediate products to Google Drive. Python consumes reviewed exports for statistical analysis, validation, and figure generation.

## Regional isolation

Earth Engine's Code Editor has no module system: scripts in `gee_scripts/` share one global scope when pasted together.

The early implementation reused a mutable top-level `roi`. Functions created while it pointed to one region could later evaluate against a different region after reassignment.

`makeRegionPipeline(roi, startMonth, endMonth)` closes over each region's own parameters, producing isolated YRD/GBA/BTH pipelines (`pipeYRD`, `pipeGBA`, `pipeBTH`).

## Two-stage execution

Earth Engine is server-side and is not launched through a local Python subprocess. GEE exports and Python analyses therefore form two connected stages.

Export tasks must be approved in the GEE Tasks tab. Files land in the Drive folder `Wetland_FVC_Exports` and are then used as Python inputs. Reviewed CSV evidence for the published workflow is already under [`../outputs/`](../outputs/).

## Export contract

All GEE exports land in a single Drive folder: `Wetland_FVC_Exports`. Column-level schema for every product is in [`data_schema.md`](data_schema.md).
