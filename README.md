# SlideSense — NER Landslide Risk Monitoring & Early Warning

A software-first prototype for the eight North-Eastern states of India:
Arunachal Pradesh, Assam, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim and Tripura.

## What this build contains

- FastAPI backend with `/api/predict`, `/api/health`, and `/api/ner-states`.
- Leaflet web interface with a professional risk dashboard and map.
- Logistic Regression baseline model for a binary target: landslide occurrence in a defined future window.
- Data pipeline that can build a training table from historical landslide events + historical weather.
- NER filtering.
- Future-weather prediction endpoint: if forecast rainfall is supplied, the same trained model can estimate risk from forecast conditions.
- Clear separation between data ingestion, feature engineering, training, API and UI.

## Important scientific limitation

This repository is a **working baseline architecture**, not a validated operational early-warning system. It does not claim that the model is accurate enough for public safety. The training pipeline deliberately avoids inventing training labels. You must build/verify the historical dataset and evaluate the model with spatial/temporal validation before using it for real warnings.

The initial baseline uses Logistic Regression because it is interpretable and gives a probability. A later version can compare Random Forest / gradient boosting models.

## Data sources used by the pipeline

1. NASA Global Landslide Catalog export / service — rainfall-triggered landslide events. The public data.nasa.gov export is a one-time export current to March 7, 2016; the pipeline therefore treats it as a historical baseline, not “all landslides ever”.
2. Open-Meteo Historical Weather API — ERA5/ERA5-Land/ECMWF historical weather and soil variables.
3. GSI Bhusanket / NLFC — use the GSI field-validated inventory or other authorized downloads as an additional source. Put the downloaded CSV in `data/raw/gsi_ner_landslides.csv` and run the pipeline. Do not scrape or redistribute data in violation of the portal's terms.

## Quick start

### 1. Install

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Get historical landslide data

The NASA service can be queried by the pipeline. For a stronger NER dataset, download the relevant GSI inventory through the official portal and place it at:

`data/raw/gsi_ner_landslides.csv`

The GSI public inventory contains much richer fields than the NASA catalog, including location/date and geoscientific information.

### 3. Build the training table

```bash
python scripts/build_training_table.py
```

This creates:

`data/processed/ner_training.csv`

The script creates positive event rows and matched negative/non-event rows. It fetches historical rainfall around event coordinates from Open-Meteo. It does **not** fabricate positive events.

### 4. Train

```bash
python scripts/train_model.py
```

The model is saved as:

`models/slidesense_logistic_regression.joblib`

Metrics are written to:

`models/metrics.json`

### 5. Run the API

```bash
uvicorn backend.main:app --reload
```

Open:

`http://127.0.0.1:8000`

## Feature contract

The baseline model expects:

- latitude
- longitude
- elevation_m
- rainfall_24h_mm
- rainfall_3d_mm
- rainfall_7d_mm
- forecast_rainfall_24h_mm
- soil_moisture_m3m3 (optional; missing values are imputed)
- slope_deg (optional; missing values are imputed)

The last two static/environmental features are intentionally optional in the first baseline so the model can be trained before a complete DEM/soil/geology pipeline is finished.

## Next upgrades

1. Add GSI's richer field-validated inventory.
2. Add DEM-derived elevation/slope/aspect.
3. Add soil/geology/land-cover layers.
4. Add satellite soil moisture.
5. Replace naive random negative sampling with spatially and temporally matched controls.
6. Compare Logistic Regression, Random Forest and gradient boosting.
7. Use spatial holdout + temporal holdout validation.
8. Calibrate probabilities and choose warning thresholds from validation data.
9. Add forecast lead-time features (6h/12h/24h/48h/72h).
10. Add uncertainty and human-review workflow before any public warning.

## Why Logistic Regression first?

It is not because it is necessarily the final best model. It is the first baseline because the output probability is easy to inspect, the model is fast to train, and the coefficients can be explained. The project can then test stronger tree-based models against this baseline.
