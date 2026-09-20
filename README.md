# SlideSpect — NER Soil Moisture Module

This repository module adds the first working Earth-observation feature:
**NASA SMAP surface soil moisture over Northeast India**.

## Repository layout

- `frontend/` — Leaflet map interface and NASA GIBS layer
- `backend/` — small FastAPI service ready for production ingestion
- `docs/` — data-source and interpretation notes

## Run frontend

From `frontend/`:

```bash
python -m http.server 8000
```

Open `http://localhost:8000`.

## Run backend

From `backend/`:

```bash
python -m venv .venv
# activate the environment
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Then check:

`http://localhost:8001/api/health`

## Current behavior

The browser requests NASA GIBS map tiles for
`SMAP_L4_Analyzed_Surface_Soil_Moisture`. The date is selected in the UI.

The backend is intentionally lightweight at this stage. The next backend job
will ingest the underlying gridded product, cache the newest valid observation,
and provide point/raster values through an API.

## Sources

NASA Worldview and NASA GIBS provide the visualization layer and metadata.
See `docs/DATA_SOURCES.md`.

## Next features

1. Scheduled SMAP ingestion.
2. Point/cell soil-moisture query on map click.
3. Daily history.
4. Rainfall.
5. Elevation/slope.
6. Landslide-risk ML model.
