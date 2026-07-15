from math import radians, sin, cos, sqrt, atan2
from typing import List, Dict


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


# Emission factors (kg CO2 per passenger-km roughly)
EMISSION_FACTORS = {
    'air_short': 0.255,
    'air_long': 0.195,
    'car': 0.12,
    'train': 0.041,
    'bus': 0.05
}


def transport_emissions(distance_km: float, mode: str = 'car', travelers: int = 1) -> float:
    """Estimate transport emissions (kg CO2) for given distance, mode and travelers."""
    mode = mode.lower()
    if mode == 'air':
        # heuristic: short vs long haul
        factor = EMISSION_FACTORS['air_short'] if distance_km < 1500 else EMISSION_FACTORS['air_long']
    else:
        factor = EMISSION_FACTORS.get(mode, EMISSION_FACTORS['car'])
    return distance_km * factor * travelers


def accommodation_emissions(nights: int, travelers: int = 1, per_night_per_person: float = 15.0) -> float:
    """Estimate accommodation emissions (kg CO2). Default 15 kg CO2 per person per night."""
    return nights * travelers * per_night_per_person


def trip_emissions(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, mode: str = 'car', travelers: int =1, nights: int = 3) -> Dict:
    dist = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    transport = transport_emissions(dist, mode=mode, travelers=travelers)
    accom = accommodation_emissions(nights, travelers)
    total = transport + accom
    return {'distance_km': round(dist,1), 'transport_kg': round(transport,1), 'accommodation_kg': round(accom,1), 'total_kg': round(total,1)}


def greener_alternatives(dest_name: str, df, origin_lat: float, origin_lon: float, mode='car', travelers=1, nights=3, topn=5, max_distance_km=2000):
    if dest_name not in df['destination_name'].values:
        return []
    src = df[df['destination_name'] == dest_name].iloc[0]
    candidates = df[df['destination_name'] != dest_name].copy()
    rows = []
    for _, r in candidates.iterrows():
        try:
            dest_lat = float(r['latitude'])
            dest_lon = float(r['longitude'])
        except Exception:
            continue
        em = trip_emissions(origin_lat, origin_lon, dest_lat, dest_lon, mode=mode, travelers=travelers, nights=nights)
        # also consider dataset eco_score and crowd_index
        eco = r.get('eco_score', 50)
        crowd = r.get('crowd_index', 50)
        score = em['total_kg'] * (1 - eco/200.0) * (1 + crowd/200.0)
        dist = em['distance_km']
        if dist > max_distance_km:
            continue
        rows.append({'destination_name': r['destination_name'], 'country': r['country'], 'distance_km': dist, 'total_kg': em['total_kg'], 'eco_score': eco, 'crowd_index': crowd, 'score': round(score,2)})
    out = sorted(rows, key=lambda x: x['total_kg'])
    return out[:topn]
