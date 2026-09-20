from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SlideSpect NER Moisture API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to the deployed SlideSpect domain later.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "slidespect-moisture"}

@app.get("/api/moisture/latest")
def latest():
    # Metadata endpoint for the prototype. Actual raster/value ingestion
    # belongs in the scheduled production job described in backend/README.md.
    return {
        "source": "NASA SMAP L4",
        "product": "SMAP_L4_Analyzed_Surface_Soil_Moisture",
        "resolution_km": 9,
        "region": "Northeast India",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "browser_visualization_active",
        "message": "Live map visualization currently uses NASA GIBS tiles."
    }
