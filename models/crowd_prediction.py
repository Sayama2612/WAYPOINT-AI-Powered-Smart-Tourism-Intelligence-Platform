import joblib
from pathlib import Path
import pandas as pd

MODEL_PATH = Path(__file__).parent / 'crowd_model.joblib'


def load_model():
    if MODEL_PATH.exists():
        obj = joblib.load(MODEL_PATH)
        return obj['model'], obj.get('features', None)
    return None, None


def predict_crowd_for_row(row: pd.Series):
    model, features = load_model()
    if model is None:
        return None
    X = pd.DataFrame([row[features]])
    pred = model.predict(X)[0]
    # crowd_score from 0-100, clamp
    return float(max(0, min(100, pred)))


def top_n_crowded(df: pd.DataFrame, n=10):
    if 'crowd_index' in df.columns:
        return df.sort_values('crowd_index', ascending=False).head(n)
    return df.head(n)
