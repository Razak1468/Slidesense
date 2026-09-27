
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from functools import lru_cache
import math, os, json, requests
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

app = FastAPI(title="SlideSpect ML API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
NASA_CSV = "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv"

FEATURES = [
    "rain_1d", "rain_3d", "rain_7d", "rain_30d",
    "soil_moisture", "humidity", "temperature", "wind",
    "pressure", "elevation"
]

# Prototype ML model. It is trained from a physically-inspired synthetic dataset so
# the application remains runnable without downloading a huge training corpus.
# NASA GLC events are used as an independent historical-evidence layer.
MODEL = None
MODEL_INFO = {}

def make_demo_training_data(n=16000, seed=42):
    rng = np.random.default_rng(seed)
    rain1 = rng.gamma(1.8, 12, n)
    rain3 = rain1 + rng.gamma(2.0, 18, n)
    rain7 = rain3 + rng.gamma(2.0, 35, n)
    rain30 = rain7 + rng.gamma(2.2, 90, n)
    soil = np.clip(rng.beta(2.2, 2.0, n), 0, 1)
    humidity = rng.uniform(35, 100, n)
    temp = rng.uniform(5, 38, n)
    wind = rng.uniform(0, 70, n)
    pressure = rng.uniform(990, 1030, n)
    elevation = rng.uniform(0, 3500, n)

    # A transparent prototype hazard-generating process, not a scientific landslide law.
    z = (
        0.028 * rain1 +
        0.014 * rain3 +
        0.006 * rain7 +
        0.0018 * rain30 +
        2.1 * soil +
        0.018 * (humidity - 60) +
        0.00035 * elevation +
        0.012 * np.maximum(rain3 - 80, 0) +
        0.008 * np.maximum(wind - 45, 0) -
        0.018 * np.maximum(pressure - 1015, 0) -
        4.2
    )
    p = 1 / (1 + np.exp(-z))
    y = rng.binomial(1, p)
    X = pd.DataFrame({
        "rain_1d": rain1, "rain_3d": rain3, "rain_7d": rain7, "rain_30d": rain30,
        "soil_moisture": soil, "humidity": humidity, "temperature": temp,
        "wind": wind, "pressure": pressure, "elevation": elevation
    })
    return X, y

def train_model():
    global MODEL, MODEL_INFO
    X, y = make_demo_training_data()
    MODEL = RandomForestClassifier(
        n_estimators=220, max_depth=10, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    MODEL.fit(X[FEATURES], y)
    MODEL_INFO = {
        "algorithm": "RandomForestClassifier",
        "training_mode": "prototype synthetic hazard-pattern dataset",
        "samples": len(X),
        "features": FEATURES,
        "warning": "Not a validated operational landslide forecast model."
    }

train_model()

@lru_cache(maxsize=32)
def get_weather(lat_r, lon_r):
    params = {
        "latitude": lat_r, "longitude": lon_r,
        "current": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,soil_moisture_0_to_1cm",
        "hourly": "precipitation,relative_humidity_2m,temperature_2m,wind_speed_10m,pressure_msl,soil_moisture_0_to_1cm",
        "daily": "precipitation_sum,precipitation_probability_max",
        "forecast_days": 7,
        "timezone": "auto"
    }
    r = requests.get(OPEN_METEO, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@lru_cache(maxsize=16)
def get_history(lat_r, lon_r):
    end = datetime.utcnow().date() - timedelta(days=2)
    start = end - timedelta(days=365 * 3)
    params = {
        "latitude": lat_r, "longitude": lon_r,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "precipitation_sum,temperature_2m_mean",
        "timezone": "auto"
    }
    r = requests.get(ARCHIVE, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

@lru_cache(maxsize=1)
def load_nasa_events():
    try:
        df = pd.read_csv(NASA_CSV)
        cols = {c.lower().strip(): c for c in df.columns}
        latc = cols.get("latitude"); lonc = cols.get("longitude")
        datec = cols.get("event_date")
        if not (latc and lonc and datec):
            return []
        out = df[[latc, lonc, datec]].copy()
        out.columns = ["lat", "lon", "date"]
        out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
        out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna().tail(15000)
        return out.to_dict("records")
    except Exception:
        return []

def haversine_km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (0.5 - math.cos((lat2-lat1)*p)/2 +
         math.cos(lat1*p)*math.cos(lat2*p) *
         (0.5 - math.cos((lon2-lon1)*p)/2))
    return 12742 * math.asin(math.sqrt(max(0, a)))

def event_evidence(lat, lon):
    events = load_nasa_events()
    nearby = []
    for e in events:
        d = haversine_km(lat, lon, e["lat"], e["lon"])
        if d <= 250:
            nearby.append((d, e))
    nearby.sort(key=lambda x: x[0])
    # Decay with distance; cap to avoid the count becoming an arbitrary probability.
    score = sum(math.exp(-d / 80.0) for d, _ in nearby[:100])
    evidence = 1 - math.exp(-score / 6.0)
    return {
        "nearby_events": len(nearby),
        "evidence_score": round(float(evidence), 3),
        "events": [
            {"lat": e["lat"], "lon": e["lon"], "date": str(e["date"])[:10], "distance_km": round(d,1)}
            for d,e in nearby[:20]
        ]
    }

def rolling_sum(values, n):
    vals = [float(x or 0) for x in values]
    return float(sum(vals[-n:]))

def features_from_forecast(weather, index):
    h = weather["hourly"]
    rain = h.get("precipitation", [])
    humidity = h.get("relative_humidity_2m", [])
    temp = h.get("temperature_2m", [])
    wind = h.get("wind_speed_10m", [])
    pressure = h.get("pressure_msl", [])
    soil = h.get("soil_moisture_0_to_1cm", [])
    def at(arr, i, default=0):
        return float(arr[i] if i < len(arr) and arr[i] is not None else default)
    r1 = sum(at(rain, j) for j in range(max(0,index-23), index+1))
    r3 = sum(at(rain, j) for j in range(max(0,index-71), index+1))
    r7 = sum(at(rain, j) for j in range(max(0,index-167), index+1))
    r30 = r7
    return {
        "rain_1d": r1, "rain_3d": r3, "rain_7d": r7, "rain_30d": r30,
        "soil_moisture": at(soil, index, 0.35),
        "humidity": at(humidity, index, 70),
        "temperature": at(temp, index, 25),
        "wind": at(wind, index, 10),
        "pressure": at(pressure, index, 1013),
        "elevation": 500.0
    }

def predict_from_features(f):
    x = pd.DataFrame([[f[k] for k in FEATURES]], columns=FEATURES)
    p = float(MODEL.predict_proba(x)[0,1])
    return p

@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL_INFO}

@app.get("/api/risk")
def risk(lat: float = Query(...), lon: float = Query(...)):
    lat = round(lat, 3); lon = round(lon, 3)
    weather = get_weather(lat, lon)
    current = weather["current"]
    h = weather["hourly"]
    # Current index: nearest forecast hour to current time.
    idx = 0
    now_iso = current.get("time")
    if now_iso and h.get("time"):
        idx = min(range(len(h["time"])), key=lambda i: abs(pd.Timestamp(h["time"][i]).value - pd.Timestamp(now_iso).value))
    f = features_from_forecast(weather, idx)
    model_p = predict_from_features(f)
    evidence = event_evidence(lat, lon)
    # Evidence is presented separately; blending is deliberately conservative and labeled prototype.
    final = min(0.99, 0.78 * model_p + 0.22 * evidence["evidence_score"])
    future = []
    for i in range(min(168, len(h.get("time", [])))):
        if i % 6 == 0:
            ff = features_from_forecast(weather, i)
            pp = predict_from_features(ff)
            future.append({"time": h["time"][i], "risk": round(pp*100,1),
                           "rain_24h": round(ff["rain_1d"],1), "rain_3d": round(ff["rain_3d"],1)})
    return {
        "location": {"lat": lat, "lon": lon},
        "current": {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "pressure": current.get("pressure_msl"),
            "wind": current.get("wind_speed_10m"),
            "soil_moisture": current.get("soil_moisture_0_to_1cm"),
            "model_probability": round(model_p*100,1),
            "historical_evidence": round(evidence["evidence_score"]*100,1),
            "risk": round(final*100,1)
        },
        "future": future,
        "events": evidence["events"],
        "nearby_event_count": evidence["nearby_events"],
        "model": MODEL_INFO,
        "sources": {
            "weather": "Open-Meteo Forecast + Historical Weather APIs",
            "events": "NASA Global Landslide Catalog"
        }
    }

@app.get("/api/map-grid")
def map_grid(lat: float = Query(...), lon: float = Query(...), span: float = 0.35):
    # Grid uses forecast weather at each point. The ML model is the same prototype model.
    pts = []
    n = 5
    for yi in range(n):
        for xi in range(n):
            la = lat - span + 2*span*yi/(n-1)
            lo = lon - span + 2*span*xi/(n-1)
            try:
                w = get_weather(round(la,3), round(lo,3))
                f = features_from_forecast(w, 0)
                p = predict_from_features(f)
                ev = event_evidence(la,lo)
                final = min(0.99, 0.78*p + 0.22*ev["evidence_score"])
                pts.append({"lat":la,"lon":lo,"risk":round(final*100,1)})
            except Exception:
                pass
    return {"points":pts}

@app.get("/api/geocode")
def geocode(name: str):
    r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name":name,"count":5,"language":"en","format":"json"}, timeout=15)
    r.raise_for_status()
    return r.json()

@app.get("/api/future")
def future(lat: float, lon: float):
    return risk(lat,lon)
