import math
from typing import List, Dict
import pandas as pd


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def suggest_alternatives(dest_name: str, df: pd.DataFrame, topn: int = 5, max_distance_km: float = 300.0) -> List[Dict]:
    """Suggest alternatives to avoid overtourism: prefer lower crowd_index, similar activities, within distance.

    Returns list of dicts with candidate info and a composite score.
    """
    if dest_name not in df['destination_name'].values:
        return []
    src = df[df['destination_name'] == dest_name].iloc[0]
    candidates = df[df['destination_name'] != dest_name].copy()
    lat1, lon1 = float(src['latitude']), float(src['longitude'])
    src_acts = set(str(src.get('activities','')).split(';'))

    rows = []
    for _, r in candidates.iterrows():
        try:
            lat2, lon2 = float(r['latitude']), float(r['longitude'])
        except Exception:
            continue
        dist = haversine(lat1, lon1, lat2, lon2)
        if dist > max_distance_km:
            continue
        # crowd improvement (higher is better)
        crowd_improve = max(0, src['crowd_index'] - r['crowd_index']) / 100.0
        # activity similarity
        acts = set(str(r.get('activities','')).split(';'))
        inter = len(src_acts & acts)
        union = len(src_acts | acts) if len(src_acts | acts) > 0 else 1
        sim = inter / union
        # composite score: prefer lower crowd and activity similarity and shorter distance
        score = 0.6 * crowd_improve + 0.3 * sim + 0.1 * max(0, 1 - dist / max_distance_km)
        rows.append({'destination_name': r['destination_name'], 'state': r['state'], 'country': r['country'], 'distance_km': round(dist,1), 'crowd_index': r['crowd_index'], 'activities': r['activities'], 'score': round(score,4)})

    out = sorted(rows, key=lambda x: x['score'], reverse=True)
    return out[:topn]
