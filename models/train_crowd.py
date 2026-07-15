"""Train a crowd prediction model on the synthetic dataset and save the model.
Run: python3 models/train_crowd.py
"""
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


BASE = Path(__file__).parent
DATA_PATH = BASE.parent / 'dataset' / 'destinations.csv'
MODEL_OUT = BASE / 'crowd_model.joblib'


def prepare_features(df: pd.DataFrame):
    df = df.copy()
    # Create simple features
    df['log_footfall'] = np.log1p(df['tourist_footfall'])
    df['season'] = df['best_season'].fillna('Unknown')
    df['climate'] = df['climate'].fillna('Unknown')
    return df


def train():
    df = pd.read_csv(DATA_PATH)
    df = prepare_features(df)

    features = ['hotel_cost', 'transport_cost', 'food_cost', 'hotel_occupancy', 'avg_temperature', 'crime_rate', 'weather_risk', 'season', 'climate']
    target = 'crowd_index'

    X = df[features]
    y = df[target]

    numeric_features = ['hotel_cost', 'transport_cost', 'food_cost', 'hotel_occupancy', 'avg_temperature', 'crime_rate', 'weather_risk']
    categorical_features = ['season', 'climate']

    preproc = ColumnTransformer([
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ])

    model = Pipeline([
        ('pre', preproc),
        ('est', RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1))
    ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)

    # Save model and metadata
    joblib.dump({'model': model, 'features': features}, MODEL_OUT)
    print('Saved crowd model to', MODEL_OUT)


if __name__ == '__main__':
    train()
