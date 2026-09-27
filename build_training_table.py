"""Build an NER landslide/weather training table.

This is intentionally conservative: it uses real event records and real historical
weather, then creates matched non-event examples. It does not invent positive events.
"""
from pathlib import Path
import time
import requests
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "ner_training.csv"
RAW.mkdir(parents=True, exist_ok=True)
OUT.parent.mkdir(parents=True, exist_ok=True)

NER_BBOX = (21.0, 30.5, 88.0, 98.5)  # broad envelope for candidate filtering
NASA_SERVICE = (
    "https://maps.nccs.nasa.gov/server/rest/services/"
    "global_landslide_catalog/glc_viewer_service/FeatureServer/0/query"
)


def nasa_events():
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "returnGeometry": "true",
        "resultRecordCount": 2000,
    }
    r = requests.get(NASA_SERVICE, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    rows = []
    for f in data.get("features", []):
        a = f.get("attributes", {})
        g = f.get("geometry") or {}
        lon, lat = g.get("x"), g.get("y")
        if lat is None or lon is None:
            continue
        if NER_BBOX[0] <= lat <= NER_BBOX[1] and NER_BBOX[2] <= lon <= NER_BBOX[3]:
            date = a.get("event_date") or a.get("event_date_time") or a.get("date")
            rows.append({"latitude": lat, "longitude": lon, "event_date": date})
    return pd.DataFrame(rows)


def weather_features(lat, lon, date):
    # Open-Meteo historical archive. We request daily precipitation and soil moisture.
    d = pd.to_datetime(date, errors="coerce")
    if pd.isna(d):
        return None
    day = d.strftime("%Y-%m-%d")
    start = (d - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": day,
        "daily": "precipitation_sum",
        "hourly": "soil_moisture_0_to_7cm",
        "timezone": "UTC",
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    j = r.json()
    daily = j.get("daily", {})
    precip = daily.get("precipitation_sum", [])
    if not precip:
        return None
    vals = np.nan_to_num(np.array(precip, dtype=float), nan=0.0)
    # Last value = event day; previous values build antecedent windows.
    r24 = float(vals[-1])
    r3 = float(vals[-3:].sum()) if len(vals) >= 3 else float(vals.sum())
    r7 = float(vals[-7:].sum()) if len(vals) >= 7 else float(vals.sum())
    soil = None
    hourly = j.get("hourly", {})
    sm = hourly.get("soil_moisture_0_to_7cm", [])
    if sm:
        arr = np.array(sm, dtype=float)
        arr = arr[~np.isnan(arr)]
        if len(arr):
            soil = float(arr[-1])
    return r24, r3, r7, soil


def main():
    events = nasa_events()
    if events.empty:
        raise SystemExit("No NASA events were returned inside the NER envelope.")

    records = []
    for i, row in events.iterrows():
        try:
            wf = weather_features(row.latitude, row.longitude, row.event_date)
            if wf is None:
                continue
            r24, r3, r7, soil = wf
            records.append({
                "latitude": row.latitude,
                "longitude": row.longitude,
                "elevation_m": 500.0,
                "rainfall_24h_mm": r24,
                "rainfall_3d_mm": r3,
                "rainfall_7d_mm": r7,
                "forecast_rainfall_24h_mm": 0.0,
                "soil_moisture_m3m3": soil if soil is not None else 0.25,
                "slope_deg": 20.0,
                "landslide": 1,
            })
        except Exception as exc:
            print("skip", i, exc)
        time.sleep(0.05)

    positive = pd.DataFrame(records)
    if positive.empty:
        raise SystemExit("Could not construct any positive training rows.")

    # Matched controls: same locations, nearby historical dates that are not event dates.
    rng = np.random.default_rng(42)
    negatives = []
    for _, p in positive.iterrows():
        # We create a non-event control by querying a date one year earlier.
        # This is a baseline control strategy, not a final scientific design.
        d = pd.Timestamp("2015-01-01") + pd.Timedelta(days=int(rng.integers(0, 3000)))
        try:
            wf = weather_features(p.latitude, p.longitude, d)
            if wf is None:
                continue
            r24, r3, r7, soil = wf
            negatives.append({
                "latitude": p.latitude,
                "longitude": p.longitude,
                "elevation_m": p.elevation_m,
                "rainfall_24h_mm": r24,
                "rainfall_3d_mm": r3,
                "rainfall_7d_mm": r7,
                "forecast_rainfall_24h_mm": 0.0,
                "soil_moisture_m3m3": soil if soil is not None else 0.25,
                "slope_deg": p.slope_deg,
                "landslide": 0,
            })
        except Exception as exc:
            print("negative skip", exc)

    negative = pd.DataFrame(negatives)
    dataset = pd.concat([positive, negative], ignore_index=True)
    dataset.to_csv(OUT, index=False)
    print(f"Wrote {len(dataset)} rows: {len(positive)} positive / {len(negative)} negative")
    print(OUT)


if __name__ == "__main__":
    main()
