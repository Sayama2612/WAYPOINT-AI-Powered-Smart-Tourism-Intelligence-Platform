"""Train a simple personalized classifier from feedback (like/dislike).
Saves models/personalized_model.joblib
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

BASE = Path(__file__).parent
# ensure repo root is on sys.path for imports when run as a script
ROOT = BASE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.db import list_feedback
DATA_PATH = BASE.parent / 'dataset' / 'destinations.csv'
MODEL_OUT = BASE / 'personalized_model.joblib'


def build_training_data():
    fb = list_feedback(limit=10000)
    if not fb:
        return None, None
    df = pd.read_csv(DATA_PATH)
    rows = []
    for f in fb:
        dest = f['destination_name']
        label = 1 if f['feedback'] == 'like' else 0
        r = df[df['destination_name'] == dest]
        if r.empty:
            continue
        r = r.iloc[0]
        rows.append({
            'hotel_cost': r['hotel_cost'], 'transport_cost': r['transport_cost'], 'food_cost': r['food_cost'],
            'crowd_index': r['crowd_index'], 'womens_safety': r['womens_safety'], 'eco_score': r['eco_score'],
            'overall_rating': r['overall_rating'], 'label': label
        })
    if not rows:
        return None, None
    tdf = pd.DataFrame(rows)
    X = tdf.drop(columns=['label'])
    y = tdf['label']
    return X, y


def train():
    X, y = build_training_data()
    if X is None:
        print('No feedback data found to train personalized model.')
        return
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    joblib.dump({'model': clf, 'features': X.columns.tolist()}, MODEL_OUT)
    print('Saved personalized model to', MODEL_OUT, 'Accuracy:', acc)


if __name__ == '__main__':
    train()
