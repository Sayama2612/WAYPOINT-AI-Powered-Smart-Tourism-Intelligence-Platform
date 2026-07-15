"""Generate synthetic monthly footfall time-series per destination.
Outputs dataset/time_series.csv with monthly footfall for past 36 months.
Run: python3 data/temporal_generator.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
DATA_PATH = BASE.parent / 'dataset' / 'destinations.csv'
OUT_PATH = BASE.parent / 'dataset' / 'time_series.csv'


def seasonal_factor(month):
    # simple seasonality: peaks in months 5-9
    return 1.0 + 0.5 * np.sin((month - 1) / 12.0 * 2 * np.pi)


def main(months=36):
    df = pd.read_csv(DATA_PATH)
    rows = []
    now = datetime.now()
    for _, r in df.iterrows():
        base = max(50, r.get('tourist_footfall', 1000) / 50)
        trend = np.random.uniform(-0.02, 0.05)  # small trend
        noise_scale = max(0.05, 1 - r.get('eco_score',50)/100)
        for i in range(months):
            dt = now.replace(day=1) - pd.DateOffset(months=months - i - 1)
            month = dt.month
            season = seasonal_factor(month)
            crowd_influence = (100 - r.get('crowd_index',50))/100
            value = base * (1 + trend * i) * season * (1 + np.random.normal(0, 0.1*noise_scale))
            value *= (1 + (r.get('crowd_index',50)-50)/200)
            rows.append({
                'destination_name': r['destination_name'],
                'year_month': dt.strftime('%Y-%m'),
                'month_index': i,
                'footfall': max(0, int(value))
            })

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print('Wrote', OUT_PATH)


if __name__ == '__main__':
    main()
