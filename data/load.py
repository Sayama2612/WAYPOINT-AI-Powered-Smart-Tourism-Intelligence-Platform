import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

def load_dataset(path=None):
    if path is None:
        path = BASE / "dataset" / "destinations.csv"
    df = pd.read_csv(path)
    return df
