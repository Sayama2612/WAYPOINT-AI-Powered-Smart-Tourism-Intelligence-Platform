"""Train a travel cost prediction model using synthetic trip samples per destination.
Run: python3 models/train_cost.py
Saves models/cost_model.joblib
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib

BASE = Path(__file__).parent
DATA_PATH = BASE.parent / 'dataset' / 'destinations.csv'
MODEL_OUT = BASE / 'cost_model.joblib'


def synthesize_samples(df, samples_per_dest=10):
    rows = []
    for _, r in df.iterrows():
        for _ in range(samples_per_dest):
            trip_days = int(max(1, np.random.poisson(5)))
            travelers = int(max(1, np.random.choice([1,2,3,4,5])))
            transport_multiplier = np.random.choice([1.0, 1.2, 0.8])
            # base costs
            hotel = max(20, float(r['hotel_cost']))
            transport = max(10, float(r['transport_cost'])) * transport_multiplier
            food = max(5, float(r['food_cost']))
            activities_cost = np.random.uniform(10, 200)
            taxes = 0.1 * (hotel * trip_days + transport + food * trip_days + activities_cost)
            total = (hotel * trip_days * travelers) + transport * travelers + (food * trip_days * travelers) + activities_cost + taxes
            rows.append({
                'destination_name': r['destination_name'],
                'hotel_cost': hotel, 'transport_cost': transport, 'food_cost': food,
                'trip_days': trip_days, 'travelers': travelers, 'activities_cost': activities_cost,
                'taxes': taxes, 'budget': r.get('budget', 0), 'crowd_index': r.get('crowd_index',50),
                'womens_safety': r.get('womens_safety',50), 'eco_score': r.get('eco_score',50),
                'total_cost': total
            })
    return pd.DataFrame(rows)


def train():
    df = pd.read_csv(DATA_PATH)
    samples = synthesize_samples(df, samples_per_dest=8)
    features = ['hotel_cost','transport_cost','food_cost','trip_days','travelers','activities_cost','budget','crowd_index','womens_safety','eco_score']
    X = samples[features]
    y = samples['total_cost']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.18, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    joblib.dump({'model': model, 'features': features}, MODEL_OUT)
    print('Saved cost model to', MODEL_OUT, 'RMSE:', rmse)


if __name__ == '__main__':
    train()
