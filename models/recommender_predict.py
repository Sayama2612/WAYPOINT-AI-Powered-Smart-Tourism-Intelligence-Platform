from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import shap

MODEL_PATH = Path(__file__).parent / 'recommender_model.joblib'


def load_model():
    if MODEL_PATH.exists():
        obj = joblib.load(MODEL_PATH)
        pre = obj.get('preprocessor')
        model = obj.get('model')
        features = obj.get('features')
        return pre, model, features
    return None, None, None


def predict_scores(df: pd.DataFrame):
    pre, model, features = load_model()
    if model is None:
        return None
    X = df[features]
    X_proc = pre.transform(X)
    preds = model.predict(X_proc)
    return np.array(preds)


def explain_instance(row: pd.Series):
    pre, model, features = load_model()
    if model is None:
        return None
    X = pd.DataFrame([row[features]])
    X_proc = pre.transform(X)
    try:
        explainer = shap.Explainer(model)
        shap_values = explainer(X_proc)
        # shap_values.values shape: (1, n_features)
        vals = shap_values.values[0]
        feature_contribs = dict(zip(features, vals.tolist()))
        base = float(shap_values.base_values[0]) if hasattr(shap_values, 'base_values') else None
        return {'base_value': base, 'contribs': feature_contribs}
    except Exception:
        return None
