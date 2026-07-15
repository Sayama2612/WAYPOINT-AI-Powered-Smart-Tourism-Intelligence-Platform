"""Train a global footfall forecasting model using lag features.
Run: python3 models/train_footfall.py
Saves models/footfall_model.joblib
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib

BASE = Path(__file__).parent
DATA_PATH = BASE.parent / 'dataset' / 'time_series.csv'
DEST_PATH = BASE.parent / 'dataset' / 'destinations.csv'
MODEL_OUT = BASE / 'footfall_model.joblib'


def create_lag_features(ts_df, lags=6):
    df = ts_df.copy()
    df_sorted = df.sort_values(['destination_name', 'year_month'])
    for lag in range(1, lags+1):
        df_sorted[f'lag_{lag}'] = df_sorted.groupby('destination_name')['footfall'].shift(lag)
    df_sorted = df_sorted.dropna()
    return df_sorted


def train():
    ts = pd.read_csv(DATA_PATH)
    dest = pd.read_csv(DEST_PATH)
    merged = ts.merge(dest[['destination_name','crowd_index','hotel_occupancy','eco_score']], on='destination_name', how='left')
    df = create_lag_features(merged, lags=6)
    feature_cols = [f'lag_{i}' for i in range(1,7)] + ['crowd_index','hotel_occupancy','eco_score']
    X = df[feature_cols]
    y = df['footfall']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    joblib.dump({'model': model, 'features': feature_cols}, MODEL_OUT)
    print('Saved footfall model to', MODEL_OUT, 'RMSE:', rmse)


if __name__ == '__main__':
    train()
