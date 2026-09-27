# SlideSpect — ML Landslide Risk Prototype

## What this project does

- Search a city/region or use browser geolocation.
- Fetches live/current and 7-day forecast weather from Open-Meteo.
- Uses a Random Forest ML model to convert weather/terrain-proxy features into a prototype risk probability.
- Uses the NASA Global Landslide Catalog as a separate historical-event evidence layer.
- Plots future model risk so forecast rainfall can change the estimated risk.
- Shows a 5×5 spatial prototype risk grid on a Leaflet map.
- Keeps the ML layer separate from the UI/API.

## Data sources

1. Open-Meteo Forecast API
2. Open-Meteo Historical Weather API
3. NASA Global Landslide Catalog Export
4. OpenStreetMap tiles via Leaflet

## Run

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
uvicorn main:app --reload
```

Backend: http://localhost:8000

### Frontend

Open `frontend/index.html` with VS Code Live Server, or serve it:

```bash
cd frontend
python -m http.server 5500
```

Then open http://localhost:5500

## Important scientific limitation

The current Random Forest is a **prototype demonstration model** trained on a transparent synthetic hazard-pattern dataset. It is NOT trained/validated as a real operational landslide-warning model.

The NASA catalog is used as historical evidence, not falsely treated as a complete absence/presence ground-truth dataset.

For a serious research version, replace the demo training data with a properly constructed spatiotemporal dataset containing:
- landslide occurrence/non-occurrence labels,
- rainfall observations,
- antecedent rainfall,
- soil moisture,
- slope,
- elevation,
- geology/lithology,
- land cover,
- drainage,
- ground movement,
- and location/time-aware train/test splits.

Do not use this prototype for public-safety decisions.

## Architecture

Data sources → ingestion → feature engineering → ML inference → risk layer → API → dashboard/map
