from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, roc_auc_score, average_precision_score,
    confusion_matrix
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "ner_training.csv"
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = [
    "latitude", "longitude", "elevation_m",
    "rainfall_24h_mm", "rainfall_3d_mm", "rainfall_7d_mm",
    "forecast_rainfall_24h_mm", "soil_moisture_m3m3", "slope_deg"
]
TARGET = "landslide"


def main():
    df = pd.read_csv(DATA)
    df = df.dropna(subset=[TARGET])
    X = df[FEATURES]
    y = df[TARGET].astype(int)

    # Group by rounded coordinate so nearby rows are not casually split across train/test.
    groups = (df["latitude"].round(1).astype(str) + "_" + df["longitude"].round(1).astype(str))
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))

    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    pipe.fit(X.iloc[train_idx], y.iloc[train_idx])

    proba = pipe.predict_proba(X.iloc[test_idx])[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "trained": True,
        "rows": int(len(df)),
        "positive_rows": int(y.sum()),
        "negative_rows": int((y == 0).sum()),
        "roc_auc": float(roc_auc_score(y.iloc[test_idx], proba)),
        "average_precision": float(average_precision_score(y.iloc[test_idx], proba)),
        "confusion_matrix": confusion_matrix(y.iloc[test_idx], pred).tolist(),
        "classification_report": classification_report(y.iloc[test_idx], pred, output_dict=True),
        "validation": "grouped spatial holdout by rounded coordinate",
        "features": FEATURES,
        "note": "Baseline research model. Not validated for operational public warning use.",
    }

    joblib.dump(pipe, MODEL_DIR / "slidesense_logistic_regression.joblib")
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
