from pathlib import Path
import joblib
import pandas as pd
import numpy as np

MODEL_PATH = Path(__file__).parent / 'cost_model.joblib'


def load_model():
    if MODEL_PATH.exists():
        obj = joblib.load(MODEL_PATH)
        return obj.get('model'), obj.get('features')
    return None, None


def predict_cost_for_destination(row: pd.Series, trip_days: int, travelers: int, transport_multiplier: float = 1.0):
    model, features = load_model()
    if model is None:
        return None
    hotel = float(row['hotel_cost'])
    transport = float(row['transport_cost']) * transport_multiplier
    food = float(row['food_cost'])
    activities_cost = np.mean([10, 200])
    X = pd.DataFrame([{ 'hotel_cost': hotel, 'transport_cost': transport, 'food_cost': food, 'trip_days': trip_days, 'travelers': travelers, 'activities_cost': activities_cost, 'budget': row.get('budget',0), 'crowd_index': row.get('crowd_index',50), 'womens_safety': row.get('womens_safety',50), 'eco_score': row.get('eco_score',50)}])
    pred = model.predict(X)[0]
    return float(pred)
