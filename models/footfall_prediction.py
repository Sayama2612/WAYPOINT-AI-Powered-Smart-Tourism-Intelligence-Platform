import joblib
from pathlib import Path
import pandas as pd

MODEL_PATH = Path(__file__).parent / 'footfall_model.joblib'


def load_model():
    if MODEL_PATH.exists():
        obj = joblib.load(MODEL_PATH)
        return obj['model'], obj.get('features')
    return None, None


def forecast_destination_series(dest_name, history_df, steps=6):
    """history_df: rows for a single destination sorted by year_month with column 'footfall'"""
    model, features = load_model()
    if model is None:
        return None
    history = history_df.sort_values('year_month')
    last = history['footfall'].values.tolist()
    results = []
    # prepare static features
    static = history.iloc[-1:][['crowd_index','hotel_occupancy','eco_score']].to_dict('records')[0]
    for _ in range(steps):
        lags = {}
        for i in range(1,7):
            lags[f'lag_{i}'] = last[-i] if len(last) >= i else last[0]
        row = [lags[f'lag_{i}'] for i in range(1,7)] + [static['crowd_index'], static['hotel_occupancy'], static['eco_score']]
        pred = model.predict([row])[0]
        results.append(float(max(0, pred)))
        last.append(pred)
    return results
