import shap
import matplotlib.pyplot as plt
from io import BytesIO


def explain_model(model, X_sample):
    """Return SHAP Explanation object for a model and a sample matrix."""
    try:
        explainer = shap.Explainer(model)
        shap_values = explainer(X_sample)
        return shap_values
    except Exception:
        return None


def render_shap_waterfall_png(shap_values, row_index: int = 0, max_display: int = 10):
    """Render a SHAP waterfall for a single row to PNG bytes."""
    try:
        plt.clf()
        # shap expects an Explanation for a single row
        sv = shap_values[row_index]
        # limit display
        shap.plots.waterfall(sv, max_display=max_display, show=False)
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


def summarize_shap_explanation(shap_values, feature_names, row_index: int = 0, top_pos: int = 3, top_neg: int = 2):
    """Return short textual summary from SHAP contributions for a row.

    Returns a tuple (positives_list, negatives_list).
    """
    try:
        vals = shap_values.values[row_index]
        contribs = dict(zip(feature_names, vals.tolist()))
        sorted_feats = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
        positives = [f"{k}: {v:.2f}" for k, v in sorted_feats if v > 0][:top_pos]
        negatives = [f"{k}: {v:.2f}" for k, v in sorted_feats if v < 0][:top_neg]
        return positives, negatives
    except Exception:
        return [], []


def generate_consumer_sentences(positives, negatives):
    """Turn lists of 'feature: value' into short consumer-friendly sentences."""
    sentences = []
    try:
        for p in positives:
            # p format: 'feature: value'
            if ':' in p:
                f, v = p.split(':', 1)
                f = f.strip()
                v = float(v.strip())
            else:
                f = p.strip(); v = None
            if f in ('crowd_index', 'crowd'):
                sentences.append('Lower crowding improves suitability')
            elif f in ('eco_score', 'eco'):
                sentences.append('High sustainability / eco score')
            elif f in ('womens_safety', 'safety'):
                sentences.append('Strong safety indicators')
            elif f in ('overall_rating','rating'):
                sentences.append('High overall rating')
            elif f in ('hotel_occupancy','hotel_occupancy_rate'):
                sentences.append('Hotels nearby have good availability')
            else:
                sentences.append(f'{f.replace("_"," ").capitalize()} contributes positively')
        for n in negatives:
            if ':' in n:
                f, v = n.split(':', 1)
                f = f.strip()
            else:
                f = n.strip()
            if f in ('weather_risk','weather'):
                sentences.append('Weather risk may reduce attractiveness')
            elif f in ('transport_cost','price_usd','budget'):
                sentences.append('Higher travel or local cost reduces fit')
            elif f in ('crowd_index', 'crowd'):
                sentences.append('Higher crowding reduces suitability')
            else:
                sentences.append(f'{f.replace("_"," ").capitalize()} is a negative factor')
        return sentences
    except Exception:
        return []
