"""
Generate a synthetic tourism dataset with at least 500 realistic records.
Run: python3 dataset/generate_dataset.py
"""
import csv
import random
from pathlib import Path

COUNTRIES = [
    ("India", ["Goa","Himachal Pradesh","Kerala","Tamil Nadu","Maharashtra","Rajasthan","Uttarakhand"]),
    ("Nepal", ["Gandaki","Bagmati","Lumbini"]),
    ("Japan", ["Hokkaido","Okinawa","Kyoto"]),
    ("Thailand", ["Chiang Mai","Phuket","Krabi"]),
    ("Spain", ["Catalonia","Andalusia","Madrid"]),
    ("USA", ["California","Colorado","Hawaii"]),
]

CLIMATES = ["Tropical","Temperate","Arid","Continental","Mediterranean"]
SEASONS = ["Winter","Spring","Summer","Autumn","Monsoon"]
ACTIVITIES = [
    "beach","trekking","wildlife","historical","cultural","food","scuba","skiing","relaxation","adventure"
]

def random_lat_lon(country_idx):
    # disperse lat/lon by country index
    base_lat = 10 + country_idx * 10
    base_lon = 70 + country_idx * 5
    return round(base_lat + random.uniform(-6,6),6), round(base_lon + random.uniform(-8,8),6)

def make_row(i):
    country_idx = random.randrange(len(COUNTRIES))
    country, states = COUNTRIES[country_idx]
    state = random.choice(states)
    name = f"{state} Spot {i}"
    lat, lon = random_lat_lon(country_idx)
    climate = random.choice(CLIMATES)
    best_season = random.choice(SEASONS)
    avg_temp = round(random.uniform(8,34),1)
    hotel_cost = int(random.gauss(70,30))
    transport_cost = int(abs(random.gauss(40,20)))
    food_cost = int(abs(random.gauss(25,10)))
    crowd_index = round(min(max(random.gauss(50,20),0),100),1)
    weather_risk = round(min(max(random.gauss(30,15),0),100),1)
    crime_rate = round(min(max(random.gauss(35,20),0),100),1)
    womens_safety = round(min(max(100 - crime_rate + random.gauss(0,10),0),100),1)
    family_score = round(min(max(60 + random.gauss(0,20),0),100),1)
    eco_score = round(min(max(random.gauss(50,20),0),100),1)
    carbon_score = round(min(max(random.gauss(60,25),0),100),1)
    activities = ";".join(random.sample(ACTIVITIES, k=random.randint(1,4)))
    tourist_footfall = int(max(50, abs(int(random.gauss(10000,8000)))))
    hotel_occupancy = round(min(max(random.gauss(65,20),10),100),1)
    travel_duration = round(abs(random.gauss(4,6)),1)
    overall_rating = round(min(max(random.gauss(4.0,0.6),1.0),5.0),2)
    budget = int(hotel_cost + transport_cost + food_cost) * 3
    return [
        name, state, country, lat, lon, budget, climate, best_season, avg_temp,
        hotel_cost, transport_cost, food_cost, crowd_index, weather_risk, crime_rate,
        womens_safety, family_score, eco_score, carbon_score, activities,
        tourist_footfall, hotel_occupancy, travel_duration, overall_rating
    ]

def main():
    out = Path(__file__).parent / "destinations.csv"
    headers = [
        "destination_name","state","country","latitude","longitude","budget",
        "climate","best_season","avg_temperature","hotel_cost","transport_cost","food_cost",
        "crowd_index","weather_risk","crime_rate","womens_safety","family_score","eco_score",
        "carbon_score","activities","tourist_footfall","hotel_occupancy","travel_duration","overall_rating"
    ]
    n = 500
    with open(out, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(1, n+1):
            writer.writerow(make_row(i))
    print(f"Generated {n} records at {out}")

if __name__ == '__main__':
    main()
