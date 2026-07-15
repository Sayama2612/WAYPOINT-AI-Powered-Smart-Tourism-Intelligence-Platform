"""Train a blended recommender model using destination features and a synthetic suitability target.
Saves models/recommender_model.joblib

Run: python3 models/train_recommender.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib

BASE = Path(__file__).parent
DATA_PATH = BASE.parent / 'dataset' / 'destinations.csv'
MODEL_OUT = BASE / 'recommender_model.joblib'


def build_synthetic_target(df: pd.DataFrame) -> pd.Series:
    # Compose a synthetic suitability score (0-100) as a proxy target
    # Higher rating, lower crowd, higher safety, higher eco, lower budget penalty
    rating = df['overall_rating'].fillna(df['overall_rating'].median()) / 5.0
    crowd = (100 - df['crowd_index'].fillna(50)) / 100.0
    safety = df['womens_safety'].fillna(50) / 100.0
    eco = df['eco_score'].fillna(50) / 100.0
    budget = df['budget'].fillna(df['budget'].median())
    budget_norm = (budget - budget.min()) / (budget.max() - budget.min() + 1e-9)
    # weights chosen to emphasize rating, crowd avoidance, safety
    score = (0.45 * rating + 0.25 * crowd + 0.18 * safety + 0.07 * eco + 0.05 * (1 - budget_norm))
    return (score * 100).clip(0,100)


def prepare_features(df: pd.DataFrame):
    df = df.copy()
    features = [
        'hotel_cost','transport_cost','food_cost','avg_temperature','crowd_index','weather_risk',
        'crime_rate','womens_safety','family_score','eco_score','carbon_score','hotel_occupancy','tourist_footfall','overall_rating'
    ]
    X = df[features].copy()
    # impute and scale will be handled in pipeline
    return X, features


def train():
    df = pd.read_csv(DATA_PATH)
    y = build_synthetic_target(df)
    X, feature_names = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.18, random_state=42)

    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
    ])

    X_train_proc = pipeline.fit_transform(X_train)
    X_test_proc = pipeline.transform(X_test)

    # Try XGBoost first, fallback to RandomForest
    try:
        import xgboost as xgb
        model = xgb.XGBRegressor(n_estimators=200, tree_method='hist', random_state=42)
        model.fit(X_train_proc, y_train)
    except Exception:
        model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        model.fit(X_train_proc, y_train)

    preds = model.predict(X_test_proc)
    rmse = np.sqrt(mean_squared_error(y_test, preds))

    # Save pipeline, model, and metadata
    joblib.dump({'preprocessor': pipeline, 'model': model, 'features': feature_names}, MODEL_OUT)
    print('Saved recommender model to', MODEL_OUT, 'RMSE:', rmse)


if __name__ == '__main__':
    train()
