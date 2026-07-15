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


def estimate_travel_time_hours(distance_km, mode='road'):
    # rough average speeds
    speeds = {'road': 60.0, 'train': 80.0, 'air': 700.0}
    speed = speeds.get(mode, 60.0)
    return distance_km / speed


def plan_itinerary(dest_names: List[str], df: pd.DataFrame, start_index: int = 0,
                   weights: Dict[str, float] = None, max_distance_km: float = 2000.0) -> Dict:
    """Greedy planner: orders given destinations to minimize composite cost.

    weights keys: distance, crowd, weather, rating
    """
    if weights is None:
        weights = {'distance': 0.3, 'crowd': 0.3, 'weather': 0.2, 'rating': -0.2}
    # map names to rows
    rows = df.set_index('destination_name')
    picks = [n for n in dest_names if n in rows.index]
    if not picks:
        return {'error': 'No valid destinations found'}
    current = picks[start_index]
    ordered = [current]
    remaining = [p for p in picks if p != current]
    total_distance = 0.0
    legs = []
    while remaining:
        best = None
        best_score = float('inf')
        lat1 = float(rows.loc[current]['latitude'])
        lon1 = float(rows.loc[current]['longitude'])
        for cand in remaining:
            lat2 = float(rows.loc[cand]['latitude'])
            lon2 = float(rows.loc[cand]['longitude'])
            dist = haversine(lat1, lon1, lat2, lon2)
            if dist > max_distance_km:
                continue
            crowd = rows.loc[cand].get('crowd_index', 50)
            weather = rows.loc[cand].get('weather_risk', 50)
            rating = rows.loc[cand].get('overall_rating', 3.0)
            # normalize heuristics roughly
            dist_norm = dist / (max_distance_km if max_distance_km>0 else 1)
            crowd_norm = crowd / 100.0
            weather_norm = weather / 100.0
            rating_norm = rating / 5.0
            score = (weights['distance'] * dist_norm + weights['crowd'] * crowd_norm +
                     weights['weather'] * weather_norm + weights['rating'] * rating_norm)
            if score < best_score:
                best_score = score
                best = (cand, dist, score)
        if best is None:
            # cannot find next within max_distance; append remaining arbitrarily
            ordered.extend(remaining)
            break
        cand, dist, score = best
        legs.append({'from': current, 'to': cand, 'distance_km': round(dist,1), 'score': round(score,4)})
        total_distance += dist
        ordered.append(cand)
        remaining.remove(cand)
        current = cand

    # compute totals and simple estimates
    est_hours = sum(estimate_travel_time_hours(l['distance_km']) for l in legs)
    return {'ordered': ordered, 'legs': legs, 'total_distance_km': round(total_distance,1), 'est_travel_hours': round(est_hours,1)}
