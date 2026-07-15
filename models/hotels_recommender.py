"""Simple hotels recommender that synthesizes a hotels dataset if missing
and recommends hotels for a selected destination based on proximity, rating, and price.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import math

BASE = Path(__file__).parent
DATA_DIR = BASE.parent / 'dataset'
HOTELS_CSV = DATA_DIR / 'hotels.csv'


def haversine_km(lat1, lon1, lat2, lon2):
    # approximate haversine distance in km
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def ensure_hotels_dataset(destinations_csv: str = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if HOTELS_CSV.exists():
        return HOTELS_CSV
    # generate synthetic hotels from destinations
    dest_path = DATA_DIR / 'destinations.csv'
    if destinations_csv:
        dest_path = Path(destinations_csv)
    if not dest_path.exists():
        raise FileNotFoundError('destinations.csv not found to synthesize hotels')
    df = pd.read_csv(dest_path)
    rows = []
    for _, r in df.iterrows():
        base_lat = float(r.get('latitude', 0))
        base_lon = float(r.get('longitude', 0))
        dest_name = r['destination_name']
        for i in range(3):
            jitter = np.random.normal(scale=0.02)
            lat = base_lat + jitter
            lon = base_lon + np.random.normal(scale=0.02)
            rating = round(max(2.5, min(5.0, np.random.normal(loc=4.0, scale=0.5))), 1)
            price = int(max(30, np.random.normal(loc=100, scale=40)))
            name = f"{dest_name} Hotel {i+1}"
            rows.append({'hotel_name': name, 'destination_name': dest_name, 'latitude': lat, 'longitude': lon, 'rating': rating, 'price_usd': price})
    hdf = pd.DataFrame(rows)
    hdf.to_csv(HOTELS_CSV, index=False)
    return HOTELS_CSV


def load_hotels():
    ensure_hotels_dataset()
    return pd.read_csv(HOTELS_CSV)


def recommend_hotels(destination_name: str, topn: int = 5):
    df_hotels = load_hotels()
    df_dest = pd.read_csv(DATA_DIR / 'destinations.csv')
    r = df_dest[df_dest['destination_name'] == destination_name]
    if r.empty:
        return []
    r = r.iloc[0]
    lat0 = float(r['latitude'])
    lon0 = float(r['longitude'])
    # compute distance
    df_hotels['distance_km'] = df_hotels.apply(lambda x: haversine_km(lat0, lon0, float(x['latitude']), float(x['longitude'])), axis=1)
    # normalize price and distance
    max_price = max(1, df_hotels['price_usd'].max())
    max_dist = max(1, df_hotels['distance_km'].max())
    df_hotels['price_norm'] = df_hotels['price_usd'] / max_price
    df_hotels['dist_norm'] = df_hotels['distance_km'] / max_dist
    # score: higher rating good, lower price & distance good
    df_hotels['score'] = df_hotels['rating'] * 2.0 - 3.0 * df_hotels['price_norm'] - 2.0 * df_hotels['dist_norm']
    out = df_hotels.sort_values('score', ascending=False).head(topn)
    return out.to_dict(orient='records')


if __name__ == '__main__':
    ensure_hotels_dataset()
    print('Generated hotels:', HOTELS_CSV)
