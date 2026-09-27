from pathlib import Path
import json
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "slidesense_logistic_regression.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
FRONTEND = ROOT / "frontend"

NER_STATES = {
    "Arunachal Pradesh", "Assam", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Sikkim", "Tripura"
}

FEATURES = [
    "latitude", "longitude", "elevation_m",
    "rainfall_24h_mm", "rainfall_3d_mm", "rainfall_7d_mm",
    "forecast_rainfall_24h_mm", "soil_moisture_m3m3", "slope_deg"
]

app = FastAPI(title="SlideSense API", version="0.1.0")
model = None

class PredictionRequest(BaseModel):
    latitude: float = Field(..., ge=21, le=30)
    longitude: float = Field(..., ge=88, le=98)
    elevation_m: float = Field(500, ge=0, le=9000)
    rainfall_24h_mm: float = Field(0, ge=0)
    rainfall_3d_mm: float = Field(0, ge=0)
    rainfall_7d_mm: float = Field(0, ge=0)
    forecast_rainfall_24h_mm: float = Field(0, ge=0)
    soil_moisture_m3m3: float = Field(0.25, ge=0, le=1)
    slope_deg: float = Field(20, ge=0, le=90)


def load_model():
    global model
    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)


def validate_ner_bbox(lat, lon):
    # Broad NER envelope. For production, replace with an official state-boundary
    # polygon check and return the exact state name.
    return 21 <= lat <= 30 and 88 <= lon <= 98


@app.on_event("startup")
def startup():
    load_model()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_path": str(MODEL_PATH),
    }


@app.get("/api/ner-states")
def ner_states():
    return sorted(NER_STATES)


@app.get("/api/metrics")
def metrics():
    if not METRICS_PATH.exists():
        return {"trained": False}
    return json.loads(METRICS_PATH.read_text())


@app.post("/api/predict")
def predict(payload: PredictionRequest):
    if not validate_ner_bbox(payload.latitude, payload.longitude):
        raise HTTPException(400, "Location is outside the current NER prediction envelope.")
    if model is None:
        raise HTTPException(
            503,
            "Model is not trained yet. Run scripts/build_training_table.py and scripts/train_model.py first."
        )

    row = np.array([[getattr(payload, f) for f in FEATURES]], dtype=float)
    probability = float(model.predict_proba(row)[0, 1])

    if probability < 0.25:
        level = "LOW"
    elif probability < 0.50:
        level = "MODERATE"
    elif probability < 0.75:
        level = "HIGH"
    else:
        level = "VERY HIGH"

    return {
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "landslide_probability": round(probability, 4),
        "risk_level": level,
        "warning": "Prototype decision-support output; not an official emergency warning.",
    }


@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")
